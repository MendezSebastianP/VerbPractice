from __future__ import annotations

import asyncio
import csv
import re
from pathlib import Path

from sqlalchemy import select

from app.core.languages import LANGUAGE_DEFINITIONS
from app.core.security import hash_password
from app.core.tags import TAG_SLUG_SET, tag_seed_rows
from app.db.models import (
    Language,
    Tag,
    User,
    UserProfile,
    Verb,
    VerbConjugation,
    VerbTag,
    VerbTranslation,
    Word,
    WordTag,
    WordTranslation,
)
from app.db.session import AsyncSessionLocal
from app.services.curated_conjugations import (
    discover_batch_conjugation_files,
    import_curated_conjugation_rows,
    import_inventory_rows,
    inventory_path as curated_inventory_path,
    load_conjugation_rows,
    load_inventory_rows,
)

RE_SPLIT = re.compile(r"[;,]")

WORD_SEED_COLUMNS = {
    "ES": ("spanish", "spanish synonyms"),
    "FR": ("french", "french synonyms"),
    "EN": ("english", "english synonyms"),
    "RU": ("russian", "russian synonyms"),
}

FR_TENSE_MAP = {
    "présent": "Présent",
    "futur": "Futur",
    "imparfait": "Imparfait",
    "passé simple": "Passé Simple",
    "conditionnel présent": "Conditionnel présent",
    "subjonctif présent": "Subjonctif présent",
    "subjonctif imparfait": "Subjonctif imparfait",
    "impératif": "Impératif",
    "imperatif": "Impératif",
}

ES_TENSE_MAP = {
    "presente": "Presente",
    "imperfecto": "Pretérito imperfecto",
    "pretérito indefinido": "Pretérito perfecto simple",
    "pretérito perfecto compuesto": "Pretérito perfecto compuesto",
    "futuro": "Futuro",
    "futuro perfecto": "Futuro perfecto",
    "condicional": "Condicional",
    "imperativo": "Imperativo",
    "subjuntivo presente": "Subjuntivo presente",
    "pretérito pluscuamperfecto": "Pretérito pluscuamperfecto",
}


def clean_text(value: str | None) -> str:
    return (value or "").strip()


def split_synonyms(value: str | None) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    return [chunk.strip() for chunk in RE_SPLIT.split(text) if chunk.strip()]


def split_tags(value: str | None) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    slugs: list[str] = []
    seen: set[str] = set()
    for chunk in RE_SPLIT.split(text):
        slug = chunk.strip().lower()
        if not slug or slug in seen or slug not in TAG_SLUG_SET:
            continue
        slugs.append(slug)
        seen.add(slug)
    return slugs


def normalize_tense(language: str, tense: str) -> str:
    base = clean_text(tense)
    key = base.lower()
    if language == "FR":
        return FR_TENSE_MAP.get(key, base)
    if language == "ES":
        return ES_TENSE_MAP.get(key, base)
    return base


def normalize_mood(language: str, mood: str) -> str:
    base = clean_text(mood)
    if language == "FR" and base.lower() == "imperatif":
        return "Impératif"
    return base


async def get_or_create_language(session, code: str, payload: dict[str, object]) -> Language:
    result = await session.execute(select(Language).where(Language.code == code))
    language = result.scalar_one_or_none()
    if language:
        language.name = str(payload["name"])
        language.pronoun_set = list(payload["pronoun_set"])
        language.difficulty_tiers = dict(payload["difficulty_tiers"])
        language.tense_definitions = dict(payload["tense_definitions"])
        return language

    language = Language(
        code=code,
        name=str(payload["name"]),
        pronoun_set=list(payload["pronoun_set"]),
        difficulty_tiers=dict(payload["difficulty_tiers"]),
        tense_definitions=dict(payload["tense_definitions"]),
    )
    session.add(language)
    await session.flush()
    return language


