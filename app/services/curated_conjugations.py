from __future__ import annotations

import csv
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cefr import CEFR_LEVEL_SET, earliest_cefr_level, normalize_cefr_level
from app.core.languages import LANGUAGE_DEFINITIONS
from app.db.models import Language, Verb, VerbConjugation, VerbTranslation

INVENTORY_FIELDNAMES = [
    "rank",
    "batch",
    "fr_infinitive",
    "es_infinitive",
    "link_order",
    "legacy_ids",
    "source_es_text",
    "en_infinitive",
    "ru_infinitive",
    "cefr_level",
]
CONJUGATION_FIELDNAMES = [
    "language_code",
    "infinitive",
    "mood",
    "tense",
    "pronoun",
    "conjugated_form",
    "batch",
    "review_status",
    "source_note",
]
REVIEW_STATUS_ORDER = {
    "draft": 0,
    "reviewed": 1,
    "approved": 2,
}
ALLOWED_REVIEW_STATUSES = set(REVIEW_STATUS_ORDER)


@dataclass(slots=True)
class InventoryLinkRow:
    rank: int
    batch: int
    fr_infinitive: str
    es_infinitive: str
    link_order: int
    legacy_ids: tuple[int, ...]
    source_es_text: str
    en_infinitive: str = ""
    ru_infinitive: str = ""
    cefr_level: str = ""

    def to_csv_row(self) -> dict[str, str]:
        return {
            "rank": str(self.rank),
            "batch": str(self.batch),
            "fr_infinitive": self.fr_infinitive,
            "es_infinitive": self.es_infinitive,
            "link_order": str(self.link_order),
            "legacy_ids": ",".join(str(item) for item in self.legacy_ids),
            "source_es_text": self.source_es_text,
            "en_infinitive": self.en_infinitive,
            "ru_infinitive": self.ru_infinitive,
            "cefr_level": self.cefr_level,
        }


@dataclass(slots=True)
class CuratedConjugationRow:
    language_code: str
    infinitive: str
    mood: str
    tense: str
    pronoun: str
    conjugated_form: str
    batch: int
    review_status: str
    source_note: str

    def to_csv_row(self) -> dict[str, str]:
        return {
            "language_code": self.language_code,
            "infinitive": self.infinitive,
            "mood": self.mood,
            "tense": self.tense,
            "pronoun": self.pronoun,
            "conjugated_form": self.conjugated_form,
            "batch": str(self.batch),
            "review_status": self.review_status,
            "source_note": self.source_note,
        }


def option_a_root() -> Path:
    return Path(__file__).resolve().parents[2]


def curated_root() -> Path:
    return option_a_root() / "app" / "data" / "curated_conjugations"


def inventory_path() -> Path:
    return curated_root() / "normalized_verb_inventory.csv"


def batches_dir() -> Path:
    return curated_root() / "batches"


def batch_manifest_path(batch: int) -> Path:
    return batches_dir() / f"batch_{batch:02d}_manifest.csv"


def batch_conjugations_path(batch: int) -> Path:
    return batches_dir() / f"batch_{batch:02d}_conjugations.csv"


