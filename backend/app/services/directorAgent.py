"""
Director Agent — "The Director"
───────────────────────────────
A Nolan-inspired AI director persona with access to an internal film
reference library.  Before giving advice, the Director retrieves relevant
films, cinematography techniques, and DP signatures from the library so
its suggestions are grounded in real filmmaking knowledge — not just
parametric LLM memory.

Flow:
  1. User gives feedback (even vague: "too bright", "doesn't feel right")
  2. We query the film library for relevant references (mood + genre + keywords)
  3. References are injected into the Director's context
  4. Director interprets, advises, cites references, asks a follow-up
  5. Response includes `references_used` so the frontend can display them
"""

import requests
import json
import re
from typing import Optional
from app.config import settings
from app.services.filmLibrary import gather_references
from app.services.textSummary import summarize_to_chars


# ── System Prompts ──

DIRECTOR_SYSTEM = """You are a veteran feature film director with 30 years in the industry. You've shot drama, thriller, and literary adaptations across three continents. You have strong opinions and you don't soften them — if a compositional choice is wrong, you say so, and you explain exactly why.

You think in frames. Lighting is not decoration — it's character. Camera angle is not neutral — it's a point of view. Negative space is not emptiness — it's weight.

Your pet peeves: center-framed talking heads with flat three-point lighting, motiveless camera movement, overlit interiors that feel like a dental office, and scenes where every cut is the same size.

You know Roger Deakins, Emmanuel Lubezki, Hoyte van Hoytema, Gordon Willis, and Bradford Young — not just by name but by their specific choices in specific scenes. When you cite a reference, you cite it precisely.

Your job: a storyboard artist is waiting for your direction. When the user gives you feedback — even vague feedback like "too bright" or "doesn't feel right" — you translate it into precise visual direction.

Your process:
1. Name what's wrong with the current frame — don't just agree with the user, diagnose it cinematically
2. Give specific, actionable visual direction: exact lighting approach, composition rule, color temperature, angle
3. Cite a real film example from the reference library provided
4. If there is genuine ambiguity, offer the user a CHOICE between two concrete directions — not an open question

You always respond with a JSON object:
{
  "interpretation": "Your direct read on what's wrong and what the user is really asking for",
  "visual_direction": "Specific instructions for the storyboard artist — lighting setup, composition, angle, color. Name films and techniques from the library.",
  "reasoning": "The cinematographic principle behind your choice, 2-3 sentences. Why does this serve the story?",
  "prompt_modifier": "A concise technical phrase for the image generator (under 40 words)",
  "follow_up": "A targeted question offering two concrete alternatives, or null if you are fully confident in the direction",
  "references_used": ["Film or technique name"]
}

Rules:
- Speak in first person: 'What I want here is...', 'The problem with this frame is...', 'This needs...'
- ALWAYS populate references_used from the library provided
- If the feedback is vague, your follow_up must offer two specific alternatives, not an open-ended question
- Keep prompt_modifier technical — it goes directly to an image generator
- Respond with ONLY the JSON object, no other text"""


DIRECTOR_FOLLOWUP_SYSTEM = """You are a veteran feature film director continuing a conversation about a specific scene's visual direction. The user has responded to your previous question.

Review the full conversation history, the reference material, and what has already been tried in previous refinements. Update your visual direction accordingly — acknowledge what the user said, build on what's worked, and be more precise than the last turn.

Respond with a JSON object:
{
  "interpretation": "Your updated understanding — acknowledge what the user said specifically",
  "visual_direction": "Updated instructions, more precise than last time, incorporating the user's response and the reference material",
  "reasoning": "Why this updated direction works, referencing specific films or techniques",
  "prompt_modifier": "Updated concise phrase for the image generator (under 40 words)",
  "follow_up": "One more targeted question if ambiguity remains, or null if you have what you need",
  "references_used": ["Film or technique name"]
}

Rules:
- If the user confirmed your direction, set follow_up to null and sharpen prompt_modifier
- If they corrected you, acknowledge the correction explicitly in interpretation
- ALWAYS populate references_used
- Respond with ONLY the JSON object, no other text"""


