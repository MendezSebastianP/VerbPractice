from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import (
    Language,
    ProgressItemType,
    SessionItem,
    TrainingMode,
    User,
    UserProfile,
    UserProgress,
    Verb,
    VerbConjugation,
    Word,
    WordTranslation,
)
from app.routers.api import _conjugation_state, _translation_state
from app.services.training_service import (
    start_conjugation_session,
    start_translation_session,
    submit_conjugation_answers,
    submit_translation_answer,
)


@pytest_asyncio.fixture()
async def sqlite_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture()
async def seeded_training_context(sqlite_session):
    fr = Language(
        code="FR",
        name="French",
        pronoun_set=["je", "tu", "il", "nous", "vous", "ils"],
        tense_definitions={"Présent": {"mood": "Indicatif"}},
        difficulty_tiers={"easy": ["Présent"], "medium": [], "hard": []},
    )
    es = Language(
        code="ES",
        name="Spanish",
        pronoun_set=["yo", "tu", "el", "nosotros", "vosotros", "ellos"],
        tense_definitions={"Presente": {"mood": "Indicativo"}},
        difficulty_tiers={"easy": ["Presente"], "medium": [], "hard": []},
    )
    sqlite_session.add_all([fr, es])
    await sqlite_session.flush()

    user = User(username="service-tester", password_hash="not-used")
    sqlite_session.add(user)
    await sqlite_session.flush()

    profile = UserProfile(
        user_id=user.id,
        xp=0,
        level=1,
        streak_days=0,
        last_active_date=date.today(),
        theme_preference="light",
    )
    sqlite_session.add(profile)

    word = Word(text="hola", language_id=es.id)
    sqlite_session.add(word)
    await sqlite_session.flush()

    sqlite_session.add(
        WordTranslation(
            word_id=word.id,
            target_language_id=fr.id,
            translation="bonjour",
            synonyms=[],
            verified=True,
            source="test",
        )
    )

    verb = Verb(infinitive="aller", language_id=fr.id)
    sqlite_session.add(verb)
    await sqlite_session.flush()

    for pronoun, form in [
        ("je", "vais"),
        ("tu", "vas"),
        ("il", "va"),
        ("nous", "allons"),
        ("vous", "allez"),
        ("ils", "vont"),
    ]:
        sqlite_session.add(
            VerbConjugation(
                verb_id=verb.id,
                language_id=fr.id,
                mood="Indicatif",
                tense="Présent",
                pronoun=pronoun,
                conjugated_form=form,
                verified=True,
                source="test",
            )
        )

    await sqlite_session.commit()
    await sqlite_session.refresh(profile)

    return {
        "db": sqlite_session,
        "user": user,
        "profile": profile,
        "word": word,
        "verb": verb,
    }


@pytest.mark.asyncio
async def test_word_score_changes_only_once_per_session(seeded_training_context):
    db = seeded_training_context["db"]
    user = seeded_training_context["user"]
    profile = seeded_training_context["profile"]

    session = await start_translation_session(
        db,
        user_id=user.id,
        mode=TrainingMode.WORD_TRANSLATION,
        direction="es_fr",
        length=1,
    )

    first_result = await submit_translation_answer(
        db,
        session=session,
        profile=profile,
        answer="salut",
        give_up=False,
    )
    second_result = await submit_translation_answer(
        db,
        session=session,
        profile=profile,
        answer="bonjour",
        give_up=False,
    )
    await db.flush()

    progress = (
        await db.execute(
            select(UserProgress).where(
                UserProgress.user_id == user.id,
                UserProgress.item_type == ProgressItemType.WORD,
                UserProgress.language_pair == "es_fr",
            )
        )
    ).scalar_one()
    items = (
        await db.execute(select(SessionItem).where(SessionItem.session_id == session.id).order_by(SessionItem.id.asc()))
    ).scalars().all()

    assert first_result["finished"] is False
    assert second_result["finished"] is True
    assert progress.probability == pytest.approx(1300.0)
    assert [item.multiplier_applied for item in items] == pytest.approx([1.3, 1.0])
    assert [item.meta["score_applied"] for item in items] == [True, False]


