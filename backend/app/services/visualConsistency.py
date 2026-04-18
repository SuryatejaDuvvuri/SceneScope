import requests
import json
import re
import uuid
import hashlib
from typing import Optional
from app.config import settings
from app.models.common import VisualContext
from app.db import get_db, from_json, to_json


# ────────────────────────────────────────────────────────────────────────────
# Extraction
# ────────────────────────────────────────────────────────────────────────────

EXTRACTION_PROMPT_BASE = """You are a storyboard artist's assistant. Given a screenplay scene, extract every visually identifiable element so that future scenes can maintain visual consistency.

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


KNOWN_ROSTER_INSTRUCTION = """

CRITICAL — KNOWN CHARACTERS:
The following characters already have canonical visual descriptions from earlier scenes. If any of them appear in this scene, you MUST reuse their description VERBATIM (copy-paste exactly). Do not paraphrase, do not embellish, do not generate a new description for them. Only generate fresh descriptions for characters NOT in this list.

{roster}
"""


def _format_roster(known_characters: dict[str, str]) -> str:
    if not known_characters:
        return "(none yet)"
    return "\n".join(f"- {name}: {desc}" for name, desc in known_characters.items())


def extractVisualDetails(
    heading: str,
    description: str,
    visualSummary: str,
    known_characters: Optional[dict[str, str]] = None,
) -> dict:
    """Extract visual details from a scene.

    When ``known_characters`` is provided, the extractor is instructed to reuse
    those descriptions verbatim for any character that re-appears, preventing
    description drift across scenes (the root cause of cross-scene face drift
    in the generated images).
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = EXTRACTION_PROMPT_BASE
    if known_characters:
        system_prompt += KNOWN_ROSTER_INSTRUCTION.format(roster=_format_roster(known_characters))

    userContent = f"Scene Heading: {heading}\n\nScene Description:\n{description}"
    if visualSummary:
        userContent += f"\n\nVisual Summary:\n{visualSummary}"

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": userContent}
        ],
        "temperature": 0.2
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)

        parsed = json.loads(content)
        result = {
            "characters": parsed.get("characters", {}),
            "locations": parsed.get("locations", {}),
            "props": parsed.get("props", {})
        }

        # Belt-and-braces: even if the LLM ignored the "verbatim" instruction,
        # force any known character back to their canonical description.
        if known_characters:
            for name, canonical in known_characters.items():
                if name in result["characters"]:
                    result["characters"][name] = canonical

        return result
    except Exception as e:
        print(f"Visual extraction failed: {e}")
        return {"characters": {}, "locations": {}, "props": {}}


# ────────────────────────────────────────────────────────────────────────────
# Project context
# ────────────────────────────────────────────────────────────────────────────


async def get_existing_characters(db, project_id: str) -> dict[str, str]:
    """Return the canonical roster of characters known for a project.

    The ``characters`` table holds the FIRST description we ever locked for
    each character — that's our single source of truth, never overwritten.
    """
    rows = await db.execute(
        "SELECT name, description FROM characters WHERE project_id = ? AND description IS NOT NULL",
        (project_id,),
    )
    return {row["name"]: row["description"] for row in await rows.fetchall()}


async def getProjectContext(project_id: str) -> VisualContext:
    """Build a VisualContext combining the canonical character roster with
    locations/props pulled from locked scenes.

    Characters come from the ``characters`` table (canonical) rather than from
    last-write-wins merging of per-scene contexts, so descriptions are stable.
    """
    db = await get_db()
    try:
        merged_locations: dict[str, str] = {}
        merged_props: dict[str, str] = {}

        rows = await db.execute(
            "SELECT visual_context FROM scenes WHERE project_id = ? AND locked = 1 ORDER BY scene_number",
            (project_id,),
        )
        for scene in await rows.fetchall():
            ctx = from_json(scene["visual_context"])
            if not ctx:
                continue
            merged_locations.update(ctx.get("locations", {}))
            merged_props.update(ctx.get("props", {}))

        characters = await get_existing_characters(db, project_id)

        return VisualContext(
            characters=characters,
            locations=merged_locations,
            props=merged_props,
        )
    finally:
        await db.close()


# ────────────────────────────────────────────────────────────────────────────
# Prompt building
# ────────────────────────────────────────────────────────────────────────────


_NAME_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_'\- ]+")


def _name_appears(name: str, scene_text: str) -> bool:
    """True if a character/location name is mentioned in the scene text.

    Matches case-insensitively on word boundaries so 'SAM' doesn't match 'Samantha'.
    """
    if not name:
        return False
    pattern = r"\b" + re.escape(name) + r"\b"
    return re.search(pattern, scene_text, re.IGNORECASE) is not None


def buildConsistencyPrompt(
    context: VisualContext,
    scene_text: Optional[str] = None,
    max_chars: int = 600,
) -> str:
    """Convert a VisualContext into a prompt fragment.

    When ``scene_text`` is provided we include only characters and locations
    that are actually mentioned in the scene — this stops a 12-character
    project from drowning every prompt in irrelevant character descriptions.
    """
    parts: list[str] = []

    for name, desc in context.characters.items():
        if scene_text and not _name_appears(name, scene_text):
            continue
        clean = desc.replace("(inferred)", "").strip()
        if clean:
            parts.append(f"{name} ({clean})")

    for name, desc in context.locations.items():
        if scene_text and not _name_appears(name, scene_text):
            continue
        if desc:
            parts.append(f"{name}: {desc}")

    if not parts:
        return ""

    combined = ". ".join(parts)
    if len(combined) > max_chars:
        # Trim on a sentence boundary so we don't cut mid-character.
        combined = combined[:max_chars].rsplit(".", 1)[0]

    return f"Visual continuity — {combined}"


