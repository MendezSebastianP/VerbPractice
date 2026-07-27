from __future__ import annotations

from collections.abc import Sequence
import logging
import re
from time import perf_counter
from typing import Any

from app.services.normalization import normalize_for_comparison
from app.services.local_nli import (
    MODEL_NAME as NLI_MODEL_NAME,
    get_local_nli_verifier,
)
from app.services.offline_dictionary_service import (
    MODEL_NAME,
    get_local_sense_ranker,
)

LOGGER = logging.getLogger(__name__)

# These are prototype thresholds, intentionally exposed in every response. They
# should be calibrated against reviewed learner answers before production use.
POSITIVE_CORRECT_THRESHOLD = 0.86
POSITIVE_RELATED_THRESHOLD = 0.80
CONCEPT_COVERAGE_THRESHOLD = 0.82
HARD_NEGATIVE_THRESHOLD = 0.84
SAFE_NEGATIVE_MARGIN = 0.025
COMPETITIVE_NEGATIVE_MARGIN = 0.01
ORDERED_NEGATIVE_THRESHOLD = 0.60
ORDERED_NEGATIVE_MARGIN = 0.08
NLI_ENTAILMENT_THRESHOLD = 0.30
NLI_AXIS_CONFIRMED_ENTAILMENT_THRESHOLD = 0.17
NLI_AXIS_CONFIRMED_MAX_TOKENS = 12
NLI_AXIS_CONFIRMED_MAX_CONTRADICTION = 0.10
NLI_AXIS_CONFIRMED_DECISION_MARGIN = 0.12
STRUCTURED_PARTIAL_POSITIVE_THRESHOLD = 0.86
STRUCTURED_PARTIAL_MAX_TOKENS = 12
NLI_MAX_CONTRADICTION = 0.35
NLI_DECISION_MARGIN = 0.09
NLI_NEGATIVE_MARGIN = 0.08

_APOSTROPHE_RE = re.compile(r"['’`´]")
_NON_WORD_RE = re.compile(r"[\W_]+", flags=re.UNICODE)
_TOKEN_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)

