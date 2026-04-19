"""
Audio Dialogue Generation Service
──────────────────────────────────
Generates character-voiced audio for screenplay dialogue using ElevenLabs TTS.
Auto-assigns distinct voices to characters and generates MP3 audio per scene.
"""

import uuid
import hashlib
import re
from pathlib import Path
from typing import Any

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

VOICE_GENDER_BY_ID = {v["voice_id"]: v["gender"] for v in PREMADE_VOICES}
FEMALE_VOICES = [v for v in PREMADE_VOICES if v["gender"] == "female"]
MALE_VOICES = [v for v in PREMADE_VOICES if v["gender"] == "male"]

FEMALE_TITLE_MARKERS = {
    "MS", "MRS", "MISS", "MADAM", "LADY",
    "MOTHER", "MOM", "MOMMY", "SISTER", "AUNT",
    "GRANDMOTHER", "GRANDMA", "WIFE", "GIRL",
    "WOMAN", "QUEEN", "PRINCESS", "DAUGHTER",
}
MALE_TITLE_MARKERS = {
    "MR", "SIR", "LORD",
    "FATHER", "DAD", "DADDY", "BROTHER", "UNCLE",
    "GRANDFATHER", "GRANDPA", "HUSBAND", "BOY",
    "MAN", "KING", "PRINCE", "SON",
}

FEMALE_PRONOUN_RE = re.compile(r"\b(she|her|hers|herself)\b", re.IGNORECASE)
MALE_PRONOUN_RE = re.compile(r"\b(he|him|his|himself)\b", re.IGNORECASE)


class ElevenLabsPaidVoiceError(RuntimeError):
    """Raised when a selected voice requires a paid ElevenLabs plan."""


def _deterministic_voice_index(character_name: str, modulo: int) -> int:
    """Hash character name to get a deterministic index for a pool size."""
    if modulo <= 0:
        return 0
    h = hashlib.md5(character_name.upper().encode()).hexdigest()
    return int(h, 16) % modulo


def _normalize_character_name(character_name: str) -> str:
    """Normalize screenplay character names for matching."""
    return re.sub(r"\s+", " ", character_name.strip())


def _infer_gender_from_title_markers(character_name: str) -> str | None:
    """Infer gender from generic role/title markers in character name."""
    tokens = re.findall(r"[A-Za-z]+", character_name.upper())
    token_set = set(tokens)
    if token_set & FEMALE_TITLE_MARKERS:
        return "female"
    if token_set & MALE_TITLE_MARKERS:
        return "male"
    return None


def _infer_gender_from_context(character_name: str, scene_context_text: str) -> str | None:
    """Infer gender by scanning nearby context pronouns around character mentions."""
    context = (scene_context_text or "").strip()
    if not context:
        return None

    name = _normalize_character_name(character_name)
    name_re = re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)
    female_hits = 0
    male_hits = 0

    for match in name_re.finditer(context):
        start = max(0, match.start() - 100)
        end = min(len(context), match.end() + 100)
        snippet = context[start:end]
        female_hits += len(FEMALE_PRONOUN_RE.findall(snippet))
        male_hits += len(MALE_PRONOUN_RE.findall(snippet))

    if female_hits > male_hits:
        return "female"
    if male_hits > female_hits:
        return "male"
    return None


def infer_character_gender(character_name: str, scene_context_text: str = "") -> str | None:
    """Infer character gender with lightweight generic heuristics."""
    by_title = _infer_gender_from_title_markers(character_name)
    if by_title:
        return by_title
    return _infer_gender_from_context(character_name, scene_context_text)


def _pick_voice_from_pool(character_name: str, preferred_gender: str | None) -> str:
    """Pick a deterministic voice from the requested gender pool."""
    if preferred_gender == "female" and FEMALE_VOICES:
        pool = FEMALE_VOICES
    elif preferred_gender == "male" and MALE_VOICES:
        pool = MALE_VOICES
    else:
        pool = PREMADE_VOICES

    idx = _deterministic_voice_index(character_name, len(pool))
    return pool[idx]["voice_id"]