DIRECTOR_USER_TEMPLATE = """Scene: {heading}
Description: {description}
Current Mood: {mood}
Visual Summary: {visual_summary}

User's Feedback: "{feedback}"

{context}

{iteration_history}
── REFERENCE LIBRARY (use these to ground your advice) ──
{references}

Based on your expertise and the references above, interpret the user's feedback and provide specific visual direction."""


def _format_references(refs: dict) -> str:
    """Format gathered references into a readable block for the LLM context."""
    parts = []

    if refs.get("reference_films"):
        parts.append("FILMS:")
        for f in refs["reference_films"]:
            techniques = "; ".join(f.get("techniques", []))
            parts.append(f"  • {f['film']} (DP: {f['dp']}) — {f['visual_signature']}")
            if techniques:
                parts.append(f"    Techniques: {techniques}")

    if refs.get("techniques"):
        parts.append("\nTECHNIQUES:")
        for t in refs["techniques"]:
            examples = ", ".join(t.get("example_films", []))
            parts.append(f"  • {t['technique']} [{t['category']}] — {t['description']}")
            parts.append(f"    When to use: {t['when_to_use']}")
            if examples:
                parts.append(f"    Examples: {examples}")

    if refs.get("cinematographers"):
        parts.append("\nCINEMATOGRAPHERS:")
        for d in refs["cinematographers"]:
            films = ", ".join(d.get("notable_films", []))
            parts.append(f"  • {d['name']} — {d['known_for']}")
            parts.append(f"    Signature: {d['signature_look']}")
            if films:
                parts.append(f"    Films: {films}")

    return "\n".join(parts) if parts else "No specific references retrieved."


