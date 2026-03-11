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

STYLE_PREFIX = "cinematic storyboard frame, detailed color illustration, film pre-visualization style"


def buildPrompt(visualSummary: str, mood: str, answers: Optional[Dict[str, str]] = None) -> str:
    parts = [STYLE_PREFIX]

    modifier = MOOD_MODIFIERS.get(mood.lower(), MOOD_MODIFIERS["neutral"])
    parts.append(modifier)
    parts.append(visualSummary.strip())

    if answers:
        answerDetails = ", ".join(f"{v}" for v in answers.values() if v)
        if answerDetails:
            parts.append(answerDetails)

    return ", ".join(parts)

# prompt = buildPrompt(
#     visualSummary="A dimly lit campus bar with two college students sitting at a small table",
#     mood="neutral",
#     answers={"lighting": "dim neon signs", "tables": "a few scattered tables"}
# )
