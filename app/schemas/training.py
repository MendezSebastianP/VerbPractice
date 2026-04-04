from typing import Literal

from pydantic import BaseModel, Field


class TranslationSessionStart(BaseModel):
    mode: Literal["word_translation", "verb_translation"]
    direction: Literal["fr_es", "es_fr"]
    length: int = Field(default=10, ge=1, le=50)


class ConjugationSessionStart(BaseModel):
    language: Literal["FR", "ES"]
    level: Literal["easy", "medium", "hard", "custom"] = "easy"
    fill_level: Literal["easy", "medium", "hard"] = "easy"
    selected_tenses: list[str] = Field(default_factory=list)


class SessionScore(BaseModel):
    correct: int
    total: int
    accuracy: float
