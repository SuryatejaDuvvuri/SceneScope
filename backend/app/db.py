import aiosqlite
import json
from pathlib import Path
from app.config import settings

# Path to the SQL schema file
SCHEMA_PATH = Path(__file__).parent.parent.parent / "scripts" / "db.sql"


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(settings.DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    return db


async def init_db():
    db = await get_db()
    try:
        # Only create tables if they don't exist yet (don't wipe data on restart)
        row = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
        if not await row.fetchone():
            schema = SCHEMA_PATH.read_text()
            await db.executescript(schema)
            await db.commit()
    finally:
        await db.close()

def to_json(data) -> str | None:
    if data is None:
        return None
    return json.dumps(data)


def from_json(text: str | None):
    if text is None:
        return None
    return json.loads(text)


def row_to_dict(row: aiosqlite.Row) -> dict:
    """Convert an aiosqlite Row to a plain dict."""
    return dict(row)
