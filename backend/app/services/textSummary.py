import re

# Terms that usually carry high visual/directorial value.
_VISUAL_HINTS = {
    "character", "characters", "location", "setting", "lighting", "light", "shadow",
    "camera", "angle", "frame", "composition", "color", "palette", "tone", "mood",
    "prop", "props", "costume", "expression", "movement", "blocking", "background",
    "close-up", "wide", "contrast", "silhouette", "rain", "night", "day", "interior", "exterior",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _split_chunks(text: str) -> list[str]:
    # Prefer sentence boundaries, then comma/semicolon phrases for denser prompts.
    sentence_chunks = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    for sentence in sentence_chunks:
        sentence = sentence.strip()
        if not sentence:
            continue
        parts = [p.strip() for p in re.split(r"[,;]\s+", sentence) if p.strip()]
        chunks.extend(parts if len(parts) > 1 else [sentence])
    return chunks


def _keyword_set(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9-]+", text.lower()))


def summarize_to_chars(text: str, max_chars: int, focus_text: str | None = None) -> str:
    """Summarize text to fit max_chars by selecting salient chunks instead of blunt truncation."""
    cleaned = _clean(text)
    if len(cleaned) <= max_chars:
        return cleaned

    chunks = _split_chunks(cleaned)
    if not chunks:
        return cleaned[:max_chars].rsplit(" ", 1)[0].strip()

    focus_terms = _keyword_set(focus_text or "")

    scored: list[tuple[float, int, str]] = []
    for idx, chunk in enumerate(chunks):
        terms = _keyword_set(chunk)
        overlap = len(terms & focus_terms)
        visual_hits = len(terms & _VISUAL_HINTS)
        length_bonus = min(len(chunk) / 160.0, 1.0)
        lead_bonus = 0.4 if idx == 0 else 0.0
        score = overlap * 3.0 + visual_hits * 1.5 + length_bonus + lead_bonus
        scored.append((score, idx, chunk))

    # Rank by score, then keep original order when assembling.
    scored.sort(key=lambda x: (-x[0], x[1]))

    selected_idx: set[int] = set()
    running_len = 0
    for _, idx, chunk in scored:
        added_len = len(chunk) + (2 if running_len else 0)
        if running_len + added_len <= max_chars:
            selected_idx.add(idx)
            running_len += added_len

    if not selected_idx:
        # Fallback: keep as many whole words as possible.
        return cleaned[:max_chars].rsplit(" ", 1)[0].strip()

    ordered = [chunks[i] for i in range(len(chunks)) if i in selected_idx]
    summary = "; ".join(ordered)

    if len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(" ", 1)[0].strip()
    return summary