_NEGATION_MARKERS = {
    # English
    "no",
    "not",
    "never",
    "neither",
    "nor",
    "without",
    "cannot",
    "cant",
    "dont",
    "doesnt",
    "didnt",
    "isnt",
    "arent",
    "wasnt",
    "werent",
    # French
    "ne",
    "n",
    "pas",
    "jamais",
    "aucun",
    "aucune",
    "sans",
    "ni",
    # Spanish / Portuguese
    "nunca",
    "jamas",
    "sin",
    "tampoco",
    "nadie",
    "ningun",
    "ninguna",
    "nao",
    "sem",
    # German / Italian
    "nicht",
    "kein",
    "keine",
    "nie",
    "ohne",
    "non",
    "mai",
    "senza",
    # Russian
    "не",
    "нет",
    "никогда",
    "без",
}
_CORRECTIVE_CONTRAST_MARKERS = {
    "but",
    "rather",
    "instead",
    "mais",
    "plutot",
    "sinon",
    "pero",
    "sino",
    "aunque",
    "mas",
    "sondern",
}
_NEGATION_SCOPE_FILLERS = {
    "a",
    "an",
    "and",
    "or",
    "the",
    "any",
    "de",
    "des",
    "du",
    "la",
    "le",
    "les",
    "et",
    "ou",
    "un",
    "une",
    "el",
    "los",
    "las",
    "una",
    "uno",
    "o",
    "y",
    "um",
    "uma",
    "ein",
    "eine",
    "oder",
    "und",
    "ist",
    "es",
    "is",
    "are",
    "est",
    "son",
}
_DIRECTIONAL_MARKERS = (
    "rather than",
    "instead of",
    "as opposed to",
    "plutot que",
    "au lieu de",
    "en lugar de",
    "en vez de",
    "а не",
    "вместо",
)
_SEMANTIC_AXES: dict[str, dict[str, tuple[str, ...]]] = {
    "meal timing": {
        "after": (
            r"\bafter (?:a |the )?(?:meal|dinner|lunch|eating)\b",
            r"\bafter (?:people |everyone |we |they )?(?:finish\w*|end\w*) (?:the )?(?:meal|dinner|lunch|eating)\b",
            r"\bapres (?:la fin du |le )?repas\b",
            r"\bapres (?:avoir )?mang\w*\b",
            r"\bdespues de (?:la )?(?:comida|cena|almuerzo)\b",
            r"\bdespues de (?:terminar de )?comer\b",
            r"\b(?:luego de|tras) (?:la )?(?:comida|cena|almuerzo|comer)\b",
            r"\bпосле (?:окончания )?(?:еды|приема пищи|обеда|ужина)\b",
        ),
        "before": (
            r"\bbefore (?:a |the )?(?:meal|dinner|lunch|eating)\b",
            r"\bbefore (?:people |everyone |we |they )?(?:start\w*|begin\w*) (?:the )?(?:meal|dinner|lunch|eating)\b",
            r"\bprior to (?:a |the )?(?:meal|dinner|lunch|eating)\b",
            r"\bavant (?:le debut du |le )?repas\b",
            r"\bavant de mang\w*\b",
            r"\bantes de (?:la )?(?:comida|cena|almuerzo)\b",
            r"\bantes de (?:empezar a )?comer\b",
            r"\bдо (?:начала )?еды\b",
            r"\bперед едой\b",
        ),
        "during": (
            r"\bduring (?:a |the )?(?:meal|dinner|lunch)\b",
            r"\bwhile (?:people|everyone|they|we)? ?(?:are )?(?:still )?eating\b",
            r"\b(?:pendant|durant) (?:le )?repas\b",
            r"\bpendant que .*mang\w*\b",
            r"\bdurante (?:la )?(?:comida|cena|almuerzo)\b",
            r"\bmientras .*com\w*\b",
            r"\bво время еды\b",
            r"\bпока .*ед",
        ),
    },
    "remaining versus leaving": {
        "remaining": (
            r"\bremain\w*\b",
            r"\bstay\w*\b",
            r"\blinger\w*\b",
            r"\bkeep (?:on )?(?:talking|chatting)\b",
            r"\bcontinu\w* (?:a )?(?:parler|discuter)\b",
            r"\brest(?:e|er|ent|ons|ez|ait|aient|era\w*|ant|ee?s?) (?:ensemble )?(?:a )?table\b",
            r"\bqued\w*\b",
            r"\bpermane\w*\b",
            r"\b(?:seguir|sigue\w*|continua\w*) (?:hablando|conversando|charlando)\b",
            r"\bоста\w*\b",
            r"\bпродолжа\w* (?:говорить|разговаривать|общаться)\b",
        ),
        "leaving": (
            r"\bleav\w*\b",
            r"\bget(?:ting)? up from (?:the )?table\b",
            r"\bwalk\w* away\b",
            r"\bquitt\w*\b",
            r"\bse lev\w*\b",
            r"\bpartir\b",
            r"\birse\b",
            r"\bse (?:va|van|fue|fueron)\b",
            r"\bmarch\w*\b",
            r"\blevant\w*\b",
            r"\bуй\w*\b",
            r"\bуход\w*\b",
            r"\bпокин\w*\b",
            r"\bвста\w* из за стол\w*\b",
        ),
    },
    "conversation versus silence": {
        "conversation": (
            r"\btalk\w*\b",
            r"\bchat\w*\b",
            r"\bconvers\w*\b",
            r"\bdiscuss\w*\b",
            r"\bsocial (?:time|moment|conversation)\b",
            r"\bdiscut\w*\b",
            r"\bbavard\w*\b",
            r"\bmoment (?:social|convivial)\b",
            r"\bhabl\w*\b",
            r"\bcharl\w*\b",
            r"\bplatic\w*\b",
            r"\bmomento (?:social|de convivencia)\b",
            r"\bразговар\w*\b",
            r"\bобща\w*\b",
            r"\bобщени\w*\b",
            r"\bбесед\w*\b",
        ),
        "silence": (
            r"\bin silence\b",
            r"\bsilent\w*\b",
            r"\bwithout (?:talking|conversation)\b",
            r"\ben silence\b",
            r"\bsans (?:parler|discuter)\b",
            r"\ben silencio\b",
            r"\bsin (?:hablar|conversar)\b",
            r"\bcallad\w*\b",
            r"\bмолча\b",
            r"\bв тишине\b",
            r"\bне разговар\w*\b",
        ),
    },
    "interpersonal address action": {
        "addressing": (
            r"\baddress\w*\b",
            r"\bspeak\w* to\b",
            r"\bs adress\w*\b",
            r"\bdirig\w* a\b",
            r"\bhablarse\b",
            r"\btratar(?:se)? (?:a alguien )?de\b",
            r"\bобращ\w*\b",
        ),
    },
    "form of address": {
        "informal": (
            r"\binformal(?:ly)?\b",
            r"\binformalmente\b",
            r"\binformellement\b",
            r"\bfamiliar second person\b",
            r"\btu\b",
            r"\btutoy\w*\b",
            r"\binformel\w*\b",
            r"\bvos\b",
            r"\bты\b",
            r"\bнеформаль\w*\b",
        ),
        "formal": (
            r"\bformal(?:ly)?\b",
            r"\bformalmente\b",
            r"\bformellement\b",
            r"\bvous\b",
            r"\bvouvoy\w*\b",
            r"\busted\b",
            r"\bвы\b",
            r"\bвежлив\w*\b",
        ),
    },
    "relation to familiar surroundings": {
        "away": (
            r"\boutside\b",
            r"\baway from\b",
            r"\bleaving\b",
            r"\bhors de\b",
            r"\bloin de\b",
            r"\bquitt\w*\b",
            r"\bfuera de\b",
            r"\blejos de\b",
            r"\bвне\b",
            r"\bвдали от\b",
            r"\bпокин\w*\b",
        ),
        "inside familiar surroundings": (
            r"\binside (?:one s )?familiar\b",
            r"\bwithin (?:one s )?familiar\b",
            r"\b(?:feel|feeling|stay|staying) (?:completely )?at home\b",
            r"\bcomfort\w* in familiar\b",
            r"\b(?:se sentir|rester) .*chez soi\b",
            r"\b(?:sentirse|quedarse) .*?(?:en casa|a gusto)\b",
            r"\bуют\w* .*знаком\w* окружен\w*\b",
            r"\bчувств\w* себя как дома\b",
        ),
    },
}


def normalize_exact_answer(text: str | None) -> str:
    """Normalize casing, accents, apostrophes, punctuation, and whitespace."""

    normalized = normalize_for_comparison(text)
    normalized = _APOSTROPHE_RE.sub("", normalized)
    return _NON_WORD_RE.sub(" ", normalized).strip()


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(normalize_exact_answer(text))


def _lexical_score(left: str, right: str) -> float:
    left_tokens = set(_tokens(left))
    right_tokens = set(_tokens(right))
    union = left_tokens | right_tokens
    if not union:
        return 0.0
    return len(left_tokens & right_tokens) / len(union)


