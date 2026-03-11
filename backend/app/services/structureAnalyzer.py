"""
Screenplay Structure Analyzer
──────────────────────────────
Analyzes the full screenplay for pacing, tension arcs, and tonal shifts.
Goes beyond per-scene mood — looks at the WHOLE script as a narrative.
"""

import requests
import json
import re
from app.config import settings
from app.models.common import StructureAnalysis


# How "different" two moods feel when you cut between them.
# 0 = same vibe, 1 = maximum contrast.
# Think of it like: how jarring would the edit feel?
MOOD_DISTANCE = {
    ("tense", "tense"): 0,
    ("tense", "uplifting"): 0.9,    # horror → comedy = jarring
    ("tense", "somber"): 0.4,       # both dark, different energy
    ("tense", "action"): 0.5,       # tension can build into action naturally
    ("uplifting", "uplifting"): 0,
    ("uplifting", "tense"): 0.9,
    ("uplifting", "somber"): 0.8,   # happy → sad = big emotional shift
    ("uplifting", "action"): 0.4,   # both high-energy
    ("somber", "somber"): 0,
    ("somber", "tense"): 0.4,
    ("somber", "uplifting"): 0.8,
    ("somber", "action"): 0.7,      # quiet grief → explosion = big contrast
    ("action", "action"): 0,
    ("action", "tense"): 0.5,
    ("action", "uplifting"): 0.4,
    ("action", "somber"): 0.7,      # fast → still = noticeable shift
}

# Map the 7 emotion labels from the current classifier to our 4 mood categories
EMOTION_TO_MOOD = {
    "anger": "tense",
    "disgust": "tense",
    "fear": "tense",
    "joy": "uplifting",
    "neutral": "uplifting",
    "sadness": "somber",
    "surprise": "action",
}

ARC_PROMPT = """You are a screenplay structure analyst. Given this sequence of scene moods from a screenplay, describe the emotional arc in 2-3 sentences.

Focus on:
- How the story opens emotionally
- Where the major tonal shifts happen
- How the emotional trajectory builds toward the ending

Be specific about which scenes mark turning points. Write like a film professor giving notes.

Scene mood sequence:
{mood_sequence}

Respond with ONLY the arc description, no JSON, no formatting."""


def _normalize_mood(mood: str) -> str:
    """Map 7-emotion labels to 4 mood categories."""
    if not mood:
        return "uplifting"
    return EMOTION_TO_MOOD.get(mood.lower(), mood.lower())


def _get_distance(mood_a: str, mood_b: str) -> float:
    """Look up how different two moods are. Returns 0-1."""
    a = _normalize_mood(mood_a)
    b = _normalize_mood(mood_b)
    return MOOD_DISTANCE.get((a, b), 0.5)


def detect_tonal_shifts(scene_moods: list[dict]) -> list[dict]:
    """Detect points where the mood changes between scenes."""
    shifts = []
    for i in range(1, len(scene_moods)):
        prev = scene_moods[i - 1]
        curr = scene_moods[i]
        prev_mood = _normalize_mood(prev["mood"])
        curr_mood = _normalize_mood(curr["mood"])

        if prev_mood != curr_mood:
            magnitude = _get_distance(prev["mood"], curr["mood"])
            shifts.append({
                "from_scene": prev["scene_number"],
                "to_scene": curr["scene_number"],
                "from_mood": prev_mood,
                "to_mood": curr_mood,
                "magnitude": magnitude,
            })
    return shifts


def assess_pacing(scene_moods: list[dict], tonal_shifts: list[dict]) -> str:
    """Characterize the script's pacing based on how often the mood changes."""
    if not scene_moods:
        return "No scenes to analyze"

    total = len(scene_moods)
    shift_ratio = len(tonal_shifts) / max(total, 1)

    # Look at where shifts cluster
    if tonal_shifts:
        shift_positions = [s["from_scene"] / max(total, 1) for s in tonal_shifts]
        avg_position = sum(shift_positions) / len(shift_positions)

        if shift_ratio < 0.2:
            return "slow burn — sustained mood with minimal tonal shifts"
        elif shift_ratio < 0.5:
            if avg_position < 0.4:
                return "front-loaded — most tonal shifts happen early, then settles"
            elif avg_position > 0.6:
                return "building — steady mood early, escalates toward the end"
            else:
                return "measured — deliberate, evenly paced tonal shifts"
        else:
            return "rapid fire — constant mood changes, high emotional volatility"
    else:
        return "monochromatic — single sustained mood throughout"


def _generate_arc_summary(scene_moods: list[dict]) -> str:
    """Call Groq to generate a narrative description of the emotional arc."""
    # Build a readable mood sequence for the LLM
    mood_lines = []
    for s in scene_moods:
        normalized = _normalize_mood(s["mood"])
        heading = s.get("heading", f"Scene {s['scene_number']}")
        mood_lines.append(f"Scene {s['scene_number']} ({heading}): {normalized}")

    mood_sequence = "\n".join(mood_lines)

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "user", "content": ARC_PROMPT.format(mood_sequence=mood_sequence)}
        ],
        "temperature": 0.4,
        "max_tokens": 200
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Arc summary generation failed: {e}")
        return "Unable to generate arc summary."


async def analyze_structure(scene_moods: list[dict]) -> StructureAnalysis:
    """Full structure analysis: tonal shifts, pacing, and narrative arc."""
    shifts = detect_tonal_shifts(scene_moods)
    pacing = assess_pacing(scene_moods, shifts)
    arc_summary = _generate_arc_summary(scene_moods)

    return StructureAnalysis(
        scene_moods=scene_moods,
        tonal_shifts=shifts,
        pacing=pacing,
        arc_summary=arc_summary,
    )
