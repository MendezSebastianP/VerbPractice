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
    check_conjugation_tense,
    conjugation_tenses_for_level,
    eligible_conjugation_verb_ids,
    eligible_translation_item_ids,
    get_conjugation_question,
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
async def test_translation_eligibility_excludes_items_without_the_target_language(seeded_training_context):
    db = seeded_training_context["db"]
    es = (await db.execute(select(Language).where(Language.code == "ES"))).scalar_one()
    orphan = Word(text="sin-traduccion", language_id=es.id)
    db.add(orphan)
    await db.flush()

    eligible_ids = await eligible_translation_item_ids(
        db,
        mode=TrainingMode.WORD_TRANSLATION,
        direction="es_fr",
    )

    assert seeded_training_context["word"].id in eligible_ids
    assert orphan.id not in eligible_ids


@pytest.mark.asyncio
@pytest.mark.parametrize(("fill_level", "expected_guides"), [("medium", 1), ("easy", 4), ("hard", 0)])
async def test_conjugation_fill_levels_use_safe_guide_counts(
    seeded_training_context,
    fill_level,
    expected_guides,
):
    db = seeded_training_context["db"]
    user = seeded_training_context["user"]
    session = await start_conjugation_session(
        db,
        user_id=user.id,
        language_code="FR",
        level="easy",
        selected_tenses=["Présent"],
        fill_level=fill_level,
        length=1,
    )

    question = await get_conjugation_question(db, session)

    assert question is not None
    assert sum(question.prefill["Présent"].values()) == expected_guides
    assert sum(not is_guide for is_guide in question.prefill["Présent"].values()) >= 1


@pytest.mark.asyncio
async def test_conjugation_uniform_tense_never_prefills_a_giveaway(seeded_training_context):
    db = seeded_training_context["db"]
    user = seeded_training_context["user"]
    conjugations = (await db.execute(select(VerbConjugation))).scalars().all()
    for conjugation in conjugations:
        conjugation.conjugated_form = "same form"
    await db.flush()

    session = await start_conjugation_session(
        db,
        user_id=user.id,
        language_code="FR",
        level="easy",
        selected_tenses=["Présent"],
        fill_level="easy",
        length=1,
    )
    question = await get_conjugation_question(db, session)

    assert question is not None
    assert not any(question.prefill["Présent"].values())


@pytest.mark.asyncio
async def test_conjugation_tense_review_freezes_answers_until_final_submit(seeded_training_context):
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
    frozen_answers = {
        "je": "wrong",
        "tu": "vas",
        "il": "va",
        "nous": "allons",
        "vous": "allez",
        "ils": "vont",
    }

    review = await check_conjugation_tense(
        db,
        session=session,
        tense="Présent",
        answers=frozen_answers,
    )
    repeated = await check_conjugation_tense(
        db,
        session=session,
        tense="Présent",
        answers={**frozen_answers, "je": "vais"},
    )

    assert review == repeated
    assert review["correct"] == 5
    assert review["total"] == 6
    assert review["cells"][0] == {
        "pronoun": "je",
        "kind": "answer",
        "answer": "wrong",
        "expected": "vais",
        "correct": False,
    }
    assert session.config["checked_conjugation_tenses"] == ["Présent"]
    assert session.config["pending_conjugation_answers"]["Présent"]["je"] == "wrong"

    result = await submit_conjugation_answers(
        db,
        session=session,
        profile=profile,
        answers={"Présent": {**frozen_answers, "je": "vais"}},
    )

    assert result["correct"] == 5
    assert result["review"]["rows"][0]["cells"][0]["answer"] == "wrong"
    assert "pending_conjugation_answers" not in session.config
    assert "checked_conjugation_tenses" not in session.config


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
    review = result["review"]
    assert review["verb"] == "aller"
    je_cell = next(row for row in review["rows"] if row["pronoun"] == "je")["cells"][0]
    assert je_cell == {
        "tense": "Présent",
        "kind": "answer",
        "answer": "faux-1",
        "expected": "vais",
        "correct": False,
    }


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
async def test_conjugation_eligibility_requires_every_requested_slot(seeded_training_context):
    db = seeded_training_context["db"]
    language = (
        await db.execute(select(Language).where(Language.code == "FR"))
    ).scalar_one()
    language.tense_definitions = {
        "Présent": {"mood": "Indicatif"},
        "Futur": {"mood": "Indicatif"},
    }
    language.difficulty_tiers = {"easy": ["Présent"], "medium": ["Futur"], "hard": []}
    await db.flush()

    present_ids = await eligible_conjugation_verb_ids(
        db,
        language=language,
        selected_tenses=["Présent"],
    )
    combined_ids = await eligible_conjugation_verb_ids(
        db,
        language=language,
        selected_tenses=["Présent", "Futur"],
    )

    assert present_ids == [seeded_training_context["verb"].id]
    assert combined_ids == []


def test_custom_conjugation_level_requires_valid_tenses():
    language = Language(
        code="EN",
        name="English",
        pronoun_set=["I", "you", "he", "we", "you (pl.)", "they"],
        tense_definitions={"Present": {"mood": "Indicative"}},
        difficulty_tiers={"easy": ["Present"], "medium": [], "hard": []},
    )

    assert conjugation_tenses_for_level(language, "custom", ["Present", "Present"]) == ["Present"]
    with pytest.raises(ValueError, match="Choose at least one tense"):
        conjugation_tenses_for_level(language, "custom", [])
    with pytest.raises(ValueError, match="Unsupported tense"):
        conjugation_tenses_for_level(language, "custom", ["Future"])


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
