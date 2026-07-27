from __future__ import annotations

import math

from fastapi import FastAPI, HTTPException, Request as FastAPIRequest
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
import numpy as np
from pydantic import ValidationError
import pytest
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware

from app.core.csrf import get_or_create_csrf_token
from app.core.rate_limit import limiter
from app.routers import playground
from app.schemas.playground import SemanticGradePayload
from app.services import semantic_grading
from app.services.local_nli import NliScores
from app.services.playground_challenges import PLAYGROUND_CHALLENGES


class FakeRanker:
    def __init__(
        self,
        scores: dict[str, float] | None = None,
        *,
        available: bool = True,
        overflow: bool = False,
    ) -> None:
        self.scores = scores or {}
        self.available = available
        self.configured = available
        self.overflow = overflow
        self.encode_calls = 0

    def encode(self, texts: list[str], *, kind: str) -> np.ndarray | None:
        self.encode_calls += 1
        if not self.available:
            return None
        if kind == "query":
            return np.asarray([[1.0, 0.0] for _ in texts], dtype=np.float32)
        return np.asarray(
            [
                [
                    self.scores[text],
                    math.sqrt(max(0.0, 1 - self.scores[text] ** 2)),
                ]
                for text in texts
            ],
            dtype=np.float32,
        )

    def would_truncate(self, texts: list[str], *, kind: str) -> bool:
        return self.overflow



class FakeVerifier:
    def __init__(
        self,
        scores: dict[str, NliScores] | None = None,
        *,
        available: bool = True,
        overflow: bool = False,
    ) -> None:
        self.scores = scores or {}
        self.available = available
        self.configured = available
        self.overflow = overflow
        self.calls = 0

    def score(
        self,
        *,
        premise: str,
        hypotheses: list[str],
    ) -> tuple[list[NliScores] | None, bool]:
        self.calls += 1
        if not self.available:
            return None, False
        if self.overflow:
            return None, True
        return [
            self.scores.get(
                hypothesis,
                NliScores(
                    entailment=0.8,
                    neutral=0.15,
                    contradiction=0.05,
                ),
            )
            for hypothesis in hypotheses
        ], False


def _patch_ranker(
    monkeypatch: pytest.MonkeyPatch,
    scores: dict[str, float] | None = None,
    *,
    available: bool = True,
    overflow: bool = False,
) -> FakeRanker:
    ranker = FakeRanker(scores, available=available, overflow=overflow)
    monkeypatch.setattr(
        semantic_grading,
        "get_local_sense_ranker",
        lambda: ranker,
    )
    _patch_verifier(monkeypatch, available=False)
    return ranker


def _patch_verifier(
    monkeypatch: pytest.MonkeyPatch,
    scores: dict[str, NliScores] | None = None,
    *,
    available: bool = True,
    overflow: bool = False,
) -> FakeVerifier:
    verifier = FakeVerifier(
        scores,
        available=available,
        overflow=overflow,
    )
    monkeypatch.setattr(
        semantic_grading,
        "get_local_nli_verifier",
        lambda: verifier,
    )
    return verifier


