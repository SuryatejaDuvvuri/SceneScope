import json
import re
from typing import Any

import requests
from pydantic import ValidationError

from app.config import settings
from app.models.common import RefinementIntent, SceneShotPlan
from app.services.textSummary import summarize_to_chars

SCENE_PLANNER_VERSION = "scene-shot-plan-v1"
INTENT_PARSER_VERSION = "refinement-intent-v1"


def _strip_json_fences(content: str) -> str:
    content = re.sub(r"^```(?:json)?\s*", "", content.strip())
    content = re.sub(r"\s*```$", "", content)
    return content.strip()


def _call_groq_json(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int = 800,
) -> dict[str, Any]:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=25)
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"Groq error: {data['error']}")
    content = data["choices"][0]["message"]["content"]
    return json.loads(_strip_json_fences(content))


def _heuristic_subjects(description: str, dialogue_lines: list[dict] | None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for line in dialogue_lines or []:
        name = (line.get("character") or "").strip()
        if not name:
            continue
        key = name.upper()
        if key not in seen:
            seen.add(key)
            out.append(name)

    pattern = r"\b[A-Z][A-Z]+(?:\s+[A-Z][A-Z]+){0,2}\b"
    for cand in re.findall(pattern, description or ""):
        if len(cand) < 3:
            continue
        normalized = cand.title()
        key = normalized.upper()
        if key not in seen:
            seen.add(key)
            out.append(normalized)
    return out[:6]


def plan_scene_to_shot(
    *,
    heading: str,
    description: str,
    mood: str,
    visual_summary: str,
    dialogue_lines: list[dict] | None = None,
    time_period: str | None = None,
    tone: str | None = None,
) -> SceneShotPlan:
    """Convert screenplay scene text into structured shot plan JSON."""
    system_prompt = """You are a storyboard planning model for screenplay visualization.

Return ONLY valid JSON with exactly this shape:
{
  "required_subjects": ["Name A", "Name B"],
  "ambient_population_hint": "short sentence or null",
  "setting_direction": "one concise sentence",
  "camera_direction": "one concise sentence",
  "blocking_direction": "one concise sentence",
  "lighting_direction": "one concise sentence",
  "continuity_constraints": ["constraint 1", "constraint 2"],
  "negative_constraints": ["do not ...", "avoid ..."]
}

Rules:
- Use concrete visual language (camera, staging, lighting, depth, silhouette clarity).
- Include named speaking characters in required_subjects when present.
- Do not invent plot events absent from the scene.
- Keep each field concise and execution-oriented.
- Return JSON only."""

    safe_desc = summarize_to_chars(description or "", 1200, focus_text=f"{heading} {mood}")
    safe_summary = summarize_to_chars(visual_summary or "", 400, focus_text=f"{heading} {mood}")
    user_prompt = (
        f"Heading: {heading}\n"
        f"Mood: {mood}\n"
        f"Time period: {time_period or 'unspecified'}\n"
        f"Tone: {tone or 'unspecified'}\n"
        f"Description:\n{safe_desc}\n\n"
        f"Current visual summary:\n{safe_summary}\n\n"
        f"Dialogue lines (JSON): {json.dumps(dialogue_lines or [])}\n"
    )

    fallback = SceneShotPlan(
        required_subjects=_heuristic_subjects(description, dialogue_lines),
        ambient_population_hint=None,
        setting_direction="prioritize setting readability and plausible environmental detail from the scene heading",
        camera_direction="favor a clear medium-wide establishing frame with readable depth",
        blocking_direction="stage named subjects with clear silhouette separation and eye-lines",
        lighting_direction="use mood-aligned motivated lighting with clear subject/background separation",
        continuity_constraints=["preserve named character identity and wardrobe consistency across iterations"],
        negative_constraints=["avoid empty environment-only frames when named characters are present"],
    )

    try:
        parsed = _call_groq_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=900,
        )
        return SceneShotPlan.model_validate(parsed)
    except (RuntimeError, ValidationError, requests.RequestException, KeyError, json.JSONDecodeError) as e:
        print(f"scene shot planner fallback: {e}")
        return fallback


def parse_refinement_intent(
    *,
    heading: str,
    description: str,
    feedback: str,
    answers: dict[str, str] | None = None,
) -> RefinementIntent:
    """Parse freeform refinement feedback into strict actionable intent JSON."""
    system_prompt = """You are a refinement intent parser for storyboard updates.

Return ONLY valid JSON with exactly this shape:
{
  "preserve_constraints": ["must stay unchanged"],
  "change_requests": ["what to change now"],
  "avoid_changes": ["what should not happen"],
  "priority": "continuity|change|balanced",
  "confidence": 0.0
}

Rules:
- Extract concrete visual intent from user feedback.
- If user says "keep same" or similar, place that in preserve_constraints.
- Keep lists short and actionable.
- confidence must be 0.0-1.0.
- Return JSON only."""

    safe_desc = summarize_to_chars(description or "", 700, focus_text=heading or "")
    safe_feedback = summarize_to_chars(feedback or "", 500, focus_text=safe_desc)
    user_prompt = (
        f"Heading: {heading}\n"
        f"Description: {safe_desc}\n"
        f"Feedback: {safe_feedback}\n"
        f"Answers JSON: {json.dumps(answers or {})}\n"
    )

    fallback = RefinementIntent(
        preserve_constraints=["preserve character identity, wardrobe, and core setting layout"],
        change_requests=[feedback.strip()] if feedback and feedback.strip() else [],
        avoid_changes=["do not replace the named leads with different people"],
        priority="balanced",
        confidence=0.45,
    )

    try:
        parsed = _call_groq_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=500,
        )
        intent = RefinementIntent.model_validate(parsed)
        intent.confidence = max(0.0, min(1.0, float(intent.confidence)))
        if intent.priority not in {"continuity", "change", "balanced"}:
            intent.priority = "balanced"
        return intent
    except (RuntimeError, ValidationError, requests.RequestException, KeyError, json.JSONDecodeError) as e:
        print(f"refinement intent parser fallback: {e}")
        return fallback
