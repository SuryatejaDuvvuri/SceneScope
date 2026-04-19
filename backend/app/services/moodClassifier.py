import requests
import json
from typing import Optional
from app.config import settings
from app.services.textSummary import summarize_to_chars

# Primary model: fine-tuned SceneScope RoBERTa, called via HF Inference API.
# Previously this was loaded locally via `transformers` + `torch`, but that
# makes the backend slug too large and blows past the 512MB RAM ceiling on
# small Render / similar hosts. Remote inference keeps the service lean.
def _hf_custom_url() -> str:
    if settings.HF_INFERENCE_ENDPOINT_URL:
        return settings.HF_INFERENCE_ENDPOINT_URL
    return f"https://router.huggingface.co/hf-inference/models/{settings.HF_MODEL_ID}"

# Fallback: generic emotion model (via HF Inference API)
HF_GENERIC_MODEL = "j-hartmann/emotion-english-distilroberta-base"
HF_GENERIC_URL = f"https://router.huggingface.co/hf-inference/models/{HF_GENERIC_MODEL}"

# Map the generic model's 7 emotions → our mood labels
# Note: generic model has no "romantic" class; "joy" in dialogue-heavy intimate scenes may
# actually be romantic, but we can't distinguish without context — treat joy as uplifting.
# "surprise" defaults to uplifting rather than tense (most surprises in context are positive).
EMOTION_TO_MOOD = {
    "anger": "tense",
    "disgust": "somber",
    "fear": "tense",
    "joy": "uplifting",
    "neutral": "somber",
    "sadness": "somber",
    "surprise": "uplifting",  # changed: surprise reunions/reveals are more often uplifting than tense
}


class MoodResult:
    def __init__(self, mood: str, confidence: float, source: str):
        self.mood = mood
        self.confidence = confidence
        self.source = source
    def __repr__(self):
        return f"MoodResult(mood={self.mood!r}, confidence={self.confidence:.2f}, source={self.source!r})"


def _extract_hf_error(data) -> str:
    if isinstance(data, dict):
        return str(data.get("error", "")).strip()
    return ""


def _response_json_or_error(response: requests.Response, model_label: str):
    """Parse JSON safely; return normalized error dict on malformed bodies."""
    try:
        return response.json()
    except Exception:
        body = (response.text or "").strip().replace("\n", " ")
        body_preview = body[:160] if body else "<empty>"
        return {
            "error": (
                f"{model_label} returned non-JSON response "
                f"(HTTP {response.status_code}): {body_preview}"
            )
        }


def _parse_hf_predictions(results) -> Optional[list]:
    if results and isinstance(results, list):
        return results[0] if isinstance(results[0], list) else results
    return None


def classify_mood_custom(text: str) -> Optional[MoodResult]:
    """Primary: fine-tuned SceneScope RoBERTa via HuggingFace Inference API."""
    # Dedicated HF Inference Endpoints require paid credits.
    # If no endpoint URL is configured, skip custom model path cleanly.
    if not settings.HF_INFERENCE_ENDPOINT_URL:
        return None
    if not settings.HUGGINGFACE_API_TOKEN or not settings.HF_MODEL_ID:
        return None

    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"}
    truncated = summarize_to_chars(text, 1500, focus_text="emotion mood tension tone")
    payload = {"inputs": truncated, "parameters": {"top_k": None}}

    try:
        response = requests.post(_hf_custom_url(), headers=headers, json=payload, timeout=20)
        results = _response_json_or_error(response, "Custom HF model")

        # Cold-start: HF returns {"error": "Model ... is currently loading", "estimated_time": N}
        error_msg = _extract_hf_error(results)
        if error_msg:
            print(f"Custom HF model unavailable: {error_msg}")
            return None

        predictions = _parse_hf_predictions(results)
        if predictions:
            top = max(predictions, key=lambda x: x["score"])
            return MoodResult(
                mood=top["label"],
                confidence=top["score"],
                source="scenescope-roberta-hf",
            )
    except Exception as e:
        print(f"Custom HF model failed: {e}")
    return None


def classify_mood_generic(text: str) -> Optional[MoodResult]:
    """Fallback: generic emotion model with mood mapping."""
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"}
    payload = {"inputs": summarize_to_chars(text, 1500, focus_text="emotion mood tension tone")}

    try:
        response = requests.post(HF_GENERIC_URL, headers=headers, json=payload, timeout=15)
        results = _response_json_or_error(response, "Generic HF model")

        error_msg = _extract_hf_error(results)
        if error_msg:
            print(f"Generic HF model unavailable: {error_msg}")
            return None

        predictions = _parse_hf_predictions(results)
        if predictions:
            top = max(predictions, key=lambda x: x["score"])
            mood = EMOTION_TO_MOOD.get(top["label"], "somber")
            return MoodResult(
                mood=mood,
                confidence=top["score"],
                source="generic-emotion"
            )
    except Exception as e:
        print(f"Generic model failed: {e}")
    return None


def classify_mood_groq(text: str) -> Optional[MoodResult]:
    """Last resort: ask Groq LLM to classify mood."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    truncated = summarize_to_chars(text, 1500, focus_text="emotion mood tension tone")
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert screenplay tone analyst. Classify the dominant emotional tone of a scene into EXACTLY one of these moods:\n"
                    "- tense: fear, danger, confrontation, pressure, paranoia, threat\n"
                    "- somber: grief, loss, isolation, despair, regret, melancholy\n"
                    "- uplifting: triumph, hope, joy, breakthrough, celebration, relief\n"
                    "- romantic: intimacy, longing, attraction, love, tenderness, desire\n"
                    "- action: urgency, movement, chase, combat, high energy, physical conflict\n\n"
                    "Critical: read the SUBTEXT, not just surface words. A quiet dinner scene between two people who clearly want each other = romantic. "
                    "A character walking alone past a happy crowd = somber (isolation). "
                    "A tense negotiation with polite words = tense. "
                    "Trust what the scene is emotionally doing, not what characters literally say.\n\n"
                    'Respond with ONLY a JSON object: {"mood": "<mood>", "confidence": 0.0-1.0}. No other text.'
                ),
            },
            {
                "role": "user",
                "content": f"Classify the emotional tone of this scene:\n\n{truncated}",
            },
        ],
        "temperature": 0.1,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        parsed = json.loads(content)
        mood = parsed.get("mood", "somber")
        if mood not in ("tense", "somber", "uplifting", "action", "romantic"):
            mood = "somber"
        return MoodResult(
            mood=mood,
            confidence=parsed.get("confidence", 0.7),
            source="groq",
        )
    except Exception as e:
        print(f"Groq classifier failed: {e}")
    return None


def classify_mood(text: str) -> MoodResult:
    """
    Classify scene mood with 3-tier fallback:
    1. Fine-tuned SceneScope RoBERTa (tense/somber)
    2. Generic emotion model (7 emotions → mapped to tense/somber)
    3. Groq LLM as last resort
    """
    result = classify_mood_custom(text)
    if result:
        return result

    result = classify_mood_generic(text)
    if result:
        return result

    result = classify_mood_groq(text)
    if result:
        return result

    return MoodResult(mood="somber", confidence=0.0, source="fallback")
