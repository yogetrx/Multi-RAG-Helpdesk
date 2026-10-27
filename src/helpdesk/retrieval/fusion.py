
import re


def fuse_results(
    results: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """Deduplicate retrieved chunks and rank them by relevance."""
    if top_k <= 0:
        return []

    best_by_text = {}

    for result in results:
        text = result.get("text", "").strip()

        if not text:
            continue

        # Normalize whitespace and case for duplicate detection.
        normalized = re.sub(r"\s+", " ", text).casefold()
        candidate = {**result, "text": text}

        if normalized not in best_by_text:
            best_by_text[normalized] = candidate
        elif result.get("score", 0.0) > best_by_text[
            normalized
        ].get("score", 0.0):
            best_by_text[normalized] = candidate

    ranked = sorted(
        best_by_text.values(),
        key=lambda item: item.get("score", 0.0),
        reverse=True,
    )

    return ranked[:top_k]
