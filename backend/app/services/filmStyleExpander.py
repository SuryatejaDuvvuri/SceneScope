"""
Film visual-style lookup via Groq LLM.

When the user enters reference films like "Dune" or "The Social Network",
we expand them into actionable visual descriptors using Groq's knowledge of
cinematography so the image model knows *what those films look like*, not just
their names.

Results are cached in-memory per server session — one Groq call per unique
film title across all requests. If Groq is unavailable we fall back gracefully
to the bare title so the prompt still includes the reference.
"""

import re
import requests
from app.config import settings

# In-memory cache: film title (lowercased) → style descriptor string
_CACHE: dict[str, str] = {}

_SYSTEM_PROMPT = """You are a cinematography expert advising storyboard artists.
When given a film title, respond with a SINGLE concise descriptor phrase (25-50 words) that captures:
- characteristic shot framing (close-ups, wide establishing, dutch angle, etc.)
- lighting quality and color palette
- visual mood and emotional tone
- any distinctive camera or staging style

Write ONLY the descriptor phrase. Do not repeat the film title. No preamble, no quotes."""


def _ask_groq(film_title: str) -> str:
    """Call Groq to describe the visual style of a single film."""
    if not settings.GROQ_API_KEY:
        return film_title

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f'Describe the cinematography style of: "{film_title}"'},
        ],
        "temperature": 0.3,
        "max_tokens": 90,
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        data = response.json()
        if "error" in data:
            print(f"Film style lookup error for '{film_title}': {data['error']}")
            return film_title
        content = data["choices"][0]["message"]["content"].strip()
        # Strip stray quotes or leading punctuation
        content = re.sub(r'^["\'\-–—]+\s*', "", content)
        content = re.sub(r'\s*["\'\-–—]+$', "", content)
        return content or film_title
    except Exception as e:
        print(f"Film style lookup failed for '{film_title}': {e}")
        return film_title


def expand_film_styles(film_titles: list[str]) -> list[str]:
    """
    Expand a list of film titles into actionable visual style descriptors.

    Returns strings of the form:
        "Dune (vast desert vistas, extreme wide establishing shots, harsh backlit
         silhouettes, muted gold-and-ochre palette, Villeneuve's stillness and scale)"

    These are intended for direct inclusion in an image generation prompt so
    the model understands what "Dune" looks like visually rather than treating
    it as an opaque title.

    Falls back to bare title strings when Groq is unavailable, so the prompt
    is never broken by a failed lookup.
    """
    if not film_titles:
        return []

    expanded: list[str] = []
    for title in film_titles:
        title = title.strip()
        if not title:
            continue
        key = title.lower()
        if key not in _CACHE:
            _CACHE[key] = _ask_groq(title)
        style = _CACHE[key]
        if style and style.lower() != title.lower():
            expanded.append(f"{title} ({style})")
        else:
            expanded.append(title)
    return expanded