def _patch_concise_sobremesa_case(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    reference = "People remain at the table talking after the meal."
    timing = "The social time happens after eating."
    timing_es = "El momento ocurre despues de comer."
    staying = "People stay together at the table."
    staying_es = "La gente permanece junta en la mesa."
    conversation = "People keep talking together."
    conversation_es = "La gente sigue hablando."
    negative = "People leave the table immediately after the meal."
    negative_es = "La gente se levanta de la mesa al terminar la comida."
    _patch_ranker(
        monkeypatch,
        {
            reference: 0.90,
            timing: 0.88,
            timing_es: 0.88,
            staying: 0.88,
            staying_es: 0.88,
            conversation: 0.87,
            conversation_es: 0.87,
            negative: 0.895,
            negative_es: 0.895,
        },
    )
    _patch_verifier(
        monkeypatch,
        {
            reference: NliScores(0.19, 0.77, 0.04),
            negative: NliScores(0.04, 0.36, 0.60),
        },
    )
    return {
        "accepted_answers": [reference],
        "required_concepts": [
            ("after the meal", [timing, timing_es]),
            ("staying at the table", [staying, staying_es]),
            ("conversation", [conversation, conversation_es]),
        ],
        "hard_negatives": [
            ("leaving immediately", [negative, negative_es]),
        ],
    }


def _challenge_rubric(challenge_id: str) -> dict[str, object]:
    challenge = PLAYGROUND_CHALLENGES[challenge_id]
    return {
        "accepted_answers": challenge.accepted_answers,
        "minimum_glosses": [
            (gloss.text, gloss.concept_evidence)
            for gloss in challenge.minimum_glosses
        ],
        "context_concepts": challenge.context_concepts,
        "required_concepts": challenge.required_concepts,
        "hard_negatives": challenge.hard_negatives,
    }


def test_normalized_exact_match_does_not_need_the_model(monkeypatch):
    ranker = _patch_ranker(monkeypatch, available=False)

    result = semantic_grading.grade_semantic_answer(
        answer="  À bientôt! ",
        accepted_answers=["a bientot"],
        required_concepts=[("farewell", ["a parting expression"])],
        hard_negatives=[("greeting", ["hello at the start of a meeting"])],
    )

    assert result["verdict"] == "correct"
    assert result["exact_match"] is True
    assert result["method"] == "exact_normalized"
    assert result["positive_score"] == 1.0
    assert result["model_available"] is False
    assert result["concept_coverage"] == 1.0
    assert result["required_concepts"][0]["covered"] is True
    assert ranker.encode_calls == 0


@pytest.mark.parametrize(
    ("challenge_id", "answer", "expected_coverage", "expected_evidence"),
    [
        (
            "se_retrouver",
            "ver de nuevo a un amigo",
            1.0,
            {
                "Meeting one another again": "explicit",
                "After time apart": "context",
            },
        ),
        (
            "tutoyer",
            "hablar de tu",
            1.0,
            {
                "Addressing another person": "context",
                "Using informal singular tu": "explicit",
            },
        ),
        (
            "flaner",
            "pasear",
            1.0,
            {
                "Moving around leisurely": "explicit",
                "Without a fixed or urgent destination": "context",
            },
        ),
        (
            "depanner",
            "la saco del apuro",
            1.0,
            {
                "Helping someone": "explicit",
                "Solving an immediate practical difficulty": "context",
            },
        ),
        (
            "s_attarder",
            "se quedo mas tiempo",
            1.0,
            {
                "Remaining in place": "explicit",
                "Longer or later than expected": "context",
            },
        ),
        (
            "madrugar",
            "levantarse muy temprano",
            1.0,
            {
                "Getting out of bed": "explicit",
                "At a very early hour": "explicit",
            },
        ),
        (
            "estrenar",
            "usarlo por primera vez",
            1.0,
            {
                "Using or wearing something": "explicit",
                "For the first time": "explicit",
            },
        ),
        (
            "empalagar",
            "desagrado luego de comer mucho azucar",
            1.0,
            {
                "Excessive sweetness or richness": "explicit",
                "Resulting weariness, saturation, or dislike": "explicit",
            },
        ),
        (
            "trasnochar",
            "quedarse despierto hasta muy tarde",
            1.0,
            {
                "Remaining awake": "explicit",
                "Until very late at night": "explicit",
            },
        ),
        (
            "anorar",
            "las echa de menos",
            1.0,
            {
                "Something valued is absent": "context",
                "Feeling emotional longing": "explicit",
            },
        ),
    ],
)
def test_curated_minimum_gloss_is_correct_without_models(
    monkeypatch,
    challenge_id,
    answer,
    expected_coverage,
    expected_evidence,
):
    ranker = _patch_ranker(monkeypatch, available=False)

    result = semantic_grading.grade_semantic_answer(
        answer=answer,
        **_challenge_rubric(challenge_id),
    )

    assert result["verdict"] == "correct"
    assert result["answer_quality"] == "concise"
    assert result["exact_match"] is True
    assert result["method"] == "curated_minimum_gloss"
    assert result["concept_coverage"] == pytest.approx(
        expected_coverage,
        abs=0.0001,
    )
    assert {
        item["label"]: item["evidence"]
        for item in result["required_concepts"]
    } == expected_evidence
    assert ranker.encode_calls == 0


@pytest.mark.parametrize(
    ("challenge_id", "answer"),
    [
        ("se_retrouver", "ver de nuevo a un amigo"),
        ("tutoyer", "usar tu en vez de usted al hablarle"),
        ("flaner", "andar despacio sin un destino"),
        ("depanner", "ayudarla con una dificultad urgente"),
        ("s_attarder", "quedarse ahi mas de lo esperado"),
        ("madrugar", "salir de la cama muy temprano"),
        ("estrenar", "ponerse algo nuevo por primera vez"),
        ("empalagar", "desagrado luego de comer mucho azucar"),
        ("trasnochar", "no dormir hasta las cuatro de la mañana"),
        ("anorar", "sentir nostalgia por la familia que esta lejos"),
    ],
)
def test_curated_spanish_learner_phrases_are_correct_without_models(
    monkeypatch,
    challenge_id,
    answer,
):
    ranker = _patch_ranker(monkeypatch, available=False)

    result = semantic_grading.grade_semantic_answer(
        answer=answer,
        **_challenge_rubric(challenge_id),
    )

    assert result["verdict"] == "correct"
    assert result["answer_quality"] == "concise"
    assert result["method"] == "curated_minimum_gloss"
    assert result["exact_match"] is True
    assert ranker.encode_calls == 0


@pytest.mark.parametrize(
    ("challenge_id", "answer"),
    [
        ("se_retrouver", "ver de nuevo a un amigo para despedirse"),
        (
            "se_retrouver",
            "ver de nuevo a un amigo significa encontrar un objeto perdido",
        ),
        ("se_retrouver", "no ver de nuevo a un amigo"),
        (
            "se_retrouver",
            "ver de nuevo a un amigo, pero es la primera vez que se conocen",
        ),
        ("tutoyer", "hablar de tu pero usando el vous formal"),
        ("flaner", "pasear pero con prisa hacia una cita urgente"),
        ("depanner", "la saco del apuro pero empeoro el problema"),
        ("s_attarder", "se quedo mas tiempo significa irse inmediatamente"),
        ("madrugar", "levantarse muy temprano después de dormir hasta tarde"),
        ("madrugar", "levantarse muy temprano para acostarse"),
        ("estrenar", "usarlo por primera vez pero ya estaba usado"),
        ("estrenar", "usarlo por primera vez significa comprarlo"),
        ("empalagar", "demasiado dulce pero muy agradable"),
        ("empalagar", "demasiado dulce por una alergia"),
        (
            "empalagar",
            "desagrado luego de comer mucho azúcar por una alergia",
        ),
        (
            "empalagar",
            "desagrado luego de comer mucho azúcar, pero estaba delicioso",
        ),
        (
            "empalagar",
            "no sentir desagrado luego de comer mucho azúcar",
        ),
        (
            "empalagar",
            "desagrado luego de comer mucho azúcar porque estaba amargo",
        ),
        (
            "trasnochar",
            "quedarse despierto hasta muy tarde significa dormir toda la noche",
        ),
        ("anorar", "los echa de menos pero no siente ningún apego"),
    ],
)
def test_minimum_gloss_requires_a_whole_answer_match(
    monkeypatch,
    challenge_id,
    answer,
):
    _patch_ranker(monkeypatch, available=False)

    result = semantic_grading.grade_semantic_answer(
        answer=answer,
        **_challenge_rubric(challenge_id),
    )

    assert result["verdict"] != "correct"
    assert result["answer_quality"] is None
    assert result["exact_match"] is False
    assert result["method"] != "curated_minimum_gloss"


def test_minimum_gloss_requires_complete_concept_evidence(monkeypatch):
    _patch_ranker(monkeypatch, available=False)

    with pytest.raises(ValueError, match="missing a required concept"):
        semantic_grading.grade_semantic_answer(
            answer="short gloss",
            accepted_answers=["a complete explanation"],
            minimum_glosses=[
                ("short gloss", [("First idea", "explicit")]),
            ],
            required_concepts=[
                ("First idea", ["the first idea"]),
                ("Second idea", ["the second idea"]),
            ],
        )


def test_minimum_gloss_context_must_be_declared_by_challenge(monkeypatch):
    _patch_ranker(monkeypatch, available=False)

    with pytest.raises(ValueError, match="context not declared"):
        semantic_grading.grade_semantic_answer(
            answer="short gloss",
            accepted_answers=["a complete explanation"],
            minimum_glosses=[
                ("short gloss", [("Context idea", "context")]),
            ],
            required_concepts=[
                ("Context idea", ["an idea supplied by context"]),
            ],
        )


def test_minimum_gloss_must_cover_at_least_one_concept(monkeypatch):
    _patch_ranker(monkeypatch, available=False)

    with pytest.raises(ValueError, match="at least one meaning concept"):
        semantic_grading.grade_semantic_answer(
            answer="short gloss",
            accepted_answers=["a complete explanation"],
            minimum_glosses=[
                ("short gloss", [("Optional detail", "optional_omitted")]),
            ],
            required_concepts=[
                ("Optional detail", ["a supporting detail"]),
            ],
        )


def test_unreviewed_paraphrase_cannot_inherit_minimum_gloss_evidence(
    monkeypatch,
):
    reference = "excessive sweetness becomes unpleasant"
    concise = "too sweet and unpleasant"
    sweetness = "excessive sweetness"
    dislike = "an unpleasant feeling"
    negative = "pleasant sweetness that makes someone want more"
    ranker = _patch_ranker(
        monkeypatch,
        {
            reference: 0.85,
            concise: 0.93,
            sweetness: 0.81,
            dislike: 0.80,
            negative: 0.84,
        },
    )

    result = semantic_grading.grade_semantic_answer(
        answer="cloying from all that sugar",
        accepted_answers=[reference],
        minimum_glosses=[
            (
                concise,
                [
                    ("sweetness", "explicit"),
                    ("dislike", "explicit"),
                ],
            ),
        ],
        required_concepts=[
            ("sweetness", [sweetness]),
            ("dislike", [dislike]),
        ],
        hard_negatives=[("pleasant", [negative])],
    )

    assert result["verdict"] != "correct"
    assert result["exact_match"] is False
    assert result["answer_quality"] is None
    assert result["method"] != "curated_minimum_gloss"
    assert result["positive_score"] == 0.85
    assert ranker.encode_calls == 2


def test_unrefuted_hard_negative_cannot_be_overridden_by_nli(monkeypatch):
    reference = "using a new possession for the first time"
    action = "putting the possession into use"
    first_time = "doing the action for the first time"
    negative = "buying a possession without using it"
    _patch_ranker(
        monkeypatch,
        {
            reference: 0.88,
            action: 0.87,
            first_time: 0.87,
            negative: 0.875,
        },
    )
    verifier = _patch_verifier(
        monkeypatch,
        {
            reference: NliScores(0.82, 0.13, 0.05),
            negative: NliScores(0.05, 0.15, 0.80),
        },
    )

    result = semantic_grading.grade_semantic_answer(
        answer="buying it for the first time",
        accepted_answers=[reference],
        required_concepts=[
            ("using", [action]),
            ("first time", [first_time]),
        ],
        hard_negatives=[("buying only", [negative])],
    )

    assert result["hard_negatives"][0]["triggered"] is True
    assert result["verdict"] != "correct"
    assert result["verification"]["checked"] is False
    assert verifier.calls == 0


def test_unsafe_embedding_margin_cannot_be_overridden_by_nli(monkeypatch):
    reference = "using a new possession for the first time"
    action = "putting the possession into use"
    first_time = "doing the action for the first time"
    negative = "acquiring a possession without using it"
    _patch_ranker(
        monkeypatch,
        {
            reference: 0.88,
            action: 0.87,
            first_time: 0.87,
            negative: 0.866,
        },
    )
    verifier = _patch_verifier(
        monkeypatch,
        {
            reference: NliScores(0.82, 0.13, 0.05),
            negative: NliScores(0.05, 0.15, 0.80),
        },
    )

    result = semantic_grading.grade_semantic_answer(
        answer="acquiring it for the first time",
        accepted_answers=[reference],
        required_concepts=[
            ("using", [action]),
            ("first time", [first_time]),
        ],
        hard_negatives=[("acquiring only", [negative])],
    )

    assert result["hard_negatives"][0]["triggered"] is False
    assert result["margin"] == pytest.approx(0.014)
    assert result["verdict"] != "correct"
    assert result["verification"]["checked"] is False
    assert verifier.calls == 0


def test_empty_answer_is_incorrect_even_without_the_model(monkeypatch):
    ranker = _patch_ranker(monkeypatch, available=False)

    result = semantic_grading.grade_semantic_answer(
        answer="   ",
        accepted_answers=["a feeling of longing for the past"],
    )

    assert result["verdict"] == "incorrect"
    assert result["method"] == "empty"
    assert ranker.encode_calls == 0


def test_model_unavailable_returns_uncertain_not_lexical_decision(monkeypatch):
    _patch_ranker(monkeypatch, available=False)

    result = semantic_grading.grade_semantic_answer(
        answer="longing for the past with sadness",
        accepted_answers=["a sad longing for the past"],
        required_concepts=[
            ("past longing", ["longing for a past time"]),
        ],
        hard_negatives=[
            ("future optimism", ["excitement about the future"]),
        ],
    )

    assert result["verdict"] == "uncertain"
    assert result["method"] == "lexical_overlap_fallback"
    assert result["model_available"] is False
    assert result["positive_score"] > 0
    assert "not trusted" in result["reasons"][0]


def test_full_rubric_with_safe_negative_margin_is_correct(monkeypatch):
    reference = "A bittersweet longing for a happy time that is absent."
    past = "longing for something absent in the past"
    bittersweet = "both warm affection and sadness"
    negative = "optimism and excitement about the future"
    _patch_ranker(
        monkeypatch,
        {
            reference: 0.92,
            past: 0.89,
            bittersweet: 0.88,
            negative: 0.76,
        },
    )
    _patch_verifier(
        monkeypatch,
        {
            reference: NliScores(0.82, 0.13, 0.05),
            negative: NliScores(0.06, 0.18, 0.76),
        },
    )

    result = semantic_grading.grade_semantic_answer(
        answer=(
            "You miss an absent time from the past and feel warmth mixed "
            "with sadness."
        ),
        accepted_answers=[reference],
        required_concepts=[
            ("past longing", [past]),
            ("bittersweet feeling", [bittersweet]),
        ],
        hard_negatives=[("future anticipation", [negative])],
    )

    assert result["verdict"] == "correct"
    assert semantic_grading.NLI_MODEL_NAME in result["method"]
    assert result["concept_coverage"] == 1.0
    assert result["margin"] == pytest.approx(0.16)
    assert result["hard_negatives"][0]["triggered"] is False
    assert result["verification"]["checked"] is True


def test_missing_required_concept_is_partial(monkeypatch):
    reference = "A bittersweet longing for a happy time in the past."
    past = "longing for something in the past"
    bittersweet = "both warm affection and sadness"
    negative = "optimism and excitement about the future"
    _patch_ranker(
        monkeypatch,
        {
            reference: 0.9,
            past: 0.87,
            bittersweet: 0.74,
            negative: 0.7,
        },
    )

    result = semantic_grading.grade_semantic_answer(
        answer="Missing something from the past.",
        accepted_answers=[reference],
        required_concepts=[
            ("past longing", [past]),
            ("bittersweet feeling", [bittersweet]),
        ],
        hard_negatives=[("future anticipation", [negative])],
    )

    assert result["verdict"] == "partial"
    assert result["concept_coverage"] == 0.5
    assert "bittersweet feeling" in result["reasons"][1]


def test_partial_credit_abstains_when_an_unrefuted_trap_is_too_close(
    monkeypatch,
):
    reference = "A social custom associated with the end of a meal."
    timing = "It happens after eating."
    conversation = "People keep talking together."
    dessert = "A sweet dessert served after eating."
    _patch_ranker(
        monkeypatch,
        {
            reference: 0.8424,
            timing: 0.83,
            conversation: 0.70,
            dessert: 0.8391,
        },
    )

    result = semantic_grading.grade_semantic_answer(
        answer="un dulce compartido en la mesa",
        accepted_answers=[reference],
        required_concepts=[
            ("after the meal", [timing]),
            ("conversation", [conversation]),
        ],
        hard_negatives=[("dessert", [dessert])],
    )

    assert result["hard_negatives"][0]["triggered"] is False
    assert result["verdict"] == "uncertain"
    assert "too close" in result["reasons"][0]


def test_competitive_hard_negative_overrides_high_positive_score(monkeypatch):
    reference = "A sentimental longing for the past."
    concept = "longing directed toward the past"
    negative = "feeling happy and optimistic about the future"
    _patch_ranker(
        monkeypatch,
        {
            reference: 0.88,
            concept: 0.86,
            negative: 0.91,
        },
    )

    result = semantic_grading.grade_semantic_answer(
        answer="It means feeling happy about what will happen next.",
        accepted_answers=[reference],
        required_concepts=[("past longing", [concept])],
        hard_negatives=[("future optimism", [negative])],
    )

    assert result["verdict"] == "incorrect"
    assert result["hard_negatives"][0]["triggered"] is True
    assert result["margin"] == pytest.approx(-0.03)


def test_near_tied_hard_negative_abstains_instead_of_rejecting(monkeypatch):
    reference = "Addressing someone with the informal singular pronoun."
    concept = "using the informal form of address"
    negative = "addressing someone formally"
    _patch_ranker(
        monkeypatch,
        {
            reference: 0.8708,
            concept: 0.86,
            negative: 0.864,
        },
    )

    result = semantic_grading.grade_semantic_answer(
        answer="To use an informal way of saying you to someone.",
        accepted_answers=[reference],
        required_concepts=[("informal address", [concept])],
        hard_negatives=[("formal address", [negative])],
    )

    assert result["hard_negatives"][0]["triggered"] is True
    assert result["verdict"] == "uncertain"
    assert result["margin"] == pytest.approx(0.0068)


def test_competitive_hard_negative_still_abstains_when_axes_confirmed(
    monkeypatch,
):
    rubric = _patch_concise_sobremesa_case(monkeypatch)

    result = semantic_grading.grade_semantic_answer(
        answer="quedarse hablando despues de comer",
        **rubric,
    )

    assert result["verdict"] == "uncertain"
    assert result["hard_negatives"][0]["triggered"] is True
    assert result["verification"]["checked"] is False
    assert len(result["verification"]["confirmed_axes"]) == 3
    assert any(
        "remaining versus leaving" in item
        for item in result["verification"]["confirmed_axes"]
    )


def test_uncurated_single_component_is_reported_as_partial(monkeypatch):
    rubric = _patch_concise_sobremesa_case(monkeypatch)

    result = semantic_grading.grade_semantic_answer(
        answer="quedarse en la mesa",
        **rubric,
    )

    assert result["verdict"] == "partial"
    assert result["concept_coverage"] == pytest.approx(1 / 3, abs=0.0001)
    assert [
        item["label"] for item in result["required_concepts"] if item["covered"]
    ] == ["staying at the table"]
    assert "after the meal" in result["reasons"][-1]
    assert "conversation" in result["reasons"][-1]


@pytest.mark.parametrize(
    "answer",
    [
        "hablando despues de comer",
        "quedarse despues de comer",
        "quedarse en silencio despues de comer",
        "irse hablando despues de comer",
        "quedarse hablando despues de clase",
        "hablando despues de comer en un restaurante",
    ],
)
def test_concise_paraphrase_gate_does_not_accept_missing_or_opposite_axes(
    monkeypatch,
    answer,
):
    rubric = _patch_concise_sobremesa_case(monkeypatch)

    result = semantic_grading.grade_semantic_answer(
        answer=answer,
        **rubric,
    )

    assert result["verdict"] != "correct"
    if answer.startswith("irse"):
        assert any(
            "remaining versus leaving" in item
            for item in result["verification"]["safety_flags"]
        )
    elif "silencio" in answer:
        assert any(
            "conversation versus silence" in item
            for item in result["verification"]["safety_flags"]
        )
    else:
        assert len(result["verification"]["confirmed_axes"]) < 3


def test_unresolved_negation_mismatch_cannot_be_marked_correct(monkeypatch):
    reference = "A strong longing for your home while you are away."
    concept = "missing home while away"
    negative = "wanting to travel farther away from home"
    _patch_ranker(
        monkeypatch,
        {
            reference: 0.92,
            concept: 0.9,
            negative: 0.72,
        },
    )

    result = semantic_grading.grade_semantic_answer(
        answer="It is not a longing for home while away.",
        accepted_answers=[reference],
        required_concepts=[("missing home", [concept])],
        hard_negatives=[("wanderlust", [negative])],
    )

    assert result["verdict"] == "uncertain"
    assert result["negation_guard"]["mismatch"] is True


def test_corrective_negation_is_diagnostic_but_cannot_enable_acceptance(monkeypatch):
    reference = "A strong longing for your home while you are away."
    concept = "missing home while away"
    negative = "a physical illness"
    _patch_ranker(
        monkeypatch,
        {
            reference: 0.92,
            concept: 0.89,
            negative: 0.94,
        },
    )

    result = semantic_grading.grade_semantic_answer(
        answer=(
            "It is not a physical illness; rather, it means missing home "
            "while you are away."
        ),
        accepted_answers=[reference],
        required_concepts=[("missing home", [concept])],
        hard_negatives=[("literal illness", [negative])],
    )

    assert result["verdict"] == "uncertain"
    assert result["negative_score"] == pytest.approx(0.94)
    assert result["hard_negatives"][0]["explicitly_rejected"] is True
    assert result["hard_negatives"][0]["triggered"] is True
    assert result["negation_guard"]["corrective_contrast"] is True
    assert result["negation_guard"]["mismatch"] is True


def test_semantic_similarity_without_concepts_stays_uncertain(monkeypatch):
    reference = "A sentimental longing for the past."
    negative = "optimism about the future"
    _patch_ranker(monkeypatch, {reference: 0.95, negative: 0.5})

    result = semantic_grading.grade_semantic_answer(
        answer="Warm memories and sadness about earlier years.",
        accepted_answers=[reference],
        hard_negatives=[("future optimism", [negative])],
    )

    assert result["verdict"] == "uncertain"
    assert "No required concepts" in result["reasons"][0]


@pytest.mark.parametrize(
    ("answer", "reference", "concept", "negative"),
    [
        (
            "People talk at the table before the meal begins.",
            "People remain at the table talking after the meal.",
            "The social time happens after eating.",
            "Conversation before eating starts.",
        ),
        (
            "On parle à table avant le repas.",
            "On reste à table pour parler après le repas.",
            "Le moment arrive après le repas.",
            "Une conversation avant de manger.",
        ),
        (
            "La gente habla en la mesa antes de comer.",
            "La gente sigue hablando en la mesa después de comer.",
            "El momento ocurre después de comer.",
            "Una conversación antes de la comida.",
        ),
        (
            "Люди разговаривают за столом до еды.",
            "Люди разговаривают за столом после еды.",
            "Этот момент происходит после еды.",
            "Разговор перед едой.",
        ),
    ],
)
def test_timing_opposites_cannot_be_marked_correct(
    monkeypatch,
    answer,
    reference,
    concept,
    negative,
):
    _patch_ranker(
        monkeypatch,
        {reference: 0.93, concept: 0.90, negative: 0.70},
    )
    _patch_verifier(monkeypatch)

    result = semantic_grading.grade_semantic_answer(
        answer=answer,
        accepted_answers=[reference],
        required_concepts=[("after the meal", [concept])],
        hard_negatives=[("before the meal", [negative])],
    )

    assert result["verdict"] == "uncertain"
    assert any(
        "meal timing" in flag for flag in result["verification"]["safety_flags"]
    )


@pytest.mark.parametrize(
    ("answer", "reference", "concept", "negative"),
    [
        (
            "The formal vous form of address.",
            "Use informal tu rather than formal vous.",
            "Address someone with informal tu instead of formal vous.",
            "Use formal vous rather than informal tu.",
        ),
        (
            "La forme d’adresse formelle avec vous.",
            "Employer tu plutôt que vous.",
            "S'adresser avec tu plutôt que vous.",
            "Employer vous plutôt que tu.",
        ),
        (
            "La forma de tratamiento formal.",
            "Usar tú en lugar de la forma formal.",
            "Dirigirse con tú en vez de la forma formal.",
            "Usar la forma formal en lugar de tú.",
        ),
        (
            "Hablarse de tú pero formalmente.",
            "Usar tú en lugar de la forma formal.",
            "Dirigirse con tú en vez de la forma formal.",
            "Usar la forma formal en lugar de tú.",
        ),
        (
            "Формальное обращение на вы.",
            "Обращаться на ты, а не на вы.",
            "Использовать ты вместо вежливого вы.",
            "Обращаться на вы, а не на ты.",
        ),
    ],
)
def test_reversed_form_of_address_cannot_be_marked_correct(
    monkeypatch,
    answer,
    reference,
    concept,
    negative,
):
    _patch_ranker(
        monkeypatch,
        {reference: 0.94, concept: 0.91, negative: 0.72},
    )
    _patch_verifier(monkeypatch)

    result = semantic_grading.grade_semantic_answer(
        answer=answer,
        accepted_answers=[reference],
        required_concepts=[("informal address", [concept])],
        hard_negatives=[("formal address", [negative])],
    )

    assert result["verdict"] == "uncertain"
    assert any(
        "form of address" in flag
        for flag in result["verification"]["safety_flags"]
    )


def test_getting_up_cannot_be_equated_with_going_to_bed(monkeypatch):
    reference = "To get up very early in the morning."
    concept_en = "Getting up from bed at dawn."
    concept_es = "Levantarse de la cama al amanecer."
    negative = "Going to bed at dawn."
    _patch_ranker(
        monkeypatch,
        {
            reference: 0.94,
            concept_en: 0.92,
            concept_es: 0.92,
            negative: 0.72,
        },
    )
    _patch_verifier(monkeypatch)

    result = semantic_grading.grade_semantic_answer(
        answer="Levantarse muy temprano significa acostarse al amanecer.",
        accepted_answers=[reference],
        required_concepts=[
            ("getting out of bed early", [concept_en, concept_es]),
        ],
        hard_negatives=[("going to bed", [negative])],
    )

    assert result["verdict"] == "uncertain"
    assert any(
        "start of day action" in flag
        for flag in result["verification"]["safety_flags"]
    )


@pytest.mark.parametrize(
    ("answer", "reference", "concept", "negative", "axis"),
    [
        (
            "run quickly without a destination",
            "stroll leisurely without a destination",
            "wander slowly without a fixed route",
            "standing still",
            "movement intent",
        ),
        (
            "get up late",
            "get up very early",
            "rise at dawn",
            "sleep all day",
            "time of day",
        ),
        (
            "wear it for the second time",
            "wear something for the first time",
            "use an item for the first time",
            "leave the item unused",
            "item use",
        ),
        (
            "too sweet and delicious",
            "too sweet and cloying",
            "excessive sweetness becomes unpleasant",
            "plain food",
            "food reaction cause",
        ),
        (
            "missing someone who is present",
            "missing someone who is absent",
            "longing for someone far away",
            "forgetting someone",
            "availability of what is missed",
        ),
        (
            "help with the problem and worsen it",
            "help solve a practical problem",
            "helping someone out of a difficulty",
            "ignoring the person",
            "practical help outcome",
        ),
        (
            "wake up early but remain in bed",
            "get up very early",
            "leave the bed at dawn",
            "eat breakfast",
            "start of day action",
        ),
    ],
)
def test_discriminating_axes_block_appended_or_substituted_opposites(
    monkeypatch,
    answer,
    reference,
    concept,
    negative,
    axis,
):
    _patch_ranker(
        monkeypatch,
        {
            reference: 0.94,
            concept: 0.91,
            negative: 0.70,
        },
    )
    _patch_verifier(monkeypatch)

    result = semantic_grading.grade_semantic_answer(
        answer=answer,
        accepted_answers=[reference],
        required_concepts=[("meaning", [concept])],
        hard_negatives=[("wrong meaning", [negative])],
    )

    assert result["verdict"] != "correct"
    assert any(
        axis in flag for flag in result["verification"]["safety_flags"]
    )


def test_nli_cannot_accept_without_confirming_the_local_action_axis(
    monkeypatch,
):
    reference = "wear something for the first time"
    concept = "use an item for the first time"
    negative = "buy an item without using it"
    _patch_ranker(
        monkeypatch,
        {
            reference: 0.90,
            concept: 0.87,
            negative: 0.75,
        },
    )
    verifier = _patch_verifier(
        monkeypatch,
        {
            reference: NliScores(0.82, 0.13, 0.05),
            negative: NliScores(0.05, 0.15, 0.80),
        },
    )

    result = semantic_grading.grade_semantic_answer(
        answer="admire it for the first time",
        accepted_answers=[reference],
        required_concepts=[("using", [concept])],
        hard_negatives=[("buying only", [negative])],
    )

    assert result["verdict"] != "correct"
    assert result["verification"]["confirmed_axes"] == []
    assert result["verification"]["checked"] is False
    assert verifier.calls == 0


def test_non_exact_similarity_abstains_when_nli_verifier_is_missing(monkeypatch):
    reference = "A feeling of being outside familiar surroundings."
    concept = "away from the usual environment"
    negative = "comfortable inside familiar surroundings"
    _patch_ranker(
        monkeypatch,
        {reference: 0.94, concept: 0.91, negative: 0.70},
    )

    result = semantic_grading.grade_semantic_answer(
        answer="Unfamiliarity from leaving the environment you know.",
        accepted_answers=[reference],
        required_concepts=[("away from familiar", [concept])],
        hard_negatives=[("comfortable at home", [negative])],
    )

    assert result["verdict"] == "uncertain"
    assert result["verification"]["available"] is False
    assert "similarity alone" in result["reasons"][0].lower()


def test_embedding_overflow_is_never_silently_accepted(monkeypatch):
    reference = "A sentimental longing for the past."
    concept = "longing for the past"
    negative = "excitement about the future"
    _patch_ranker(
        monkeypatch,
        {reference: 0.95, concept: 0.92, negative: 0.60},
        overflow=True,
    )

    result = semantic_grading.grade_semantic_answer(
        answer="A long answer whose contradictory suffix must remain visible.",
        accepted_answers=[reference],
        required_concepts=[("past longing", [concept])],
        hard_negatives=[("future excitement", [negative])],
    )

    assert result["verdict"] == "uncertain"
    assert result["verification"]["overflow"] is False
    assert any(
        "semantic truncation" in flag
        for flag in result["verification"]["safety_flags"]
    )


def test_payload_uses_server_owned_challenge_and_caps_answer():
    with pytest.raises(ValidationError):
        SemanticGradePayload(
            csrf_token="token",
            challenge_id="se_retrouver",
            answer="x" * 601,
        )

    with pytest.raises(ValidationError):
        SemanticGradePayload(
            csrf_token="token",
            challenge_id="client-supplied-rubric",
            answer="answer",
        )

    expected_ids = (
        "se_retrouver",
        "tutoyer",
        "flaner",
        "depanner",
        "s_attarder",
        "madrugar",
        "estrenar",
        "empalagar",
        "trasnochar",
        "anorar",
    )
    assert tuple(PLAYGROUND_CHALLENGES) == expected_ids
    for challenge_id in expected_ids:
        payload = SemanticGradePayload(
            csrf_token="token",
            challenge_id=challenge_id,
            answer="answer",
        )
        assert set(payload.model_dump()) == {
            "csrf_token",
            "challenge_id",
            "answer",
        }

    for retired_id in (
        "depaysement",
        "sobremesa",
        "retrouvailles",
        "esprit_escalier",
    ):
        with pytest.raises(ValidationError):
            SemanticGradePayload(
                csrf_token="token",
                challenge_id=retired_id,
                answer="answer",
            )


def test_installed_models_never_accept_curated_multilingual_opposites():
    ranker = semantic_grading.get_local_sense_ranker()
    verifier = semantic_grading.get_local_nli_verifier()
    if not _component_is_configured(ranker) or not _component_is_configured(verifier):
        pytest.skip("Pinned local semantic models are not installed.")

    cases = {
        "se_retrouver": [
            "Two strangers meeting and introducing themselves for the first time.",
            "Deux inconnus qui font connaissance pour la première fois.",
            "Dos desconocidos que se conocen por primera vez.",
            "Первая встреча незнакомых людей.",
            "Retrouver un objet perdu.",
            "Ver de nuevo a un amigo para despedirse.",
            "No ver de nuevo a un amigo.",
            (
                "Ver de nuevo a un amigo, pero es la primera vez "
                "que se conocen."
            ),
        ],
        "tutoyer": [
            "Addressing someone with formal vous.",
            "S’adresser à quelqu’un en utilisant le vous formel.",
            "Tratar a alguien de usted formalmente.",
            "Обращаться к человеку на вы.",
            "Insultar a alguien o hablarle con grosería.",
            "Hablar de tú significa tratar de usted.",
            "Hablarle de usted.",
            "Lui parler avec vous.",
        ],
        "flaner": [
            "Hurrying directly to an urgent appointment.",
            "Se dépêcher directement vers un rendez-vous urgent.",
            "Ir deprisa y directamente a una cita urgente.",
            "Estar perdido e intentar encontrar el camino.",
            "Caminar rápido para hacer ejercicio.",
            "Pasear sin rumbo significa correr hacia una cita.",
            "No pasear sin rumbo.",
            "No caminar tranquilamente sin destino.",
            "No vagar sin destino.",
            "Andar deprisa sin destino.",
            "Correr sin destino.",
            "Correr tranquilamente sin destino.",
            "Pasear rápidamente sin rumbo.",
            "Andar perdido sin destino.",
            "Dar una vuelta corriendo.",
            "Быстро гулять без цели.",
            "Quedarse quieto sin rumbo.",
        ],
        "depanner": [
            "Expressing sympathy without offering practical help.",
            "Exprimer de la sympathie sans apporter d’aide concrète.",
            "Mostrar simpatía sin ofrecer ayuda práctica.",
            "Empeorar el problema práctico de la persona.",
            "Reparar una máquina averiada en vez de ayudar a la viajera.",
            "La sacó del apuro, pero empeoró el problema.",
            "Ayudarla con una dificultad y perjudicarla.",
            "La ayudó con el problema y lo agravó.",
        ],
        "s_attarder": [
            "Arriving late after everyone else.",
            "Arriver en retard après tout le monde.",
            "Llegar tarde después de los demás.",
            "Irse inmediatamente sin quedarse.",
            "Ser obligado a quedarse contra la propia voluntad.",
            "Se quedó más tiempo, es decir, se fue inmediatamente.",
        ],
        "madrugar": [
            "Going to bed early in the evening.",
            "Se coucher tôt le soir.",
            "Acostarse temprano por la noche.",
            "Рано ложиться спать вечером.",
            "Quedarse despierto toda la noche hasta el amanecer.",
            "Dormir hasta tarde por la mañana.",
            "Levantarse muy temprano significa acostarse al amanecer.",
            "Levantarse tarde.",
            "Levantarse muy tarde.",
            "Get up late.",
            "Se lever très tard.",
            "Встать очень поздно.",
            "Despertarse temprano y seguir en cama.",
            "Salir de la cama cuando ya era tarde.",
        ],
        "estrenar": [
            "Buying something new without using it.",
            "Acheter quelque chose de neuf sans l’utiliser.",
            "Comprar algo nuevo sin usarlo.",
            "Купить новую вещь, не используя её.",
            "Volver a usar algo que ya se ha usado muchas veces.",
            "Usarlo por primera vez, pero ya se había usado muchas veces.",
            "Comprarlo por primera vez.",
            "Ponérselo otra vez.",
            "Adquirirlo por primera vez.",
            "Ponérselo por segunda vez.",
            "Wear it for the second time.",
            "Le porter pour la deuxième fois.",
            "Надеть во второй раз.",
            "Tocarlo por primera vez.",
            "Lavarlo por primera vez.",
            "Guardarlo por primera vez.",
            "Olerlo por primera vez.",
            "Tenerlo por primera vez.",
        ],
        "empalagar": [
            "Being pleasantly sweet and enjoyable.",
            "Être agréablement sucré et plaisant.",
            "Ser agradablemente dulce y apetecible.",
            "Быть приятно сладким и вкусным.",
            "Tener una reacción alérgica a un ingrediente.",
            "Saber amargo porque la comida está estropeada.",
            "Demasiado dulce, pero agradable y quiero seguir comiendo.",
            "Desagrado luego de comer mucho azúcar por una alergia.",
            "No sentir desagrado luego de comer mucho azúcar.",
            "Me dio asco de tan dulce, pero estaba delicioso.",
            "Mucho azúcar me causa desagrado por una alergia.",
            "Me dio asco porque estaba amargo.",
            "Asco por demasiado sal.",
            "Demasiado dulce y delicioso.",
            "Demasiado dulce y agradable.",
            "Demasiado dulce y apetitoso.",
            "Too sweet and delicious.",
            "Слишком сладкий и вкусный.",
            "Demasiado dulce y nada desagradable.",
        ],
        "trasnochar": [
            "Sleeping first and then getting up very early.",
            "Dormir puis se lever très tôt.",
            "Dormir y después levantarse muy temprano.",
            "Acostarse temprano por la noche.",
            "Dormir tranquilamente toda la noche.",
            "Dormir hasta las cuatro.",
            "No estar despierto hasta tarde.",
            "No pasar la noche sin dormir.",
            (
                "Quedarse despierto hasta muy tarde significa dormir "
                "toda la noche."
            ),
        ],
        "anorar": [
            "Remembering something neutrally without missing it.",
            "Se souvenir de quelque chose sans ressentir de manque.",
            "Recordar algo de manera neutral sin echarlo de menos.",
            "Olvidarlo o no sentir ningún apego.",
            "Tener ganas de algo nuevo que nunca se ha vivido.",
            "Los echa de menos, pero no siente ningún apego.",
            "Sentir nostalgia por algo presente.",
        ],
    }
    for challenge_id, answers in cases.items():
        for answer in answers:
            result = semantic_grading.grade_semantic_answer(
                answer=answer,
                **_challenge_rubric(challenge_id),
            )
            assert result["verdict"] != "correct", (challenge_id, answer, result)

    for challenge_id, challenge in PLAYGROUND_CHALLENGES.items():
        accepted = semantic_grading.grade_semantic_answer(
            answer=challenge.accepted_answers[0],
            **_challenge_rubric(challenge_id),
        )
        assert accepted["verdict"] == "correct", (challenge_id, accepted)
        assert accepted["answer_quality"] == "complete"

        concise = semantic_grading.grade_semantic_answer(
            answer=challenge.minimum_glosses[0].text,
            **_challenge_rubric(challenge_id),
        )
        assert concise["verdict"] == "correct", (challenge_id, concise)
        assert concise["answer_quality"] == "concise"

        trap = semantic_grading.grade_semantic_answer(
            answer=challenge.hard_negatives[0][1][0],
            **_challenge_rubric(challenge_id),
        )
        assert trap["verdict"] == "incorrect", (challenge_id, trap)


@pytest.mark.parametrize(
    ("challenge_id", "answer"),
    [
        ("se_retrouver", "ver otra vez a mi amigo"),
        ("se_retrouver", "volver a encontrarme con un viejo amigo"),
        ("se_retrouver", "encontrarse después de mucho tiempo"),
        ("tutoyer", "tutear a alguien"),
        ("tutoyer", "dirigirse a él usando tú"),
        ("flaner", "pasear tranquilamente sin rumbo"),
        ("flaner", "pasear sin prisa ni destino"),
        ("flaner", "vagar tranquilamente sin destino"),
        ("depanner", "resolverle el problema urgente"),
        ("depanner", "ayudarla a salir de un problema"),
        ("s_attarder", "quedarse más de la cuenta"),
        ("s_attarder", "quedarse más tiempo antes de irse"),
        ("madrugar", "despertarse al amanecer"),
        ("madrugar", "levantarse antes del amanecer"),
        ("estrenar", "darle su primer uso"),
        ("estrenar", "vestirlo por primera vez"),
        ("empalagar", "mucho azucar me causa desagrado"),
        ("empalagar", "me dio asco de tan dulce"),
        ("empalagar", "hartar por ser demasiado dulce"),
        ("empalagar", "hartarse de tanto azúcar"),
        ("trasnochar", "seguir sin dormir hasta las cuatro"),
        ("trasnochar", "acostarse muy tarde"),
        ("trasnochar", "permanecer despierto hasta las cinco"),
        ("anorar", "extrañar mucho a su familia"),
        ("anorar", "echar de menos a los amigos lejanos"),
    ],
)
def test_reviewed_spanish_short_paraphrases_are_curated_exact_matches(
    monkeypatch,
    challenge_id,
    answer,
):
    ranker = _patch_ranker(monkeypatch, available=False)

    result = semantic_grading.grade_semantic_answer(
        answer=answer,
        **_challenge_rubric(challenge_id),
    )

    assert result["verdict"] == "correct", (challenge_id, answer, result)
    assert result["answer_quality"] == "concise"
    assert result["exact_match"] is True
    assert result["method"] == "curated_minimum_gloss"
    assert ranker.encode_calls == 0


@pytest.mark.parametrize(
    ("language", "challenge_id", "valid_answer", "wrong_answer"),
    [
        (
            "German",
            "se_retrouver",
            (
                "Wenn Menschen, die sich kennen, nach langer Trennung "
                "wieder zusammenkommen."
            ),
            "Wenn zwei Fremde sich zum ersten Mal kennenlernen.",
        ),
        (
            "Italian",
            "tutoyer",
            (
                "Rivolgersi a qualcuno usando il tu informale invece "
                "del vous formale."
            ),
            (
                "Rivolgersi a qualcuno usando il vous formale invece "
                "del tu."
            ),
        ),
        (
            "Portuguese",
            "madrugar",
            "Levantar-se da cama ao amanhecer ou muito cedo de manhã.",
            "Ficar acordado a noite toda até o amanhecer.",
        ),
        (
            "Chinese",
            "estrenar",
            "第一次穿上或使用某样东西。",
            "买了新东西，但还没有使用。",
        ),
        (
            "Arabic",
            "empalagar",
            (
                "أن يكون الطعام شديد الحلاوة أو الدسامة إلى حدّ يصبح "
                "منفّرًا وتفقد الرغبة في تناوله."
            ),
            (
                "أن يكون الطعام حلوًا ولذيذًا بحيث ترغب في تناول "
                "المزيد منه."
            ),
        ),
        (
            "Japanese",
            "s_attarder",
            "帰るはずの時間を過ぎても、その場所に長く残ること。",
            "遅れて到着すること。",
        ),
        (
            "Korean",
            "anorar",
            "곁에 없는 소중한 사람이나 시간을 그리워하는 것.",
            "아무 감정 없이 중립적으로 기억하는 것.",
        ),
    ],
)
def test_installed_models_process_unlisted_languages_conservatively(
    language: str,
    challenge_id: str,
    valid_answer: str,
    wrong_answer: str,
):
    """Arbitrary-language input is accepted without sacrificing trap safety.

    The pinned models do not perform equally in every language. A complete
    valid explanation may therefore abstain, but must not be counted wrong;
    the nearby wrong meaning must never be counted correct.
    """

    ranker = semantic_grading.get_local_sense_ranker()
    verifier = semantic_grading.get_local_nli_verifier()
    if not _component_is_configured(ranker) or not _component_is_configured(
        verifier
    ):
        pytest.skip("Pinned local semantic models are not installed.")

    valid = semantic_grading.grade_semantic_answer(
        answer=valid_answer,
        **_challenge_rubric(challenge_id),
    )
    wrong = semantic_grading.grade_semantic_answer(
        answer=wrong_answer,
        **_challenge_rubric(challenge_id),
    )

    assert valid["verdict"] != "incorrect", (
        language,
        challenge_id,
        valid,
    )
    assert wrong["verdict"] != "correct", (
        language,
        challenge_id,
        wrong,
    )


def _component_is_configured(component) -> bool:
    return bool(getattr(component, "configured", False))


def _request_with_csrf(token: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/playground/semantic-grade",
            "headers": [],
            "session": {"csrf_token": token},
            "client": ("127.0.0.1", 12345),
        }
    )


