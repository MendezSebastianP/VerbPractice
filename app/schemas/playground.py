from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


CsrfToken = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=256),
]
AnswerText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=600),
]


class SemanticGradePayload(BaseModel):
    csrf_token: CsrfToken
    challenge_id: Literal["depaysement", "sobremesa", "tutoyer"]
    answer: AnswerText = ""


class SemanticMatch(BaseModel):
    text: str
    score: float


class SemanticConceptResult(BaseModel):
    label: str
    score: float
    matched_example: str
    covered: bool
    evidence: Literal[
        "semantic",
        "explicit",
        "context",
        "optional_omitted",
        "missing",
    ]


class SemanticHardNegativeResult(BaseModel):
    label: str
    score: float
    matched_example: str
    triggered: bool
    explicitly_rejected: bool


class SemanticNegationGuard(BaseModel):
    mismatch: bool
    corrective_contrast: bool
    answer_markers: list[str]
    reference_markers: list[str]


class SemanticVerification(BaseModel):
    available: bool
    model_name: str
    checked: bool
    entailment_score: float | None
    contradiction_score: float | None
    negative_entailment_score: float | None
    entailment_margin: float | None
    matched_reference: str | None
    overflow: bool
    safety_flags: list[str]
    confirmed_axes: list[str]


class SemanticGradeResponse(BaseModel):
    verdict: Literal["correct", "partial", "incorrect", "uncertain"]
    exact_match: bool
    answer_quality: Literal["complete", "concise"] | None
    method: str
    latency_ms: float = Field(ge=0)
    model_available: bool
    model_name: str
    positive_score: float
    negative_score: float | None
    margin: float | None
    concept_coverage: float = Field(ge=0, le=1)
    matched_reference: SemanticMatch
    required_concepts: list[SemanticConceptResult]
    hard_negatives: list[SemanticHardNegativeResult]
    negation_guard: SemanticNegationGuard
    verification: SemanticVerification
    thresholds: dict[str, float]
    reasons: list[str]
