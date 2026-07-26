from __future__ import annotations

import json

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.models import (
    Language,
    User,
    UserAddedWord,
    UserPreference,
    UserProfile,
    UserWordLookup,
    Word,
    WordLexicalEntry,
    WordNativeTranslation,
    WordSense,
    WordSenseTranslation,
)
from app.core.security import AuthContext
from app.routers.words import add_word, select_word_sense
from app.schemas.spa import AddWordPayload, SelectWordSensePayload
from app.services.offline_dictionary_service import find_ranked_sense
from app.services.word_ai_service import (
    LexicalContent,
    NativeContent,
    TranslatedWord,
    _user_message,
    translate_word,
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


async def _languages(db) -> tuple[Language, Language]:
    en = Language(
        code="EN",
        name="English",
        pronoun_set=[],
        tense_definitions={},
        difficulty_tiers={},
    )
    fr = Language(
        code="FR",
        name="French",
        pronoun_set=[],
        tense_definitions={},
        difficulty_tiers={},
    )
    db.add_all([en, fr])
    await db.flush()
    return en, fr


@pytest.mark.asyncio
async def test_context_ranks_existing_dictionary_senses_without_question(
    sqlite_session,
):
    en, fr = await _languages(sqlite_session)
    word = Word(text="bank", language_id=en.id)
    sqlite_session.add(word)
    await sqlite_session.flush()
    financial = WordSense(
        word_id=word.id,
        sense_key="test:financial",
        definition="an institution for money, deposits, and loans",
        synonyms=[],
        examples=[],
        source="test_dictionary",
        is_trusted=True,
        is_primary=True,
    )
    river = WordSense(
        word_id=word.id,
        sense_key="test:river",
        definition="sloping land beside a river and water",
        synonyms=[],
        examples=[],
        source="test_dictionary",
        is_trusted=True,
    )
    sqlite_session.add_all([financial, river])
    await sqlite_session.flush()
    sqlite_session.add_all(
        [
            WordSenseTranslation(
                sense_id=financial.id,
                target_language_id=fr.id,
                translation="banque",
                source="test_dictionary",
            ),
            WordSenseTranslation(
                sense_id=river.id,
                target_language_id=fr.id,
                translation="rive",
                source="test_dictionary",
            ),
        ]
    )
    await sqlite_session.flush()

    ranked = await find_ranked_sense(
        sqlite_session,
        word=word,
        target_language_id=fr.id,
        context="The children sat beside the river and watched the water.",
    )

    assert ranked is not None
    assert ranked.sense.sense_key == "test:river"
    assert ranked.translations[0].translation == "rive"
    assert ranked.method in {"lexical_overlap", "intfloat/multilingual-e5-small"}


@pytest.mark.asyncio
async def test_offline_dictionary_translation_needs_no_api_key(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    word = Word(text="bank", language_id=en.id)
    sqlite_session.add(word)
    await sqlite_session.flush()
    sense = WordSense(
        word_id=word.id,
        sense_key="test:river",
        definition="land beside a river",
        synonyms=[],
        examples=[],
        source="test_dictionary",
        is_trusted=True,
        is_primary=True,
    )
    sqlite_session.add(sense)
    await sqlite_session.flush()
    sqlite_session.add(
        WordSenseTranslation(
            sense_id=sense.id,
            target_language_id=fr.id,
            translation="rive",
            source="test_dictionary",
        )
    )
    await sqlite_session.flush()
    monkeypatch.setattr(settings, "openai_api_key", None)

    result = await translate_word(
        sqlite_session,
        input_text="bank",
        learning_lang=en,
        mother_tongue=fr,
        context="They sat beside the river.",
    )

    assert result.natives is not None
    assert result.natives[0].translation == "rive"
    assert result.selected_sense_id == sense.id
    assert result.reportable is False


def test_context_and_question_are_serialized_as_distinct_fields():
    payload = json.loads(
        _user_message(
            "bank",
            "Why were the children sitting beside the river?",
            "Why is the translation not banque?",
        )
    )
    assert payload["context"] == "Why were the children sitting beside the river?"
    assert payload["user_question"] == "Why is the translation not banque?"
    assert payload["context_is_quoted_source_material"] is True


@pytest.mark.asyncio
async def test_contextual_ai_result_does_not_write_global_lexical_cache(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    word = Word(text="bank", language_id=en.id)
    sqlite_session.add(word)
    await sqlite_session.flush()
    lexical = WordLexicalEntry(
        word_id=word.id,
        definition="a financial institution",
        synonyms=[],
        examples=[],
        source="openai_gpt4o",
    )
    native = WordNativeTranslation(
        word_id=word.id,
        native_language_id=fr.id,
        translation="banque",
        source="openai_gpt4o",
    )
    untrusted_sense = WordSense(
        word_id=word.id,
        sense_key="legacy:financial",
        definition="a financial institution",
        synonyms=[],
        examples=[],
        source="openai_gpt4o",
        is_trusted=False,
        is_primary=True,
    )
    sqlite_session.add_all([lexical, native, untrusted_sense])
    await sqlite_session.flush()
    sqlite_session.add(
        WordSenseTranslation(
            sense_id=untrusted_sense.id,
            target_language_id=fr.id,
            translation="banque",
            source="openai_gpt4o",
        )
    )
    await sqlite_session.flush()

    async def fake_json(*args, **kwargs):
        return {
            "status": "exact",
            "canonical_text": "bank",
            "definition": "land beside a river",
            "synonyms": [],
            "examples": ["They sat on the bank."],
            "native_translations": [{"translation": "rive", "note": None}],
            "suggested_tags": [],
            "question_answer": "Here it refers to the side of a river.",
        }

    monkeypatch.setattr(
        "app.services.word_ai_service._call_openai_json", fake_json
    )
    result = await translate_word(
        sqlite_session,
        input_text="bank",
        learning_lang=en,
        mother_tongue=fr,
        context="They sat beside the river.",
        question="What does it mean here?",
        user_id=1,
    )

    assert result.question_answer == "Here it refers to the side of a river."
    assert result.lexical is not None
    assert result.lexical.definition == "land beside a river"
    assert result.reportable is False
    assert result.ranking_method == "private_ai"
    assert (
        await sqlite_session.scalar(select(func.count(WordLexicalEntry.id)))
    ) == 1
    assert (
        await sqlite_session.scalar(select(func.count(WordNativeTranslation.id)))
    ) == 1
    assert await sqlite_session.scalar(select(func.count(WordSense.id))) == 1
    assert await sqlite_session.scalar(select(func.count(Word.id))) == 1
    assert lexical.definition == "a financial institution"


@pytest.mark.asyncio
async def test_plain_ai_lookup_populates_global_sense_cache(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    async def fake_json(*args, **kwargs):
        return {
            "status": "exact",
            "canonical_text": "bank",
            "definition": "a financial institution",
            "synonyms": [],
            "examples": [],
            "native_translations": [{"translation": "banque", "note": None}],
            "suggested_tags": [],
            "question_answer": "",
        }

    monkeypatch.setattr(
        "app.services.word_ai_service._call_openai_json", fake_json
    )
    result = await translate_word(
        sqlite_session,
        input_text="bank",
        learning_lang=en,
        mother_tongue=fr,
    )

    assert result.reportable is True
    assert result.selected_sense_id is not None
    assert (
        await sqlite_session.scalar(select(func.count(WordLexicalEntry.id)))
    ) == 1
    assert (
        await sqlite_session.scalar(select(func.count(WordNativeTranslation.id)))
    ) == 1
    assert await sqlite_session.scalar(select(func.count(WordSense.id))) == 1
    assert (
        await sqlite_session.scalar(select(func.count(WordSenseTranslation.id)))
    ) == 1


@pytest.mark.asyncio
async def test_private_lookup_rows_are_scoped_by_user(sqlite_session):
    en, fr = await _languages(sqlite_session)
    word = Word(text="bank", language_id=en.id)
    first = User(username="first", password_hash="x")
    second = User(username="second", password_hash="x")
    sqlite_session.add_all([word, first, second])
    await sqlite_session.flush()
    sqlite_session.add_all(
        [
            UserWordLookup(
                user_id=first.id,
                word_id=word.id,
                source_language_id=en.id,
                target_language_id=fr.id,
                context="private first context",
                question="private first question",
                answer="private first answer",
                result_data={},
            ),
            UserWordLookup(
                user_id=second.id,
                word_id=word.id,
                source_language_id=en.id,
                target_language_id=fr.id,
                context="private second context",
                question="private second question",
                answer="private second answer",
                result_data={},
            ),
        ]
    )
    await sqlite_session.flush()

    rows = (
        await sqlite_session.execute(
            select(UserWordLookup).where(UserWordLookup.user_id == first.id)
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].question == "private first question"
    assert "second" not in (rows[0].context or "")


@pytest.mark.asyncio
async def test_add_endpoint_stores_context_and_question_only_in_private_lookup(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    word = Word(text="bank", language_id=en.id)
    user = User(username="lookup-owner", password_hash="x")
    sqlite_session.add_all([word, user])
    await sqlite_session.flush()
    profile = UserProfile(
        user_id=user.id,
        xp=0,
        level=1,
        streak_days=0,
        theme_preference="light",
    )
    preference = UserPreference(
        user_id=user.id,
        learning_language_id=en.id,
        mother_tongue_language_id=fr.id,
    )
    sqlite_session.add_all([profile, preference])
    await sqlite_session.flush()

    async def fake_translate(*args, **kwargs):
        return TranslatedWord(
            status="exact",
            word=word,
            lexical=LexicalContent(
                id=None,
                word_id=word.id,
                definition="land beside a river",
                synonyms=[],
                examples=[],
            ),
            natives=[
                NativeContent(
                    id=None,
                    word_id=word.id,
                    native_language_id=fr.id,
                    translation="rive",
                    note=None,
                )
            ],
            question_answer="It is the land beside the river.",
            ranking_method="private_ai",
            reportable=False,
        )

    monkeypatch.setattr("app.routers.words.translate_word", fake_translate)
    monkeypatch.setattr("app.routers.words.validate_csrf", lambda *args: None)
    response = await add_word(
        request=object(),
        payload=AddWordPayload(
            csrf_token="x",
            input_text="bank",
            context="They sat beside the river.",
            question="What does it mean here?",
            context_source="manual",
            learning_lang_code="EN",
            mother_lang_code="FR",
        ),
        auth=AuthContext(user=user, profile=profile),
        db=sqlite_session,
    )

    lookup = (
        await sqlite_session.execute(
            select(UserWordLookup).where(UserWordLookup.user_id == user.id)
        )
    ).scalar_one()
    assert lookup.context == "They sat beside the river."
    assert lookup.question == "What does it mean here?"
    assert lookup.answer == "It is the land beside the river."
    assert lookup.result_data["natives"][0]["translation"] == "rive"
    assert response["question_answer"] == lookup.answer
    assert response["lookup_id"] == lookup.id
    assert response["reportable"] is False
    assert await sqlite_session.scalar(select(func.count(WordSense.id))) == 0


@pytest.mark.asyncio
async def test_user_can_replace_ranked_sense_on_private_lookup(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    user = User(username="sense-owner", password_hash="x")
    word = Word(text="bank", language_id=en.id)
    sqlite_session.add_all([user, word])
    await sqlite_session.flush()
    profile = UserProfile(
        user_id=user.id,
        xp=0,
        level=1,
        streak_days=0,
        theme_preference="light",
    )
    financial = WordSense(
        word_id=word.id,
        sense_key="test:financial",
        definition="a financial institution",
        synonyms=[],
        examples=[],
        source="test_dictionary",
        is_trusted=True,
        is_primary=True,
    )
    river = WordSense(
        word_id=word.id,
        sense_key="test:river",
        definition="land beside a river",
        synonyms=[],
        examples=[],
        source="test_dictionary",
        is_trusted=True,
    )
    sqlite_session.add_all([profile, financial, river])
    await sqlite_session.flush()
    sqlite_session.add_all(
        [
            WordSenseTranslation(
                sense_id=financial.id,
                target_language_id=fr.id,
                translation="banque",
                source="test_dictionary",
            ),
            WordSenseTranslation(
                sense_id=river.id,
                target_language_id=fr.id,
                translation="rive",
                source="test_dictionary",
            ),
        ]
    )
    added = UserAddedWord(
        user_id=user.id,
        word_id=word.id,
        selected_sense_id=financial.id,
        language_pair="en_fr",
    )
    lookup = UserWordLookup(
        user_id=user.id,
        word_id=word.id,
        selected_sense_id=financial.id,
        source_language_id=en.id,
        target_language_id=fr.id,
        context="They sat beside the river.",
        result_data={},
        ranking_method="intfloat/multilingual-e5-small",
    )
    sqlite_session.add_all([added, lookup])
    await sqlite_session.flush()

    monkeypatch.setattr("app.routers.words.validate_csrf", lambda *args: None)
    response = await select_word_sense(
        request=object(),
        lookup_id=lookup.id,
        payload=SelectWordSensePayload(csrf_token="x", sense_id=river.id),
        auth=AuthContext(user=user, profile=profile),
        db=sqlite_session,
    )

    assert response["selected_sense_id"] == river.id
    assert response["natives"][0]["translation"] == "rive"
    assert lookup.selected_sense_id == river.id
    assert lookup.ranking_method == "user_selected"
    assert added.selected_sense_id == river.id
