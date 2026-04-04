from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.models import Language, Verb, VerbConjugation, VerbTranslation, Word, WordTranslation
from app.services.curated_conjugations import (
    discover_batch_conjugation_files,
    inventory_path,
    load_conjugation_rows,
    load_inventory_rows,
    summarize_curated_batches,
)


def _clean_text(value: str | None) -> str:
    return (value or "").strip()


def _normalize_synonyms(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item.strip() for item in value if item and item.strip()]
    return [item.strip() for item in value.split(",") if item.strip()]


async def _language_by_code(db: AsyncSession, code: str) -> Language:
    language = (await db.execute(select(Language).where(Language.code == code.strip().upper()))).scalar_one_or_none()
    if language is None:
        raise ValueError(f"Unknown language code: {code}")
    return language


def _serialize_word_row(row: Any) -> dict[str, Any]:
    translation, word, source_language, target_language = row
    return {
        "id": translation.id,
        "word_id": word.id,
        "text": word.text,
        "language_code": source_language.code,
        "language_name": source_language.name,
        "translation": translation.translation,
        "target_language_code": target_language.code,
        "target_language_name": target_language.name,
        "synonyms": list(translation.synonyms or []),
        "verified": translation.verified,
        "source": translation.source,
    }


def _serialize_verb_row(row: Any) -> dict[str, Any]:
    translation, verb, source_language, target_language = row
    return {
        "id": translation.id,
        "verb_id": verb.id,
        "infinitive": verb.infinitive,
        "language_code": source_language.code,
        "language_name": source_language.name,
        "translation": translation.translation,
        "target_language_code": target_language.code,
        "target_language_name": target_language.name,
        "synonyms": list(translation.synonyms or []),
        "verified": translation.verified,
        "source": translation.source,
    }


def _serialize_conjugation_row(row: Any) -> dict[str, Any]:
    conjugation, verb, language = row
    return {
        "id": conjugation.id,
        "verb_id": verb.id,
        "infinitive": verb.infinitive,
        "language_code": language.code,
        "language_name": language.name,
        "mood": conjugation.mood,
        "tense": conjugation.tense,
        "pronoun": conjugation.pronoun,
        "conjugated_form": conjugation.conjugated_form,
        "verified": conjugation.verified,
        "source": conjugation.source,
    }


def _verified_filter(column, verified: str | None):
    if verified == "true":
        return column.is_(True)
    if verified == "false":
        return column.is_(False)
    return None


async def content_summary(db: AsyncSession) -> dict[str, Any]:
    counts = {
        "words": (
            await db.execute(
                select(
                    func.count(WordTranslation.id),
                    func.count(WordTranslation.id).filter(WordTranslation.verified.is_(False)),
                )
            )
        ).one(),
        "verbs": (
            await db.execute(
                select(
                    func.count(VerbTranslation.id),
                    func.count(VerbTranslation.id).filter(VerbTranslation.verified.is_(False)),
                )
            )
        ).one(),
        "conjugations": (
            await db.execute(
                select(
                    func.count(VerbConjugation.id),
                    func.count(VerbConjugation.id).filter(VerbConjugation.verified.is_(False)),
                )
            )
        ).one(),
    }
    curated = curated_summary()
    return {
        "words": {"total": counts["words"][0], "needs_review": counts["words"][1]},
        "verbs": {"total": counts["verbs"][0], "needs_review": counts["verbs"][1]},
        "conjugations": {"total": counts["conjugations"][0], "needs_review": counts["conjugations"][1]},
        "curated": curated,
    }


def curated_summary() -> dict[str, Any]:
    inventory_file = inventory_path()
    if not inventory_file.exists():
        return {
            "inventory_links": 0,
            "batches_total": 0,
            "batches_with_authored": 0,
            "batches_import_ready": 0,
            "required_slots": 0,
            "authored_slots": 0,
            "reviewed_slots": 0,
            "approved_slots": 0,
            "authored_pct": 0.0,
            "reviewed_pct": 0.0,
            "approved_pct": 0.0,
            "batches": [],
        }

    inventory_rows = load_inventory_rows(inventory_file)
    authored_rows = []
    for batch_file in discover_batch_conjugation_files():
        authored_rows.extend(load_conjugation_rows(batch_file))

    batches = summarize_curated_batches(inventory_rows, authored_rows)
    required_slots = sum(int(row["required_slots"]) for row in batches)
    authored_slots = sum(int(row["authored_slots"]) for row in batches)
    reviewed_slots = sum(int(row["reviewed_slots"]) for row in batches)
    approved_slots = sum(int(row["approved_slots"]) for row in batches)

    def pct(value: int) -> float:
        return round((value / required_slots) * 100, 1) if required_slots else 0.0

    return {
        "inventory_links": len(inventory_rows),
        "batches_total": len(batches),
        "batches_with_authored": sum(1 for row in batches if int(row["authored_slots"]) > 0),
        "batches_import_ready": sum(1 for row in batches if bool(row["import_ready"])),
        "required_slots": required_slots,
        "authored_slots": authored_slots,
        "reviewed_slots": reviewed_slots,
        "approved_slots": approved_slots,
        "authored_pct": pct(authored_slots),
        "reviewed_pct": pct(reviewed_slots),
        "approved_pct": pct(approved_slots),
        "batches": batches,
    }


