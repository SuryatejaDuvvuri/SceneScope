"""
Auth Routes
───────────
Google OAuth login flow + user info endpoint.

Flow:
  1. Frontend navigates to  GET /api/auth/google
  2. Backend redirects → Google consent screen
  3. Google redirects → GET /api/auth/google/callback
  4. Backend creates/finds user, mints JWT
  5. Redirects to frontend:  {FRONTEND_URL}/auth/callback?token=xxx
"""

from urllib.parse import urlencode
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
import httpx

from app.config import settings
from app.auth import create_access_token, get_current_user, get_or_create_user

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def _callback_url(request: Request) -> str:
    """Build the OAuth redirect_uri.

    Prefer BACKEND_PUBLIC_URL when configured so the URI is stable and matches
    exactly what's registered in the Google Cloud Console (behind a proxy like
    Render/Cloudflare, request.url_for can otherwise emit http:// or the wrong
    host). Fall back to request-derived URL for local dev.
    """
    base = (settings.BACKEND_PUBLIC_URL or "").rstrip("/")
    if base:
        return f"{base}/api/auth/google/callback"
    return str(request.url_for("google_callback"))


@router.get("/google")
async def google_login(request: Request):
    """Redirect user to Google OAuth consent screen."""
    callback_url = _callback_url(request)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request, code: str):
    """Exchange auth code for tokens, create/find user, redirect with JWT."""
    callback_url = _callback_url(request)

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": callback_url,
        })
        token_data = token_resp.json()

        if "access_token" not in token_data:
            return RedirectResponse(f"{settings.FRONTEND_URL}/auth/callback?error=token_exchange_failed")

        # Fetch user info from Google
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        userinfo = userinfo_resp.json()

    if "email" not in userinfo:
        return RedirectResponse(f"{settings.FRONTEND_URL}/auth/callback?error=no_email")

    # Create or find user
    user = await get_or_create_user(
        email=userinfo["email"],
        name=userinfo.get("name"),
        avatar_url=userinfo.get("picture"),
        provider="google",
        provider_id=userinfo.get("id", ""),
    )

    # Mint JWT and redirect to frontend
    token = create_access_token(user["id"])
    return RedirectResponse(f"{settings.FRONTEND_URL}/auth/callback?token={token}")


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Return current authenticated user info."""
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "avatar_url": user["avatar_url"],
    }