async def get_or_create_word(session, *, text: str, language_id: int) -> Word:
    result = await session.execute(
        select(Word).where(Word.text == text, Word.language_id == language_id)
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    row = Word(text=text, language_id=language_id)
    session.add(row)
    await session.flush()
    return row


async def get_or_create_verb(session, *, infinitive: str, language_id: int) -> Verb:
    result = await session.execute(
        select(Verb).where(Verb.infinitive == infinitive, Verb.language_id == language_id)
    )
    row = result.scalar_one_or_none()
    if row:
        return row
    row = Verb(infinitive=infinitive, language_id=language_id)
    session.add(row)
    await session.flush()
    return row


async def ensure_curated_tags(session) -> dict[str, Tag]:
    result = await session.execute(select(Tag))
    existing = {tag.slug: tag for tag in result.scalars().all()}
    for row in tag_seed_rows():
        slug = str(row["slug"])
        tag = existing.get(slug)
        if tag is None:
            tag = Tag(
                slug=slug,
                display_name=str(row["display_name"]),
                kind=str(row["kind"]),
                applies_to=list(row["applies_to"]),
            )
            session.add(tag)
            existing[slug] = tag
        else:
            tag.display_name = str(row["display_name"])
            tag.kind = str(row["kind"])
            tag.applies_to = list(row["applies_to"])
    await session.flush()
    return existing


async def attach_word_tags(
    session,
    *,
    word_id: int,
    tag_ids: list[int],
    source: str = "system_curated",
) -> None:
    if not tag_ids:
        return
    existing = await session.execute(
        select(WordTag.tag_id).where(
            WordTag.word_id == word_id,
            WordTag.tag_id.in_(tag_ids),
        )
    )
    existing_ids = {row[0] for row in existing.all()}
    for tag_id in tag_ids:
        if tag_id not in existing_ids:
            session.add(WordTag(word_id=word_id, tag_id=tag_id, source=source))


async def attach_verb_tags(
    session,
    *,
    verb_id: int,
    tag_ids: list[int],
    source: str = "system_curated",
) -> None:
    if not tag_ids:
        return
    existing = await session.execute(
        select(VerbTag.tag_id).where(
            VerbTag.verb_id == verb_id,
            VerbTag.tag_id.in_(tag_ids),
        )
    )
    existing_ids = {row[0] for row in existing.all()}
    for tag_id in tag_ids:
        if tag_id not in existing_ids:
            session.add(VerbTag(verb_id=verb_id, tag_id=tag_id, source=source))


async def upsert_word_translation(
    session,
    *,
    word_id: int,
    target_language_id: int,
    translation: str,
    synonyms: list[str],
) -> None:
    result = await session.execute(
        select(WordTranslation).where(
            WordTranslation.word_id == word_id,
            WordTranslation.target_language_id == target_language_id,
            WordTranslation.translation == translation,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        if synonyms:
            row.synonyms = sorted(set([*row.synonyms, *synonyms]))
        return

    session.add(
        WordTranslation(
            word_id=word_id,
            target_language_id=target_language_id,
            translation=translation,
            synonyms=synonyms,
            verified=False,
            source="legacy_csv_auto",
        )
    )


async def upsert_verb_translation(
    session,
    *,
    verb_id: int,
    target_language_id: int,
    translation: str,
    synonyms: list[str],
) -> None:
    result = await session.execute(
        select(VerbTranslation).where(
            VerbTranslation.verb_id == verb_id,
            VerbTranslation.target_language_id == target_language_id,
            VerbTranslation.translation == translation,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        if synonyms:
            row.synonyms = sorted(set([*row.synonyms, *synonyms]))
        return

    session.add(
        VerbTranslation(
            verb_id=verb_id,
            target_language_id=target_language_id,
            translation=translation,
            synonyms=synonyms,
            verified=False,
            source="legacy_csv_auto",
        )
    )


async def ensure_demo_user(session) -> None:
    result = await session.execute(select(User).where(User.username == "demo"))
    user = result.scalar_one_or_none()
    if user:
        return

    user = User(username="demo", password_hash=hash_password("demo12345"), is_admin=True)
    session.add(user)
    await session.flush()
    session.add(UserProfile(user_id=user.id, xp=0, level=1, streak_days=0, theme_preference="light"))


async def run_seed() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    legacy_seed_root = repo_root / "app" / "data" / "legacy_seed"

    words_csv = legacy_seed_root / "words" / "es_fr_top1000.csv"
    verbs_csv = legacy_seed_root / "verbs" / "1000verbs.csv"
    conjugations_csv = legacy_seed_root / "conjugations" / "conjugations_fixed.csv"

    async with AsyncSessionLocal() as session:
        # Languages
        languages: dict[str, Language] = {}
        for code, payload in LANGUAGE_DEFINITIONS.items():
            languages[code] = await get_or_create_language(session, code, payload)

        await session.flush()
        tag_by_slug = await ensure_curated_tags(session)

        # Words (pairwise across any populated seed-language columns)
        with words_csv.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                seeded_words: dict[str, Word] = {}
                seeded_texts: dict[str, str] = {}
                seeded_synonyms: dict[str, list[str]] = {}
                tag_ids = [
                    tag_by_slug[slug].id
                    for slug in split_tags(row.get("tags"))
                    if slug in tag_by_slug
                ]

                for code, (text_column, synonym_column) in WORD_SEED_COLUMNS.items():
                    if code not in languages:
                        continue
                    text = clean_text(row.get(text_column))
                    if not text:
                        continue
                    seeded_words[code] = await get_or_create_word(
                        session,
                        text=text,
                        language_id=languages[code].id,
                    )
                    seeded_texts[code] = text
                    seeded_synonyms[code] = split_synonyms(row.get(synonym_column))

                for word in seeded_words.values():
                    await attach_word_tags(session, word_id=word.id, tag_ids=tag_ids)

                if len(seeded_words) < 2:
                    continue

                for source_code, source_word in seeded_words.items():
                    for target_code, target_text in seeded_texts.items():
                        if source_code == target_code:
                            continue
                        await upsert_word_translation(
                            session,
                            word_id=source_word.id,
                            target_language_id=languages[target_code].id,
                            translation=target_text,
                            synonyms=seeded_synonyms.get(target_code, []),
                        )

        # Verbs + legacy_id map for conjugation import
        legacy_to_fr_verb_id: dict[int, int] = {}
        with verbs_csv.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    legacy_id = int(clean_text(row.get("ID")))
                except ValueError:
                    continue

                fr = clean_text(row.get("FR")).strip()
                es_raw = clean_text(row.get("ES"))
                if not fr or not es_raw:
                    continue
                tag_ids = [
                    tag_by_slug[slug].id
                    for slug in split_tags(row.get("tags"))
                    if slug in tag_by_slug
                ]

                es_candidates = split_synonyms(es_raw)
                es_main = es_candidates[0] if es_candidates else es_raw
                es_synonyms = es_candidates[1:] if len(es_candidates) > 1 else []

                fr_verb = await get_or_create_verb(
                    session,
                    infinitive=fr,
                    language_id=languages["FR"].id,
                )
                es_verb = await get_or_create_verb(
                    session,
                    infinitive=es_main,
                    language_id=languages["ES"].id,
                )

                legacy_to_fr_verb_id[legacy_id] = fr_verb.id

                await attach_verb_tags(session, verb_id=fr_verb.id, tag_ids=tag_ids)
                await attach_verb_tags(session, verb_id=es_verb.id, tag_ids=tag_ids)

                await upsert_verb_translation(
                    session,
                    verb_id=fr_verb.id,
                    target_language_id=languages["ES"].id,
                    translation=es_main,
                    synonyms=es_synonyms,
                )
                await upsert_verb_translation(
                    session,
                    verb_id=es_verb.id,
                    target_language_id=languages["FR"].id,
                    translation=fr,
                    synonyms=[],
                )

        # Conjugations
        with conjugations_csv.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    legacy_verb_id = int(clean_text(row.get("verb_id")))
                except ValueError:
                    continue

                new_verb_id = legacy_to_fr_verb_id.get(legacy_verb_id)
                if not new_verb_id:
                    continue

                language_code = clean_text(row.get("language")).upper()
                if language_code not in languages:
                    continue

                mood = normalize_mood(language_code, clean_text(row.get("mood")))
                tense = normalize_tense(language_code, clean_text(row.get("tense")))
                pronoun = clean_text(row.get("pronoun"))
                form = clean_text(row.get("conjugated_form"))

                if not tense or not form:
                    continue

                existing = await session.execute(
                    select(VerbConjugation).where(
                        VerbConjugation.verb_id == new_verb_id,
                        VerbConjugation.language_id == languages[language_code].id,
                        VerbConjugation.mood == mood,
                        VerbConjugation.tense == tense,
                        VerbConjugation.pronoun == pronoun,
                    )
                )
                existing_row = existing.scalar_one_or_none()
                if existing_row:
                    existing_row.conjugated_form = form
                    continue

                session.add(
                    VerbConjugation(
                        verb_id=new_verb_id,
                        language_id=languages[language_code].id,
                        mood=mood,
                        tense=tense,
                        pronoun=pronoun,
                        conjugated_form=form,
                        verified=False,
                        source="legacy_csv_mlconjug3",
                    )
                )

        curated_inventory = curated_inventory_path()
        if curated_inventory.exists():
            curated_inventory_rows = load_inventory_rows(curated_inventory)
            await import_inventory_rows(session, curated_inventory_rows)

            curated_batch_files = discover_batch_conjugation_files()
            curated_conjugation_rows = []
            for batch_file in curated_batch_files:
                curated_conjugation_rows.extend(load_conjugation_rows(batch_file))

            if curated_conjugation_rows:
                await import_curated_conjugation_rows(
                    session,
                    curated_conjugation_rows,
                    skip_drafts=True,
                    fail_on_drafts=False,
                    minimum_review_status="approved",
                )

        await ensure_demo_user(session)
        await session.commit()

    print("Seed completed. Demo user: demo / demo12345")


if __name__ == "__main__":
    asyncio.run(run_seed())