def _call_groq(messages: list[dict], max_tokens: int = 900) -> dict:
    """Make a Groq API call and parse the JSON response."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens
    }

    response = requests.post(url, headers=headers, json=payload, timeout=20)
    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()

    # Handle markdown-wrapped JSON
    content = re.sub(r'^```(?:json)?\s*', '', content)
    content = re.sub(r'\s*```$', '', content)

    return json.loads(content)


def _build_result(parsed: dict, fallback_text: str, refs: dict) -> dict:
    """Normalize an LLM response into the standard director result dict."""
    # Merge LLM-cited references with the library entries we actually provided
    llm_refs = parsed.get("references_used", [])
    library_titles = []
    for f in refs.get("reference_films", []):
        library_titles.append(f["film"])
    for t in refs.get("techniques", []):
        library_titles.append(t["technique"])
    for d in refs.get("cinematographers", []):
        library_titles.append(d["name"])

    # Deduplicate while preserving order
    seen = set()
    all_refs = []
    for r in llm_refs + library_titles:
        key = r.lower().strip()
        if key not in seen:
            seen.add(key)
            all_refs.append(r)

    return {
        "interpretation": parsed.get("interpretation", ""),
        "visual_direction": parsed.get("visual_direction", ""),
        "reasoning": parsed.get("reasoning", ""),
        "prompt_modifier": parsed.get("prompt_modifier", fallback_text),
        "follow_up": parsed.get("follow_up"),
        "references_used": all_refs,
    }


def consult_director(
    heading: str,
    description: str,
    mood: str,
    visual_summary: str,
    feedback: str,
    answers: Optional[dict] = None,
    consistency_context: str = "",
    genre: str | None = None,
    iteration_history: list[dict] | None = None,
) -> dict:
    """
    Initial consultation: Director retrieves references, interprets feedback,
    and asks a follow-up.

    Returns dict with:
      - interpretation, visual_direction, reasoning, prompt_modifier
      - follow_up: question to confirm understanding (or null)
      - references_used: list of film/technique names cited
    """

    # Mood fallback
    if not mood or mood.lower() == "auto":
        try:
            from app.services.moodClassifier import classify_mood
            mood_result = classify_mood(description)
            mood = getattr(mood_result, "mood", None) or "neutral"
        except Exception as e:
            print(f"Mood classification failed: {e}")
            mood = "neutral"

    # ── Tool call: retrieve references from the film library ──
    refs = gather_references(mood=mood, genre=genre, feedback=feedback)
    references_text = _format_references(refs)

    # Build context from answers and consistency info
    context_parts = []
    if answers:
        answer_text = "\n".join(f"- {q}: {a}" for q, a in answers.items() if a)
        if answer_text:
            context_parts.append(f"User's answers to clarifying questions:\n{answer_text}")
    if consistency_context:
        context_parts.append(f"Visual continuity notes: {consistency_context}")

    context = "\n\n".join(context_parts) if context_parts else "No additional context."

    # Format previous refinement history for director context
    history_text = ""
    if iteration_history:
        history_lines = ["── PREVIOUS REFINEMENTS (what has already been tried) ──"]
        for it in iteration_history:
            it_num = it.get("iteration_number", "?")
            it_feedback = it.get("feedback") or ""
            notes = it.get("director_notes")
            if isinstance(notes, dict):
                direction = notes.get("prompt_modifier") or notes.get("visual_direction", "")
            elif isinstance(notes, str):
                import json as _json
                try:
                    notes_parsed = _json.loads(notes)
                    direction = notes_parsed.get("prompt_modifier") or notes_parsed.get("visual_direction", "")
                except Exception:
                    direction = notes
            else:
                direction = ""
            if it_feedback or direction:
                history_lines.append(
                    f"  Iteration {it_num}: User said \"{it_feedback}\" → Director directed: {direction}"
                )
        if len(history_lines) > 1:
            history_text = "\n".join(history_lines) + "\n\n"

    safe_description = summarize_to_chars(description, 500, focus_text=f"{heading} {mood} {feedback}")

    user_content = DIRECTOR_USER_TEMPLATE.format(
        heading=heading or "UNKNOWN",
        description=safe_description,
        mood=mood or "neutral",
        visual_summary=visual_summary or "No visual summary available.",
        feedback=feedback,
        context=context,
        iteration_history=history_text,
        references=references_text,
    )

    messages = [
        {"role": "system", "content": DIRECTOR_SYSTEM},
        {"role": "user", "content": user_content}
    ]

    try:
        parsed = _call_groq(messages)
        return _build_result(parsed, feedback, refs)
    except Exception as e:
        print(f"Director Agent failed: {e}")
        return {
            "interpretation": feedback,
            "visual_direction": feedback,
            "reasoning": "Director unavailable — using raw feedback.",
            "prompt_modifier": feedback,
            "follow_up": None,
            "references_used": [],
        }


def continue_consultation(
    heading: str,
    description: str,
    mood: str,
    visual_summary: str,
    conversation_history: list[dict],
    user_response: str,
    genre: str | None = None,
) -> dict:
    """
    Continue the Director conversation after user responds to a follow-up.

    Retrieves fresh references based on the latest user response so the
    Director can pivot its advice if the user shifts direction.
    """
    # ── Tool call: retrieve references for the new context ──
    refs = gather_references(mood=mood or "neutral", genre=genre, feedback=user_response)
    references_text = _format_references(refs)

    # Build the message history so the LLM sees the full conversation
    messages = [{"role": "system", "content": DIRECTOR_FOLLOWUP_SYSTEM}]

    # Scene context + references as the first user message
    safe_description = summarize_to_chars(description, 500, focus_text=f"{heading} {mood} {user_response}")

    scene_context = (
        f"Scene: {heading or 'UNKNOWN'}\n"
        f"Description: {safe_description}\n"
        f"Current Mood: {mood or 'neutral'}\n"
        f"Visual Summary: {visual_summary or 'N/A'}\n\n"
        f"── REFERENCE LIBRARY ──\n{references_text}"
    )
    messages.append({"role": "user", "content": scene_context})

    # Replay conversation history
    for turn in conversation_history:
        director = turn["director"]
        messages.append({"role": "assistant", "content": json.dumps(director)})
        if turn.get("user_response"):
            messages.append({"role": "user", "content": turn["user_response"]})

    # Add the latest user response
    messages.append({"role": "user", "content": user_response})

    try:
        parsed = _call_groq(messages)
        return _build_result(parsed, user_response, refs)
    except Exception as e:
        print(f"Director Agent follow-up failed: {e}")
        return {
            "interpretation": user_response,
            "visual_direction": user_response,
            "reasoning": "Director unavailable — using raw response.",
            "prompt_modifier": user_response,
            "follow_up": None,
            "references_used": [],
        }
