from typing import Optional, Dict

MOOD_MODIFIERS = {
    # Primary moods (from fine-tuned model)
    "tense": "deep shadows, low-key lighting, tight framing, cold blue tones, dutch angles, high contrast",
    "somber": "desaturated cool tones, soft diffused lighting, isolated framing, empty space around subjects, muted palette",
    # Fallback moods (from generic emotion model via EMOTION_TO_MOOD mapping)
    "uplifting": "warm golden lighting, open composition, bright and saturated colors, wide shots",
    "action": "dynamic angles, motion blur, dramatic lighting, wide framing, high energy composition",
    # Legacy labels (in case generic model returns raw emotions)
    "anger": "harsh lighting, high contrast, tight framing, red and dark tones, aggressive composition",
    "disgust": "grimy textures, muted sickly greens, uncomfortable close-ups, cluttered frame",
    "fear": "deep shadows, low-key lighting, wide empty spaces, cold blue tones, dutch angles",
    "joy": "warm golden lighting, open composition, bright and saturated colors, wide shots",
    "neutral": "balanced natural lighting, standard framing, muted earth tones, clean composition",
    "sadness": "desaturated cool tones, soft diffused lighting, isolated framing, empty space around subjects",
    "surprise": "dramatic lighting shifts, dynamic angles, high contrast, sharp focus, wide framing",
}

STYLE_PREFIX = "hand-painted storyboard illustration, colored ink and watercolor"
STYLE_SUFFIX = "visible brushstrokes, painted color art, NOT a photograph, NOT photorealistic"


def buildPrompt(
    visualSummary: str,
    mood: str,
    answers: Optional[Dict[str, str]] = None,
    reference_films: Optional[list[str]] = None,
) -> str:
    # Style anchor first to set the medium, then scene content, then reinforce at end
    parts = [STYLE_PREFIX, visualSummary.strip()]

    if answers:
        answerDetails = ", ".join(f"{v}" for v in answers.values() if v)
        if answerDetails:
            parts.append(answerDetails)

    modifier = MOOD_MODIFIERS.get(mood.lower(), MOOD_MODIFIERS["neutral"])
    parts.append(modifier)

    if reference_films:
        films = ", ".join(f.strip() for f in reference_films if f and f.strip())
        if films:
            parts.append(f"cinematic influences: {films}")

    parts.append(STYLE_SUFFIX)

    return ", ".join(parts)
