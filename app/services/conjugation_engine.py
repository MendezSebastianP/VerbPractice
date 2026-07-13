from __future__ import annotations

from dataclasses import dataclass
import re

from app.services.normalization import normalize_for_comparison
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


def accepted_conjugation_forms(expected: str, language_code: str) -> set[str]:
    """Expand display notation into the individual forms learners may enter."""
    expected = expected.strip()
    forms = {expected}

    if language_code == "RU":
        alternatives = re.fullmatch(r"(.+?)\s+\(([^()]*)\)", expected)
        if alternatives:
            forms.add(alternatives.group(1).strip())
            forms.update(part.strip() for part in alternatives.group(2).split(",") if part.strip())
        return forms

    if language_code == "FR":
        pending = [expected]
        attached_group = re.compile(r"(?<=\S)\(([^(),\s]+)\)")
        while pending:
            candidate = pending.pop()
            match = attached_group.search(candidate)
            if not match:
                forms.add(candidate)
                continue
            pending.append(candidate[: match.start()] + candidate[match.end() :])
            pending.append(candidate[: match.start()] + match.group(1) + candidate[match.end() :])
        return forms

    # Parenthesized register notes are display metadata, not part of the form.
    annotation = re.fullmatch(r"(.+?)\s+\([^()]+\)", expected)
    if annotation:
        forms.add(annotation.group(1).strip())
    return forms


def conjugation_answer_is_correct(user_answer: str, expected: str, language_code: str) -> bool:
    normalized_answer = normalize_for_comparison(user_answer)
    return bool(normalized_answer) and any(
        normalized_answer == normalize_for_comparison(candidate)
        for candidate in accepted_conjugation_forms(expected, language_code)
    )


def average_multiplier_from_checks(
    checks: list[PronounCheck],
    *,
    correct_multiplier: float = 0.7,
) -> float:
    if not checks:
        return 1.0
    values = [correct_multiplier if check.is_correct else 1.5 for check in checks]
    return sum(values) / len(values)


def update_tense_score(
    current_score: float,
    checks: list[PronounCheck],
    *,
    correct_multiplier: float = 0.7,
) -> TenseUpdateResult:
    multiplier = average_multiplier_from_checks(checks, correct_multiplier=correct_multiplier)
    new_score = clamp_probability(current_score * multiplier)
    return TenseUpdateResult(new_tense_score=new_score, multiplier=multiplier, checks=checks)
