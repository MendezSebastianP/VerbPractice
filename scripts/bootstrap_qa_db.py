from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import Base
from app.db.models import Language, User, UserProfile, Verb, VerbConjugation, VerbTranslation, Word, WordTranslation
from app.db.session import AsyncSessionLocal, engine

WORD_TRANSLATIONS = {
    "hola": "bonjour",
    "tiempo": "temps",
    "mundo": "monde",
    "casa": "maison",
    "libro": "livre",
    "amigo": "ami",
}

VERB_TRANSLATIONS = {
    "aller": "ir",
    "avoir": "haber",
    "faire": "hacer",
    "parler": "hablar",
}


async def get_or_create_language(
    db,
    *,
    code: str,
    name: str,
    pronouns: list[str],
    tense_definitions: dict[str, dict[str, str]],
    difficulty_tiers: dict[str, list[str]],
) -> Language:
    existing = await db.execute(select(Language).where(Language.code == code))
    language = existing.scalar_one_or_none()
    if language is not None:
        return language

    language = Language(
        code=code,
        name=name,
        pronoun_set=pronouns,
        tense_definitions=tense_definitions,
        difficulty_tiers=difficulty_tiers,
    )
    db.add(language)
    await db.flush()
    return language


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        fr = await get_or_create_language(
            db,
            code="FR",
            name="French",
            pronouns=["je", "tu", "il", "nous", "vous", "ils"],
            tense_definitions={"Présent": {"mood": "Indicatif"}},
            difficulty_tiers={"easy": ["Présent"], "medium": [], "hard": []},
        )
        es = await get_or_create_language(
            db,
            code="ES",
            name="Spanish",
            pronouns=["yo", "tu", "el", "nosotros", "vosotros", "ellos"],
            tense_definitions={"Presente": {"mood": "Indicativo"}},
            difficulty_tiers={"easy": ["Presente"], "medium": [], "hard": []},
        )

        for source, target in WORD_TRANSLATIONS.items():
            word = Word(text=source, language_id=es.id)
            db.add(word)
            await db.flush()
            db.add(
                WordTranslation(
                    word_id=word.id,
                    target_language_id=fr.id,
                    translation=target,
                    synonyms=[],
                    verified=True,
                    source="qa_seed",
                )
            )

        first_verb_id: int | None = None
        for source, target in VERB_TRANSLATIONS.items():
            verb = Verb(infinitive=source, language_id=fr.id)
            db.add(verb)
            await db.flush()
            if first_verb_id is None:
                first_verb_id = verb.id
            db.add(
                VerbTranslation(
                    verb_id=verb.id,
                    target_language_id=es.id,
                    translation=target,
                    synonyms=[],
                    verified=True,
                    source="qa_seed",
                )
            )

        assert first_verb_id is not None
        for pronoun, form in [
            ("je", "vais"),
            ("tu", "vas"),
            ("il", "va"),
            ("nous", "allons"),
            ("vous", "allez"),
            ("ils", "vont"),
        ]:
            db.add(
                VerbConjugation(
                    verb_id=first_verb_id,
                    language_id=fr.id,
                    mood="Indicatif",
                    tense="Présent",
                    pronoun=pronoun,
                    conjugated_form=form,
                    verified=True,
                    source="qa_seed",
                )
            )

        for username in ["demo", "circle"]:
            user = User(
                username=username,
                password_hash=hash_password("demo12345"),
                is_admin=username == "demo",
            )
            db.add(user)
            await db.flush()
            db.add(
                UserProfile(
                    user_id=user.id,
                    xp=0,
                    level=1,
                    streak_days=0,
                    theme_preference="light",
                )
            )

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
