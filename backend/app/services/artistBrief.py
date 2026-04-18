"""
Artist's mental framing — the pre-draw reasoning pass.

Before a human storyboard artist puts pencil to paper, they spend a few seconds
reasoning about the scene: *"college bar = small, busy, warm low light. Two
people in a booth angled toward each other. Ambient patrons blurred behind.
Intimate conversation under noise."*

This module runs the same reasoning via Groq and returns a ~40-word brief that
gets injected into the image prompt right before the visual summary. The goal
is to give the diffusion model the same situational priming a human artist
brings to the page — setting archetype, expected population/activity, emotional
beat, implicit staging — without hardcoding it per scene type.

Cached in-memory by (heading, description) hash so refinements reuse the same
brief across iterations of the same scene (we only re-reason when the scene
changes, not when the user tweaks a color).
"""

import hashlib
import requests
from typing import Optional

from app.config import settings

_CACHE: dict[str, str] = {}

_SYSTEM_PROMPT = """You are a veteran storyboard artist. Before drawing any panel, you spend a few seconds reasoning about the scene the way an experienced artist does — not describing the shot, but building a mental model of the world you're about to draw.

Given a scene heading and description, produce ONE concise paragraph (35-55 words) covering:
- setting archetype — what this kind of place typically looks and feels like (size, density, light quality, ambient activity)
- who is in frame and their implicit relationship/power dynamic
- the emotional beat of this specific moment
- a natural staging instinct — where the camera would sit, what the blocking suggests

Write in the voice of an artist thinking to themselves while looking at the script. Plain prose, no bullet points, no headers, no preamble. Do NOT describe shot type in film-school jargon ("medium close-up, OTS"). Think like a person drawing, not a DP writing a shot list."""


def _hash_key(heading: str, description: str) -> str:
    raw = f"{heading.strip()}\x1f{description.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_artist_brief(heading: str, description: str) -> Optional[str]:
    """Return a ~40-word artist's mental framing of the scene, or None on failure.

    None is a safe signal — the prompt builder simply omits the brief section
    rather than failing the whole generation.
    """
    if not settings.GROQ_API_KEY:
        return None
    if not (description and description.strip()):
        return None

    key = _hash_key(heading or "", description)
    if key in _CACHE:
        return _CACHE[key]

    user_msg = (
        f"SCENE HEADING: {heading or 'UNKNOWN'}\n\n"
        f"SCENE DESCRIPTION:\n{description.strip()[:1200]}"
    )

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.5,
        "max_tokens": 160,
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        data = response.json()
        if "error" in data:
            print(f"Artist brief error: {data['error']}")
            return None
        content = data["choices"][0]["message"]["content"].strip()
        # Strip surrounding quotes/markdown artifacts
        content = content.strip('"').strip("'").strip()
        if not content:
            return None
        _CACHE[key] = content
        return content
    except Exception as e:
        print(f"Artist brief failed: {e}")
        return None
