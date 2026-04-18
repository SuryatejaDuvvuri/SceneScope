import requests
import json
from typing import Optional
from app.config import settings

HF_MODEL = "j-hartmann/emotion-english-distilroberta-base"
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
MOOD_LABELS = ["anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise"]


class MoodResult:
    def __init__(self, mood: str, confidence: float, source: str):
        self.mood = mood
        self.confidence = confidence
        self.source = source 
    def __repr__(self):
        return f"MoodResult(mood={self.mood!r}, confidence={self.confidence:.2f}, source={self.source!r})"


def classify_mood_hf(text: str) -> Optional[MoodResult]:
    headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"}
    payload = {"inputs": text}

    response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=15)
    results = response.json()

    if results and isinstance(results, list):
        predictions = results[0] if isinstance(results[0], list) else results
        # Find the top prediction
        top = max(predictions, key=lambda x: x["score"])
        return MoodResult(
            mood=top["label"],
            confidence=top["score"],
            source="huggingface"
        )
    return None

def classify_mood_groq(text: str) -> Optional[MoodResult]:
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
                "content": "You are a screenplay tone analyzer. Given a scene description, respond with ONLY a JSON object with two keys: \"mood\" (one of: anger, disgust, fear, joy, neutral, sadness, surprise) and \"confidence\" (a float between 0 and 1). No other text."
            },
            {
                "role": "user",
                "content": f"What is the emotional tone of this scene?\n\n{text}"
            }
        ],
        "temperature": 0.1
    }

    response = requests.post(url, headers=headers, json=payload, timeout=15)
    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()
    parsed = json.loads(content)
    return MoodResult(
        mood=parsed["mood"],
        confidence=parsed.get("confidence", 0.0),
        source="groq"
    )


def classify_mood(text: str) -> MoodResult:
    result = classify_mood_hf(text)
    if result:
        return result

    result = classify_mood_groq(text)
    if result:
        return result
    
    return MoodResult(mood="neutral", confidence=0.0, source="fallback")
