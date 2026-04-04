from __future__ import annotations

from collections.abc import Mapping

LANGUAGE_DEFINITIONS: dict[str, dict[str, object]] = {
    "FR": {
        "name": "French",
        "pronoun_set": ["je", "tu", "il (elle, on)", "nous", "vous", "ils (elles)"],
        "difficulty_tiers": {
            "easy": ["Présent", "Futur", "Passé composé"],
            "medium": ["Imparfait", "Conditionnel présent", "Impératif"],
            "hard": ["Subjonctif présent", "Passé Simple", "Subjonctif imparfait"],
        },
        "tense_definitions": {
            "Présent": {"mood": "Indicatif"},
            "Futur": {"mood": "Indicatif"},
            "Passé composé": {"mood": "Indicatif"},
            "Imparfait": {"mood": "Indicatif"},
            "Conditionnel présent": {"mood": "Conditionnel"},
            "Impératif": {"mood": "Impératif"},
            "Subjonctif présent": {"mood": "Subjonctif"},
            "Passé Simple": {"mood": "Indicatif"},
            "Subjonctif imparfait": {"mood": "Subjonctif"},
        },
    },
    "ES": {
        "name": "Spanish",
        "pronoun_set": ["yo", "tú", "él", "nosotros", "vosotros", "ellos"],
        "difficulty_tiers": {
            "easy": ["Presente", "Futuro", "Pretérito perfecto compuesto"],
            "medium": ["Pretérito imperfecto", "Condicional", "Imperativo", "Futuro perfecto"],
            "hard": ["Subjuntivo presente", "Pretérito perfecto simple", "Pretérito pluscuamperfecto"],
        },
        "tense_definitions": {
            "Presente": {"mood": "Indicativo"},
            "Futuro": {"mood": "Indicativo"},
            "Pretérito perfecto compuesto": {"mood": "Indicativo"},
            "Pretérito imperfecto": {"mood": "Indicativo"},
            "Condicional": {"mood": "Condicional"},
            "Imperativo": {"mood": "Imperativo"},
            "Futuro perfecto": {"mood": "Indicativo"},
            "Subjuntivo presente": {"mood": "Subjuntivo"},
            "Pretérito perfecto simple": {"mood": "Indicativo"},
            "Pretérito pluscuamperfecto": {"mood": "Indicativo"},
        },
    },
}


def tenses_for_level(language: Mapping[str, object], level: str) -> list[str]:
    tiers = language["difficulty_tiers"]
    if not isinstance(tiers, Mapping):
        return []

    easy = list(tiers.get("easy", []))
    medium = list(tiers.get("medium", []))
    hard = list(tiers.get("hard", []))

    if level == "easy":
        return easy
    if level == "medium":
        return [*easy, *medium]
    if level == "hard":
        return [*easy, *medium, *hard]
    return []