def _ordered_lexical_score(answer: str, candidate: str) -> float:
    """Favor matching word order when checking known wrong explanations."""

    answer_tokens = _tokens(answer)
    candidate_tokens = _tokens(candidate)
    if not answer_tokens or not candidate_tokens:
        return 0.0
    answer_unigrams = set(answer_tokens)
    candidate_unigrams = set(candidate_tokens)
    unigram_coverage = len(answer_unigrams & candidate_unigrams) / len(
        candidate_unigrams
    )
    answer_bigrams = set(zip(answer_tokens, answer_tokens[1:]))
    candidate_bigrams = set(zip(candidate_tokens, candidate_tokens[1:]))
    bigram_coverage = (
        len(answer_bigrams & candidate_bigrams) / len(candidate_bigrams)
        if candidate_bigrams
        else unigram_coverage
    )
    return 0.35 * unigram_coverage + 0.65 * bigram_coverage


def _axis_values(text: str, values: dict[str, tuple[str, ...]]) -> set[str]:
    return {
        value
        for value, patterns in values.items()
        if any(re.search(pattern, text) for pattern in patterns)
    }


def _axis_claims(
    text: str,
    values: dict[str, tuple[str, ...]],
) -> tuple[set[str], set[str]]:
    normalized = normalize_exact_answer(text)
    for marker in _DIRECTIONAL_MARKERS:
        marker_index = normalized.find(f" {marker} ")
        if marker_index >= 0:
            left = normalized[:marker_index]
            right = normalized[marker_index + len(marker) + 2 :]
            return _axis_values(left, values), _axis_values(right, values)
    return _axis_values(normalized, values), set()


def _axis_evidence(
    answer: str,
    positive_examples: Sequence[str],
) -> tuple[list[str], list[str], int]:
    findings: list[str] = []
    confirmations: list[str] = []
    expected_axis_count = 0
    for axis_label, values in _SEMANTIC_AXES.items():
        asserted_counts = {value: 0 for value in values}
        for example in positive_examples:
            asserted, _ = _axis_claims(example, values)
            for value in asserted:
                asserted_counts[value] += 1
        expected_values = [
            value
            for value, count in asserted_counts.items()
            if count >= 2
            and not any(
                other_count
                for other_value, other_count in asserted_counts.items()
                if other_value != value
            )
        ]
        if len(expected_values) != 1:
            continue
        expected_axis_count += 1
        expected = expected_values[0]
        answer_asserted, answer_rejected = _axis_claims(answer, values)
        opposing = sorted(answer_asserted - {expected})
        if expected in answer_rejected:
            findings.append(f"{axis_label}: rejects “{expected}”")
        elif opposing:
            findings.append(
                f"{axis_label}: says “{', '.join(opposing)}” instead of “{expected}”"
            )
        elif expected in answer_asserted:
            confirmations.append(f"{axis_label} = “{expected}”")
    return findings, confirmations, expected_axis_count


def _ordered_negative_findings(
    answer: str,
    references: Sequence[str],
    negative_rows: Sequence[tuple[str, Sequence[str]]],
) -> list[str]:
    positive_score = max(
        (_ordered_lexical_score(answer, reference) for reference in references),
        default=0.0,
    )
    findings: list[str] = []
    for label, examples in negative_rows:
        negative_score = max(
            (_ordered_lexical_score(answer, example) for example in examples),
            default=0.0,
        )
        if (
            negative_score >= ORDERED_NEGATIVE_THRESHOLD
            and negative_score - positive_score >= ORDERED_NEGATIVE_MARGIN
        ):
            findings.append(f"word order is close to the “{label}” trap")
    return findings


def _negation_markers(text: str) -> list[str]:
    return sorted(set(_tokens(text)) & _NEGATION_MARKERS)


def _has_corrective_contrast(text: str) -> bool:
    return bool(set(_tokens(text)) & _CORRECTIVE_CONTRAST_MARKERS)


def _explicitly_negates_candidate(answer: str, candidate: str) -> bool:
    """Detect short forms such as "not a physical illness".

    This is deliberately narrow: it only suppresses a hard-negative signal
    when answer words overlap the negative example and a negator occurs in the
    immediately preceding four-token window.
    """

    answer_tokens = _tokens(answer)
    candidate_tokens = [
        token
        for token in _tokens(candidate)
        if token not in _NEGATION_MARKERS and token not in _NEGATION_SCOPE_FILLERS
    ]
    if not candidate_tokens:
        return False

    candidate_set = set(candidate_tokens)
    overlap = candidate_set & set(answer_tokens)
    if len(overlap) / len(candidate_set) < 0.6:
        return False

    matching_indexes = [
        index for index, token in enumerate(answer_tokens) if token in overlap
    ]
    if not matching_indexes:
        return False
    first_match = min(matching_indexes)
    preceding = answer_tokens[max(0, first_match - 4) : first_match]
    return bool(set(preceding) & _NEGATION_MARKERS)


