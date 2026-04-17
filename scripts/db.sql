-- SceneScope Database Schema
-- Run: sqlite3 scenescope.db < scripts/db.sql

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    avatar_url TEXT,
    provider TEXT NOT NULL DEFAULT 'google',   -- oauth provider
    provider_id TEXT NOT NULL,                 -- provider-specific user id
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    genre TEXT,
    time_period TEXT,
    tone TEXT,
    films TEXT,  -- JSON array of reference film names
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scenes (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    scene_number INTEGER NOT NULL,
    heading TEXT,
    description TEXT NOT NULL,
    mood TEXT,                    -- tense | uplifting | somber | action
    mood_confidence REAL,        -- 0.0 - 1.0 from classifier
    vague_elements TEXT,         -- JSON array of strings
    clarifying_questions TEXT,   -- JSON array of strings
    visual_summary TEXT,         -- LLM-generated visual description
    current_iteration_id TEXT,
    locked INTEGER DEFAULT 0,    -- 0 = unlocked, 1 = locked
    visual_context TEXT,         -- JSON: extracted characters/locations/props for consistency
    dialogue TEXT,               -- JSON array: [{character, text, parenthetical}]
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scene_iterations (
    id TEXT PRIMARY KEY,
    scene_id TEXT NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    iteration_number INTEGER NOT NULL,
    prompt_used TEXT NOT NULL,
    answers TEXT,        -- JSON object: {"question": "answer", ...}
    feedback TEXT,       -- freeform user feedback
    sketch_url TEXT,     -- path to generated image
    image_provider TEXT, -- "together" or "openai"
    director_notes TEXT, -- JSON: director agent interpretation + reasoning
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    role TEXT,
    age TEXT,
    description TEXT,
    image_url TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scene_audio (
    id TEXT PRIMARY KEY,
    scene_id TEXT NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    audio_url TEXT NOT NULL,
    dialogue_data TEXT,          -- JSON: the dialogue lines used for generation
    total_duration_ms INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS character_voices (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    character_name TEXT NOT NULL,
    voice_id TEXT NOT NULL,
    voice_provider TEXT DEFAULT 'elevenlabs',
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(project_id, character_name)
);

CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_scenes_project_id ON scenes(project_id);
CREATE INDEX IF NOT EXISTS idx_iterations_scene_id ON scene_iterations(scene_id);
CREATE INDEX IF NOT EXISTS idx_characters_project_id ON characters(project_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);