# ────────────────────────────────────────────────────────────────────────────
# Deterministic seeds
# ────────────────────────────────────────────────────────────────────────────


def _hash_to_seed(*parts: str) -> int:
    """Stable 31-bit positive int derived from the given strings.

    Most diffusion APIs accept any 32-bit int; we stay positive and < 2^31 to
    be safe across providers (some treat the field as signed).
    """
    digest = hashlib.sha256("::".join(parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def project_seed(project_id: str) -> int:
    return _hash_to_seed("project", project_id)


def character_seed(project_id: str, character_name: str) -> int:
    return _hash_to_seed("character", project_id, character_name.upper())


# ────────────────────────────────────────────────────────────────────────────
# Character reference storage
# ────────────────────────────────────────────────────────────────────────────


async def save_character_reference(
    project_id: str,
    character_name: str,
    image_url: Optional[str],
    description: str,
    seed: Optional[int] = None,
):
    """Insert a character if new, or selectively update fields.

    Importantly, ``description`` is treated as canonical — we set it on first
    insert and NEVER overwrite it. ``image_url`` and ``seed`` are updated only
    when previously empty (so a real per-character portrait can replace a
    placeholder, but we don't churn references on every scene lock).
    """
    db = await get_db()
    try:
        row = await db.execute(
            "SELECT id, description, image_url, seed FROM characters WHERE project_id = ? AND name = ?",
            (project_id, character_name),
        )
        existing = await row.fetchone()
        if existing:
            updates: list[str] = []
            values: list = []
            if not existing["image_url"] and image_url:
                updates.append("image_url = ?")
                values.append(image_url)
            if existing["seed"] is None and seed is not None:
                updates.append("seed = ?")
                values.append(seed)
            if updates:
                values.append(existing["id"])
                await db.execute(
                    f"UPDATE characters SET {', '.join(updates)}, updated_at = datetime('now') WHERE id = ?",
                    values,
                )
                await db.commit()
            return

        char_id = uuid.uuid4().hex
        if seed is None:
            seed = character_seed(project_id, character_name)
        await db.execute(
            """INSERT INTO characters (id, project_id, name, description, image_url, seed, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
            (char_id, project_id, character_name, description, image_url, seed),
        )
        await db.commit()
    finally:
        await db.close()


async def get_character_references(project_id: str) -> list[dict]:
    """All characters with a usable reference image."""
    db = await get_db()
    try:
        rows = await db.execute(
            "SELECT name, description, image_url, seed FROM characters WHERE project_id = ? AND image_url IS NOT NULL",
            (project_id,),
        )
        return [dict(r) for r in await rows.fetchall()]
    finally:
        await db.close()


async def get_character_refs_for_scene(project_id: str, scene_text: str) -> list[dict]:
    """Subset of character references whose name appears in the scene text."""
    refs = await get_character_references(project_id)
    return [r for r in refs if _name_appears(r["name"], scene_text)]


# ────────────────────────────────────────────────────────────────────────────
# Portrait generation
# ────────────────────────────────────────────────────────────────────────────


async def ensure_character_portraits(
    project_id: str,
    new_characters: dict[str, str],
):
    """For each newly-locked character, generate a clean solo portrait and
    store it as the character's reference image.

    A single wide-shot scene sketch is a terrible character reference — the
    subject is one of many and may be blurry, partial, or far from camera.
    A dedicated portrait gives Ideogram (and any other character-conditioning
    provider we add later) a clean subject to lock onto.

    Failures are tolerated: lock should not fail if portrait generation fails.
    """
    if not new_characters:
        return

    # Imported lazily to avoid circular import (imageGenerator → promptBuilder
    # which is imported elsewhere from visualConsistency consumers).
    from app.services.imageGenerator import generateCharacterPortrait

    db = await get_db()
    try:
        for name, desc in new_characters.items():
            try:
                row = await db.execute(
                    "SELECT id, image_url FROM characters WHERE project_id = ? AND name = ?",
                    (project_id, name),
                )
                existing = await row.fetchone()
                if existing and existing["image_url"]:
                    continue

                seed = character_seed(project_id, name)
                portrait = generateCharacterPortrait(name=name, description=desc, seed=seed)
                if not portrait:
                    continue

                portrait_url = f"/static/images/{portrait.filePath.split('/')[-1]}"
                base_url = (settings.BACKEND_PUBLIC_URL or "").rstrip("/")
                full_url = f"{base_url}{portrait_url}" if base_url else portrait_url

                if existing:
                    await db.execute(
                        "UPDATE characters SET image_url = ?, seed = COALESCE(seed, ?), updated_at = datetime('now') WHERE id = ?",
                        (full_url, seed, existing["id"]),
                    )
                else:
                    await db.execute(
                        """INSERT INTO characters (id, project_id, name, description, image_url, seed, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
                        (uuid.uuid4().hex, project_id, name, desc, full_url, seed),
                    )
                await db.commit()
            except Exception as e:
                print(f"Portrait generation failed for {name}: {e}")
                continue
    finally:
        await db.close()
