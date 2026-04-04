from __future__ import annotations

from pydantic import BaseModel, Field


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
    direction: str


class TranslationAnswerPayload(CsrfPayload):
    answer: str = ""


class ConjugationStartPayload(CsrfPayload):
    language: str
    level: str
    fill_level: str
    selected_tenses: list[str] = Field(default_factory=list)
    length: int = 5


class ConjugationSubmitPayload(CsrfPayload):
    answers: dict[str, dict[str, str]] = Field(default_factory=dict)


class ChatStreamPayload(CsrfPayload):
    message: str = Field(min_length=1, max_length=1200)


class CircleFriendPayload(CsrfPayload):
    username: str = Field(min_length=1, max_length=128)


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
