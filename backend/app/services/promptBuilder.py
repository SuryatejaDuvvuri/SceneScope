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

# Medium anchor — set at the very top so the model commits to this style before
# reading any scene content.
STYLE_PREFIX = (
    "2D illustrated storyboard keyframe, hand-painted production art, colored ink and watercolor wash, "
    "mild graphic flattening — reads as drawn boards, not a photograph"
)

PROMPT_BUILDER_VERSION = "prompt-builder-v3"

# Style reinforcement — repeated at the end to counteract any photorealism drift
# introduced by long scene descriptions.
STYLE_SUFFIX = (
    "loose painted edges, visible brushstrokes, simplified faces and hands, stylized not photographic, "
    "no DSLR snapshot, no hyperreal skin or pore detail, no glossy 3D render"
)

# The craft priorities a professional storyboard artist brings to every panel.
# Written as instructions to the model, not as a genre label.
STORYBOARD_PRIORITIES = (
    "draw this like a professional storyboard artist: "
    "clear perspective lines and readable depth planes, "
    "simplified but believable anatomy that reads from a distance, "
    "staging and blocking that shows character relationships and power dynamics at a glance, "
    "expressive acting poses that convey emotion without dialogue — posture, gesture, eyeline, "
    "silhouette clarity so every figure is immediately readable, "
    "composition that guides the eye to the story beat in this frame, "
    "goal is to communicate the idea and feeling fast — confident sketch over polished finish"
)


def buildPrompt(
    visualSummary: str,
    mood: str,
    answers: Optional[Dict[str, str]] = None,
    reference_films: Optional[list[str]] = None,
    consistency: Optional[str] = None,
    required_subjects: Optional[list[str]] = None,
    time_period: Optional[str] = None,
    tone: Optional[str] = None,
    ambient_population_hint: Optional[str] = None,
    director_modifier: Optional[str] = None,
) -> str:
    """Compose the final image prompt for one storyboard keyframe.

    Token-order rationale (earlier = higher diffusion attention):
    1. Style anchor          — commits the model to 2D storyboard medium immediately
    2. Identity consistency  — canonical character/location descriptions (most important
                               for cross-scene stability)
    3. Setting population    — crowd/ambient context so the model knows the world isn't empty
    4. Named subjects        — who MUST appear in frame, with physical descriptions when known
    5. Scene content         — what is actually happening (visual summary + user answers)
    6. Time period + tone    — period fidelity and overall visual register
    7. Storyboard craft      — the "how to draw it" meta-instruction
    8. Mood modifier         — lighting / color palette for this beat
    9. Reference films       — expanded style descriptors (e.g. "Dune (vast desert vistas...)")
    10. Director modifier    — any additional cinematic direction from the Director Agent
    11. Character uniqueness — LAST so it has strong closing-attention weight as a guard
    12. Style suffix         — reinforces the medium one final time
    """
    parts = [STYLE_PREFIX]

    # ── 2. Identity consistency (highest-priority fixed attribute) ──────────────
    if consistency:
        parts.append(consistency)

    # ── 3. Setting population (crowd / ambient context) ─────────────────────────
    if ambient_population_hint:
        parts.append(ambient_population_hint)

    # ── 4. Named subjects ────────────────────────────────────────────────────────
    if required_subjects:
        clean_subjects = [s.strip() for s in required_subjects if s and s.strip()]
        if clean_subjects:
            # Hard inclusion constraint — prevents "empty room" outputs when
            # named characters are clearly on-screen.
            parts.append(
                "INCLUDE IN FRAME: "
                + ", ".join(clean_subjects[:5])
                + "; do not generate an empty environment-only shot if named characters are present"
            )

    # ── 5. Scene content ─────────────────────────────────────────────────────────
    parts.append(visualSummary.strip())

    if answers:
        answer_details = ", ".join(v for v in answers.values() if v)
        if answer_details:
            parts.append(answer_details)

    # ── 6. Time period + tone ────────────────────────────────────────────────────
    if time_period:
        parts.append(f"time period: {time_period.strip()}")

    if tone:
        parts.append(f"visual tone: {tone.strip()}")

    # ── 7. Storyboard craft priorities ───────────────────────────────────────────
    parts.append(STORYBOARD_PRIORITIES)

    # ── 8. Mood / lighting ───────────────────────────────────────────────────────
    modifier = MOOD_MODIFIERS.get(mood.lower(), MOOD_MODIFIERS["neutral"])
    parts.append(modifier)

    # ── 9. Reference films (expanded with visual descriptors) ────────────────────
    if reference_films:
        films = ", ".join(f.strip() for f in reference_films if f and f.strip())
        if films:
            parts.append(f"cinematic references: {films}")

    # ── 10. Director modifier ────────────────────────────────────────────────────
    if director_modifier and director_modifier.strip():
        parts.append(director_modifier.strip())

    # ── 11. Character uniqueness (closing guard — strong closing attention) ──────
    if required_subjects:
        clean_subjects = [s.strip() for s in required_subjects if s and s.strip()]
        if clean_subjects:
            parts.append(
                "CHARACTER RULE: each named lead appears exactly ONCE in frame — "
                "no duplicate clones, no repeated identical faces; "
                "crowd extras are generic background silhouettes, NOT extra copies of the named leads"
            )

    # ── 12. Style suffix ─────────────────────────────────────────────────────────
    parts.append(STYLE_SUFFIX)

    return ", ".join(parts)


def enrich_subjects_with_descriptions(
    names: list[str],
    known_roster: dict[str, str],
) -> list[str]:
    """Add canonical physical descriptions to character names when available.

    Turns ["Mark", "Erica"] into
    ["Mark (young intense programmer, dark hoodie, sharp eyes)",
     "Erica (confident, preppy winter coat)"]
    so the image model knows what each character looks like without relying on
    prior locked-scene conditioning.

    Caps each description at 70 chars to avoid bloating the prompt.
    """
    enriched: list[str] = []
    for name in names:
        key = name.strip().upper()
        desc: Optional[str] = None
        for roster_name, roster_desc in known_roster.items():
            if roster_name.strip().upper() == key:
                desc = roster_desc
                break
        if desc:
            # Remove "(inferred)" tags and trim
            desc = desc.replace("(inferred)", "").strip()
            if len(desc) > 70:
                desc = desc[:70].rsplit(" ", 1)[0]
            enriched.append(f"{name} ({desc})")
        else:
            enriched.append(name)
    return enriched


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