def _deduplicate(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalize_exact_answer(value)
        if not normalized:
            raise ValueError("Rubric examples must contain letters or numbers.")
        if normalized not in seen:
            seen.add(normalized)
            result.append(value.strip())
    return result


def _round_score(value: float | None) -> float | None:
    return None if value is None else round(float(value), 4)


def _component_configured(component: Any) -> bool:
    configured = getattr(component, "configured", None)
    if configured is not None:
        return bool(configured)
    return bool(getattr(component, "available", False))


def _verification_payload(
    *,
    available: bool,
    checked: bool = False,
    entailment_score: float | None = None,
    contradiction_score: float | None = None,
    negative_entailment_score: float | None = None,
    entailment_margin: float | None = None,
    matched_reference: str | None = None,
    overflow: bool = False,
    safety_flags: Sequence[str] = (),
    confirmed_axes: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "available": available,
        "model_name": NLI_MODEL_NAME,
        "checked": checked,
        "entailment_score": _round_score(entailment_score),
        "contradiction_score": _round_score(contradiction_score),
        "negative_entailment_score": _round_score(negative_entailment_score),
        "entailment_margin": _round_score(entailment_margin),
        "matched_reference": matched_reference,
        "overflow": overflow,
        "safety_flags": list(safety_flags),
        "confirmed_axes": list(confirmed_axes),
    }


def _candidate_scores(
    answer: str,
    candidates: list[str],
) -> tuple[list[float], bool, bool]:
    try:
        ranker = get_local_sense_ranker()
        if ranker.available:
            would_truncate = getattr(ranker, "would_truncate", None)
            if callable(would_truncate) and (
                would_truncate([answer], kind="query")
                or would_truncate(candidates, kind="passage")
            ):
                return (
                    [_lexical_score(answer, candidate) for candidate in candidates],
                    True,
                    True,
                )
            answer_vector = ranker.encode([answer], kind="query")
            candidate_vectors = ranker.encode(candidates, kind="passage")
            if answer_vector is not None and candidate_vectors is not None:
                scores = candidate_vectors @ answer_vector[0]
                return [float(score) for score in scores], True, False
    except Exception:
        LOGGER.exception("Local semantic grading failed; using lexical diagnostics")
    return (
        [_lexical_score(answer, candidate) for candidate in candidates],
        False,
        False,
    )


def _threshold_payload() -> dict[str, float]:
    return {
        "positive_correct": POSITIVE_CORRECT_THRESHOLD,
        "positive_related": POSITIVE_RELATED_THRESHOLD,
        "concept_covered": CONCEPT_COVERAGE_THRESHOLD,
        "hard_negative": HARD_NEGATIVE_THRESHOLD,
        "safe_negative_margin": SAFE_NEGATIVE_MARGIN,
        "competitive_negative_margin": COMPETITIVE_NEGATIVE_MARGIN,
        "ordered_negative": ORDERED_NEGATIVE_THRESHOLD,
        "ordered_negative_margin": ORDERED_NEGATIVE_MARGIN,
        "nli_entailment": NLI_ENTAILMENT_THRESHOLD,
        "nli_axis_confirmed_entailment": NLI_AXIS_CONFIRMED_ENTAILMENT_THRESHOLD,
        "nli_axis_confirmed_max_tokens": NLI_AXIS_CONFIRMED_MAX_TOKENS,
        "nli_axis_confirmed_max_contradiction": (
            NLI_AXIS_CONFIRMED_MAX_CONTRADICTION
        ),
        "nli_axis_confirmed_decision_margin": NLI_AXIS_CONFIRMED_DECISION_MARGIN,
        "structured_partial_positive": STRUCTURED_PARTIAL_POSITIVE_THRESHOLD,
        "structured_partial_max_tokens": STRUCTURED_PARTIAL_MAX_TOKENS,
        "nli_max_contradiction": NLI_MAX_CONTRADICTION,
        "nli_decision_margin": NLI_DECISION_MARGIN,
        "nli_negative_margin": NLI_NEGATIVE_MARGIN,
    }


def grade_semantic_answer(
    *,
    answer: str,
    accepted_answers: Sequence[str],
    minimum_glosses: Sequence[
        tuple[str, Sequence[tuple[str, str]]]
    ] = (),
    context_concepts: Sequence[str] = (),
    required_concepts: Sequence[tuple[str, Sequence[str]]] = (),
    hard_negatives: Sequence[tuple[str, Sequence[str]]] = (),
) -> dict[str, Any]:
    """Grade an explanation locally using exact rules plus multilingual E5.

    Full explanations require concept, hard-negative, and entailment evidence.
    Separately curated concise glosses can be correct without pretending that
    they contain every supporting detail in a dictionary-style definition.
    """

    started = perf_counter()
    cleaned_answer = answer.strip()
    references = _deduplicate(accepted_answers)
    concept_rows = [
        (label.strip(), _deduplicate(examples))
        for label, examples in required_concepts
    ]
    negative_rows = [
        (label.strip(), _deduplicate(examples))
        for label, examples in hard_negatives
    ]
    if not references:
        raise ValueError("At least one accepted answer is required.")

    concept_labels = {label for label, _ in concept_rows}
    context_concept_labels = {
        label.strip() for label in context_concepts if label.strip()
    }
    unknown_context_labels = context_concept_labels - concept_labels
    if unknown_context_labels:
        raise ValueError(
            "Context evidence references an unknown concept: "
            + ", ".join(sorted(unknown_context_labels))
            + "."
        )
    allowed_minimum_evidence = {
        "explicit",
        "context",
        "optional_omitted",
    }
    minimum_gloss_rows: list[tuple[str, dict[str, str]]] = []
    seen_minimum_glosses: set[str] = set()
    reference_normalized = {
        normalize_exact_answer(item) for item in references
    }
    for text, evidence_rows in minimum_glosses:
        normalized_text = normalize_exact_answer(text)
        if not normalized_text:
            raise ValueError("Minimum glosses must contain letters or numbers.")
        if (
            normalized_text in seen_minimum_glosses
            or normalized_text in reference_normalized
        ):
            continue
        evidence = dict(evidence_rows)
        if len(evidence) != len(evidence_rows):
            raise ValueError(
                "A minimum gloss cannot define the same concept twice."
            )
        unknown_labels = set(evidence) - concept_labels
        if unknown_labels:
            raise ValueError(
                "Minimum gloss evidence references an unknown concept: "
                + ", ".join(sorted(unknown_labels))
                + "."
            )
        missing_labels = concept_labels - set(evidence)
        if missing_labels:
            raise ValueError(
                "Minimum gloss evidence is missing a required concept: "
                + ", ".join(sorted(missing_labels))
                + "."
            )
        invalid_evidence = set(evidence.values()) - allowed_minimum_evidence
        if invalid_evidence:
            raise ValueError(
                "Unknown minimum-gloss evidence type: "
                + ", ".join(sorted(invalid_evidence))
                + "."
            )
        undeclared_context = {
            label
            for label, value in evidence.items()
            if value == "context" and label not in context_concept_labels
        }
        if undeclared_context:
            raise ValueError(
                "Minimum gloss relies on context not declared by the challenge: "
                + ", ".join(sorted(undeclared_context))
                + "."
            )
        if not any(
            value in {"explicit", "context"} for value in evidence.values()
        ):
            raise ValueError(
                "A minimum gloss must cover at least one meaning concept."
            )
        seen_minimum_glosses.add(normalized_text)
        minimum_gloss_rows.append((text.strip(), evidence))

    positive_normalized = reference_normalized | seen_minimum_glosses
    for _, examples in negative_rows:
        overlap = positive_normalized & {
            normalize_exact_answer(example) for example in examples
        }
        if overlap:
            raise ValueError(
                "A hard-negative example cannot duplicate an accepted answer."
            )

    all_candidates = list(references)
    concept_slices: list[tuple[int, int]] = []
    for _, examples in concept_rows:
        start = len(all_candidates)
        all_candidates.extend(examples)
        concept_slices.append((start, len(all_candidates)))
    negative_slices: list[tuple[int, int]] = []
    for _, examples in negative_rows:
        start = len(all_candidates)
        all_candidates.extend(examples)
        negative_slices.append((start, len(all_candidates)))

    normalized_answer = normalize_exact_answer(cleaned_answer)
    exact_reference_index = next(
        (
            index
            for index, reference in enumerate(references)
            if normalized_answer
            and normalized_answer == normalize_exact_answer(reference)
        ),
        None,
    )
    exact_minimum_gloss_index = next(
        (
            index
            for index, (gloss, _) in enumerate(minimum_gloss_rows)
            if normalized_answer
            and normalized_answer == normalize_exact_answer(gloss)
        ),
        None,
    )
    exact_negative: tuple[int, int] | None = None
    if normalized_answer:
        for row_index, (_, examples) in enumerate(negative_rows):
            for example_index, example in enumerate(examples):
                if normalized_answer == normalize_exact_answer(example):
                    exact_negative = (row_index, example_index)
                    break
            if exact_negative is not None:
                break

    exact_concise_match = exact_minimum_gloss_index is not None
    exact_match = exact_reference_index is not None or exact_concise_match
    short_circuit = exact_match or not cleaned_answer or exact_negative is not None
    if short_circuit:
        # Exact and empty decisions must not cold-load or execute either model.
        scores = [0.0] * len(all_candidates)
        model_available = _component_configured(get_local_sense_ranker())
        input_overflow = False
        if exact_reference_index is not None:
            scores[exact_reference_index] = 1.0
            for start, end in concept_slices:
                scores[start:end] = [1.0] * (end - start)
        elif exact_negative is not None:
            row_index, example_index = exact_negative
            negative_start, _ = negative_slices[row_index]
            scores[negative_start + example_index] = 1.0
    else:
        scores, model_available, input_overflow = _candidate_scores(
            cleaned_answer,
            all_candidates,
        )

    reference_scores = scores[: len(references)]
    matched_reference_index = max(
        range(len(references)),
        key=reference_scores.__getitem__,
    )
    if exact_reference_index is not None:
        matched_reference_index = exact_reference_index
        reference_scores[matched_reference_index] = 1.0
    positive_score = reference_scores[matched_reference_index]
    matched_reference_text = references[matched_reference_index]
    matched_reference_is_concise = False
    if exact_minimum_gloss_index is not None:
        matched_reference_text = minimum_gloss_rows[
            exact_minimum_gloss_index
        ][0]
        positive_score = 1.0
        matched_reference_is_concise = True

    concept_results: list[dict[str, Any]] = []
    for (label, examples), (start, end) in zip(
        concept_rows,
        concept_slices,
        strict=True,
    ):
        row_scores = scores[start:end]
        best_index = max(range(len(examples)), key=row_scores.__getitem__)
        best_score = row_scores[best_index]
        concept_results.append(
            {
                "label": label,
                "score": _round_score(best_score),
                "matched_example": examples[best_index],
                "covered": best_score >= CONCEPT_COVERAGE_THRESHOLD,
                "evidence": (
                    "semantic"
                    if best_score >= CONCEPT_COVERAGE_THRESHOLD
                    else "missing"
                ),
            }
        )

    hard_negative_results: list[dict[str, Any]] = []
    active_negative_scores: list[float] = []
    for row_index, ((label, examples), (start, end)) in enumerate(
        zip(negative_rows, negative_slices, strict=True)
    ):
        row_scores = scores[start:end]
        best_index = max(range(len(examples)), key=row_scores.__getitem__)
        best_score = row_scores[best_index]
        explicitly_rejected = _explicitly_negates_candidate(
            cleaned_answer,
            examples[best_index],
        )
        # Negation is useful diagnostic evidence, but it must never remove a
        # hard negative and thereby make an automatic acceptance easier.
        active_negative_scores.append(best_score)
        triggered = (
            exact_negative == (row_index, best_index)
            or (
                best_score >= HARD_NEGATIVE_THRESHOLD
                and best_score >= positive_score - COMPETITIVE_NEGATIVE_MARGIN
            )
        )
        hard_negative_results.append(
            {
                "label": label,
                "score": _round_score(best_score),
                "matched_example": examples[best_index],
                "triggered": triggered,
                "explicitly_rejected": explicitly_rejected,
            }
        )

    negative_score = (
        max(active_negative_scores) if active_negative_scores else None
    )
    margin = (
        positive_score - negative_score
        if negative_score is not None
        else None
    )
    covered_count = sum(item["covered"] for item in concept_results)
    concept_coverage = (
        covered_count / len(concept_results) if concept_results else 0.0
    )
    answer_negations = _negation_markers(cleaned_answer)
    reference_negations = _negation_markers(matched_reference_text)
    corrective_contrast = _has_corrective_contrast(cleaned_answer)
    negation_mismatch = bool(answer_negations) != bool(reference_negations)

    positive_axis_examples = list(references)
    for _, examples in concept_rows:
        positive_axis_examples.extend(examples)
    safety_flags, confirmed_axes, expected_axis_count = _axis_evidence(
        cleaned_answer,
        positive_axis_examples,
    )
    safety_flags.extend(
        _ordered_negative_findings(
            cleaned_answer,
            references,
            negative_rows,
        )
    )
    if negation_mismatch:
        safety_flags.append(
            "negation changes the polarity of the closest accepted explanation"
        )
    if input_overflow:
        safety_flags.append(
            "the answer is too long to verify without semantic truncation"
        )
    safety_flags = list(dict.fromkeys(safety_flags))

    if exact_concise_match:
        minimum_evidence = minimum_gloss_rows[
            exact_minimum_gloss_index
        ][1]
        for result in concept_results:
            evidence = minimum_evidence.get(result["label"], "missing")
            covered = evidence in {"explicit", "context"}
            result["covered"] = covered
            result["score"] = 1.0 if covered else 0.0
            result["evidence"] = evidence
        covered_count = sum(item["covered"] for item in concept_results)
        concept_coverage = (
            covered_count / len(concept_results) if concept_results else 0.0
        )

    reasons: list[str] = []
    triggered_negatives = [
        item["label"] for item in hard_negative_results if item["triggered"]
    ]
    unrefuted_triggered_negatives: list[str] = []
    negative_axis_refutations: list[bool] = []
    for result, (_, examples) in zip(
        hard_negative_results,
        negative_rows,
        strict=True,
    ):
        negative_refutation_flags, _, _ = _axis_evidence(
            cleaned_answer,
            examples,
        )
        axis_refuted = bool(negative_refutation_flags)
        negative_axis_refutations.append(axis_refuted)
        if result["triggered"] and not axis_refuted:
            unrefuted_triggered_negatives.append(result["label"])
    nearest_negative_axis_refuted = False
    if active_negative_scores:
        nearest_negative_index = max(
            range(len(active_negative_scores)),
            key=active_negative_scores.__getitem__,
        )
        nearest_negative_axis_refuted = negative_axis_refutations[
            nearest_negative_index
        ]
    partial_negative_safe = (
        margin is None
        or margin >= SAFE_NEGATIVE_MARGIN
        or nearest_negative_axis_refuted
    )

    verifier = get_local_nli_verifier()
    verifier_available = _component_configured(verifier)
    verification = _verification_payload(
        available=verifier_available,
        safety_flags=safety_flags,
        confirmed_axes=confirmed_axes,
    )
    verification_passed = False
    strong_negative = (
        bool(triggered_negatives)
        and negative_score is not None
        and negative_score - positive_score >= SAFE_NEGATIVE_MARGIN
    )
    structured_partial = False
    structured_partial_candidate = (
        not short_circuit
        and model_available
        and not input_overflow
        and not strong_negative
        and bool(concept_results)
        and bool(negative_rows)
        and not safety_flags
        and not unrefuted_triggered_negatives
        and partial_negative_safe
        and expected_axis_count >= 2
        and 0 < len(confirmed_axes) < expected_axis_count
        and len(_tokens(cleaned_answer)) <= STRUCTURED_PARTIAL_MAX_TOKENS
        and positive_score >= STRUCTURED_PARTIAL_POSITIVE_THRESHOLD
    )
    if structured_partial_candidate:
        axis_bound_concepts = 0
        axis_adjusted_coverage: list[bool] = []
        for result, (_, examples) in zip(
            concept_results,
            concept_rows,
            strict=True,
        ):
            concept_flags, concept_confirmations, concept_axis_count = (
                _axis_evidence(cleaned_answer, examples)
            )
            if concept_axis_count:
                axis_bound_concepts += 1
                axis_adjusted_coverage.append(
                    not concept_flags
                    and len(concept_confirmations) == concept_axis_count
                )
            else:
                axis_adjusted_coverage.append(bool(result["covered"]))

        adjusted_covered_count = sum(axis_adjusted_coverage)
        structured_partial = (
            axis_bound_concepts >= 2
            and 0 < adjusted_covered_count < len(concept_results)
        )
        if structured_partial:
            for result, covered in zip(
                concept_results,
                axis_adjusted_coverage,
                strict=True,
            ):
                result["covered"] = covered
                result["evidence"] = "explicit" if covered else "missing"
            covered_count = adjusted_covered_count
            concept_coverage = covered_count / len(concept_results)

    should_verify = (
        not short_circuit
        and model_available
        and not input_overflow
        and not strong_negative
        and bool(concept_results)
        and covered_count == len(concept_results)
        and bool(negative_rows)
        and not safety_flags
        and positive_score >= POSITIVE_CORRECT_THRESHOLD
    )
    if should_verify:
        try:
            verifier_available = verifier.available
            verification = _verification_payload(
                available=verifier_available,
                safety_flags=safety_flags,
                confirmed_axes=confirmed_axes,
            )
            if verifier_available:
                top_reference_indexes = sorted(
                    range(len(references)),
                    key=reference_scores.__getitem__,
                    reverse=True,
                )
                hypotheses = [
                    references[index] for index in top_reference_indexes
                ]
                negative_hypotheses = [
                    item["matched_example"] for item in hard_negative_results
                ]
                nli_scores, nli_overflow = verifier.score(
                    premise=cleaned_answer,
                    hypotheses=hypotheses + negative_hypotheses,
                )
                if nli_overflow:
                    safety_flags.append(
                        "the answer-reference pair exceeds the verifier token budget"
                    )
                    verification = _verification_payload(
                        available=True,
                        overflow=True,
                        safety_flags=safety_flags,
                        confirmed_axes=confirmed_axes,
                    )
                elif nli_scores:
                    positive_nli_scores = nli_scores[: len(hypotheses)]
                    negative_nli_scores = nli_scores[len(hypotheses) :]
                    evidence_index = max(
                        range(len(positive_nli_scores)),
                        key=lambda index: (
                            positive_nli_scores[index].entailment
                            - positive_nli_scores[index].contradiction
                        ),
                    )
                    evidence = positive_nli_scores[evidence_index]
                    negative_evidence = max(
                        negative_nli_scores,
                        key=lambda item: item.entailment - item.contradiction,
                    )
                    entailment_margin = (
                        evidence.entailment
                        - evidence.contradiction
                        - negative_evidence.entailment
                        + negative_evidence.contradiction
                    )
                    nli_decision_margin = (
                        evidence.entailment - evidence.contradiction
                    )
                    strict_verification_passed = (
                        evidence.entailment >= NLI_ENTAILMENT_THRESHOLD
                        and evidence.contradiction <= NLI_MAX_CONTRADICTION
                        and nli_decision_margin >= NLI_DECISION_MARGIN
                        and entailment_margin >= NLI_NEGATIVE_MARGIN
                    )
                    concise_axis_verification_passed = (
                        len(_tokens(cleaned_answer))
                        <= NLI_AXIS_CONFIRMED_MAX_TOKENS
                        and expected_axis_count >= 2
                        and len(confirmed_axes) == expected_axis_count
                        and evidence.entailment
                        >= NLI_AXIS_CONFIRMED_ENTAILMENT_THRESHOLD
                        and evidence.contradiction
                        <= NLI_AXIS_CONFIRMED_MAX_CONTRADICTION
                        and nli_decision_margin
                        >= NLI_AXIS_CONFIRMED_DECISION_MARGIN
                        and entailment_margin >= NLI_NEGATIVE_MARGIN
                    )
                    verification_passed = (
                        strict_verification_passed
                        or concise_axis_verification_passed
                    )
                    verification = _verification_payload(
                        available=True,
                        checked=True,
                        entailment_score=evidence.entailment,
                        contradiction_score=evidence.contradiction,
                        negative_entailment_score=negative_evidence.entailment,
                        entailment_margin=entailment_margin,
                        matched_reference=hypotheses[evidence_index],
                        safety_flags=safety_flags,
                        confirmed_axes=confirmed_axes,
                    )
        except Exception:
            LOGGER.exception("Local NLI verification failed; abstaining")
            verifier_available = False
            verification = _verification_payload(
                available=False,
                safety_flags=safety_flags,
                confirmed_axes=confirmed_axes,
            )

    if exact_match:
        verdict = "correct"
        if exact_concise_match:
            method = "curated_minimum_gloss"
            reasons.append(
                "The answer exactly matches a curated minimum gloss after normalization."
            )
            reasons.append(
                "It carries enough meaning to be correct in this context."
            )
            optional_details = [
                item["label"]
                for item in concept_results
                if item["evidence"] == "optional_omitted"
            ]
            if optional_details:
                reasons.append(
                    "For a fuller explanation, you could also mention: "
                    + ", ".join(optional_details)
                    + "."
                )
        else:
            method = "exact_normalized"
            reasons.append(
                "The answer exactly matches a curated accepted answer after normalization."
            )
    elif not cleaned_answer:
        verdict = "incorrect"
        method = "empty"
        reasons.append("No answer was provided.")
    elif exact_negative is not None:
        verdict = "incorrect"
        method = "exact_hard_negative"
        reasons.append(
            "The answer exactly matches a known wrong or contradictory answer."
        )
    elif not model_available:
        verdict = "uncertain"
        method = "lexical_overlap_fallback"
        reasons.append(
            "The local semantic model is unavailable; lexical overlap is shown "
            "but is not trusted for a decision."
        )
    elif input_overflow:
        verdict = "uncertain"
        method = MODEL_NAME
        reasons.append(
            "The answer exceeds the semantic model's token budget. It was not "
            "silently truncated, so this result needs review."
        )
    elif strong_negative:
        verdict = "incorrect"
        method = MODEL_NAME
        reasons.append(
            "A known wrong or contradictory meaning is clearly stronger than "
            "the accepted meaning."
        )
        reasons.append(f"Triggered hard negative: {', '.join(triggered_negatives)}.")
        reasons.extend(f"Safety check: {finding}." for finding in safety_flags)
    elif structured_partial:
        verdict = "partial"
        method = f"{MODEL_NAME} + local meaning checks"
        confirmed = [
            item["label"] for item in concept_results if item["covered"]
        ]
        missing = [
            item["label"] for item in concept_results if not item["covered"]
        ]
        reasons.append(
            f"The answer explicitly carries {covered_count} of "
            f"{len(concept_results)} required meaning components."
        )
        reasons.append(f"Confirmed: {', '.join(confirmed)}.")
        reasons.append(f"Missing or unclear: {', '.join(missing)}.")
    elif triggered_negatives and not verification_passed:
        verdict = "uncertain"
        method = MODEL_NAME
        reasons.append(
            "A known wrong meaning is competitive, but its lead is too small "
            "for a reliable rejection."
        )
        reasons.append(f"Competitive hard negative: {', '.join(triggered_negatives)}.")
        reasons.extend(f"Safety check: {finding}." for finding in safety_flags)
    elif safety_flags:
        verdict = "uncertain"
        method = f"{MODEL_NAME} + local safety rules"
        reasons.append(
            "A conservative contradiction check found wording that may reverse "
            "the intended meaning."
        )
        reasons.extend(f"Safety check: {finding}." for finding in safety_flags)
    elif not concept_results:
        verdict = "uncertain"
        method = MODEL_NAME
        reasons.append(
            "No required concepts were supplied, so semantic similarity alone "
            "cannot mark the answer correct."
        )
    elif covered_count < len(concept_results):
        method = MODEL_NAME
        if (
            covered_count
            and positive_score >= POSITIVE_RELATED_THRESHOLD
            and partial_negative_safe
        ):
            verdict = "partial"
            missing = [
                item["label"] for item in concept_results if not item["covered"]
            ]
            reasons.append(
                f"The answer covers {covered_count} of {len(concept_results)} required concepts."
            )
            reasons.append(f"Missing or unclear: {', '.join(missing)}.")
        elif covered_count and positive_score >= POSITIVE_RELATED_THRESHOLD:
            verdict = "uncertain"
            reasons.append(
                "The answer contains part of the rubric, but its nearest known "
                "trap is too close to award partial credit safely."
            )
        elif positive_score < POSITIVE_RELATED_THRESHOLD:
            verdict = "incorrect"
            reasons.append(
                "The answer is below the related-meaning threshold and does not "
                "cover the rubric."
            )
        else:
            verdict = "uncertain"
            reasons.append(
                "The answer is related, but the required meaning components "
                "are not clear enough."
            )
    elif not negative_rows:
        verdict = "uncertain"
        method = MODEL_NAME
        reasons.append(
            "All concepts appear present, but hard-negative examples are "
            "required before an automatic correct verdict."
        )
    elif positive_score < POSITIVE_CORRECT_THRESHOLD:
        verdict = "uncertain"
        method = MODEL_NAME
        reasons.append(
            "All concepts appear present, but similarity to the accepted explanations is borderline."
        )
    elif (
        margin is not None
        and margin < SAFE_NEGATIVE_MARGIN
        and not verification_passed
    ):
        verdict = "uncertain"
        method = MODEL_NAME
        reasons.append(
            "Accepted and rejected meanings are too close for a reliable automatic decision."
        )
    elif not verifier_available:
        verdict = "uncertain"
        method = MODEL_NAME
        reasons.append(
            "The embedding signals look positive, but the local entailment "
            "verifier is unavailable. Similarity alone cannot mark a paraphrase correct."
        )
    elif verification["overflow"]:
        verdict = "uncertain"
        method = f"{MODEL_NAME} + {NLI_MODEL_NAME}"
        reasons.append(
            "The answer-reference pair is too long for complete contradiction checking."
        )
    elif not verification_passed:
        verdict = "uncertain"
        method = f"{MODEL_NAME} + {NLI_MODEL_NAME}"
        reasons.append(
            "The answer is semantically close, but the local entailment model "
            "did not confirm it strongly enough."
        )
    else:
        verdict = "correct"
        method = f"{MODEL_NAME} + {NLI_MODEL_NAME}"
        reasons.append("All required concepts are covered.")
        if confirmed_axes:
            reasons.append(
                "Explicit meaning checks confirmed: "
                + "; ".join(confirmed_axes)
                + "."
            )
        reasons.append(
            "The local entailment verifier gave the accepted meaning a safe "
            "lead over known traps and found no strong contradiction."
        )

    return {
        "verdict": verdict,
        "exact_match": exact_match,
        "answer_quality": (
            "concise"
            if verdict == "correct" and matched_reference_is_concise
            else "complete"
            if verdict == "correct"
            else None
        ),
        "method": method,
        "latency_ms": round((perf_counter() - started) * 1000, 2),
        "model_available": model_available,
        "model_name": MODEL_NAME,
        "positive_score": _round_score(positive_score),
        "negative_score": _round_score(negative_score),
        "margin": _round_score(margin),
        "concept_coverage": round(concept_coverage, 4),
        "matched_reference": {
            "text": matched_reference_text,
            "score": _round_score(positive_score),
        },
        "required_concepts": concept_results,
        "hard_negatives": hard_negative_results,
        "negation_guard": {
            "mismatch": negation_mismatch,
            "corrective_contrast": corrective_contrast,
            "answer_markers": answer_negations,
            "reference_markers": reference_negations,
        },
        "verification": verification,
        "thresholds": _threshold_payload(),
        "reasons": reasons,
    }
