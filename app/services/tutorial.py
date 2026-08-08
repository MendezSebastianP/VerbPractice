"""Seeding and lookup for the scripted first-run tutorial.

The tutorial tells the learner exactly what to type, so its words must be the
same every time — the scheduler's weighted picks are useless here. This module
puts the curated set into the inventory (idempotently) and hands back the fixed,
ordered item ids a tutorial session runs on.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.tutorial_content import (
    LANGUAGE_CODES,
    TUTORIAL_DEFINITIONS,
    TUTORIAL_EXAMPLES,
    TUTORIAL_PART_OF_SPEECH,
    TUTORIAL_SOURCE,
    TUTORIAL_WORDS,
    tutorial_pairs,
)
from app.db.models import (
    Language,
    ProgressItemType,
    UserProgress,
    Word,
    WordSense,
    WordSenseTranslation,
    WordTranslation,
)


async def _language_map(db: AsyncSession) -> dict[str, Language]:
    rows = await db.execute(select(Language).where(Language.code.in_(LANGUAGE_CODES)))
    return {language.code: language for language in rows.scalars().all()}


async def ensure_tutorial_words(db: AsyncSession) -> None:
    """Make sure every curated word and translation exists.

    Safe to call on every tutorial start: existing rows are left alone, so this
    never fights with the curated import or a user's own edits.
    """
    languages = await _language_map(db)
    missing = [code for code in LANGUAGE_CODES if code not in languages]
    if missing:
        raise ValueError(f"Tutorial needs these languages seeded first: {missing}")

    # Words, one per (concept, language).
    word_ids: dict[tuple[int, str], Word] = {}
    for index, entry in enumerate(TUTORIAL_WORDS):
        for code in LANGUAGE_CODES:
            language = languages[code]
            text = entry[code]
            existing = await db.execute(
                select(Word).where(Word.text == text, Word.language_id == language.id)
            )
            word = existing.scalar_one_or_none()
            if word is None:
                word = Word(text=text, language_id=language.id, cefr_level="A1")
                db.add(word)
                await db.flush()
            word_ids[(index, code)] = word

    # Translations, both ways for every ordered pair.
    for index, entry in enumerate(TUTORIAL_WORDS):
        for source in LANGUAGE_CODES:
            for target in LANGUAGE_CODES:
                if source == target:
                    continue
                word = word_ids[(index, source)]
                target_language = languages[target]
                translation = entry[target]
                existing = await db.execute(
                    select(WordTranslation).where(
                        WordTranslation.word_id == word.id,
                        WordTranslation.target_language_id == target_language.id,
                        WordTranslation.translation == translation,
                    )
                )
                if existing.scalar_one_or_none() is None:
                    db.add(
                        WordTranslation(
                            word_id=word.id,
                            target_language_id=target_language.id,
                            translation=translation,
                            synonyms=[],
                            verified=True,
                            source=TUTORIAL_SOURCE,
                        )
                    )
    await db.flush()

    # A trusted sense with its translations is what lets the Add Word lookup
    # resolve offline. Without it translate_word() falls through to the model
    # and every first run costs tokens for an answer we already ship.
    for index, entry in enumerate(TUTORIAL_WORDS):
        definitions = TUTORIAL_DEFINITIONS[index]
        for code in LANGUAGE_CODES:
            word = word_ids[(index, code)]
            sense_key = f"{TUTORIAL_SOURCE}:{entry['EN']}"
            found = await db.execute(
                select(WordSense).where(
                    WordSense.word_id == word.id, WordSense.sense_key == sense_key
                )
            )
            sense = found.scalar_one_or_none()
            if sense is None:
                sense = WordSense(
                    word_id=word.id,
                    sense_key=sense_key,
                    part_of_speech=TUTORIAL_PART_OF_SPEECH,
                    definition=definitions[code],
                    synonyms=[],
                    examples=list(TUTORIAL_EXAMPLES[index][code]),
                    source=TUTORIAL_SOURCE,
                    is_trusted=True,
                    is_primary=True,
                )
                db.add(sense)
                await db.flush()

            # Seeded before examples were curated: fill them in so an older
            # database renders the same result panel as a fresh one.
            if not sense.examples:
                sense.examples = list(TUTORIAL_EXAMPLES[index][code])

            # Ranking orders by is_primary then id, and the imported dictionary
            # marks several senses primary — for "house" the lowest id happens
            # to be "one of the twelve divisions of an astrological chart".
            # These five words are the first thing a learner ever looks up, so
            # the everyday sense is made the only primary one.
            others = await db.execute(
                select(WordSense).where(
                    WordSense.word_id == word.id,
                    WordSense.id != sense.id,
                    WordSense.is_primary.is_(True),
                )
            )
            for other in others.scalars().all():
                other.is_primary = False
            sense.is_primary = True
            await db.flush()

            for target in LANGUAGE_CODES:
                if target == code:
                    continue
                target_language = languages[target]
                translation = entry[target]
                exists = await db.execute(
                    select(WordSenseTranslation).where(
                        WordSenseTranslation.sense_id == sense.id,
                        WordSenseTranslation.target_language_id == target_language.id,
                        WordSenseTranslation.translation == translation,
                    )
                )
                if exists.scalar_one_or_none() is None:
                    db.add(
                        WordSenseTranslation(
                            sense_id=sense.id,
                            target_language_id=target_language.id,
                            translation=translation,
                            source=TUTORIAL_SOURCE,
                            priority=0,
                        )
                    )
    await db.flush()


async def tutorial_word_ids(db: AsyncSession, *, direction: str) -> list[int]:
    """Ordered word ids for a tutorial run in this direction."""
    source_code, target_code = direction.upper().split("_")
    pairs = tutorial_pairs(source_code, target_code)
    if not pairs:
        return []

    languages = await _language_map(db)
    source_language = languages.get(source_code)
    if source_language is None:
        return []

    ids: list[int] = []
    for prompt, _answer in pairs:
        row = await db.execute(
            select(Word.id).where(Word.text == prompt, Word.language_id == source_language.id)
        )
        word_id = row.scalar_one_or_none()
        if word_id is None:
            return []
        ids.append(word_id)
    return ids


async def unlock_tutorial_items(
    db: AsyncSession, *, user_id: int, language_pair: str, item_ids: list[int]
) -> None:
    """Give the learner progress rows for the tutorial words.

    A tutorial session bypasses the scheduler, so these rows would not otherwise
    exist — and grading writes to them.
    """
    existing = await db.execute(
        select(UserProgress.item_id).where(
            UserProgress.user_id == user_id,
            UserProgress.item_type == ProgressItemType.WORD,
            UserProgress.language_pair == language_pair,
            UserProgress.item_id.in_(item_ids),
        )
    )
    have = {item_id for (item_id,) in existing.all()}
    for item_id in item_ids:
        if item_id in have:
            continue
        db.add(
            UserProgress(
                user_id=user_id,
                item_type=ProgressItemType.WORD,
                item_id=item_id,
                language_pair=language_pair,
                unlocked=True,
            )
        )
    await db.flush()


async def tutorial_script(db: AsyncSession, *, direction: str) -> dict:
    """Prompt/answer pairs the client script reads, in tutorial order."""
    source_code, target_code = direction.upper().split("_")
    pairs = tutorial_pairs(source_code, target_code)
    return {
        "direction": direction.lower(),
        "items": [{"prompt": prompt, "answer": answer} for prompt, answer in pairs],
    }
