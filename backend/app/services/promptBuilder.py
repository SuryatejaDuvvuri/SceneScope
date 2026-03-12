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

STYLE_PREFIX = (
    "cinematic storyboard illustration, 2D hand-drawn color art, visible ink linework and pencil sketch shading, "
    "graphic novel panel style, NOT photorealistic, flat color fills with cross-hatching, "
    "film pre-visualization sketch, warm muted color palette, consistent illustration art style"
)


def buildPrompt(
    visualSummary: str,
    mood: str,
    answers: Optional[Dict[str, str]] = None,
    reference_films: Optional[list[str]] = None,
) -> str:
    parts = [STYLE_PREFIX]

    modifier = MOOD_MODIFIERS.get(mood.lower(), MOOD_MODIFIERS["neutral"])
    parts.append(modifier)
    parts.append(visualSummary.strip())

    if answers:
        answerDetails = ", ".join(f"{v}" for v in answers.values() if v)
        if answerDetails:
            parts.append(answerDetails)

    if reference_films:
        films = ", ".join(f.strip() for f in reference_films if f and f.strip())
        if films:
            parts.append(f"cinematic influences: {films}")

    return ", ".join(parts)
