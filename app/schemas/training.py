from typing import Literal

from pydantic import BaseModel, Field

from app.core.languages import LANGUAGE_DEFINITIONS


class TranslationSessionStart(BaseModel):
    mode: Literal["word_translation", "verb_translation"]
    direction: str = Field(pattern=r"^[a-z]{2}_[a-z]{2}$")
    length: int = Field(default=10, ge=1, le=50)

    def model_post_init(self, __context) -> None:
        source, target = self.direction.split("_")
        for code in (source.upper(), target.upper()):
            if code not in LANGUAGE_DEFINITIONS:
                raise ValueError(f"Unknown language code in direction: {code}")
        if source == target:
            raise ValueError("Direction source and target must differ")


class ConjugationSessionStart(BaseModel):
    language: str = Field(pattern=r"^[A-Z]{2}$")
    level: Literal["easy", "medium", "hard", "custom"] = "easy"
    fill_level: Literal["easy", "medium", "hard"] = "easy"
    selected_tenses: list[str] = Field(default_factory=list)

    def model_post_init(self, __context) -> None:
        if self.language not in LANGUAGE_DEFINITIONS:
            raise ValueError(f"Unknown language code: {self.language}")


class SessionScore(BaseModel):
    correct: int
    total: int
    accuracy: float
