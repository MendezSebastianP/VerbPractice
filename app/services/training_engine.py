from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone

from app.services.normalization import normalize_for_comparison

MIN_PROBABILITY = 20.0
MAX_PROBABILITY = 100000.0


@dataclass(slots=True)
class WeightedItem:
    item_id: int
    probability: float
    last_seen: datetime | None = None


@dataclass(slots=True)
class GradeResult:
    is_correct: bool
    is_synonym: bool
    multiplier: float
    expected_primary: str


def recency_multiplier(last_seen: datetime | None, now: datetime | None = None) -> float:
    if last_seen is None:
        return 1.15

    if now is None:
        now = datetime.now(timezone.utc)

    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)

    delta_days = max(0.0, (now - last_seen).total_seconds() / 86400)
    return min(1.5, 1.0 + 0.05 * delta_days)


def weighted_sample_without_replacement(items: list[WeightedItem], count: int) -> list[int]:
    if not items or count <= 0:
        return []

    pool: list[tuple[int, float]] = []
    for item in items:
        effective_weight = max(0.0001, float(item.probability) * recency_multiplier(item.last_seen))
        pool.append((item.item_id, effective_weight))

    selected: list[int] = []
    for _ in range(min(count, len(pool))):
        total = sum(weight for _, weight in pool)
        if total <= 0:
            break

        roll = random.random() * total
        cumulative = 0.0
        chosen_index = 0
        for idx, (_, weight) in enumerate(pool):
            cumulative += weight
            if roll <= cumulative:
                chosen_index = idx
                break

        selected.append(pool[chosen_index][0])
        del pool[chosen_index]

    return selected


def clamp_probability(value: float) -> float:
    return max(MIN_PROBABILITY, min(MAX_PROBABILITY, value))


def update_probability(current: float, multiplier: float) -> float:
    return clamp_probability(current * multiplier)


def grade_translation(
    answer: str,
    accepted: list[str],
    synonym_answers: list[str] | None = None,
) -> GradeResult:
    normalized_answer = normalize_for_comparison(answer)
    normalized_accepted = [normalize_for_comparison(val) for val in accepted if val.strip()]
    normalized_synonyms = [normalize_for_comparison(val) for val in (synonym_answers or []) if val.strip()]

    expected_primary = accepted[0].strip() if accepted else ""

    if normalized_answer and normalized_answer in normalized_accepted:
        return GradeResult(is_correct=True, is_synonym=False, multiplier=0.7, expected_primary=expected_primary)

    if normalized_answer and normalized_answer in normalized_synonyms:
        return GradeResult(is_correct=True, is_synonym=True, multiplier=0.8, expected_primary=expected_primary)

    return GradeResult(is_correct=False, is_synonym=False, multiplier=1.3, expected_primary=expected_primary)


def hint_text(expected: str, level: int) -> str:
    base = (expected or "").split(",")[0].strip()
    capped = max(0, min(level, len(base)))
    return base[:capped]
