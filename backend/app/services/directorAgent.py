"""
Director Agent
──────────────
An AI persona that acts as an expert film director.
Interprets vague user feedback into specific visual/cinematographic direction,
provides educational reasoning for film students, and acts as the intermediary
between the user and the image generator.

The Director is CONVERSATIONAL — it interprets feedback, asks a follow-up
question to confirm its understanding, and refines its direction based on
the user's response. Only when the user accepts does the direction get
passed to the image generator.
"""

import requests
import json
import re
from typing import Optional
from app.config import settings


DIRECTOR_SYSTEM = """You are an expert film director with 30 years of experience in visual storytelling. You've studied under masters like Roger Deakins, Emmanuel Lubezki, and Wally Pfister.

Your job: interpret what the user wants for a scene and translate it into precise visual direction for a storyboard artist. You speak with authority but warmth — like a professor who genuinely wants their student to understand WHY each choice matters.

When the user gives feedback (even vague feedback like "too bright" or "doesn't feel right"), you:
1. Acknowledge what they're feeling
2. Diagnose what's causing it cinematically
3. Provide specific, actionable visual direction
4. Briefly explain WHY this direction works (the educational part)
5. Ask ONE follow-up question to confirm you understood correctly

You always respond with a JSON object:
{
  "interpretation": "What you think the user is asking for, in plain language",
  "visual_direction": "Specific instructions for the storyboard artist (lighting, composition, color, angle, mood)",
  "reasoning": "1-2 sentences explaining the cinematographic principle behind your choice. Reference real films or cinematographers when relevant.",
  "prompt_modifier": "A concise phrase to append to the image generation prompt (under 40 words)",
  "follow_up": "ONE specific question to confirm your interpretation or offer an alternative approach. Keep it short."
}

Rules:
- ALWAYS ask a follow-up question — you're having a conversation, not issuing orders
- If the feedback is vague, your follow-up should help narrow down exactly what the user envisions
- Reference real films/cinematographers when it adds educational value
- Keep prompt_modifier focused and technical — it goes directly to the image generator
- Respond with ONLY the JSON object, no other text"""


DIRECTOR_FOLLOWUP_SYSTEM = """You are an expert film director continuing a conversation about a scene's visual direction. The user has responded to your previous follow-up question.

Based on the full conversation history, update your visual direction. The user may have:
- Confirmed your interpretation (refine and finalize)
- Corrected your interpretation (adjust your direction)
- Added new details (incorporate them)

Respond with a JSON object:
{
  "interpretation": "Your updated understanding based on the full conversation",
  "visual_direction": "Updated specific instructions incorporating the user's response",
  "reasoning": "Updated explanation of the cinematographic choices",
  "prompt_modifier": "Updated concise phrase for the image generator (under 40 words)",
  "follow_up": "Another follow-up question if you need more clarity, or null if you're confident in the direction"
}

Rules:
- If the user's response makes the direction clear, set follow_up to null
- If there's still ambiguity, ask ONE more targeted question
- Always update prompt_modifier to reflect the latest understanding
- Respond with ONLY the JSON object, no other text"""


DIRECTOR_USER_TEMPLATE = """Scene: {heading}
Description: {description}
Current Mood: {mood}
Visual Summary: {visual_summary}

User's Feedback: "{feedback}"

{context}

Based on your expertise, interpret the user's feedback and provide specific visual direction."""


def _call_groq(messages: list[dict], max_tokens: int = 400) -> dict:
    """Make a Groq API call and parse the JSON response."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": settings.GROQ_MODEL,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": max_tokens
    }

    response = requests.post(url, headers=headers, json=payload, timeout=20)
    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()

    # Handle markdown-wrapped JSON
    content = re.sub(r'^```(?:json)?\s*', '', content)
    content = re.sub(r'\s*```$', '', content)

    return json.loads(content)


def consult_director(
    heading: str,
    description: str,
    mood: str,
    visual_summary: str,
    feedback: str,
    answers: Optional[dict] = None,
    consistency_context: str = "",
) -> dict:
    """
    Initial consultation: Director interprets feedback and asks a follow-up.

    Returns dict with:
      - interpretation: what the director thinks the user means
      - visual_direction: specific cinematographic instructions
      - reasoning: educational explanation
      - prompt_modifier: concise phrase for the image generator
      - follow_up: question to confirm understanding (or null)
    """

    # If mood is None, 'auto', or empty, classify using moodClassifier
    if not mood or mood.lower() == "auto":
        try:
            from app.services.moodClassifier import classify_mood
            mood_result = classify_mood(description)
            mood = getattr(mood_result, "mood", None) or "neutral"
        except Exception as e:
            print(f"Mood classification failed: {e}")
            mood = "neutral"

    # Build context from answers and consistency info
    context_parts = []
    if answers:
        answer_text = "\n".join(f"- {q}: {a}" for q, a in answers.items() if a)
        if answer_text:
            context_parts.append(f"User's answers to clarifying questions:\n{answer_text}")
    if consistency_context:
        context_parts.append(f"Visual continuity notes: {consistency_context}")

    context = "\n\n".join(context_parts) if context_parts else "No additional context."

    user_content = DIRECTOR_USER_TEMPLATE.format(
        heading=heading or "UNKNOWN",
        description=description[:500],
        mood=mood or "neutral",
        visual_summary=visual_summary or "No visual summary available.",
        feedback=feedback,
        context=context,
    )

    messages = [
        {"role": "system", "content": DIRECTOR_SYSTEM},
        {"role": "user", "content": user_content}
    ]

    try:
        parsed = _call_groq(messages)
        return {
            "interpretation": parsed.get("interpretation", ""),
            "visual_direction": parsed.get("visual_direction", ""),
            "reasoning": parsed.get("reasoning", ""),
            "prompt_modifier": parsed.get("prompt_modifier", feedback),
            "follow_up": parsed.get("follow_up"),
        }
    except Exception as e:
        print(f"Director Agent failed: {e}")
        return {
            "interpretation": feedback,
            "visual_direction": feedback,
            "reasoning": "Director unavailable — using raw feedback.",
            "prompt_modifier": feedback,
            "follow_up": None,
        }


def continue_consultation(
    heading: str,
    description: str,
    mood: str,
    visual_summary: str,
    conversation_history: list[dict],
    user_response: str,
) -> dict:
    """
    Continue the Director conversation after user responds to a follow-up.

    conversation_history: list of previous director exchanges, each containing
      the director's notes and the user's response. Format:
      [{"director": {...notes}, "user_response": "..."}, ...]

    user_response: the user's latest response to the director's follow-up

    Returns same dict structure as consult_director.
    """
    # Build the message history so the LLM sees the full conversation
    messages = [{"role": "system", "content": DIRECTOR_FOLLOWUP_SYSTEM}]

    # Scene context as the first user message
    scene_context = (
        f"Scene: {heading or 'UNKNOWN'}\n"
        f"Description: {description[:500]}\n"
        f"Current Mood: {mood or 'neutral'}\n"
        f"Visual Summary: {visual_summary or 'N/A'}"
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
        return {
            "interpretation": parsed.get("interpretation", ""),
            "visual_direction": parsed.get("visual_direction", ""),
            "reasoning": parsed.get("reasoning", ""),
            "prompt_modifier": parsed.get("prompt_modifier", user_response),
            "follow_up": parsed.get("follow_up"),
        }
    except Exception as e:
        print(f"Director Agent follow-up failed: {e}")
        return {
            "interpretation": user_response,
            "visual_direction": user_response,
            "reasoning": "Director unavailable — using raw response.",
            "prompt_modifier": user_response,
            "follow_up": None,
        }
