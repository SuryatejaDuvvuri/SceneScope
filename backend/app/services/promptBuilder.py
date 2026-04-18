from typing import Optional, Dict

MOOD_MODIFIERS = {
    # Primary moods (from fine-tuned model)
    "tense": "deep shadows, low-key lighting, tight framing, cold blue tones, dutch angles, high contrast",
    "somber": "desaturated cool tones, soft diffused lighting, isolated framing, empty space around subjects, muted palette",
    "romantic": "warm soft lighting, shallow depth of field, intimate close framing, warm amber and rose tones, gentle bokeh, faces in close proximity",
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
    consistency: Optional[str] = None,
) -> str:
    """Compose the final image prompt.

    Token order matters for diffusion models: earlier tokens get more attention.
    We therefore place consistency context (canonical character/location
    descriptions) RIGHT after the style anchor and BEFORE the scene-specific
    content. This is the single biggest lever for cross-scene character
    identity stability — the previous tail-end placement meant character
    descriptions had near-zero attention weight.
    """
    parts = [STYLE_PREFIX]

    if consistency:
        parts.append(consistency)

    parts.append(visualSummary.strip())

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


def buildCharacterPortraitPrompt(name: str, description: str) -> str:
    """A focused prompt for generating a clean reference portrait of one character.

    Used at scene-lock time to produce the per-character image stored in the
    ``characters`` table. Single subject, neutral background, the same style
    anchors as scene generation so the portrait blends with later scene art.
    """
    clean_desc = description.replace("(inferred)", "").strip()
    parts = [
        STYLE_PREFIX,
        f"character reference portrait of {name}",
        clean_desc,
        "single subject, head and shoulders, neutral plain background, even soft lighting, front-facing, no text, no props",
        STYLE_SUFFIX,
    ]
    return ", ".join(p for p in parts if p)
