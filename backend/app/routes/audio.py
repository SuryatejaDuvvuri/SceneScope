"""
Audio API Routes
────────────────
Generate and retrieve character-voiced dialogue audio for scenes.
"""

import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.db import get_db, from_json, to_json
from app.services.audioGenerator import generate_scene_audio, get_or_assign_voice, PREMADE_VOICES
from app.auth import get_current_user

router = APIRouter(tags=["audio"])


class AudioResponse(BaseModel):
    id: str
    scene_id: str
    audio_url: str
    dialogue_data: list[dict]
    total_duration_ms: int


class VoiceAssignment(BaseModel):
    voice_id: str


class VoiceInfo(BaseModel):
    character_name: str
    voice_id: str
    voice_name: Optional[str] = None


@router.post("/scenes/{scene_id}/audio", response_model=AudioResponse)
async def generate_audio(scene_id: str, user: dict = Depends(get_current_user)):
    """Generate audio for a scene's dialogue using ElevenLabs TTS."""
    db = await get_db()
    try:
        # Verify ownership
        row = await db.execute(
            """SELECT s.*, p.id as proj_id FROM scenes s
               JOIN projects p ON s.project_id = p.id
               WHERE s.id = ? AND p.user_id = ?""",
            (scene_id, user["id"]),
        )
        scene = await row.fetchone()
        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")

        dialogue = from_json(scene["dialogue"]) if scene["dialogue"] else []
        if not dialogue:
            raise HTTPException(status_code=400, detail="Scene has no dialogue to generate audio for")

        result = await generate_scene_audio(
            scene_id=scene_id,
            project_id=scene["project_id"],
            dialogue_lines=dialogue,
        )
        return AudioResponse(**result)
    finally:
        await db.close()


@router.get("/scenes/{scene_id}/audio", response_model=Optional[AudioResponse])
async def get_audio(scene_id: str, user: dict = Depends(get_current_user)):
    """Get existing audio for a scene (most recent generation)."""
    db = await get_db()
    try:
        # Verify ownership
        row = await db.execute(
            """SELECT s.id FROM scenes s
               JOIN projects p ON s.project_id = p.id
               WHERE s.id = ? AND p.user_id = ?""",
            (scene_id, user["id"]),
        )
        if not await row.fetchone():
            raise HTTPException(status_code=404, detail="Scene not found")

        row = await db.execute(
            "SELECT * FROM scene_audio WHERE scene_id = ? ORDER BY created_at DESC LIMIT 1",
            (scene_id,),
        )
        audio = await row.fetchone()
        if not audio:
            return None

        return AudioResponse(
            id=audio["id"],
            scene_id=audio["scene_id"],
            audio_url=audio["audio_url"],
            dialogue_data=from_json(audio["dialogue_data"]) or [],
            total_duration_ms=audio["total_duration_ms"] or 0,
        )
    finally:
        await db.close()


@router.get("/projects/{project_id}/voices", response_model=list[VoiceInfo])
async def get_voices(project_id: str, user: dict = Depends(get_current_user)):
    """Get all voice assignments for characters in a project."""
    db = await get_db()
    try:
        row = await db.execute(
            "SELECT id FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user["id"]),
        )
        if not await row.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        rows = await db.execute(
            "SELECT character_name, voice_id FROM character_voices WHERE project_id = ?",
            (project_id,),
        )
        voices = await rows.fetchall()

        # Map voice_id to voice name for display
        voice_map = {v["voice_id"]: v["name"] for v in PREMADE_VOICES}

        return [
            VoiceInfo(
                character_name=v["character_name"],
                voice_id=v["voice_id"],
                voice_name=voice_map.get(v["voice_id"]),
            )
            for v in voices
        ]
    finally:
        await db.close()


@router.put("/projects/{project_id}/voices/{character_name}", response_model=VoiceInfo)
async def set_voice(
    project_id: str,
    character_name: str,
    body: VoiceAssignment,
    user: dict = Depends(get_current_user),
):
    """Manually assign a voice to a character, overriding auto-assignment."""
    db = await get_db()
    try:
        row = await db.execute(
            "SELECT id FROM projects WHERE id = ? AND user_id = ?",
            (project_id, user["id"]),
        )
        if not await row.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        # Upsert voice assignment
        row = await db.execute(
            "SELECT id FROM character_voices WHERE project_id = ? AND character_name = ?",
            (project_id, character_name),
        )
        existing = await row.fetchone()
        if existing:
            await db.execute(
                "UPDATE character_voices SET voice_id = ? WHERE id = ?",
                (body.voice_id, existing["id"]),
            )
        else:
            cv_id = uuid.uuid4().hex
            await db.execute(
                "INSERT INTO character_voices (id, project_id, character_name, voice_id) VALUES (?, ?, ?, ?)",
                (cv_id, project_id, character_name, body.voice_id),
            )
        await db.commit()

        voice_map = {v["voice_id"]: v["name"] for v in PREMADE_VOICES}
        return VoiceInfo(
            character_name=character_name,
            voice_id=body.voice_id,
            voice_name=voice_map.get(body.voice_id),
        )
    finally:
        await db.close()