async def list_word_rows(
    db: AsyncSession,
    *,
    search: str = "",
    verified: str | None = None,
    limit: int = 60,
) -> list[dict[str, Any]]:
    source_language = aliased(Language)
    target_language = aliased(Language)
    stmt = (
        select(WordTranslation, Word, source_language, target_language)
        .join(Word, Word.id == WordTranslation.word_id)
        .join(source_language, source_language.id == Word.language_id)
        .join(target_language, target_language.id == WordTranslation.target_language_id)
        .order_by(Word.id.asc(), WordTranslation.id.asc())
        .limit(limit)
    )
    search_text = _clean_text(search)
    if search_text:
        like = f"%{search_text}%"
        stmt = stmt.where(
            or_(
                Word.text.ilike(like),
                WordTranslation.translation.ilike(like),
                WordTranslation.source.ilike(like),
            )
        )
    verified_filter = _verified_filter(WordTranslation.verified, verified)
    if verified_filter is not None:
        stmt = stmt.where(verified_filter)
    rows = (await db.execute(stmt)).all()
    return [_serialize_word_row(row) for row in rows]


async def list_verb_rows(
    db: AsyncSession,
    *,
    search: str = "",
    verified: str | None = None,
    limit: int = 60,
) -> list[dict[str, Any]]:
    source_language = aliased(Language)
    target_language = aliased(Language)
    stmt = (
        select(VerbTranslation, Verb, source_language, target_language)
        .join(Verb, Verb.id == VerbTranslation.verb_id)
        .join(source_language, source_language.id == Verb.language_id)
        .join(target_language, target_language.id == VerbTranslation.target_language_id)
        .order_by(Verb.id.asc(), VerbTranslation.id.asc())
        .limit(limit)
    )
    search_text = _clean_text(search)
    if search_text:
        like = f"%{search_text}%"
        stmt = stmt.where(
            or_(
                Verb.infinitive.ilike(like),
                VerbTranslation.translation.ilike(like),
                VerbTranslation.source.ilike(like),
            )
        )
    verified_filter = _verified_filter(VerbTranslation.verified, verified)
    if verified_filter is not None:
        stmt = stmt.where(verified_filter)
    rows = (await db.execute(stmt)).all()
    return [_serialize_verb_row(row) for row in rows]


async def list_conjugation_rows(
    db: AsyncSession,
    *,
    search: str = "",
    verified: str | None = None,
    language_code: str | None = None,
    limit: int = 80,
) -> list[dict[str, Any]]:
    stmt = (
        select(VerbConjugation, Verb, Language)
        .join(Verb, Verb.id == VerbConjugation.verb_id)
        .join(Language, Language.id == VerbConjugation.language_id)
        .order_by(VerbConjugation.id.asc())
        .limit(limit)
    )
    search_text = _clean_text(search)
    if search_text:
        like = f"%{search_text}%"
        stmt = stmt.where(
            or_(
                Verb.infinitive.ilike(like),
                VerbConjugation.tense.ilike(like),
                VerbConjugation.pronoun.ilike(like),
                VerbConjugation.conjugated_form.ilike(like),
                VerbConjugation.source.ilike(like),
            )
        )
    verified_filter = _verified_filter(VerbConjugation.verified, verified)
    if verified_filter is not None:
        stmt = stmt.where(verified_filter)
    if language_code:
        stmt = stmt.where(Language.code == language_code.strip().upper())
    rows = (await db.execute(stmt)).all()
    return [_serialize_conjugation_row(row) for row in rows]


