import requests
import json
from typing import Optional
from app.config import settings

# Primary: your fine-tuned model (tense/somber binary classifier)
HF_CUSTOM_MODEL = settings.HF_MODEL_ID
HF_CUSTOM_URL = f"https://api-inference.huggingface.co/models/{HF_CUSTOM_MODEL}"

# Fallback: generic emotion model
HF_GENERIC_MODEL = "j-hartmann/emotion-english-distilroberta-base"
HF_GENERIC_URL = f"https://api-inference.huggingface.co/models/{HF_GENERIC_MODEL}"

# Map the generic model's 7 emotions → our mood labels
EMOTION_TO_MOOD = {
    "anger": "tense",
    "disgust": "somber",
    "fear": "tense",
    "joy": "uplifting",
    "neutral": "somber",
    "sadness": "somber",
    "surprise": "tense",
}


class MoodResult:
    def __init__(self, mood: str, confidence: float, source: str):
        self.mood = mood
        self.confidence = confidence
        self.source = source
    def __repr__(self):
        return f"MoodResult(mood={self.mood!r}, confidence={self.confidence:.2f}, source={self.source!r})"


def classify_mood_custom(text: str) -> Optional[MoodResult]:
    """Use your fine-tuned SceneScope model (tense vs somber)."""
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"}
    payload = {"inputs": text[:1500]}

    try:
        response = requests.post(HF_CUSTOM_URL, headers=headers, json=payload, timeout=20)
        results = response.json()

        if results and isinstance(results, list):
            predictions = results[0] if isinstance(results[0], list) else results
            top = max(predictions, key=lambda x: x["score"])
            return MoodResult(
                mood=top["label"],
                confidence=top["score"],
                source="scenescope-roberta"
            )
    except Exception as e:
        print(f"Custom model failed: {e}")
    return None


def classify_mood_generic(text: str) -> Optional[MoodResult]:
    """Fallback: generic emotion model with mood mapping."""
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"}
    payload = {"inputs": text[:1500]}

    try:
        response = requests.post(HF_GENERIC_URL, headers=headers, json=payload, timeout=15)
        results = response.json()

        if results and isinstance(results, list):
            predictions = results[0] if isinstance(results[0], list) else results
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
    """Last resort: ask Groq LLM to classify."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": 'You are a screenplay tone analyzer. Given a scene, respond with ONLY a JSON object: {"mood": "tense|somber", "confidence": 0.0-1.0}. No other text.'
            },
            {
                "role": "user",
                "content": f"What is the emotional tone of this scene?\n\n{text[:1500]}"
            }
        ],
        "temperature": 0.1
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        parsed = json.loads(content)
        return MoodResult(
            mood=parsed["mood"],
            confidence=parsed.get("confidence", 0.0),
            source="groq"
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