async def get_or_assign_voice(project_id: str, character_name: str, preferred_gender: str | None = None) -> str:
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

        # Auto-assign based on character name hash + optional gender hint.
        voice_id = _pick_voice_from_pool(character_name, preferred_gender)

        cv_id = uuid.uuid4().hex
        await db.execute(
            "INSERT OR IGNORE INTO character_voices (id, project_id, character_name, voice_id) VALUES (?, ?, ?, ?)",
            (cv_id, project_id, character_name, voice_id)
        )
        await db.commit()
        return voice_id
    finally:
        await db.close()


async def update_character_voice(project_id: str, character_name: str, voice_id: str) -> None:
    """Persist a replacement voice assignment for future generations."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE character_voices SET voice_id = ? WHERE project_id = ? AND character_name = ?",
            (voice_id, project_id, character_name),
        )
        await db.commit()
    finally:
        await db.close()


def _extract_elevenlabs_error_code(response: requests.Response) -> str:
    """Best-effort parse of ElevenLabs structured error code."""
    try:
        data = response.json()
    except Exception:
        return ""
    detail: Any = data.get("detail") if isinstance(data, dict) else None
    if isinstance(detail, dict):
        return str(detail.get("code", "")).strip()
    return ""


def _pick_fallback_voice_id(assigned_voice_id: str) -> str:
    """Pick a fallback voice that is likely free-plan compatible.

    Priority:
      1) Explicit env override (ELEVENLABS_FALLBACK_VOICE_ID)
      2) Account voices endpoint, excluding library voices
      3) A known premade voice as final fallback
    """
    override = (settings.ELEVENLABS_FALLBACK_VOICE_ID or "").strip()
    if override:
        return override

    headers = {"xi-api-key": settings.ELEVENLABS_API_KEY}
    response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers, timeout=15)
    if response.status_code == 200:
        data = response.json() if response.content else {}
        voices = data.get("voices", []) if isinstance(data, dict) else []

        # Free users cannot use "library" voices via API.
        for voice in voices:
            if not isinstance(voice, dict):
                continue
            voice_id = str(voice.get("voice_id", "")).strip()
            category = str(voice.get("category", "")).strip().lower()
            if voice_id and voice_id != assigned_voice_id and category != "library":
                return voice_id

    # Rachel is broadly available in ElevenLabs examples/docs.
    return "21m00Tcm4TlvDq8ikWAM"


def _needs_gender_reassignment(voice_id: str, preferred_gender: str | None) -> bool:
    """Detect when an existing assignment conflicts with inferred gender."""
    if not preferred_gender:
        return False
    existing_gender = VOICE_GENDER_BY_ID.get(voice_id)
    if not existing_gender:
        return False
    return existing_gender != preferred_gender


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
    if response.status_code == 402:
        code = _extract_elevenlabs_error_code(response)
        if code == "paid_plan_required":
            raise ElevenLabsPaidVoiceError(
                f"Selected ElevenLabs voice '{voice_id}' requires a paid plan."
            )
    if response.status_code >= 400:
        raise RuntimeError(f"ElevenLabs API HTTP {response.status_code}: {response.text[:200]}")

    return response.content


async def generate_scene_audio(
    scene_id: str,
    project_id: str,
    dialogue_lines: list[dict],
    scene_context_text: str = "",
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
        character = line["character"]
        preferred_gender = infer_character_gender(character, scene_context_text)
        voice_id = await get_or_assign_voice(project_id, character, preferred_gender=preferred_gender)
        if _needs_gender_reassignment(voice_id, preferred_gender):
            voice_id = _pick_voice_from_pool(character, preferred_gender)
            await update_character_voice(project_id, character, voice_id)
        # Prepend parenthetical as direction if present
        text = line["text"]
        if line.get("parenthetical"):
            text = f"({line['parenthetical']}) {text}"
        try:
            chunk = _generate_tts(text, voice_id)
        except ElevenLabsPaidVoiceError:
            fallback_voice_id = _pick_fallback_voice_id(voice_id)
            chunk = _generate_tts(text, fallback_voice_id)
            await update_character_voice(project_id, character, fallback_voice_id)
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
