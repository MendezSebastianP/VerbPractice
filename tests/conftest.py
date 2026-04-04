import asyncio
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import Base
from app.db.models import Language, User, UserProfile, Verb, VerbConjugation, VerbTranslation, Word, WordTranslation
from app.db.session import AsyncSessionLocal, engine
from app.main import app

TEST_PASSWORD = "smoke-pass-123"
TEST_USERNAME = "smoke_qa"
FRIEND_USERNAME = "circle_qa"

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
    "venir": "venir",
    "voir": "ver",
}


async def _get_or_create_language(
    db,
    *,
    code: str,
    name: str,
    pronouns: list[str],
    tense_definitions: dict[str, dict[str, str]],
    difficulty_tiers: dict[str, list[str]],
) -> Language:
    result = await db.execute(select(Language).where(Language.code == code))
    language = result.scalar_one_or_none()
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


async def _ensure_smoke_data() -> dict[str, str]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        fr = await _get_or_create_language(
            db,
            code="FR",
            name="French",
            pronouns=["je", "tu", "il", "nous", "vous", "ils"],
            tense_definitions={
                "Présent": {"mood": "Indicatif"},
                "Futur": {"mood": "Indicatif"},
            },
            difficulty_tiers={"easy": ["Présent"], "medium": ["Futur"], "hard": []},
        )
        es = await _get_or_create_language(
            db,
            code="ES",
            name="Spanish",
            pronouns=["yo", "tu", "el", "nosotros", "vosotros", "ellos"],
            tense_definitions={"Presente": {"mood": "Indicativo"}},
            difficulty_tiers={"easy": ["Presente"], "medium": [], "hard": []},
        )

        for source, target in WORD_TRANSLATIONS.items():
            word = (
                await db.execute(select(Word).where(Word.text == source, Word.language_id == es.id))
            ).scalar_one_or_none()
            if word is None:
                word = Word(text=source, language_id=es.id)
                db.add(word)
                await db.flush()

            translation = (
                await db.execute(
                    select(WordTranslation).where(
                        WordTranslation.word_id == word.id,
                        WordTranslation.target_language_id == fr.id,
                        WordTranslation.translation == target,
                    )
                )
            ).scalar_one_or_none()
            if translation is None:
                db.add(
                    WordTranslation(
                        word_id=word.id,
                        target_language_id=fr.id,
                        translation=target,
                        synonyms=[],
                        verified=True,
                        source="smoke_test",
                    )
                )

        present_rows = [
            ("je", "vais"),
            ("tu", "vas"),
            ("il", "va"),
            ("nous", "allons"),
            ("vous", "allez"),
            ("ils", "vont"),
        ]
        for index, (source, target) in enumerate(VERB_TRANSLATIONS.items()):
            verb = (
                await db.execute(select(Verb).where(Verb.infinitive == source, Verb.language_id == fr.id))
            ).scalar_one_or_none()
            if verb is None:
                verb = Verb(infinitive=source, language_id=fr.id)
                db.add(verb)
                await db.flush()

            translation = (
                await db.execute(
                    select(VerbTranslation).where(
                        VerbTranslation.verb_id == verb.id,
                        VerbTranslation.target_language_id == es.id,
                        VerbTranslation.translation == target,
                    )
                )
            ).scalar_one_or_none()
            if translation is None:
                db.add(
                    VerbTranslation(
                        verb_id=verb.id,
                        target_language_id=es.id,
                        translation=target,
                        synonyms=[],
                        verified=True,
                        source="smoke_test",
                    )
                )

            if index == 0:
                for pronoun, form in present_rows:
                    existing = (
                        await db.execute(
                            select(VerbConjugation).where(
                                VerbConjugation.verb_id == verb.id,
                                VerbConjugation.language_id == fr.id,
                                VerbConjugation.mood == "Indicatif",
                                VerbConjugation.tense == "Présent",
                                VerbConjugation.pronoun == pronoun,
                            )
                        )
                    ).scalar_one_or_none()
                    if existing is None:
                        db.add(
                            VerbConjugation(
                                verb_id=verb.id,
                                language_id=fr.id,
                                mood="Indicatif",
                                tense="Présent",
                                pronoun=pronoun,
                                conjugated_form=form,
                                verified=True,
                                source="smoke_test",
                            )
                        )

        for username in [TEST_USERNAME, FRIEND_USERNAME]:
            user = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
            if user is None:
                user = User(
                    username=username,
                    password_hash=hash_password(TEST_PASSWORD),
                    is_admin=username == TEST_USERNAME,
                )
                db.add(user)
                await db.flush()
                db.add(
                    UserProfile(
                        user_id=user.id,
                        xp=0,
                        level=1,
                        streak_days=0,
                        last_active_date=date.today(),
                        theme_preference="light",
                    )
                )
            elif username == TEST_USERNAME and not user.is_admin:
                user.is_admin = True

        await db.commit()

    return {"username": TEST_USERNAME, "password": TEST_PASSWORD}


@pytest.fixture(scope="session")
def smoke_user():
    try:
        return asyncio.run(_ensure_smoke_data())
    except Exception as exc:  # pragma: no cover - skip path only used when DB is unavailable
        pytest.skip(f"Smoke routes need a reachable PostgreSQL database: {exc}")


@pytest.fixture(scope="session")
def circle_user():
    return {"username": FRIEND_USERNAME, "password": TEST_PASSWORD}


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
