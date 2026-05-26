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
    set_id: int | None = None


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


class SettingsPatchPayload(CsrfPayload):
    mother_tongue_code: str | None = None
    learning_language_code: str | None = None
    translation_display_mode: str | None = None
    force_unlock_added_words: bool | None = None
    last_practice_pair: str | None = None
    last_practice_mode: str | None = None


class AddWordPayload(CsrfPayload):
    input_text: str = Field(min_length=1, max_length=128)
    context: str | None = Field(default=None, max_length=512)
    learning_lang_code: str | None = Field(default=None, max_length=8)


class AddWordOfflinePayload(CsrfPayload):
    learning_text: str = Field(min_length=1, max_length=128)
    native_text: str = Field(min_length=1, max_length=256)
    learning_lang_code: str = Field(min_length=2, max_length=8)
    mother_lang_code: str = Field(min_length=2, max_length=8)
    note: str | None = Field(default=None, max_length=256)


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