def clean_cell(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def canonical_key(value: str) -> str:
    return clean_cell(value).casefold()


def review_status_at_least(status: str, minimum_status: str) -> bool:
    return REVIEW_STATUS_ORDER.get(status, -1) >= REVIEW_STATUS_ORDER[minimum_status]


def split_es_candidates(value: str | None) -> list[str]:
    raw = clean_cell(value)
    if not raw:
        return []
    parts = [clean_cell(chunk) for chunk in raw.split(",")]
    return [chunk for chunk in parts if chunk]


def parse_legacy_verb_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize_legacy_inventory_rows(
    raw_rows: list[dict[str, str]],
    *,
    limit: int = 1000,
    batch_size: int = 50,
) -> list[InventoryLinkRow]:
    aggregates: list[dict[str, Any]] = []
    by_french: dict[str, dict[str, Any]] = {}

    for raw_row in raw_rows:
        fr_infinitive = clean_cell(raw_row.get("FR"))
        if not fr_infinitive:
            continue

        fr_key = canonical_key(fr_infinitive)
        entry = by_french.get(fr_key)
        if entry is None:
            if len(aggregates) >= limit:
                break
            entry = {
                "fr_infinitive": fr_infinitive,
                "legacy_ids": [],
                "source_es_values": [],
                "es_candidates": [],
                "es_seen": set(),
                "cefr_level": normalize_cefr_level(raw_row.get("cefr_level")) or "",
            }
            by_french[fr_key] = entry
            aggregates.append(entry)
        else:
            incoming_level = normalize_cefr_level(raw_row.get("cefr_level"))
            entry["cefr_level"] = (
                earliest_cefr_level(entry["cefr_level"], incoming_level) or ""
            )

        legacy_id_raw = clean_cell(raw_row.get("ID"))
        if legacy_id_raw.isdigit():
            legacy_id = int(legacy_id_raw)
            if legacy_id not in entry["legacy_ids"]:
                entry["legacy_ids"].append(legacy_id)

        es_raw = clean_cell(raw_row.get("ES"))
        if es_raw and es_raw not in entry["source_es_values"]:
            entry["source_es_values"].append(es_raw)

        for es_candidate in split_es_candidates(es_raw):
            es_key = canonical_key(es_candidate)
            if es_key in entry["es_seen"]:
                continue
            entry["es_seen"].add(es_key)
            entry["es_candidates"].append(es_candidate)

    normalized_rows: list[InventoryLinkRow] = []
    for rank, entry in enumerate(aggregates, start=1):
        batch = ((rank - 1) // batch_size) + 1
        source_es_text = " | ".join(entry["source_es_values"])
        for link_order, es_infinitive in enumerate(entry["es_candidates"], start=1):
            normalized_rows.append(
                InventoryLinkRow(
                    rank=rank,
                    batch=batch,
                    fr_infinitive=entry["fr_infinitive"],
                    es_infinitive=es_infinitive,
                    link_order=link_order,
                    legacy_ids=tuple(entry["legacy_ids"]),
                    source_es_text=source_es_text,
                    cefr_level=entry["cefr_level"],
                )
            )
    return normalized_rows


def write_inventory_rows(path: Path, rows: list[InventoryLinkRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INVENTORY_FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())


def load_inventory_rows(path: Path) -> list[InventoryLinkRow]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            InventoryLinkRow(
                rank=int(clean_cell(row.get("rank")) or 0),
                batch=int(clean_cell(row.get("batch")) or 0),
                fr_infinitive=clean_cell(row.get("fr_infinitive")),
                es_infinitive=clean_cell(row.get("es_infinitive")),
                link_order=int(clean_cell(row.get("link_order")) or 0),
                legacy_ids=tuple(
                    int(chunk)
                    for chunk in clean_cell(row.get("legacy_ids")).split(",")
                    if clean_cell(chunk).isdigit()
                ),
                source_es_text=clean_cell(row.get("source_es_text")),
                en_infinitive=clean_cell(row.get("en_infinitive")),
                ru_infinitive=clean_cell(row.get("ru_infinitive")),
                cefr_level=normalize_cefr_level(row.get("cefr_level")) or "",
            )
            for row in reader
        ]


def write_conjugation_rows(path: Path, rows: list[CuratedConjugationRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CONJUGATION_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())


def load_conjugation_rows(path: Path) -> list[CuratedConjugationRow]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[CuratedConjugationRow] = []
        for raw_row in reader:
            if not any(clean_cell(value) for value in raw_row.values()):
                continue
            rows.append(
                CuratedConjugationRow(
                    language_code=clean_cell(raw_row.get("language_code")).upper(),
                    infinitive=clean_cell(raw_row.get("infinitive")),
                    mood=clean_cell(raw_row.get("mood")),
                    tense=clean_cell(raw_row.get("tense")),
                    pronoun=clean_cell(raw_row.get("pronoun")),
                    conjugated_form=clean_cell(raw_row.get("conjugated_form")),
                    batch=int(clean_cell(raw_row.get("batch")) or 0),
                    review_status=(clean_cell(raw_row.get("review_status")) or "draft").lower(),
                    source_note=clean_cell(raw_row.get("source_note")),
                )
            )
        return rows


def discover_batch_conjugation_files(root: Path | None = None) -> list[Path]:
    search_root = root or batches_dir()
    if not search_root.exists():
        return []
    return sorted(search_root.glob("batch_*_conjugations.csv"))


def inventory_rows_for_batch(rows: list[InventoryLinkRow], batch: int) -> list[InventoryLinkRow]:
    return [row for row in rows if row.batch == batch]


def canonical_inventory_cefr_levels(
    rows: list[InventoryLinkRow],
) -> dict[tuple[str, str], str]:
    levels: dict[tuple[str, str], str] = {}
    for row in rows:
        row_level = normalize_cefr_level(row.cefr_level)
        if row_level is None:
            raise ValueError(
                f"Inventory row rank {row.rank} is missing its required CEFR level."
            )
        for language_code, infinitive in (
            ("FR", row.fr_infinitive),
            ("ES", row.es_infinitive),
            ("EN", row.en_infinitive),
            ("RU", row.ru_infinitive),
        ):
            if not infinitive:
                continue
            key = (language_code, infinitive)
            levels[key] = earliest_cefr_level(levels.get(key), row_level) or row_level
    return levels


def ordered_verbs_for_batch(rows: list[InventoryLinkRow], batch: int) -> dict[str, list[str]]:
    batch_rows = inventory_rows_for_batch(rows, batch)
    fr_seen = OrderedDict()
    es_seen = OrderedDict()
    en_seen = OrderedDict()
    ru_seen = OrderedDict()
    for row in batch_rows:
        fr_seen.setdefault(row.fr_infinitive, None)
        es_seen.setdefault(row.es_infinitive, None)
        if row.en_infinitive:
            en_seen.setdefault(row.en_infinitive, None)
        if row.ru_infinitive:
            ru_seen.setdefault(row.ru_infinitive, None)
    return {
        "FR": list(fr_seen.keys()),
        "ES": list(es_seen.keys()),
        **({"EN": list(en_seen.keys())} if en_seen else {}),
        **({"RU": list(ru_seen.keys())} if ru_seen else {}),
    }


def build_batch_manifest_rows(rows: list[InventoryLinkRow], batch: int) -> list[InventoryLinkRow]:
    return inventory_rows_for_batch(rows, batch)


def build_batch_template_rows(rows: list[InventoryLinkRow], batch: int) -> list[CuratedConjugationRow]:
    verbs_by_language = ordered_verbs_for_batch(rows, batch)
    template_rows: list[CuratedConjugationRow] = []
    for language_code, infinitives in verbs_by_language.items():
        language_payload = LANGUAGE_DEFINITIONS[language_code]
        tense_definitions = language_payload["tense_definitions"]
        pronouns = language_payload["pronoun_set"]
        for infinitive in infinitives:
            for tense, tense_meta in tense_definitions.items():
                mood = str(tense_meta["mood"])
                for pronoun in pronouns:
                    template_rows.append(
                        CuratedConjugationRow(
                            language_code=language_code,
                            infinitive=infinitive,
                            mood=mood,
                            tense=tense,
                            pronoun=pronoun,
                            conjugated_form="",
                            batch=batch,
                            review_status="draft",
                            source_note="",
                        )
                    )
    return template_rows


def validate_inventory_rows(rows: list[InventoryLinkRow], *, batch_size: int = 50) -> list[str]:
    errors: list[str] = []
    seen_links: set[tuple[int, str, str]] = set()
    rank_to_fr: dict[int, str] = {}

    for row in rows:
        if not row.rank or not row.batch:
            errors.append("Inventory row is missing rank or batch.")
        if not row.fr_infinitive or not row.es_infinitive:
            errors.append(f"Inventory row rank {row.rank} has empty French or Spanish infinitive.")
        if not row.cefr_level:
            errors.append(f"Inventory row rank {row.rank} is missing its CEFR level.")
        elif row.cefr_level not in CEFR_LEVEL_SET:
            errors.append(
                f"Inventory row rank {row.rank} has unsupported CEFR level '{row.cefr_level}'."
            )
        expected_batch = ((row.rank - 1) // batch_size) + 1 if row.rank else row.batch
        if row.batch != expected_batch:
            errors.append(
                f"Inventory row rank {row.rank} for {row.fr_infinitive} has batch {row.batch}, expected {expected_batch}."
            )
        duplicate_key = (row.rank, canonical_key(row.fr_infinitive), canonical_key(row.es_infinitive))
        if duplicate_key in seen_links:
            errors.append(
                f"Duplicate inventory link for rank {row.rank}: {row.fr_infinitive} -> {row.es_infinitive}."
            )
        seen_links.add(duplicate_key)

        existing_fr = rank_to_fr.get(row.rank)
        if existing_fr is None:
            rank_to_fr[row.rank] = row.fr_infinitive
        elif canonical_key(existing_fr) != canonical_key(row.fr_infinitive):
            errors.append(
                f"Rank {row.rank} maps to multiple French infinitives: {existing_fr} and {row.fr_infinitive}."
            )

    return errors


def validate_curated_batch_rows(
    inventory_rows: list[InventoryLinkRow],
    conjugation_rows: list[CuratedConjugationRow],
    *,
    batch: int,
    reviewed_only: bool = False,
    require_complete: bool = True,
    minimum_review_status: str | None = None,
) -> list[str]:
    errors: list[str] = []
    expected_verbs = ordered_verbs_for_batch(inventory_rows, batch)
    if not any(expected_verbs.values()):
        return [f"Batch {batch:02d} does not exist in the normalized inventory."]

    filtered_rows = [row for row in conjugation_rows if row.batch == batch]
    if minimum_review_status is not None:
        filtered_rows = [
            row for row in filtered_rows if review_status_at_least(row.review_status, minimum_review_status)
        ]
    elif reviewed_only:
        filtered_rows = [row for row in filtered_rows if row.review_status == "reviewed"]

    slot_counts: defaultdict[tuple[str, str, str, str, str], int] = defaultdict(int)
    actual_slots: set[tuple[str, str, str, str, str]] = set()

    for row in filtered_rows:
        if row.review_status not in ALLOWED_REVIEW_STATUSES:
            errors.append(
                f"Unsupported review status '{row.review_status}' for {row.language_code} {row.infinitive} {row.tense} {row.pronoun}."
            )
        language_payload = LANGUAGE_DEFINITIONS.get(row.language_code)
        if language_payload is None:
            errors.append(f"Unsupported language code '{row.language_code}' in batch {batch:02d}.")
            continue

        tense_definitions = language_payload["tense_definitions"]
        pronouns = language_payload["pronoun_set"]

        expected_language_verbs = expected_verbs.get(row.language_code)
        if expected_language_verbs is None:
            errors.append(
                f"Batch {batch:02d} references {row.language_code} rows, but that language is not in the inventory batch."
            )
        elif row.infinitive not in expected_language_verbs:
            errors.append(
                f"Batch {batch:02d} references {row.language_code} verb '{row.infinitive}' which is not in the inventory batch."
            )
        if row.tense not in tense_definitions:
            errors.append(
                f"Unsupported tense '{row.tense}' for language {row.language_code} in batch {batch:02d}."
            )
            continue

        expected_mood = str(tense_definitions[row.tense]["mood"])
        if row.mood != expected_mood:
            errors.append(
                f"Mood mismatch for {row.language_code} {row.infinitive} {row.tense}: got '{row.mood}', expected '{expected_mood}'."
            )
        if row.pronoun not in pronouns:
            errors.append(
                f"Unsupported pronoun '{row.pronoun}' for language {row.language_code} in batch {batch:02d}."
            )

        slot_key = (row.language_code, row.infinitive, row.mood, row.tense, row.pronoun)
        slot_counts[slot_key] += 1
        if row.conjugated_form:
            actual_slots.add(slot_key)
        else:
            errors.append(
                f"Empty conjugated form for {row.language_code} {row.infinitive} {row.tense} {row.pronoun}."
            )

    for slot_key, count in slot_counts.items():
        if count > 1:
            language_code, infinitive, mood, tense, pronoun = slot_key
            errors.append(
                f"Duplicate conjugation slot for {language_code} {infinitive} {mood}/{tense} {pronoun}."
            )

    if require_complete:
        expected_slots: set[tuple[str, str, str, str, str]] = set()
        for language_code, infinitives in expected_verbs.items():
            language_payload = LANGUAGE_DEFINITIONS[language_code]
            tense_definitions = language_payload["tense_definitions"]
            pronouns = language_payload["pronoun_set"]
            for infinitive in infinitives:
                for tense, tense_meta in tense_definitions.items():
                    mood = str(tense_meta["mood"])
                    for pronoun in pronouns:
                        expected_slots.add((language_code, infinitive, mood, tense, pronoun))

        missing_slots = sorted(expected_slots - actual_slots)
        for language_code, infinitive, mood, tense, pronoun in missing_slots:
            errors.append(
                f"Missing conjugation slot for {language_code} {infinitive} {mood}/{tense} {pronoun}."
            )

    return errors


async def _language_map(session: AsyncSession) -> dict[str, Language]:
    result = await session.execute(select(Language))
    return {row.code: row for row in result.scalars().all()}


async def _get_or_create_verb(
    session: AsyncSession,
    *,
    cache: dict[tuple[str, str], Verb],
    languages: dict[str, Language],
    language_code: str,
    infinitive: str,
    cefr_level: str | None,
) -> tuple[Verb, bool]:
    key = (language_code, infinitive)
    cached = cache.get(key)
    if cached is not None:
        cached.cefr_level = normalize_cefr_level(cefr_level)
        return cached, False

    language = languages[language_code]
    result = await session.execute(
        select(Verb).where(Verb.language_id == language.id, Verb.infinitive == infinitive)
    )
    verb = result.scalar_one_or_none()
    created = False
    if verb is None:
        verb = Verb(
            infinitive=infinitive,
            language_id=language.id,
            cefr_level=normalize_cefr_level(cefr_level),
        )
        session.add(verb)
        await session.flush()
        created = True
    else:
        verb.cefr_level = normalize_cefr_level(cefr_level)
    cache[key] = verb
    return verb, created


async def _ensure_translation(
    session: AsyncSession,
    *,
    verb: Verb,
    target_language: Language,
    translation: str,
) -> tuple[VerbTranslation, bool]:
    result = await session.execute(
        select(VerbTranslation).where(
            VerbTranslation.verb_id == verb.id,
            VerbTranslation.target_language_id == target_language.id,
            VerbTranslation.translation == translation,
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return row, False

    row = VerbTranslation(
        verb_id=verb.id,
        target_language_id=target_language.id,
        translation=translation,
        synonyms=[],
        verified=True,
        source="curated_inventory",
    )
    session.add(row)
    return row, True


async def import_inventory_rows(
    session: AsyncSession,
    rows: list[InventoryLinkRow],
    *,
    batch: int | None = None,
) -> dict[str, int]:
    languages = await _language_map(session)
    verb_cache: dict[tuple[str, str], Verb] = {}
    counts = {
        "verbs_created": 0,
        "translations_created": 0,
    }

    canonical_cefr_levels = canonical_inventory_cefr_levels(rows)
    selected_rows = [row for row in rows if batch is None or row.batch == batch]
    for row in selected_rows:
        en_verb: Verb | None = None
        fr_verb, fr_created = await _get_or_create_verb(
            session,
            cache=verb_cache,
            languages=languages,
            language_code="FR",
            infinitive=row.fr_infinitive,
            cefr_level=canonical_cefr_levels[("FR", row.fr_infinitive)],
        )
        es_verb, es_created = await _get_or_create_verb(
            session,
            cache=verb_cache,
            languages=languages,
            language_code="ES",
            infinitive=row.es_infinitive,
            cefr_level=canonical_cefr_levels[("ES", row.es_infinitive)],
        )
        counts["verbs_created"] += int(fr_created) + int(es_created)

        _, created_fr_to_es = await _ensure_translation(
            session,
            verb=fr_verb,
            target_language=languages["ES"],
            translation=row.es_infinitive,
        )
        _, created_es_to_fr = await _ensure_translation(
            session,
            verb=es_verb,
            target_language=languages["FR"],
            translation=row.fr_infinitive,
        )
        counts["translations_created"] += int(created_fr_to_es) + int(created_es_to_fr)

        if row.en_infinitive and "EN" in languages:
            en_verb, en_created = await _get_or_create_verb(
                session,
                cache=verb_cache,
                languages=languages,
                language_code="EN",
                infinitive=row.en_infinitive,
                cefr_level=canonical_cefr_levels[("EN", row.en_infinitive)],
            )
            counts["verbs_created"] += int(en_created)

            _, created_fr_to_en = await _ensure_translation(
                session,
                verb=fr_verb,
                target_language=languages["EN"],
                translation=row.en_infinitive,
            )
            _, created_en_to_fr = await _ensure_translation(
                session,
                verb=en_verb,
                target_language=languages["FR"],
                translation=row.fr_infinitive,
            )
            _, created_es_to_en = await _ensure_translation(
                session,
                verb=es_verb,
                target_language=languages["EN"],
                translation=row.en_infinitive,
            )
            _, created_en_to_es = await _ensure_translation(
                session,
                verb=en_verb,
                target_language=languages["ES"],
                translation=row.es_infinitive,
            )
            counts["translations_created"] += (
                int(created_fr_to_en)
                + int(created_en_to_fr)
                + int(created_es_to_en)
                + int(created_en_to_es)
            )

        if row.ru_infinitive and "RU" in languages:
            ru_verb, ru_created = await _get_or_create_verb(
                session,
                cache=verb_cache,
                languages=languages,
                language_code="RU",
                infinitive=row.ru_infinitive,
                cefr_level=canonical_cefr_levels[("RU", row.ru_infinitive)],
            )
            counts["verbs_created"] += int(ru_created)

            _, created_fr_to_ru = await _ensure_translation(
                session,
                verb=fr_verb,
                target_language=languages["RU"],
                translation=row.ru_infinitive,
            )
            _, created_ru_to_fr = await _ensure_translation(
                session,
                verb=ru_verb,
                target_language=languages["FR"],
                translation=row.fr_infinitive,
            )
            _, created_es_to_ru = await _ensure_translation(
                session,
                verb=es_verb,
                target_language=languages["RU"],
                translation=row.ru_infinitive,
            )
            _, created_ru_to_es = await _ensure_translation(
                session,
                verb=ru_verb,
                target_language=languages["ES"],
                translation=row.es_infinitive,
            )
            created_en_to_ru = False
            created_ru_to_en = False
            if en_verb is not None:
                _, created_en_to_ru = await _ensure_translation(
                    session,
                    verb=en_verb,
                    target_language=languages["RU"],
                    translation=row.ru_infinitive,
                )
                _, created_ru_to_en = await _ensure_translation(
                    session,
                    verb=ru_verb,
                    target_language=languages["EN"],
                    translation=row.en_infinitive,
                )
            counts["translations_created"] += (
                int(created_fr_to_ru)
                + int(created_ru_to_fr)
                + int(created_es_to_ru)
                + int(created_ru_to_es)
                + int(created_en_to_ru)
                + int(created_ru_to_en)
            )

    return counts


async def import_curated_conjugation_rows(
    session: AsyncSession,
    rows: list[CuratedConjugationRow],
    *,
    batch: int | None = None,
    language_codes: set[str] | None = None,
    skip_drafts: bool = True,
    fail_on_drafts: bool = False,
    minimum_review_status: str = "reviewed",
) -> dict[str, int]:
    languages = await _language_map(session)
    selected_rows = [row for row in rows if batch is None or row.batch == batch]

    if language_codes:
        selected_languages = {code.upper() for code in language_codes}
        unknown_languages = selected_languages - set(languages)
        if unknown_languages:
            raise ValueError(f"Unsupported language codes: {', '.join(sorted(unknown_languages))}")
        selected_rows = [row for row in selected_rows if row.language_code in selected_languages]

    if minimum_review_status not in ALLOWED_REVIEW_STATUSES:
        raise ValueError(f"Unsupported minimum review status: {minimum_review_status}")

    if fail_on_drafts and any(
        not review_status_at_least(row.review_status, minimum_review_status) for row in selected_rows
    ):
        raise ValueError("Rows below the required review status are present in the selected curated conjugation batch.")

    if skip_drafts:
        selected_rows = [
            row for row in selected_rows if review_status_at_least(row.review_status, minimum_review_status)
        ]

    # The inventory can map the same translated infinitive from more than one
    # French rank. Keep the latest curated occurrence for each database slot so
    # source labels and forms do not churn on every idempotent full import.
    rows_by_slot: dict[tuple[str, str, str, str, str], CuratedConjugationRow] = {}
    for row in selected_rows:
        rows_by_slot[(row.language_code, row.infinitive, row.mood, row.tense, row.pronoun)] = row
    selected_rows = list(rows_by_slot.values())

    counts = {
        "conjugations_created": 0,
        "conjugations_updated": 0,
        "conjugations_skipped": 0,
    }

    if not selected_rows:
        return counts

    selected_codes = {row.language_code for row in selected_rows}
    selected_language_ids = {languages[code].id for code in selected_codes}
    selected_infinitives = {row.infinitive for row in selected_rows}
    existing_verbs = (
        await session.execute(
            select(Verb).where(
                Verb.language_id.in_(selected_language_ids),
                Verb.infinitive.in_(selected_infinitives),
            )
        )
    ).scalars().all()
    code_by_language_id = {language.id: code for code, language in languages.items()}
    verb_cache = {
        (code_by_language_id[verb.language_id], verb.infinitive): verb
        for verb in existing_verbs
    }

    for language_code, infinitive in sorted({(row.language_code, row.infinitive) for row in selected_rows}):
        key = (language_code, infinitive)
        if key in verb_cache:
            continue
        verb = Verb(infinitive=infinitive, language_id=languages[language_code].id)
        session.add(verb)
        verb_cache[key] = verb

    await session.flush()

    selected_verb_ids = {verb.id for verb in verb_cache.values() if verb.id is not None}
    existing_conjugations = (
        await session.execute(
            select(VerbConjugation).where(
                VerbConjugation.language_id.in_(selected_language_ids),
                VerbConjugation.verb_id.in_(selected_verb_ids),
            )
        )
    ).scalars().all()
    conjugation_cache = {
        (row.verb_id, row.language_id, row.mood, row.tense, row.pronoun): row
        for row in existing_conjugations
    }

    for row in selected_rows:
        verb = verb_cache[(row.language_code, row.infinitive)]
        language = languages[row.language_code]
        slot_key = (verb.id, language.id, row.mood, row.tense, row.pronoun)
        existing = conjugation_cache.get(slot_key)
        source_value = f"curated_manual_batch_{row.batch:02d}"
        if existing is None:
            existing = VerbConjugation(
                verb_id=verb.id,
                language_id=language.id,
                mood=row.mood,
                tense=row.tense,
                pronoun=row.pronoun,
                conjugated_form=row.conjugated_form,
                verified=True,
                source=source_value,
            )
            session.add(existing)
            conjugation_cache[slot_key] = existing
            counts["conjugations_created"] += 1
            continue

        changed = False
        if existing.conjugated_form != row.conjugated_form:
            existing.conjugated_form = row.conjugated_form
            changed = True
        if not existing.verified:
            existing.verified = True
            changed = True
        if existing.source != source_value:
            existing.source = source_value
            changed = True
        if changed:
            counts["conjugations_updated"] += 1
        else:
            counts["conjugations_skipped"] += 1

    return counts


def summarize_curated_batches(
    inventory_rows: list[InventoryLinkRow],
    conjugation_rows: list[CuratedConjugationRow],
) -> list[dict[str, int | float | bool]]:
    summaries: list[dict[str, int | float | bool]] = []
    for batch in sorted({row.batch for row in inventory_rows}):
        expected_rows = build_batch_template_rows(inventory_rows, batch)
        actual_rows = [row for row in conjugation_rows if row.batch == batch]
        required = len(expected_rows)
        authored = len([row for row in actual_rows if row.conjugated_form])
        reviewed = len([row for row in actual_rows if row.conjugated_form and row.review_status == "reviewed"])
        approved = len([row for row in actual_rows if row.conjugated_form and row.review_status == "approved"])
        summaries.append(
            {
                "batch": batch,
                "required_slots": required,
                "authored_slots": authored,
                "reviewed_slots": reviewed,
                "approved_slots": approved,
                "authored_pct": round((authored / required) * 100, 1) if required else 0.0,
                "reviewed_pct": round((reviewed / required) * 100, 1) if required else 0.0,
                "approved_pct": round((approved / required) * 100, 1) if required else 0.0,
                "import_ready": approved >= required and required > 0,
            }
        )
    return summaries
