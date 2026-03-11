"""
Shot Type Suggester Service
────────────────────────────
Suggests camera shots, angles, and movements based on scene mood + content.

This is what makes SceneScope useful for film students — it doesn't just
generate a sketch, it teaches them WHY certain shots work for certain moods.

YOUR JOB (the complex part):
- Implement suggest_shots() — the core logic
- Decide: rule-based mapping vs LLM-powered suggestions vs hybrid

Approach options:
  A) Rule-based: mood → hardcoded shot mappings (fast, deterministic, less nuanced)
  B) LLM-powered: send mood + description to Groq, ask for shot suggestions (slower, smarter)
  C) Hybrid: rule-based primary shot + LLM for alternatives (recommended)
"""

from app.models.common import ShotSuggestion, ShotSuggestions


# ── Shot Knowledge Base (your starting point) ──
# Film theory: shot types communicate specific emotional information

MOOD_SHOT_DEFAULTS = {
    "tense": ShotSuggestion(
        shot_type="close-up",
        angle="slightly low angle",
        movement="slow dolly in",
        reasoning="Close-ups heighten tension by filling the frame with the subject, removing escape routes for the eye. Low angle adds subtle menace."
    ),
    "uplifting": ShotSuggestion(
        shot_type="wide shot",
        angle="eye level",
        movement="slow crane up",
        reasoning="Wide shots create a sense of openness and possibility. Eye level keeps the audience on equal footing with the character. Crane up suggests rising spirits."
    ),
    "somber": ShotSuggestion(
        shot_type="medium wide shot",
        angle="slightly high angle",
        movement="static",
        reasoning="Medium wide shots show isolation within the environment. High angle diminishes the subject, emphasizing vulnerability. Static camera mirrors emotional numbness."
    ),
    "action": ShotSuggestion(
        shot_type="medium shot",
        angle="low angle",
        movement="handheld tracking",
        reasoning="Medium shots keep the action readable while maintaining energy. Low angle makes characters look powerful. Handheld adds kinetic urgency."
    ),
}

# Map the 7 emotion labels (from current classifier) to our 4 mood categories
EMOTION_TO_MOOD = {
    "anger": "tense",
    "disgust": "tense",
    "fear": "tense",
    "joy": "uplifting",
    "neutral": "uplifting",
    "sadness": "somber",
    "surprise": "action",
}


def suggest_shots(mood: str, description: str) -> ShotSuggestions:
    """
    TODO (you): Implement shot suggestions based on mood + scene content.

    Current implementation: basic rule-based mapping from mood → default shot.

    Your job: make this smarter. Ideas:
    1. Parse the description for keywords (e.g., "chase" → tracking shot,
       "whispers" → extreme close-up, "landscape" → extreme wide)
    2. Call Groq for 2-3 alternative shot suggestions with reasoning
    3. Factor in scene heading (INT vs EXT affects framing)
    4. Consider number of characters (dialogue = over-the-shoulder,
       solo = portrait framing, crowd = wide establishing)

    The reasoning field is KEY — film students learn from understanding
    WHY a shot choice works, not just WHAT it is.
    """
    # Normalize mood: if using 7-emotion model, map to 4 categories
    normalized_mood = EMOTION_TO_MOOD.get(mood.lower(), mood.lower())

    primary = MOOD_SHOT_DEFAULTS.get(
        normalized_mood,
        MOOD_SHOT_DEFAULTS["uplifting"]  # fallback
    )

    return ShotSuggestions(
        primary=primary,
        alternatives=[]  # TODO: add LLM-powered alternatives
    )
