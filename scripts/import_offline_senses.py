from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.db.models import Language, Word, WordSense, WordSenseTranslation
from app.db.session import AsyncSessionLocal


def _clean_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _clean_synonyms(value: object) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    for item in _clean_list(value):
        if isinstance(item, str) and item.strip():
            cleaned.append({"text": item.strip()})
        elif isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            gloss = str(item.get("gloss") or "").strip()
            if text:
                cleaned.append(
                    {"text": text, **({"gloss": gloss} if gloss else {})}
                )
    return cleaned


async def import_file(path: Path) -> dict[str, int]:
    counts = {
        "lines": 0,
        "words_created": 0,
        "senses_created": 0,
        "senses_updated": 0,
        "translations_created": 0,
    }
    async with AsyncSessionLocal() as db:
        languages = {
            language.code.upper(): language
            for language in (await db.execute(select(Language))).scalars().all()
        }
        language_codes_by_id = {
            language.id: code for code, language in languages.items()
        }
        word_cache: dict[tuple[str, str], Word] = {}
        for existing_word in (
            await db.execute(select(Word).order_by(Word.id))
        ).scalars():
            code = language_codes_by_id.get(existing_word.language_id)
            if code is not None:
                word_cache.setdefault(
                    (code, existing_word.text.casefold()),
                    existing_word,
                )
        with path.open(encoding="utf-8") as source:
            for line_number, raw_line in enumerate(source, start=1):
                if not raw_line.strip():
                    continue
                counts["lines"] += 1
                try:
                    payload = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"{path}:{line_number}: invalid JSON: {exc}"
                    ) from exc

                source_code = str(payload.get("language") or "").upper()
                word_text = str(payload.get("word") or "").strip().casefold()
                sense_key = str(payload.get("sense_key") or "").strip()
                definition = str(payload.get("definition") or "").strip()
                if source_code not in languages:
                    raise ValueError(
                        f"{path}:{line_number}: unknown language code {source_code!r}"
                    )
                if not word_text or not sense_key or not definition:
                    raise ValueError(
                        f"{path}:{line_number}: word, sense_key, and definition are required"
                    )

                source_language = languages[source_code]
                word_cache_key = (source_code, word_text)
                word = word_cache.get(word_cache_key)
                if word is None:
                    word = Word(text=word_text, language_id=source_language.id)
                    db.add(word)
                    await db.flush()
                    word_cache[word_cache_key] = word
                    counts["words_created"] += 1

                sense = (
                    await db.execute(
                        select(WordSense).where(
                            WordSense.word_id == word.id,
                            WordSense.sense_key == sense_key,
                        )
                    )
                ).scalar_one_or_none()
                if sense is None:
                    sense = WordSense(
                        word_id=word.id,
                        sense_key=sense_key,
                        definition=definition,
                    )
                    db.add(sense)
                    await db.flush()
                    counts["senses_created"] += 1
                else:
                    counts["senses_updated"] += 1

                sense.definition = definition
                sense.part_of_speech = (
                    str(payload.get("part_of_speech") or "").strip() or None
                )
                sense.synonyms = _clean_synonyms(payload.get("synonyms"))
                sense.examples = [
                    str(item).strip()
                    for item in _clean_list(payload.get("examples"))
                    if str(item).strip()
                ]
                sense.source = (
                    str(payload.get("source") or "offline_dictionary").strip()
                    or "offline_dictionary"
                )
                sense.source_version = (
                    str(payload.get("source_version") or "").strip() or None
                )
                sense.is_trusted = True
                sense.is_primary = bool(payload.get("is_primary", False))
                sense.embedding = None
                sense.embedding_model = None

                raw_translations = payload.get("translations") or {}
                if not isinstance(raw_translations, dict):
                    raise ValueError(
                        f"{path}:{line_number}: translations must be an object"
                    )
                for target_code, entries in raw_translations.items():
                    target_language = languages.get(str(target_code).upper())
                    if target_language is None:
                        raise ValueError(
                            f"{path}:{line_number}: unknown target language {target_code!r}"
                        )
                    if not isinstance(entries, list):
                        entries = [entries]
                    for priority, raw_entry in enumerate(entries):
                        if isinstance(raw_entry, str):
                            translation = raw_entry.strip()
                            note = None
                        elif isinstance(raw_entry, dict):
                            translation = str(
                                raw_entry.get("translation") or ""
                            ).strip()
                            note = (
                                str(raw_entry.get("note") or "").strip() or None
                            )
                        else:
                            continue
                        if not translation:
                            continue
                        existing = (
                            await db.execute(
                                select(WordSenseTranslation).where(
                                    WordSenseTranslation.sense_id == sense.id,
                                    WordSenseTranslation.target_language_id
                                    == target_language.id,
                                    WordSenseTranslation.translation
                                    == translation,
                                )
                            )
                        ).scalar_one_or_none()
                        if existing is None:
                            existing = WordSenseTranslation(
                                sense_id=sense.id,
                                target_language_id=target_language.id,
                                translation=translation,
                            )
                            db.add(existing)
                            counts["translations_created"] += 1
                        existing.note = note
                        existing.source = sense.source
                        existing.priority = priority

        await db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import normalized, trusted offline dictionary senses from JSONL."
    )
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    if not args.input.is_file():
        raise SystemExit(f"Input file does not exist: {args.input}")
    counts = asyncio.run(import_file(args.input.resolve()))
    print(json.dumps(counts, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
