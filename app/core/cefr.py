from __future__ import annotations

from typing import Final


CEFR_LEVELS: Final[tuple[str, ...]] = ("A1", "A2", "B1", "B2", "C1", "C2")
CEFR_LEVEL_SET: Final[frozenset[str]] = frozenset(CEFR_LEVELS)
CEFR_LEVEL_INDEX: Final[dict[str, int]] = {
    level: index for index, level in enumerate(CEFR_LEVELS)
}
CEFR_TAG_SLUGS: Final[frozenset[str]] = frozenset(
    level.lower() for level in CEFR_LEVELS
)


def normalize_cefr_level(value: str | None) -> str | None:
    """Return a canonical CEFR level or reject an unsupported value."""

    level = (value or "").strip().upper()
    if not level:
        return None
    if level not in CEFR_LEVEL_SET:
        allowed = ", ".join(CEFR_LEVELS)
        raise ValueError(f"Unsupported CEFR level '{value}'. Expected one of: {allowed}.")
    return level


def earliest_cefr_level(*values: str | None) -> str | None:
    """Choose the easiest classified sense when database headwords are shared."""

    levels = [normalize_cefr_level(value) for value in values]
    classified = [level for level in levels if level is not None]
    if not classified:
        return None
    return min(classified, key=CEFR_LEVEL_INDEX.__getitem__)
