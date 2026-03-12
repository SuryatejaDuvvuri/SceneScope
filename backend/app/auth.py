"""
Authentication utilities
────────────────────────
JWT creation / verification and the FastAPI `get_current_user` dependency.
"""

import uuid
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.config import settings
from app.db import get_db

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

security = HTTPBearer()


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str) -> str:
    """Return user_id from token or raise."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """FastAPI dependency – extracts & validates JWT, returns user row as dict."""
    user_id = verify_access_token(credentials.credentials)
    db = await get_db()
    try:
        row = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = await row.fetchone()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return dict(user)
    finally:
        await db.close()


async def get_or_create_user(email: str, name: str | None, avatar_url: str | None, provider: str, provider_id: str) -> dict:
    """Find existing user by email or create a new one. Returns user dict."""
    db = await get_db()
    try:
        row = await db.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = await row.fetchone()
        if user:
            # Update name/avatar in case they changed
            await db.execute(
                "UPDATE users SET name = ?, avatar_url = ?, updated_at = datetime('now') WHERE id = ?",
                (name or user["name"], avatar_url or user["avatar_url"], user["id"]),
            )
            await db.commit()
            row = await db.execute("SELECT * FROM users WHERE id = ?", (user["id"],))
            user = await row.fetchone()
            return dict(user)

        user_id = uuid.uuid4().hex
        await db.execute(
            "INSERT INTO users (id, email, name, avatar_url, provider, provider_id) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, email, name, avatar_url, provider, provider_id),
        )
        await db.commit()
        row = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return dict(await row.fetchone())
    finally:
        await db.close()
