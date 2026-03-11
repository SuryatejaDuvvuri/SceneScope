import requests
import json
import re
from typing import List, Optional
from app.config import settings


class AnalysisResult:
    def __init__(self, vagueElements: List[str], clarifyingQuestions: List[dict], visualSummary: str):
        self.vagueElements = vagueElements
        self.clarifyingQuestions = clarifyingQuestions
        self.visualSummary = visualSummary

    def __repr__(self):
        return (f"AnalysisResult(\n  vagueElements={self.vagueElements!r},\n"
                f"  clarifyingQuestions={self.clarifyingQuestions!r},\n"
                f"  visualSummary={self.visualSummary!r})")


ANALYSIS_PROMPT = """
You are a screenplay scene analyst helping a director pre-visualize scenes. Given a scene heading and description, respond with ONLY a JSON object with these three keys:

1. "vagueElements": A list of strings identifying parts of the scene description that are vague or lack visual specificity (e.g., "stark and simple" — what does that look like?).

2. "clarifyingQuestions": A list of objects, each with:
   - "question": A question a director would need answered to visualize this scene accurately
   - "suggestion": A reasonable default answer based on the scene's mood and context (what an experienced director would choose)
   Example: {"question": "What type of lighting is in the bar?", "suggestion": "Dim warm overhead lights with neon beer signs casting colored reflections"}

3. "visualSummary": A single concise paragraph describing what this scene looks like visually, filling in reasonable defaults for any vague elements. Focused on setting, composition, lighting, color, and mood.

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

    # Handle markdown-wrapped JSON
    content = re.sub(r'^```(?:json)?\s*', '', content)
    content = re.sub(r'\s*```$', '', content)

    parsed = json.loads(content)

    # Normalize clarifyingQuestions — handle both old format (strings) and new format (objects)
    raw_questions = parsed.get("clarifyingQuestions", [])
    questions = []
    for q in raw_questions:
        if isinstance(q, str):
            questions.append({"question": q, "suggestion": ""})
        elif isinstance(q, dict):
            questions.append({
                "question": q.get("question", ""),
                "suggestion": q.get("suggestion", ""),
            })

    return AnalysisResult(
        vagueElements=parsed.get("vagueElements", []),
        clarifyingQuestions=questions,
        visualSummary=parsed.get("visualSummary", "")
    )


REFINEMENT_QUESTIONS_PROMPT = """You are a screenplay scene analyst helping a director refine a storyboard visualization. This scene has already been visualized at least once — the user has answered previous questions and given feedback.

Your job: generate NEW clarifying questions that dig deeper into the scene based on what the user already answered and their feedback. Do NOT repeat any previous questions.

Focus on:
- Aspects NOT yet addressed (camera movement, depth of field, background activity, character expressions, specific props)
- Areas where the user's feedback suggests dissatisfaction (lighting, composition, mood, character positioning)
- Finer visual details that would help an image generator produce a more accurate result

Respond with ONLY a JSON object:
{
  "clarifyingQuestions": [
    {"question": "...", "suggestion": "..."}
  ]
}

Generate 3-4 questions maximum. Each question should explore a DIFFERENT visual aspect from what was already asked. Respond with ONLY valid JSON."""


def generateRefinementQuestions(
    heading: str,
    description: str,
    mood: str,
    visual_summary: str,
    previous_questions: list[dict],
    previous_answers: dict[str, str],
    feedback: str | None = None,
    iteration_number: int = 1,
) -> list[dict]:
    """Generate new clarifying questions for the next refinement iteration.
    Questions are context-aware and avoid repeating what was already asked."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    # Build context showing what was already asked and answered
    prev_qa = ""
    if previous_questions and previous_answers:
        qa_pairs = []
        for q in previous_questions:
            q_text = q.get("question", q) if isinstance(q, dict) else q
            a_text = previous_answers.get(q_text, "(no answer)")
            qa_pairs.append(f"  Q: {q_text}\n  A: {a_text}")
        prev_qa = "\n".join(qa_pairs)

    userContent = (
        f"Scene Heading: {heading}\n"
        f"Scene Description:\n{description[:500]}\n"
        f"Mood: {mood}\n"
        f"Visual Summary: {visual_summary[:300]}\n"
        f"Iteration: {iteration_number}\n\n"
        f"Previous questions and answers:\n{prev_qa}\n\n"
    )
    if feedback:
        userContent += f"User's feedback on the current sketch: \"{feedback}\"\n\n"
    userContent += "Generate NEW clarifying questions that explore different visual aspects from what was already asked."

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": REFINEMENT_QUESTIONS_PROMPT},
            {"role": "user", "content": userContent}
        ],
        "temperature": 0.4
    }

    try:
        print(f"🔍 Calling Groq for refinement questions (iteration {iteration_number})...")
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        data = response.json()

        if "error" in data:
            print(f"❌ Groq API error: {data['error']}")
            return []

        content = data["choices"][0]["message"]["content"].strip()
        print(f"📝 Groq response for refinement questions:\n{content[:500]}")

        content = re.sub(r'^```(?:json)?\s*', '', content)
        content = re.sub(r'\s*```$', '', content)

        parsed = json.loads(content)

        raw_questions = parsed.get("clarifyingQuestions", [])
        questions = []
        for q in raw_questions:
            if isinstance(q, str):
                questions.append({"question": q, "suggestion": ""})
            elif isinstance(q, dict):
                questions.append({
                    "question": q.get("question", ""),
                    "suggestion": q.get("suggestion", ""),
                })
        return questions
    except Exception as e:
        import traceback
        print(f"❌ Refinement question generation failed: {e}")
        traceback.print_exc()
        return []
