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

STYLE_PREFIX = (
    "2D illustrated storyboard keyframe, hand-painted production art, colored ink and watercolor wash, "
    "mild graphic flattening — reads as drawn boards, not a photograph"
)
PROMPT_BUILDER_VERSION = "prompt-builder-v2"
STYLE_SUFFIX = (
    "loose painted edges, visible brushstrokes, simplified faces and hands, stylized not photographic, "
    "no DSLR snapshot, no hyperreal skin or pore detail, no glossy 3D render"
)
STORYBOARD_PRIORITIES = (
    "storyboard priorities: clear perspective and depth readability, believable simplified anatomy, "
    "clean staging/blocking and silhouettes, expressive acting poses/facial intent, sequence-art clarity "
    "that communicates ideas and emotion fast; prefer confident sketch readability over polished detail"
)


def buildPrompt(
    visualSummary: str,
    mood: str,
    answers: Optional[Dict[str, str]] = None,
    reference_films: Optional[list[str]] = None,
    consistency: Optional[str] = None,
    required_subjects: Optional[list[str]] = None,
    planning_directives: Optional[list[str]] = None,
    time_period: Optional[str] = None,
    tone: Optional[str] = None,
    ambient_population_hint: Optional[str] = None,
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

    if required_subjects:
        clean_subjects = [s.strip() for s in required_subjects if s and s.strip()]
        if clean_subjects:
            # Hard constraint to prevent "empty room" outputs when scene dialogue
            # clearly implies on-screen characters.
            parts.append(
                "MANDATORY SUBJECTS: include visible human characters "
                + ", ".join(clean_subjects[:4])
                + " in frame; do not generate an empty environment-only shot"
            )
            parts.append(
                "CHARACTER UNIQUENESS: each named lead appears as exactly one person in frame — "
                "no duplicated clones, no repeated identical faces, no twin copies of the same character; "
                "crowd extras are generic silhouettes, not extra instances of leads"
            )

    if ambient_population_hint:
        parts.append(ambient_population_hint)

    if planning_directives:
        directives = [d.strip() for d in planning_directives if d and d.strip()]
        parts.extend(directives[:8])

    if time_period:
        parts.append(f"time period fidelity: {time_period.strip()}")

    if tone:
        parts.append(f"visual tone target: {tone.strip()}")

    parts.append(STORYBOARD_PRIORITIES)

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
        "single subject only, head and shoulders, neutral plain background, even soft lighting, "
        "front-facing, no text, no props, no duplicate faces",
        STYLE_SUFFIX,
    ]
    return ", ".join(p for p in parts if p)
