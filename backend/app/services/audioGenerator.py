"""
Audio Dialogue Generation Service
──────────────────────────────────
Generates character-voiced audio for screenplay dialogue using ElevenLabs TTS.
Auto-assigns distinct voices to characters and generates MP3 audio per scene.
"""

import os
import uuid
import hashlib
from pathlib import Path
from typing import Optional

import requests

from app.config import settings
from app.db import get_db, to_json


# Pre-made ElevenLabs voices for auto-assignment.
# Mix of genders, ages, and accents for character variety.
PREMADE_VOICES = [
    {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "gender": "female"},
    {"voice_id": "29vD33N1CtxCmqQRPOHJ", "name": "Drew", "gender": "male"},
    {"voice_id": "2EiwWnXFnvU5JabPnv8n", "name": "Clyde", "gender": "male"},
    {"voice_id": "5Q0t7uMcjvnagumLfvZi", "name": "Paul", "gender": "male"},
    {"voice_id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "gender": "female"},
    {"voice_id": "CYw3kZ02Hs0563khs1Fj", "name": "Dave", "gender": "male"},
    {"voice_id": "D38z5RcWu1voky8WS1ja", "name": "Fin", "gender": "male"},
    {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "gender": "female"},
    {"voice_id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "gender": "male"},
    {"voice_id": "GBv7mTt0atIp3Br8iCZE", "name": "Thomas", "gender": "male"},
    {"voice_id": "IKne3meq5aSn9XLyUdCD", "name": "Charlie", "gender": "male"},
    {"voice_id": "JBFqnCBsd6RMkjVDRZzb", "name": "George", "gender": "male"},
    {"voice_id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli", "gender": "female"},
    {"voice_id": "N2lVS1w4EtoT3dr4eOWO", "name": "Callum", "gender": "male"},
    {"voice_id": "ODq5zmih8GrVes37Dizd", "name": "Patrick", "gender": "male"},
    {"voice_id": "SOYHLrjzK2X1ezoPC6cr", "name": "Harry", "gender": "male"},
    {"voice_id": "TX3LPaxmHKxFdv7VOQHJ", "name": "Liam", "gender": "male"},
    {"voice_id": "ThT5KcBeYPX3keUQqHPh", "name": "Dorothy", "gender": "female"},
    {"voice_id": "VR6AewLTigWG4xSOukaG", "name": "Arnold", "gender": "male"},
    {"voice_id": "XB0fDUnXU5powFXDhCwa", "name": "Charlotte", "gender": "female"},
    {"voice_id": "Xb7hH8MSUJpSbSDYk0k2", "name": "Alice", "gender": "female"},
    {"voice_id": "XrExE9yKIg1WjnnlVkGX", "name": "Matilda", "gender": "female"},
    {"voice_id": "bIHbv24MWmeRgasZH58o", "name": "Will", "gender": "male"},
    {"voice_id": "cgSgspJ2msm6clMCkdW9", "name": "Jessica", "gender": "female"},
    {"voice_id": "cjVigY5qzO86Huf0OWal", "name": "Eric", "gender": "male"},
    {"voice_id": "iP95p4xoKVk53GoZ742B", "name": "Chris", "gender": "male"},
    {"voice_id": "nPczCjzI2devNBz1zQrb", "name": "Brian", "gender": "male"},
    {"voice_id": "onwK4e9ZLuTAKqWW03F9", "name": "Daniel", "gender": "male"},
    {"voice_id": "pFZP5JQG7iQjIQuC4Bku", "name": "Lily", "gender": "female"},
    {"voice_id": "pqHfZKP75CvOlQylNhV4", "name": "Bill", "gender": "male"},
]


def _deterministic_voice_index(character_name: str) -> int:
    """Hash character name to get a deterministic voice index."""
    h = hashlib.md5(character_name.upper().encode()).hexdigest()
    return int(h, 16) % len(PREMADE_VOICES)


async def get_or_assign_voice(project_id: str, character_name: str) -> str:
    """Get existing voice assignment or auto-assign one deterministically."""
    db = await get_db()
    try:
        row = await db.execute(
            "SELECT voice_id FROM character_voices WHERE project_id = ? AND character_name = ?",
            (project_id, character_name)
        )
        existing = await row.fetchone()
        if existing:
            return existing["voice_id"]

        # Auto-assign based on character name hash
        idx = _deterministic_voice_index(character_name)
        voice = PREMADE_VOICES[idx]
        voice_id = voice["voice_id"]

        cv_id = uuid.uuid4().hex
        await db.execute(
            "INSERT OR IGNORE INTO character_voices (id, project_id, character_name, voice_id) VALUES (?, ?, ?, ?)",
            (cv_id, project_id, character_name, voice_id)
        )
        await db.commit()
        return voice_id
    finally:
        await db.close()


def _generate_tts(text: str, voice_id: str) -> bytes:
    """Call ElevenLabs TTS API and return raw MP3 bytes."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.5,
            "use_speaker_boost": True,
        },
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code == 401:
        raise RuntimeError("ElevenLabs auth failed (401). Check ELEVENLABS_API_KEY.")
    if response.status_code >= 400:
        raise RuntimeError(f"ElevenLabs API HTTP {response.status_code}: {response.text[:200]}")

    return response.content


async def generate_scene_audio(
    scene_id: str,
    project_id: str,
    dialogue_lines: list[dict],
) -> dict:
    """Generate audio for all dialogue lines in a scene.

    Returns dict with audio_url, dialogue_data, total_duration_ms.
    """
    if not settings.ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY not configured")

    if not dialogue_lines:
        raise ValueError("No dialogue lines to generate audio for")

    # Build audio for each line
    audio_chunks: list[bytes] = []
    for line in dialogue_lines:
        voice_id = await get_or_assign_voice(project_id, line["character"])
        # Prepend parenthetical as direction if present
        text = line["text"]
        if line.get("parenthetical"):
            text = f"({line['parenthetical']}) {text}"
        chunk = _generate_tts(text, voice_id)
        audio_chunks.append(chunk)

    # Concatenate MP3 chunks (simple concatenation works for MP3)
    combined = b"".join(audio_chunks)

    # Save to audio directory
    audio_dir = Path(settings.AUDIO_DIR) / scene_id
    audio_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.mp3"
    filepath = audio_dir / filename
    filepath.write_bytes(combined)

    audio_url = f"/static/audio/{scene_id}/{filename}"

    # Estimate duration (~128kbps MP3: bytes * 8 / 128000 * 1000 = bytes / 16)
    estimated_duration_ms = len(combined) // 16

    # Save to DB
    db = await get_db()
    try:
        audio_id = uuid.uuid4().hex
        await db.execute(
            """INSERT INTO scene_audio (id, scene_id, audio_url, dialogue_data, total_duration_ms)
               VALUES (?, ?, ?, ?, ?)""",
            (audio_id, scene_id, audio_url, to_json(dialogue_lines), estimated_duration_ms)
        )
        await db.commit()
    finally:
        await db.close()

    return {
        "id": audio_id,
        "scene_id": scene_id,
        "audio_url": audio_url,
        "dialogue_data": dialogue_lines,
        "total_duration_ms": estimated_duration_ms,
    }
