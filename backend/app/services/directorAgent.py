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

DIRECTOR_SYSTEM = """You are The Director: an exacting filmcraft coach for screenplay pre-visualization.

Your job is not to flatter. Your job is to turn vague writer feedback into concrete shot direction that an image model can execute.

Use this diagnosis -> direction framework:
1) Diagnose the mismatch (tone, blocking, lens distance, lighting motivation, composition hierarchy).
2) Pick one dominant visual intention.
3) Specify shot grammar in concrete terms:
   - framing (e.g. wide/two-shot/close-up)
   - camera height/angle and implied lens distance
   - lighting pattern, key/fill ratio, color temperature
   - subject/background separation
   - continuity constraints that must not change
   - storyboard craft checks: perspective readability, believable anatomy simplification, clear staging/blocking, expressive acting beats
4) Ground in 1-2 references from the provided library.

Return ONLY JSON:
{
  "interpretation": "one short paragraph diagnosing what is wrong now and what the user intends",
  "visual_direction": "numbered actionable instructions (3-6 bullets compressed into prose)",
  "reasoning": "2-3 sentences linking direction to story psychology and viewer perception",
  "prompt_modifier": "technical generator phrase (35-70 words, concrete camera+lighting+continuity constraints)",
  "follow_up": "null when clear; otherwise forced choice in A/B form",
  "references_used": ["only items that are in the supplied reference library"]
}

Hard rules:
- Never produce generic advice like "make it cinematic" or "improve lighting".
- If continuity context exists, explicitly preserve identity/wardrobe/palette/layout.
- Prefer decisive direction over optionality; ask follow_up only when ambiguity blocks execution.
- Respond with JSON only."""


DIRECTOR_FOLLOWUP_SYSTEM = """You are The Director continuing a refinement consultation.

The user has answered your previous A/B-style follow-up. You must converge quickly.

Output JSON:
{
  "interpretation": "explicitly acknowledge user correction/choice",
  "visual_direction": "tighter than previous turn; remove ambiguity",
  "reasoning": "why this better serves scene intent",
  "prompt_modifier": "35-70 word execution-ready modifier with camera+lighting+continuity specifics",
  "follow_up": "null unless absolutely required; if required, provide A/B forced choice",
  "references_used": ["only references from supplied library"]
}

Rules:
- Prioritize specificity and continuity over flourish.
- Avoid repeating previous generic wording.
- Respond with JSON only."""


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
        "temperature": settings.DIRECTOR_TEMPERATURE,
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

    # Deduplicate while preserving order, then keep it short for UI relevance.
    seen = set()
    all_refs = []
    for r in llm_refs + library_titles:
        key = r.lower().strip()
        if key not in seen:
            seen.add(key)
            all_refs.append(r)

    prompt_modifier = (parsed.get("prompt_modifier") or "").strip()
    if len(prompt_modifier) < 25:
        # Recover from low-quality output by distilling visual_direction into a
        # concrete modifier rather than passing user feedback verbatim.
        source = parsed.get("visual_direction") or fallback_text
        prompt_modifier = summarize_to_chars(
            source,
            180,
            focus_text="camera framing lighting color temperature continuity composition lens",
        )

    return {
        "interpretation": parsed.get("interpretation", ""),
        "visual_direction": parsed.get("visual_direction", ""),
        "reasoning": parsed.get("reasoning", ""),
        "prompt_modifier": prompt_modifier or fallback_text,
        "follow_up": parsed.get("follow_up"),
        "references_used": all_refs[:8],
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
