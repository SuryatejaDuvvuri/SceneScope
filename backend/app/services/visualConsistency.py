import requests
import json
import re
import uuid
from typing import Optional
from app.config import settings
from app.models.common import VisualContext
from app.db import get_db, from_json, to_json


EXTRACTION_PROMPT = """You are a storyboard artist's assistant. Given a screenplay scene, extract every visually identifiable element so that future scenes can maintain visual consistency.

For each element, describe ONLY physical appearance — not personality, not emotions, not plot relevance.

Rules:
- Character descriptions: age range, build, hair color/style, clothing. If the scene doesn't describe appearance, infer reasonable defaults from context clues (name, role, setting) and mark with "(inferred)".
- Location descriptions: architecture, materials, colors, condition, notable features. Pull the location name from the scene heading.
- Props: only include objects that are visually distinctive or likely to reappear. Describe shape, material, color, condition.
- Keep each description under 15 words.

Respond with ONLY a JSON object:
{
  "characters": {"CHARACTER_NAME": "physical description"},
  "locations": {"LOCATION_NAME": "physical description"},
  "props": {"PROP_NAME": "physical description"}
}

If a category has no items, use an empty object {}."""


def extractVisualDetails(heading: str, description: str, visualSummary: str) -> dict:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    userContent = f"Scene Heading: {heading}\n\nScene Description:\n{description}"
    if visualSummary:
        userContent += f"\n\nVisual Summary:\n{visualSummary}"

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": userContent}
        ],
        "temperature": 0.2
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Handle markdown-wrapped JSON
        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)

        parsed = json.loads(content)
        return {
            "characters": parsed.get("characters", {}),
            "locations": parsed.get("locations", {}),
            "props": parsed.get("props", {})
        }
    except Exception as e:
        print(f"Visual extraction failed: {e}")
        return {"characters": {}, "locations": {}, "props": {}}


async def getProjectContext(project_id: str) -> VisualContext:
    db = await get_db()
    try:
        rows = await db.execute(
            "SELECT visual_context FROM scenes WHERE project_id = ? AND locked = 1 ORDER BY scene_number",
            (project_id,)
        )
        scenes = await rows.fetchall()

        merged_characters = {}
        merged_locations = {}
        merged_props = {}

        for scene in scenes:
            ctx = from_json(scene["visual_context"])
            if not ctx:
                continue
            merged_characters.update(ctx.get("characters", {}))
            merged_locations.update(ctx.get("locations", {}))
            merged_props.update(ctx.get("props", {}))

        return VisualContext(
            characters=merged_characters,
            locations=merged_locations,
            props=merged_props
        )
    finally:
        await db.close()


def buildConsistencyPrompt(context: VisualContext) -> str:
    """Convert a VisualContext into a concise prompt suffix for image generation."""
    parts = []

    for name, desc in context.characters.items():
        clean = desc.replace("(inferred)", "").strip()
        parts.append(f"{name} is {clean}")

    for name, desc in context.locations.items():
        parts.append(f"{name}: {desc}")

    if not parts:
        return ""

    combined = ". ".join(parts)
    if len(combined) > 200:
        combined = combined[:200].rsplit(".", 1)[0]

    return f"Visual continuity: {combined}"


async def save_character_reference(project_id: str, character_name: str, image_url: str, description: str):
    """Save or update a character's reference image when a scene is locked."""
    db = await get_db()
    try:
        row = await db.execute(
            "SELECT id FROM characters WHERE project_id = ? AND name = ?",
            (project_id, character_name)
        )
        existing = await row.fetchone()
        if existing:
            await db.execute(
                "UPDATE characters SET image_url = ?, description = ?, updated_at = datetime('now') WHERE id = ?",
                (image_url, description, existing["id"])
            )
        else:
            char_id = uuid.uuid4().hex
            await db.execute(
                "INSERT INTO characters (id, project_id, name, description, image_url, created_at, updated_at) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
                (char_id, project_id, character_name, description, image_url)
            )
        await db.commit()
    finally:
        await db.close()


async def get_character_references(project_id: str) -> list[dict]:
    """Get all character reference images for a project."""
    db = await get_db()
    try:
        rows = await db.execute(
            "SELECT name, description, image_url FROM characters WHERE project_id = ? AND image_url IS NOT NULL",
            (project_id,)
        )
        return [dict(r) for r in await rows.fetchall()]
    finally:
        await db.close()