@pytest.mark.asyncio
async def test_word_first_correct_still_scores_normally(seeded_training_context):
    db = seeded_training_context["db"]
    user = seeded_training_context["user"]
    profile = seeded_training_context["profile"]

    session = await start_translation_session(
        db,
        user_id=user.id,
        mode=TrainingMode.WORD_TRANSLATION,
        direction="es_fr",
        length=1,
    )

    result = await submit_translation_answer(
        db,
        session=session,
        profile=profile,
        answer="bonjour",
        give_up=False,
    )
    await db.flush()

    progress = (
        await db.execute(
            select(UserProgress).where(
                UserProgress.user_id == user.id,
                UserProgress.item_type == ProgressItemType.WORD,
                UserProgress.language_pair == "es_fr",
            )
        )
    ).scalar_one()
    item = (
        await db.execute(select(SessionItem).where(SessionItem.session_id == session.id))
    ).scalar_one()

    assert result["finished"] is True
    assert progress.probability == pytest.approx(700.0)
    assert item.multiplier_applied == pytest.approx(0.7)
    assert item.meta["score_applied"] is True


@pytest.mark.asyncio
async def test_conjugation_multiple_wrong_pronouns_all_change_tense_score(seeded_training_context):
    db = seeded_training_context["db"]
    user = seeded_training_context["user"]
    profile = seeded_training_context["profile"]

    session = await start_conjugation_session(
        db,
        user_id=user.id,
        language_code="FR",
        level="easy",
        selected_tenses=["Présent"],
        fill_level="hard",
        length=1,
    )

    result = await submit_conjugation_answers(
        db,
        session=session,
        profile=profile,
        answers={
            "Présent": {
                "je": "faux-1",
                "tu": "faux-2",
                "il": "va",
                "nous": "allons",
                "vous": "allez",
                "ils": "vont",
            }
        },
    )
    await db.flush()

    progress = (
        await db.execute(
            select(UserProgress).where(
                UserProgress.user_id == user.id,
                UserProgress.item_type == ProgressItemType.CONJUGATION,
                UserProgress.language_pair == "fr_conj",
            )
        )
    ).scalar_one()
    item = (
        await db.execute(select(SessionItem).where(SessionItem.session_id == session.id))
    ).scalar_one()

    assert result["finished"] is True
    assert progress.extra_data["tense_scores"]["Présent"] == pytest.approx(966.6666666667)
    assert progress.probability == pytest.approx(966.6666666667)
    assert item.multiplier_applied == pytest.approx(0.9666666667)
    assert item.meta["score_applied"] is True
    assert sum(1 for check in item.meta["checks"] if check["score_applied"]) == 6


@pytest.mark.asyncio
async def test_conjugation_same_slot_does_not_score_twice_in_same_session(seeded_training_context):
    db = seeded_training_context["db"]
    user = seeded_training_context["user"]
    profile = seeded_training_context["profile"]

    session = await start_conjugation_session(
        db,
        user_id=user.id,
        language_code="FR",
        level="easy",
        selected_tenses=["Présent"],
        fill_level="hard",
        length=1,
    )

    wrong_answers = {
        "Présent": {
            "je": "x",
            "tu": "x",
            "il": "x",
            "nous": "x",
            "vous": "x",
            "ils": "x",
        }
    }
    await submit_conjugation_answers(db, session=session, profile=profile, answers=wrong_answers)

    config = dict(session.config or {})
    config["index"] = 0
    session.config = config
    session.completed_at = None

    await submit_conjugation_answers(db, session=session, profile=profile, answers=wrong_answers)
    await db.flush()

    progress = (
        await db.execute(
            select(UserProgress).where(
                UserProgress.user_id == user.id,
                UserProgress.item_type == ProgressItemType.CONJUGATION,
                UserProgress.language_pair == "fr_conj",
            )
        )
    ).scalar_one()
    items = (
        await db.execute(select(SessionItem).where(SessionItem.session_id == session.id).order_by(SessionItem.id.asc()))
    ).scalars().all()

    assert progress.extra_data["tense_scores"]["Présent"] == pytest.approx(1500.0)
    assert [item.multiplier_applied for item in items] == pytest.approx([1.5, 1.0])
    assert items[1].meta["score_applied"] is False
    assert all(check["score_applied"] is False for check in items[1].meta["checks"])


@pytest.mark.asyncio
async def test_finished_states_expose_retry_signal_and_last_settings(seeded_training_context):
    db = seeded_training_context["db"]
    user = seeded_training_context["user"]

    translation_state = await _translation_state(
        db,
        user_id=user.id,
        mode=TrainingMode.WORD_TRANSLATION,
        result={"finished": True, "direction": "fr_es", "length": 20},
    )
    conjugation_state = await _conjugation_state(
        db,
        user_id=user.id,
        result={"finished": True, "language_pair": "fr_conj"},
    )

    assert translation_state["setup"] is True
    assert translation_state["finished"] is True
    assert translation_state["defaults"] == {"length": 20, "direction": "fr_es"}
    assert conjugation_state["setup"] is True
    assert conjugation_state["finished"] is True
