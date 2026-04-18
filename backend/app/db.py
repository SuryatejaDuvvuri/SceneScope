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
        else:
            # Migrations: add users table and user_id column if missing
            row = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not await row.fetchone():
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        email TEXT NOT NULL UNIQUE,
                        name TEXT,
                        avatar_url TEXT,
                        provider TEXT NOT NULL DEFAULT 'google',
                        provider_id TEXT NOT NULL,
                        created_at TEXT DEFAULT (datetime('now')),
                        updated_at TEXT DEFAULT (datetime('now'))
                    )
                """)
                await db.commit()
            # Add user_id column to projects if missing
            cols = await db.execute("PRAGMA table_info(projects)")
            col_names = [c["name"] for c in await cols.fetchall()]
            if "user_id" not in col_names:
                await db.execute("ALTER TABLE projects ADD COLUMN user_id TEXT REFERENCES users(id)")
                await db.commit()

            # Add dialogue column to scenes if missing
            cols = await db.execute("PRAGMA table_info(scenes)")
            col_names = [c["name"] for c in await cols.fetchall()]
            if "dialogue" not in col_names:
                await db.execute("ALTER TABLE scenes ADD COLUMN dialogue TEXT")
                await db.commit()

            # Create scene_audio table if missing
            row = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scene_audio'")
            if not await row.fetchone():
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS scene_audio (
                        id TEXT PRIMARY KEY,
                        scene_id TEXT NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
                        audio_url TEXT NOT NULL,
                        dialogue_data TEXT,
                        total_duration_ms INTEGER,
                        created_at TEXT DEFAULT (datetime('now'))
                    )
                """)
                await db.commit()

            # Add seed column to characters if missing (deterministic per-character image gen)
            cols = await db.execute("PRAGMA table_info(characters)")
            char_cols = [c["name"] for c in await cols.fetchall()]
            if char_cols and "seed" not in char_cols:
                await db.execute("ALTER TABLE characters ADD COLUMN seed INTEGER")
                await db.commit()

            # Create character_voices table if missing
            row = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='character_voices'")
            if not await row.fetchone():
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS character_voices (
                        id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                        character_name TEXT NOT NULL,
                        voice_id TEXT NOT NULL,
                        voice_provider TEXT DEFAULT 'elevenlabs',
                        created_at TEXT DEFAULT (datetime('now')),
                        UNIQUE(project_id, character_name)
                    )
                """)
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
