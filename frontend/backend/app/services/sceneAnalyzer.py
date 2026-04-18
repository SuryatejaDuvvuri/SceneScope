import requests
import json
from typing import List, Optional
from app.config import settings


class AnalysisResult:
    def __init__(self, vagueElements: List[str], clarifyingQuestions: List[str], visualSummary: str):
        self.vagueElements = vagueElements
        self.clarifyingQuestions = clarifyingQuestions
        self.visualSummary = visualSummary

    def __repr__(self):
        return (f"AnalysisResult(\n  vagueElements={self.vagueElements!r},\n"
                f"  clarifyingQuestions={self.clarifyingQuestions!r},\n"
                f"  visualSummary={self.visualSummary!r})")


ANALYSIS_PROMPT = """
You are a screenplay scene analyst. Given a scene heading and description, analyze the scene and respond with ONLY a JSON object with these three keys:

1. "vagueElements": A list of strings identifying parts of the scene description that are vague, subjective, or lack visual specificity (e.g., "stark and simple" — what does that look like?).

2. "clarifyingQuestions": A list of questions a director or artist would need answered to visualize this scene accurately (e.g., "How many tables are in the bar?", "What lighting — dim, fluorescent, neon?").

3. "visualSummary": A single concise paragraph describing what this scene looks like visually, filling in reasonable defaults for any vague elements. This should read like a storyboard note — focused on setting, composition, lighting, and mood.

Respond with ONLY valid JSON. No other text."""


def analyzeScene(heading: str, description: str, mood: Optional[str] = None) -> AnalysisResult:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    userContent = f"Scene Heading: {heading}\n\nScene Description:\n{description}"
    if mood:
        userContent += f"\n\nDetected Mood: {mood}"

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": ANALYSIS_PROMPT},
            {"role": "user", "content": userContent}
        ],
        "temperature": 0.3
    }

    response = requests.post(url, headers=headers, json=payload, timeout=20)
    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()
    parsed = json.loads(content)

    return AnalysisResult(
        vagueElements=parsed.get("vagueElements", []),
        clarifyingQuestions=parsed.get("clarifyingQuestions", []),
        visualSummary=parsed.get("visualSummary", "")
    )

# result = analyzeScene("INT. CAMPUS BAR - NIGHT", description, mood="neutral")
# print(result)
