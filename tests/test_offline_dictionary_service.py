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
    Tag,
    User,
    UserAddedWord,
    UserPreference,
    UserProfile,
    UserProgress,
    UserWordLookup,
    Verb,
    VerbTag,
    VerbTranslation,
    Word,
    WordLexicalEntry,
    WordNativeTranslation,
    WordSense,
    WordSenseTranslation,
    WordTag,
    WordTranslation,
)
from app.core.security import AuthContext
from app.routers.words import (
    add_word,
    add_word_offline,
    delete_user_word,
    list_user_words,
    priority_queue,
    select_word_sense,
    word_history,
)
from app.schemas.spa import (
    AddWordOfflinePayload,
    AddWordPayload,
    DeleteUserWordPayload,
    SelectWordSensePayload,
)
from app.services.offline_dictionary_service import find_ranked_sense
from app.services.word_ai_service import (
    WORD_AI_SOURCE,
    DefinitionPresentation,
    LexicalContent,
    NativeContent,
    SenseCandidate,
    TranslatedWord,
    WordAIError,
    _user_message,
    present_definitions,
    translate_selected_sense,
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
async def test_definition_presentation_localizes_without_mutating_canonical_data(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    word = Word(text="bank", language_id=en.id)
    sqlite_session.add(word)
    await sqlite_session.flush()
    result = TranslatedWord(
        status="exact",
        word=word,
        lexical=LexicalContent(
            id=None,
            word_id=word.id,
            definition="land beside a river",
            synonyms=[],
            examples=[],
        ),
        natives=[],
        selected_sense_id=12,
        sense_candidates=[
            SenseCandidate(
                id=12,
                sense_key="river",
                definition="land beside a river",
                part_of_speech="noun",
            ),
            SenseCandidate(
                id=13,
                sense_key="financial",
                definition="an institution that holds money",
                part_of_speech="noun",
            ),
        ],
    )
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    captured = {}

    async def fake_json(_client, system, user, **kwargs):
        captured["system"] = system
        captured["user"] = json.loads(user)
        captured["extra_data"] = kwargs["extra_data"]
        return {
            "definitions": {
                "primary": "Terrain situé au bord d’une rivière.",
                "sense:12": "Terrain situé au bord d’une rivière.",
                "sense:13": "Institution qui conserve de l’argent.",
            }
        }

    monkeypatch.setattr(
        "app.services.word_ai_service._call_openai_json", fake_json
    )
    presentation = await present_definitions(
        sqlite_session,
        result=result,
        learning_lang=en,
        definition_language=fr,
        user_id=7,
    )

    assert presentation.language_code == "FR"
    assert presentation.text == "Terrain situé au bord d’une rivière."
    assert presentation.candidate_definitions[13].startswith("Institution")
    assert result.lexical.definition == "land beside a river"
    assert captured["user"]["definitions"]["primary"] == "land beside a river"
    assert "French" in captured["system"]
    assert captured["extra_data"]["definition_language_code"] == "FR"


@pytest.mark.asyncio
async def test_source_definition_presentation_needs_no_ai(
    sqlite_session, monkeypatch
):
    en, _ = await _languages(sqlite_session)
    word = Word(text="bank", language_id=en.id)
    sqlite_session.add(word)
    await sqlite_session.flush()
    result = TranslatedWord(
        status="exact",
        word=word,
        lexical=LexicalContent(
            id=None,
            word_id=word.id,
            definition="land beside a river",
            synonyms=[],
            examples=[],
        ),
        natives=[],
    )
    monkeypatch.setattr(settings, "openai_api_key", None)

    presentation = await present_definitions(
        sqlite_session,
        result=result,
        learning_lang=en,
        definition_language=en,
    )

    assert presentation.text == "land beside a river"
    assert presentation.language_code == "EN"


@pytest.mark.asyncio
async def test_target_definition_requires_ai_configuration(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    word = Word(text="bank", language_id=en.id)
    sqlite_session.add(word)
    await sqlite_session.flush()
    result = TranslatedWord(
        status="exact",
        word=word,
        lexical=LexicalContent(
            id=None,
            word_id=word.id,
            definition="land beside a river",
            synonyms=[],
            examples=[],
        ),
        natives=[],
    )
    monkeypatch.setattr(settings, "openai_api_key", None)

    with pytest.raises(WordAIError, match="translation language"):
        await present_definitions(
            sqlite_session,
            result=result,
            learning_lang=en,
            definition_language=fr,
        )


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


@pytest.mark.asyncio
async def test_trusted_monolingual_definition_needs_no_translation_or_api_key(
    sqlite_session, monkeypatch
):
    en, _ = await _languages(sqlite_session)
    word = Word(text="bank", language_id=en.id)
    sqlite_session.add(word)
    await sqlite_session.flush()
    sense = WordSense(
        word_id=word.id,
        sense_key="test:river",
        definition="land beside a river",
        synonyms=[],
        examples=["They sat on the bank."],
        source="test_dictionary",
        is_trusted=True,
        is_primary=True,
    )
    sqlite_session.add(sense)
    await sqlite_session.flush()
    monkeypatch.setattr(settings, "openai_api_key", None)

    result = await translate_word(
        sqlite_session,
        input_text="bank",
        learning_lang=en,
        mother_tongue=en,
        context="They sat beside the river.",
    )

    assert result.lexical is not None
    assert result.lexical.definition == "land beside a river"
    assert result.natives == []
    assert result.selected_sense_id == sense.id
    assert result.reportable is False
    assert (
        await sqlite_session.scalar(
            select(func.count(WordSenseTranslation.id))
        )
    ) == 0
    assert (
        await sqlite_session.scalar(
            select(func.count(WordNativeTranslation.id))
        )
    ) == 0


@pytest.mark.asyncio
async def test_monolingual_dictionary_sense_can_be_selected_without_translation(
    sqlite_session,
):
    en, _ = await _languages(sqlite_session)
    word = Word(text="bank", language_id=en.id)
    sqlite_session.add(word)
    await sqlite_session.flush()
    financial = WordSense(
        word_id=word.id,
        sense_key="test:financial",
        definition="an institution that holds money",
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
    sqlite_session.add_all([financial, river])
    await sqlite_session.flush()

    result = await translate_selected_sense(
        sqlite_session,
        word=word,
        sense_id=river.id,
        learning_lang=en,
        mother_tongue=en,
    )

    assert result.selected_sense_id == river.id
    assert result.lexical is not None
    assert result.lexical.definition == "land beside a river"
    assert result.natives == []


@pytest.mark.asyncio
async def test_plain_ai_monolingual_lookup_never_creates_identity_translations(
    sqlite_session, monkeypatch
):
    en, _ = await _languages(sqlite_session)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    async def fake_json(*args, **kwargs):
        return {
            "status": "exact",
            "canonical_text": "ephemeral",
            "part_of_speech": "adjective",
            "cefr_level": "C1",
            "definition": "lasting for only a very short time",
            "synonyms": [],
            "examples": ["Fame can be ephemeral."],
            "native_translations": [],
            "suggested_tags": [],
            "question_answer": "",
        }

    monkeypatch.setattr(
        "app.services.word_ai_service._call_openai_json", fake_json
    )
    result = await translate_word(
        sqlite_session,
        input_text="ephemeral",
        learning_lang=en,
        mother_tongue=en,
    )

    assert result.natives == []
    assert result.lexical is not None
    assert result.lexical.definition.startswith("lasting")
    assert (
        await sqlite_session.scalar(
            select(func.count(WordNativeTranslation.id))
        )
    ) == 0
    assert (
        await sqlite_session.scalar(select(func.count(WordTranslation.id)))
    ) == 0
    assert (
        await sqlite_session.scalar(
            select(func.count(WordSenseTranslation.id))
        )
    ) == 0


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
            "part_of_speech": "noun",
            "cefr_level": "B1",
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
    assert await sqlite_session.scalar(select(func.count(WordTranslation.id))) == 0
    assert await sqlite_session.scalar(select(func.count(Verb.id))) == 0
    assert word.cefr_level is None
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
async def test_plain_ai_verb_lookup_populates_level_tags_and_trainer_inventories(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    async def fake_json(*args, **kwargs):
        return {
            "status": "exact",
            "canonical_text": "run",
            "part_of_speech": "verb",
            "cefr_level": "A1",
            "definition": "to move quickly on foot",
            "synonyms": [],
            "examples": ["I run every morning."],
            "native_translations": [{"translation": "courir", "note": None}],
            "suggested_tags": ["verb_action", "verb_motion", "b2"],
            "question_answer": "",
        }

    monkeypatch.setattr(
        "app.services.word_ai_service._call_openai_json", fake_json
    )
    result = await translate_word(
        sqlite_session,
        input_text="ran",
        learning_lang=en,
        mother_tongue=fr,
    )

    word = (
        await sqlite_session.execute(select(Word).where(Word.text == "run"))
    ).scalar_one()
    verb = (
        await sqlite_session.execute(select(Verb).where(Verb.infinitive == "run"))
    ).scalar_one()
    word_translation = (
        await sqlite_session.execute(
            select(WordTranslation).where(WordTranslation.word_id == word.id)
        )
    ).scalar_one()
    verb_translation = (
        await sqlite_session.execute(
            select(VerbTranslation).where(VerbTranslation.verb_id == verb.id)
        )
    ).scalar_one()
    word_tags = {
        slug
        for (slug,) in (
            await sqlite_session.execute(
                select(Tag.slug)
                .join(WordTag, WordTag.tag_id == Tag.id)
                .where(WordTag.word_id == word.id)
            )
        ).all()
    }
    verb_tags = {
        slug
        for (slug,) in (
            await sqlite_session.execute(
                select(Tag.slug)
                .join(VerbTag, VerbTag.tag_id == Tag.id)
                .where(VerbTag.verb_id == verb.id)
            )
        ).all()
    }

    assert result.part_of_speech == "verb"
    assert result.cefr_level == "A1"
    assert word.cefr_level == "A1"
    assert verb.cefr_level == "A1"
    assert word_translation.translation == "courir"
    assert word_translation.verified is False
    assert word_translation.source == WORD_AI_SOURCE
    assert verb_translation.translation == "courir"
    assert verb_translation.verified is False
    assert verb_translation.source == WORD_AI_SOURCE
    assert {"verb", "verb_action", "verb_motion", "a1"} <= word_tags
    assert "b2" not in word_tags
    assert {"verb", "verb_action", "verb_motion", "a1"} <= verb_tags


@pytest.mark.asyncio
async def test_plain_ai_lookup_moves_existing_inflected_word_to_canonical_headword(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    inflected = Word(text="ran", language_id=en.id)
    sqlite_session.add(inflected)
    await sqlite_session.flush()

    async def fake_json(*args, **kwargs):
        return {
            "status": "corrected",
            "canonical_text": "run",
            "original_input": "ran",
            "part_of_speech": "verb",
            "cefr_level": "A1",
            "definition": "to move quickly on foot",
            "synonyms": [],
            "examples": ["I run every morning."],
            "native_translations": [{"translation": "courir", "note": None}],
            "suggested_tags": ["verb", "verb_action"],
            "question_answer": "",
        }

    monkeypatch.setattr(
        "app.services.word_ai_service._call_openai_json", fake_json
    )
    result = await translate_word(
        sqlite_session,
        input_text="ran",
        learning_lang=en,
        mother_tongue=fr,
    )

    canonical = (
        await sqlite_session.execute(select(Word).where(Word.text == "run"))
    ).scalar_one()
    lexical = (
        await sqlite_session.execute(select(WordLexicalEntry))
    ).scalar_one()
    sense = (await sqlite_session.execute(select(WordSense))).scalar_one()
    verbs = (await sqlite_session.execute(select(Verb))).scalars().all()

    assert result.word is canonical
    assert lexical.word_id == canonical.id
    assert sense.word_id == canonical.id
    assert inflected.id != canonical.id
    assert (
        await sqlite_session.scalar(
            select(func.count(WordLexicalEntry.id)).where(
                WordLexicalEntry.word_id == inflected.id
            )
        )
    ) == 0
    assert [verb.infinitive for verb in verbs] == ["run"]


@pytest.mark.asyncio
async def test_explicit_nonverb_pos_overrides_conflicting_ai_verb_tags(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    async def fake_json(*args, **kwargs):
        return {
            "status": "exact",
            "canonical_text": "bank",
            "part_of_speech": "noun",
            "cefr_level": "B1",
            "definition": "a financial institution",
            "synonyms": [],
            "examples": ["The bank opens at nine."],
            "native_translations": [{"translation": "banque", "note": None}],
            "suggested_tags": ["verb", "verb_action", "food"],
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

    word = (
        await sqlite_session.execute(select(Word).where(Word.text == "bank"))
    ).scalar_one()
    word_tags = {
        slug
        for (slug,) in (
            await sqlite_session.execute(
                select(Tag.slug)
                .join(WordTag, WordTag.tag_id == Tag.id)
                .where(WordTag.word_id == word.id)
            )
        ).all()
    }

    assert result.part_of_speech == "noun"
    assert result.suggested_tags == ["food", "b1"]
    assert word_tags == {"food", "b1"}
    assert await sqlite_session.scalar(select(func.count(Verb.id))) == 0


@pytest.mark.asyncio
async def test_plain_ai_lookup_preserves_existing_curated_levels_and_translation(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    word = Word(text="run", language_id=en.id, cefr_level="A1")
    verb = Verb(infinitive="run", language_id=en.id, cefr_level="A2")
    sqlite_session.add_all([word, verb])
    await sqlite_session.flush()
    curated = VerbTranslation(
        verb_id=verb.id,
        target_language_id=fr.id,
        translation="courir",
        synonyms=[],
        verified=True,
        source="curated_test",
    )
    sqlite_session.add(curated)
    await sqlite_session.flush()

    async def fake_json(*args, **kwargs):
        return {
            "status": "exact",
            "canonical_text": "run",
            "part_of_speech": "verb",
            "cefr_level": "B2",
            "definition": "to move quickly on foot",
            "synonyms": [],
            "examples": [],
            "native_translations": [{"translation": "courir", "note": None}],
            "suggested_tags": ["verb_action"],
            "question_answer": "",
        }

    monkeypatch.setattr(
        "app.services.word_ai_service._call_openai_json", fake_json
    )
    result = await translate_word(
        sqlite_session,
        input_text="run",
        learning_lang=en,
        mother_tongue=fr,
    )

    assert word.cefr_level == "A1"
    assert verb.cefr_level == "A2"
    translations = (
        await sqlite_session.execute(
            select(VerbTranslation).where(VerbTranslation.verb_id == verb.id)
        )
    ).scalars().all()
    assert translations == [curated]
    assert curated.verified is True
    assert curated.source == "curated_test"
    assert result.cefr_level == "A1"
    word_difficulty_tags = {
        slug
        for (slug,) in (
            await sqlite_session.execute(
                select(Tag.slug)
                .join(WordTag, WordTag.tag_id == Tag.id)
                .where(
                    WordTag.word_id == word.id,
                    Tag.kind == "difficulty",
                )
            )
        ).all()
    }
    verb_difficulty_tags = {
        slug
        for (slug,) in (
            await sqlite_session.execute(
                select(Tag.slug)
                .join(VerbTag, VerbTag.tag_id == Tag.id)
                .where(
                    VerbTag.verb_id == verb.id,
                    Tag.kind == "difficulty",
                )
            )
        ).all()
    }
    assert word_difficulty_tags == {"a1"}
    assert verb_difficulty_tags == {"a2"}


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

    async def fake_present(*args, **kwargs):
        assert kwargs["definition_language"].id == fr.id
        return DefinitionPresentation(
            text="Terrain situé au bord d’une rivière.",
            language_code="FR",
            candidate_definitions={},
        )

    monkeypatch.setattr("app.routers.words.translate_word", fake_translate)
    monkeypatch.setattr("app.routers.words.present_definitions", fake_present)
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
async def test_add_word_same_language_is_saved_definition_not_practice(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    word = Word(text="bank", language_id=en.id)
    user = User(username="monolingual-lookup-owner", password_hash="x")
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
        force_unlock_added_words=True,
    )
    sqlite_session.add_all([profile, preference])
    await sqlite_session.flush()

    async def fake_translate(*args, **kwargs):
        assert kwargs["learning_lang"].id == en.id
        assert kwargs["mother_tongue"].id == en.id
        assert kwargs["context"] == "They sat beside the river."
        return TranslatedWord(
            status="exact",
            word=word,
            lexical=LexicalContent(
                id=None,
                word_id=word.id,
                definition="land beside a river",
                synonyms=[],
                examples=["They sat on the bank."],
            ),
            natives=[],
            ranking_method="single_sense",
            reportable=False,
        )

    monkeypatch.setattr("app.routers.words.translate_word", fake_translate)
    monkeypatch.setattr("app.routers.words.validate_csrf", lambda *args: None)
    auth = AuthContext(user=user, profile=profile)
    response = await add_word(
        request=object(),
        payload=AddWordPayload(
            csrf_token="x",
            input_text="bank",
            context="They sat beside the river.",
            context_source="photo",
            learning_lang_code="EN",
            mother_lang_code="EN",
        ),
        auth=auth,
        db=sqlite_session,
    )

    assert response["lookup_mode"] == "definition"
    assert response["practice_eligible"] is False
    assert response["definition_language_code"] == "EN"
    assert response["display_definition"]["text"] == "land beside a river"
    assert response["natives"] == []
    assert response["priority_queue_id"] is None
    assert response["force_unlocked"] is False
    added = (
        await sqlite_session.execute(
            select(UserAddedWord).where(UserAddedWord.user_id == user.id)
        )
    ).scalar_one()
    lookup = (
        await sqlite_session.execute(
            select(UserWordLookup).where(UserWordLookup.user_id == user.id)
        )
    ).scalar_one()
    assert added.language_pair == "en_en"
    assert lookup.source_language_id == lookup.target_language_id == en.id
    assert lookup.context_source == "photo"
    assert (
        await sqlite_session.scalar(select(func.count(UserProgress.id)))
    ) == 0
    assert (
        await sqlite_session.scalar(
            select(func.count(WordNativeTranslation.id))
        )
    ) == 0
    assert (
        await sqlite_session.scalar(select(func.count(WordTranslation.id)))
    ) == 0

    queue = await priority_queue(auth=auth, db=sqlite_session)
    assert queue["entries"] == []
    history = await word_history(limit=20, auth=auth, db=sqlite_session)
    assert history["entries"][0]["lookup_mode"] == "definition"
    assert history["entries"][0]["practice_eligible"] is False
    managed = await list_user_words(
        language_pair="en_en", auth=auth, db=sqlite_session
    )
    assert managed["entries"][0]["lookup_mode"] == "definition"
    assert managed["entries"][0]["definition"] == "land beside a river"

    await delete_user_word(
        word_id=word.id,
        request=object(),
        payload=DeleteUserWordPayload(
            csrf_token="x", language_pair="en_en"
        ),
        auth=auth,
        db=sqlite_session,
    )
    assert (
        await sqlite_session.scalar(select(func.count(UserAddedWord.id)))
    ) == 0
    assert (
        await sqlite_session.scalar(select(func.count(UserWordLookup.id)))
    ) == 0


@pytest.mark.asyncio
async def test_add_endpoint_snapshots_target_language_definition(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    word = Word(text="bank", language_id=en.id)
    user = User(username="localized-lookup-owner", password_hash="x")
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
            reportable=False,
        )

    captured = {}

    async def fake_present(*args, **kwargs):
        captured["definition_language"] = kwargs["definition_language"]
        return DefinitionPresentation(
            text="Terrain situé au bord d’une rivière.",
            language_code="FR",
            candidate_definitions={},
        )

    monkeypatch.setattr("app.routers.words.translate_word", fake_translate)
    monkeypatch.setattr("app.routers.words.present_definitions", fake_present)
    monkeypatch.setattr("app.routers.words.validate_csrf", lambda *args: None)
    response = await add_word(
        request=object(),
        payload=AddWordPayload(
            csrf_token="x",
            input_text="bank",
            definition_language="target",
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
    assert captured["definition_language"].id == fr.id
    assert response["lexical"]["definition"] == "land beside a river"
    assert response["definition_language_code"] == "FR"
    assert response["display_definition"] == {
        "text": "Terrain situé au bord d’une rivière.",
        "language_code": "FR",
    }
    assert lookup.result_data["lexical"]["definition"] == "land beside a river"
    assert lookup.result_data["display_definition"] == response["display_definition"]

    history = await word_history(
        limit=20,
        auth=AuthContext(user=user, profile=profile),
        db=sqlite_session,
    )
    assert history["entries"][0]["definition_language_code"] == "FR"
    assert (
        history["entries"][0]["display_definition"]
        == response["display_definition"]
    )


@pytest.mark.asyncio
async def test_target_display_definition_does_not_poison_global_cache(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    user = User(username="cache-isolation-owner", password_hash="x")
    sqlite_session.add(user)
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
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr("app.routers.words.validate_csrf", lambda *args: None)

    async def fake_json(*args, **kwargs):
        if kwargs.get("feature") == "word_definition_language":
            request_data = json.loads(args[2])
            return {
                "definitions": {
                    key: "Une institution qui conserve et prête de l’argent."
                    for key in request_data["definitions"]
                }
            }
        return {
            "status": "exact",
            "canonical_text": "bank",
            "part_of_speech": "noun",
            "cefr_level": "A2",
            "definition": "an institution that holds and lends money",
            "synonyms": [],
            "examples": ["The bank approved the loan."],
            "native_translations": [{"translation": "banque", "note": None}],
            "suggested_tags": [],
            "question_answer": "",
        }

    monkeypatch.setattr(
        "app.services.word_ai_service._call_openai_json", fake_json
    )
    response = await add_word(
        request=object(),
        payload=AddWordPayload(
            csrf_token="x",
            input_text="bank",
            definition_language="target",
            learning_lang_code="EN",
            mother_lang_code="FR",
        ),
        auth=AuthContext(user=user, profile=profile),
        db=sqlite_session,
    )

    lexical = (
        await sqlite_session.execute(select(WordLexicalEntry))
    ).scalar_one()
    sense = (await sqlite_session.execute(select(WordSense))).scalar_one()
    lookup = (
        await sqlite_session.execute(select(UserWordLookup))
    ).scalar_one()
    assert lexical.definition == "an institution that holds and lends money"
    assert sense.definition == lexical.definition
    assert response["display_definition"]["text"].startswith("Une institution")
    assert lookup.result_data["display_definition"] == response["display_definition"]
    assert lookup.result_data["lexical"]["definition"] == lexical.definition


@pytest.mark.asyncio
async def test_offline_add_does_not_cache_translation_as_definition(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    user = User(username="manual-word-owner", password_hash="x")
    sqlite_session.add(user)
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
    monkeypatch.setattr("app.routers.words.validate_csrf", lambda *args: None)

    await add_word_offline(
        request=object(),
        payload=AddWordOfflinePayload(
            csrf_token="x",
            learning_text="bank",
            native_text="banque",
            learning_lang_code="EN",
            mother_lang_code="FR",
        ),
        auth=AuthContext(user=user, profile=profile),
        db=sqlite_session,
    )

    assert (
        await sqlite_session.scalar(select(func.count(WordLexicalEntry.id)))
        == 0
    )
    native = (
        await sqlite_session.execute(select(WordNativeTranslation))
    ).scalar_one()
    assert native.translation == "banque"
    history = await word_history(
        limit=20,
        auth=AuthContext(user=user, profile=profile),
        db=sqlite_session,
    )
    assert history["entries"][0]["display_definition"]["text"] == ""
    assert history["entries"][0]["natives"][0]["translation"] == "banque"


@pytest.mark.asyncio
async def test_history_repairs_legacy_private_pseudo_definition_from_trusted_sense(
    sqlite_session,
):
    en, fr = await _languages(sqlite_session)
    es = Language(
        code="ES",
        name="Spanish",
        pronoun_set=[],
        tense_definitions={},
        difficulty_tiers={},
    )
    user = User(username="legacy-history-owner", password_hash="x")
    word = Word(text="bank", language_id=en.id)
    sqlite_session.add_all([es, user, word])
    await sqlite_session.flush()
    profile = UserProfile(
        user_id=user.id,
        xp=0,
        level=1,
        streak_days=0,
        theme_preference="light",
    )
    lexical = WordLexicalEntry(
        word_id=word.id,
        definition="banque",
        synonyms=[],
        examples=[],
        source="manual",
    )
    sense = WordSense(
        word_id=word.id,
        sense_key="trusted:financial",
        definition="an institution that holds and lends money",
        synonyms=[],
        examples=[],
        source="test_dictionary",
        is_trusted=True,
        is_primary=True,
    )
    sqlite_session.add_all([profile, lexical, sense])
    await sqlite_session.flush()
    native = WordNativeTranslation(
        word_id=word.id,
        native_language_id=fr.id,
        translation="banque",
        source="manual",
    )
    spanish_native = WordNativeTranslation(
        word_id=word.id,
        native_language_id=es.id,
        translation="banco",
        source="test_dictionary",
    )
    sense_native = WordSenseTranslation(
        sense_id=sense.id,
        target_language_id=es.id,
        translation="banco",
        source="test_dictionary",
    )
    added = UserAddedWord(
        user_id=user.id,
        word_id=word.id,
        selected_sense_id=sense.id,
        language_pair="en_es",
    )
    lookup = UserWordLookup(
        user_id=user.id,
        word_id=word.id,
        selected_sense_id=sense.id,
        source_language_id=en.id,
        target_language_id=es.id,
        result_data={
            "lexical": {
                "id": lexical.id,
                "word_id": word.id,
                "definition": "banque",
                "synonyms": [],
                "examples": [],
                "extended_content": None,
            },
            "natives": [
                {
                    "id": None,
                    "word_id": word.id,
                    "native_language_code": "ES",
                    "translation": "banco",
                    "note": None,
                }
            ],
        },
    )
    sqlite_session.add_all(
        [native, spanish_native, sense_native, added, lookup]
    )
    await sqlite_session.flush()

    history = await word_history(
        limit=20,
        auth=AuthContext(user=user, profile=profile),
        db=sqlite_session,
    )

    entry = history["entries"][0]
    assert entry["definition_language_code"] == "EN"
    assert entry["display_definition"] == {
        "text": "an institution that holds and lends money",
        "language_code": "EN",
    }
    assert entry["lexical"]["definition"] == entry["display_definition"]["text"]
    assert lexical.definition == "banque"
    assert sense.definition == "an institution that holds and lends money"


@pytest.mark.asyncio
async def test_legacy_manual_pseudo_definition_is_repaired_on_online_lookup(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    word = Word(text="bank", language_id=en.id)
    sqlite_session.add(word)
    await sqlite_session.flush()
    lexical = WordLexicalEntry(
        word_id=word.id,
        definition="banque",
        synonyms=[],
        examples=[],
        source="manual",
    )
    native = WordNativeTranslation(
        word_id=word.id,
        native_language_id=fr.id,
        translation="banque",
        source="manual",
    )
    sqlite_session.add_all([lexical, native])
    await sqlite_session.flush()
    legacy_sense = WordSense(
        word_id=word.id,
        sense_key=f"legacy:{lexical.id}",
        definition="banque",
        synonyms=[],
        examples=[],
        source="manual",
        is_trusted=False,
        is_primary=True,
    )
    sqlite_session.add(legacy_sense)
    await sqlite_session.flush()
    sqlite_session.add(
        WordSenseTranslation(
            sense_id=legacy_sense.id,
            target_language_id=fr.id,
            translation="banque",
            source="manual",
        )
    )
    await sqlite_session.flush()
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    async def fake_json(*args, **kwargs):
        return {
            "status": "exact",
            "canonical_text": "bank",
            "part_of_speech": "noun",
            "cefr_level": "A2",
            "definition": "an institution that holds and lends money",
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

    assert result.lexical is lexical
    assert lexical.definition == "an institution that holds and lends money"
    assert lexical.source != "manual"
    assert legacy_sense.definition == lexical.definition
    assert legacy_sense.source == lexical.source
    assert (
        await sqlite_session.scalar(select(func.count(WordLexicalEntry.id)))
        == 1
    )
    assert await sqlite_session.scalar(select(func.count(WordSense.id))) == 1


@pytest.mark.asyncio
async def test_distinct_manual_source_definition_is_preserved(
    sqlite_session, monkeypatch
):
    en, fr = await _languages(sqlite_session)
    word = Word(text="bank", language_id=en.id)
    sqlite_session.add(word)
    await sqlite_session.flush()
    lexical = WordLexicalEntry(
        word_id=word.id,
        definition="an institution that holds and lends money",
        synonyms=[],
        examples=[],
        source="manual",
    )
    native = WordNativeTranslation(
        word_id=word.id,
        native_language_id=fr.id,
        translation="banque",
        source="manual",
    )
    sqlite_session.add_all([lexical, native])
    await sqlite_session.flush()
    monkeypatch.setattr(settings, "openai_api_key", None)

    result = await translate_word(
        sqlite_session,
        input_text="bank",
        learning_lang=en,
        mother_tongue=fr,
    )

    assert result.lexical is lexical
    assert lexical.definition == "an institution that holds and lends money"
    assert lexical.source == "manual"


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
        result_data={"definition_language_code": "FR"},
        ranking_method="intfloat/multilingual-e5-small",
    )
    sqlite_session.add_all([added, lookup])
    await sqlite_session.flush()

    async def fake_present(*args, **kwargs):
        localized = {
            candidate.id: (
                "Terrain situé au bord d’une rivière."
                if candidate.id == river.id
                else "Institution qui conserve de l’argent."
            )
            for candidate in (kwargs["result"].sense_candidates or [])
        }
        return DefinitionPresentation(
            text="Terrain situé au bord d’une rivière.",
            language_code=kwargs["definition_language"].code,
            candidate_definitions=localized,
        )

    monkeypatch.setattr("app.routers.words.present_definitions", fake_present)
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
    assert response["definition_language_code"] == "FR"
    assert response["display_definition"]["text"].startswith("Terrain")
    assert lookup.selected_sense_id == river.id
    assert lookup.result_data["definition_language_code"] == "FR"
    assert lookup.ranking_method == "user_selected"
    assert added.selected_sense_id == river.id