async def create_word_row(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    source_language = await _language_by_code(db, payload["language_code"])
    target_language = await _language_by_code(db, payload["target_language_code"])
    text = _clean_text(payload.get("text"))
    translation_value = _clean_text(payload.get("translation"))
    if not text or not translation_value:
        raise ValueError("Both source text and translation are required")

    word = (
        await db.execute(
            select(Word).where(Word.text == text, Word.language_id == source_language.id)
        )
    ).scalar_one_or_none()
    if word is None:
        word = Word(text=text, language_id=source_language.id)
        db.add(word)
        await db.flush()

    translation = WordTranslation(
        word_id=word.id,
        target_language_id=target_language.id,
        translation=translation_value,
        synonyms=_normalize_synonyms(payload.get("synonyms")),
        verified=bool(payload.get("verified", False)),
        source=_clean_text(payload.get("source")) or "admin_manual",
    )
    db.add(translation)
    await db.flush()
    source_alias = aliased(Language)
    target_alias = aliased(Language)
    created = (
        await db.execute(
            select(WordTranslation, Word, source_alias, target_alias)
            .join(Word, Word.id == WordTranslation.word_id)
            .join(source_alias, source_alias.id == Word.language_id)
            .join(target_alias, target_alias.id == WordTranslation.target_language_id)
            .where(WordTranslation.id == translation.id)
        )
    ).one()
    return _serialize_word_row(created)


async def update_word_row(db: AsyncSession, translation_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    translation = (await db.execute(select(WordTranslation).where(WordTranslation.id == translation_id))).scalar_one_or_none()
    if translation is None:
        raise ValueError("Word translation row not found")
    word = (await db.execute(select(Word).where(Word.id == translation.word_id))).scalar_one()

    if "text" in payload:
        text = _clean_text(payload.get("text"))
        if text:
            word.text = text
    if "language_code" in payload:
        word.language_id = (await _language_by_code(db, payload["language_code"])).id
    if "target_language_code" in payload:
        translation.target_language_id = (await _language_by_code(db, payload["target_language_code"])).id
    if "translation" in payload:
        value = _clean_text(payload.get("translation"))
        if value:
            translation.translation = value
    if "synonyms" in payload:
        translation.synonyms = _normalize_synonyms(payload.get("synonyms"))
    if "verified" in payload:
        translation.verified = bool(payload.get("verified"))
    if "source" in payload:
        source = _clean_text(payload.get("source"))
        translation.source = source or translation.source

    await db.flush()
    source_alias = aliased(Language)
    target_alias = aliased(Language)
    updated = (
        await db.execute(
            select(WordTranslation, Word, source_alias, target_alias)
            .join(Word, Word.id == WordTranslation.word_id)
            .join(source_alias, source_alias.id == Word.language_id)
            .join(target_alias, target_alias.id == WordTranslation.target_language_id)
            .where(WordTranslation.id == translation.id)
        )
    ).one()
    return _serialize_word_row(updated)


async def delete_word_row(db: AsyncSession, translation_id: int) -> None:
    translation = (await db.execute(select(WordTranslation).where(WordTranslation.id == translation_id))).scalar_one_or_none()
    if translation is not None:
        await db.delete(translation)


async def create_verb_row(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    source_language = await _language_by_code(db, payload["language_code"])
    target_language = await _language_by_code(db, payload["target_language_code"])
    infinitive = _clean_text(payload.get("infinitive"))
    translation_value = _clean_text(payload.get("translation"))
    if not infinitive or not translation_value:
        raise ValueError("Both infinitive and translation are required")

    verb = (
        await db.execute(
            select(Verb).where(Verb.infinitive == infinitive, Verb.language_id == source_language.id)
        )
    ).scalar_one_or_none()
    if verb is None:
        verb = Verb(infinitive=infinitive, language_id=source_language.id)
        db.add(verb)
        await db.flush()

    translation = VerbTranslation(
        verb_id=verb.id,
        target_language_id=target_language.id,
        translation=translation_value,
        synonyms=_normalize_synonyms(payload.get("synonyms")),
        verified=bool(payload.get("verified", False)),
        source=_clean_text(payload.get("source")) or "admin_manual",
    )
    db.add(translation)
    await db.flush()

    source_alias = aliased(Language)
    target_alias = aliased(Language)
    created = (
        await db.execute(
            select(VerbTranslation, Verb, source_alias, target_alias)
            .join(Verb, Verb.id == VerbTranslation.verb_id)
            .join(source_alias, source_alias.id == Verb.language_id)
            .join(target_alias, target_alias.id == VerbTranslation.target_language_id)
            .where(VerbTranslation.id == translation.id)
        )
    ).one()
    return _serialize_verb_row(created)


async def update_verb_row(db: AsyncSession, translation_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    translation = (await db.execute(select(VerbTranslation).where(VerbTranslation.id == translation_id))).scalar_one_or_none()
    if translation is None:
        raise ValueError("Verb translation row not found")
    verb = (await db.execute(select(Verb).where(Verb.id == translation.verb_id))).scalar_one()

    if "infinitive" in payload:
        infinitive = _clean_text(payload.get("infinitive"))
        if infinitive:
            verb.infinitive = infinitive
    if "language_code" in payload:
        verb.language_id = (await _language_by_code(db, payload["language_code"])).id
    if "target_language_code" in payload:
        translation.target_language_id = (await _language_by_code(db, payload["target_language_code"])).id
    if "translation" in payload:
        value = _clean_text(payload.get("translation"))
        if value:
            translation.translation = value
    if "synonyms" in payload:
        translation.synonyms = _normalize_synonyms(payload.get("synonyms"))
    if "verified" in payload:
        translation.verified = bool(payload.get("verified"))
    if "source" in payload:
        source = _clean_text(payload.get("source"))
        translation.source = source or translation.source

    await db.flush()
    source_alias = aliased(Language)
    target_alias = aliased(Language)
    updated = (
        await db.execute(
            select(VerbTranslation, Verb, source_alias, target_alias)
            .join(Verb, Verb.id == VerbTranslation.verb_id)
            .join(source_alias, source_alias.id == Verb.language_id)
            .join(target_alias, target_alias.id == VerbTranslation.target_language_id)
            .where(VerbTranslation.id == translation.id)
        )
    ).one()
    return _serialize_verb_row(updated)


async def delete_verb_row(db: AsyncSession, translation_id: int) -> None:
    translation = (await db.execute(select(VerbTranslation).where(VerbTranslation.id == translation_id))).scalar_one_or_none()
    if translation is not None:
        await db.delete(translation)


async def create_conjugation_row(db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    language = await _language_by_code(db, payload["language_code"])
    infinitive = _clean_text(payload.get("infinitive"))
    if not infinitive:
        raise ValueError("Infinitive is required")
    verb = (
        await db.execute(
            select(Verb).where(Verb.infinitive == infinitive, Verb.language_id == language.id)
        )
    ).scalar_one_or_none()
    if verb is None:
        verb = Verb(infinitive=infinitive, language_id=language.id)
        db.add(verb)
        await db.flush()

    conjugation = VerbConjugation(
        verb_id=verb.id,
        language_id=language.id,
        mood=_clean_text(payload.get("mood")),
        tense=_clean_text(payload.get("tense")),
        pronoun=_clean_text(payload.get("pronoun")),
        conjugated_form=_clean_text(payload.get("conjugated_form")),
        verified=bool(payload.get("verified", False)),
        source=_clean_text(payload.get("source")) or "admin_manual",
    )
    if not all([conjugation.mood, conjugation.tense, conjugation.pronoun, conjugation.conjugated_form]):
        raise ValueError("Mood, tense, pronoun, and conjugated form are required")
    db.add(conjugation)
    await db.flush()
    created = (
        await db.execute(
            select(VerbConjugation, Verb, Language)
            .join(Verb, Verb.id == VerbConjugation.verb_id)
            .join(Language, Language.id == VerbConjugation.language_id)
            .where(VerbConjugation.id == conjugation.id)
        )
    ).one()
    return _serialize_conjugation_row(created)


async def update_conjugation_row(db: AsyncSession, conjugation_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    conjugation = (await db.execute(select(VerbConjugation).where(VerbConjugation.id == conjugation_id))).scalar_one_or_none()
    if conjugation is None:
        raise ValueError("Conjugation row not found")

    if "language_code" in payload:
        language = await _language_by_code(db, payload["language_code"])
        conjugation.language_id = language.id
        if "infinitive" in payload:
            infinitive = _clean_text(payload.get("infinitive"))
            if infinitive:
                verb = (
                    await db.execute(
                        select(Verb).where(Verb.infinitive == infinitive, Verb.language_id == language.id)
                    )
                ).scalar_one_or_none()
                if verb is None:
                    verb = Verb(infinitive=infinitive, language_id=language.id)
                    db.add(verb)
                    await db.flush()
                conjugation.verb_id = verb.id
    elif "infinitive" in payload:
        infinitive = _clean_text(payload.get("infinitive"))
        if infinitive:
            current_verb = (await db.execute(select(Verb).where(Verb.id == conjugation.verb_id))).scalar_one()
            current_verb.infinitive = infinitive

    for key in ("mood", "tense", "pronoun", "conjugated_form", "source"):
        if key in payload:
            value = _clean_text(payload.get(key))
            if value:
                setattr(conjugation, key, value)
    if "verified" in payload:
        conjugation.verified = bool(payload.get("verified"))

    await db.flush()
    updated = (
        await db.execute(
            select(VerbConjugation, Verb, Language)
            .join(Verb, Verb.id == VerbConjugation.verb_id)
            .join(Language, Language.id == VerbConjugation.language_id)
            .where(VerbConjugation.id == conjugation.id)
        )
    ).one()
    return _serialize_conjugation_row(updated)


async def delete_conjugation_row(db: AsyncSession, conjugation_id: int) -> None:
    conjugation = (await db.execute(select(VerbConjugation).where(VerbConjugation.id == conjugation_id))).scalar_one_or_none()
    if conjugation is not None:
        await db.delete(conjugation)
