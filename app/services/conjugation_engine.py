from __future__ import annotations

from dataclasses import dataclass

from app.services.training_engine import clamp_probability


@dataclass(slots=True)
class PronounCheck:
    pronoun: str
    user_answer: str
    correct_answer: str
    is_correct: bool


@dataclass(slots=True)
class TenseUpdateResult:
    new_tense_score: float
    multiplier: float
    checks: list[PronounCheck]


def average_multiplier_from_checks(checks: list[PronounCheck]) -> float:
    if not checks:
        return 1.0
    values = [0.7 if check.is_correct else 1.5 for check in checks]
    return sum(values) / len(values)


def update_tense_score(current_score: float, checks: list[PronounCheck]) -> TenseUpdateResult:
    multiplier = average_multiplier_from_checks(checks)
    new_score = clamp_probability(current_score * multiplier)
    return TenseUpdateResult(new_tense_score=new_score, multiplier=multiplier, checks=checks)
