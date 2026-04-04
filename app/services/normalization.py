from __future__ import annotations

import unicodedata

SPECIAL_REPLACEMENTS = {
    "ñ": "n",
    "ç": "c",
    "œ": "oe",
    "æ": "ae",
}


def normalize_for_comparison(text: str | None) -> str:
    if not text:
        return ""

    lowered = text.strip().lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    no_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")

    normalized = no_marks
    for source, target in SPECIAL_REPLACEMENTS.items():
        normalized = normalized.replace(source, target)

    return normalized