@pytest.mark.asyncio
async def test_playground_endpoint_is_public_but_csrf_protected(monkeypatch):
    _patch_ranker(monkeypatch, available=False)

    async def run_inline(**kwargs):
        return semantic_grading.grade_semantic_answer(**kwargs)

    # Avoid creating a default executor solely for this route contract test;
    # pytest-asyncio's Python 3.12 runner can otherwise wait on executor
    # shutdown after the assertions have completed.
    monkeypatch.setattr(
        playground,
        "_grade_in_thread",
        run_inline,
    )
    payload = SemanticGradePayload(
        csrf_token="token",
        challenge_id="empalagar",
        answer="demasiado dulce",
    )
    # Call through the route's undecorated function so this unit test does not
    # depend on SlowAPI's process-global counter. The absence of auth
    # dependencies is part of the public playground contract.
    response = await playground.semantic_grade.__wrapped__(
        _request_with_csrf("token"),
        payload,
    )

    assert response.verdict == "correct"
    assert response.answer_quality == "concise"
    assert response.method == "curated_minimum_gloss"
    assert {
        item.label: item.evidence
        for item in response.required_concepts
    } == {
        "Excessive sweetness or richness": "explicit",
        "Resulting weariness, saturation, or dislike": "optional_omitted",
    }
    assert response.model_name == semantic_grading.MODEL_NAME
    route = next(
        route
        for route in playground.router.routes
        if route.path == "/api/playground/semantic-grade"
    )
    assert route.dependant.dependencies == []
    assert "app.routers.playground.semantic_grade" in limiter._route_limits

    with pytest.raises(HTTPException) as exc_info:
        await playground.semantic_grade.__wrapped__(
            _request_with_csrf("wrong-token"),
            payload,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid CSRF token"


@pytest.mark.asyncio
async def test_playground_rate_limit_is_enforced_through_asgi(monkeypatch):
    _patch_ranker(monkeypatch, available=False)

    async def run_inline(**kwargs):
        return semantic_grading.grade_semantic_answer(**kwargs)

    monkeypatch.setattr(playground, "_grade_in_thread", run_inline)
    test_app = FastAPI()
    test_app.state.limiter = limiter

    @test_app.exception_handler(RateLimitExceeded)
    async def handle_rate_limit(_: FastAPIRequest, exc: RateLimitExceeded):
        return JSONResponse(status_code=429, content={"detail": str(exc.detail)})

    @test_app.get("/token")
    async def token(request: FastAPIRequest):
        return {"csrf_token": get_or_create_csrf_token(request)}

    test_app.include_router(playground.router)
    test_app.add_middleware(SessionMiddleware, secret_key="semantic-test-secret")
    test_app.add_middleware(SlowAPIMiddleware)

    limiter.reset()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://semantic.test",
        ) as client:
            csrf_token = (await client.get("/token")).json()["csrf_token"]
            payload = {
                "csrf_token": csrf_token,
                "challenge_id": "se_retrouver",
                "answer": PLAYGROUND_CHALLENGES[
                    "se_retrouver"
                ].accepted_answers[0],
            }
            responses = [
                await client.post("/api/playground/semantic-grade", json=payload)
                for _ in range(11)
            ]
        assert [response.status_code for response in responses[:10]] == [200] * 10
        assert responses[10].status_code == 429
    finally:
        limiter.reset()
