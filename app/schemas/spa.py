from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.core.languages import LANGUAGE_DEFINITIONS


class CredentialsPayload(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=255)
    csrf_token: str = Field(min_length=1)


class RegisterPayload(CredentialsPayload):
    confirm_password: str = Field(min_length=1, max_length=255)


class CsrfPayload(BaseModel):
    csrf_token: str = Field(min_length=1)


class ThemePayload(CsrfPayload):
    theme: str


class SoundPreferencePayload(CsrfPayload):
    sound_enabled: bool


class TranslationStartPayload(CsrfPayload):
    length: int = 10
    direction: str = Field(pattern=r"^[a-z]{2}_[a-z]{2}$")
    set_id: int | None = None
    # Requests the curated, fixed-order first-run round.
    tutorial: bool = False

    @model_validator(mode="after")
    def validate_direction(self):
        source, target = self.direction.split("_")
        if source == target:
            raise ValueError("Source and target languages must differ")
        unknown = [code.upper() for code in (source, target) if code.upper() not in LANGUAGE_DEFINITIONS]
        if unknown:
            raise ValueError(f"Unknown language code: {unknown[0]}")
        return self


class TranslationAnswerPayload(CsrfPayload):
    answer: str = ""


class ConjugationStartPayload(CsrfPayload):
    language: str = Field(pattern=r"^[A-Z]{2}$")
    level: Literal["easy", "medium", "hard", "custom"]
    fill_level: Literal["easy", "medium", "hard"]
    selected_tenses: list[str] = Field(default_factory=list)
    length: int = 5

    @model_validator(mode="after")
    def validate_language(self):
        if self.language not in LANGUAGE_DEFINITIONS:
            raise ValueError(f"Unknown language code: {self.language}")
        return self


class ConjugationSubmitPayload(CsrfPayload):
    answers: dict[str, dict[str, str]] = Field(default_factory=dict)


class ConjugationTenseSubmitPayload(CsrfPayload):
    tense: str = Field(min_length=1, max_length=100)
    answers: dict[str, str] = Field(default_factory=dict)


class ChatStreamPayload(CsrfPayload):
    message: str = Field(min_length=1, max_length=1200)


class CircleFriendPayload(CsrfPayload):
    username: str = Field(min_length=1, max_length=128)


class TrainerSetupPayload(BaseModel):
    mode: str = Field(min_length=1, max_length=32)
    setup: dict = Field(default_factory=dict)


class OnboardingPatchPayload(CsrfPayload):
    """Partial update of first-run progress. Lists are merged, never replaced."""

    completed: list[str] | None = Field(default=None, max_length=16)
    seen_tours: list[str] | None = Field(default=None, max_length=16)
    skipped: bool | None = None
    reset: bool | None = None


class SettingsPatchPayload(CsrfPayload):
    mother_tongue_code: str | None = None
    learning_language_code: str | None = None
    translation_display_mode: str | None = None
    force_unlock_added_words: bool | None = None
    show_shortcuts: bool | None = None
    last_practice_pair: str | None = None
    last_practice_mode: str | None = None
    trainer_setup: TrainerSetupPayload | None = None


class AddWordPayload(CsrfPayload):
    input_text: str = Field(min_length=1, max_length=128)
    context: str | None = Field(default=None, max_length=512)
    question: str | None = Field(default=None, max_length=512)
    context_source: str = Field(
        default="manual", pattern=r"^(manual|photo)$"
    )
    learning_lang_code: str | None = Field(default=None, max_length=8)
    mother_lang_code: str | None = Field(default=None, max_length=8)


class SelectWordSensePayload(CsrfPayload):
    sense_id: int = Field(gt=0)


class AddWordOfflinePayload(CsrfPayload):
    learning_text: str = Field(min_length=1, max_length=128)
    native_text: str = Field(min_length=1, max_length=256)
    learning_lang_code: str = Field(min_length=2, max_length=8)
    mother_lang_code: str = Field(min_length=2, max_length=8)
    note: str | None = Field(default=None, max_length=256)


class OcrWordBox(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)


class OcrWordResult(BaseModel):
    text: str
    confidence: float = Field(ge=0, le=100)
    box: OcrWordBox


class OcrExtractResponse(BaseModel):
    text: str
    lines: list[str]
    mean_confidence: float | None = None
    ocr_lang: str
    words: list[OcrWordResult] = Field(default_factory=list)


class DeleteUserWordPayload(CsrfPayload):
    language_pair: str = Field(min_length=4, max_length=16)


class ExpandWordPayload(CsrfPayload):
    pass


class ReportTranslationPayload(CsrfPayload):
    entry_type: str = Field(pattern=r"^(lexical|native)$")
    entry_id: int
    reason: str | None = Field(default=None, max_length=512)


class ResolveReportPayload(CsrfPayload):
    action: str = Field(pattern=r"^(dismiss|delete_translation|regenerate)$")


class AdminWordRowPayload(CsrfPayload):
    text: str | None = None
    language_code: str | None = None
    translation: str | None = None
    target_language_code: str | None = None
    synonyms: list[str] | str | None = None
    verified: bool | None = None
    source: str | None = None


class AdminVerbRowPayload(CsrfPayload):
    infinitive: str | None = None
    language_code: str | None = None
    translation: str | None = None
    target_language_code: str | None = None
    synonyms: list[str] | str | None = None
    verified: bool | None = None
    source: str | None = None


class AdminConjugationRowPayload(CsrfPayload):
    infinitive: str | None = None
    language_code: str | None = None
    mood: str | None = None
    tense: str | None = None
    pronoun: str | None = None
    conjugated_form: str | None = None
    verified: bool | None = None
    source: str | None = None
