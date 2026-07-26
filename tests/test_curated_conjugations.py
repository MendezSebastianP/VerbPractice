from __future__ import annotations

from dataclasses import replace

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.languages import LANGUAGE_DEFINITIONS, tenses_for_level
from app.db.base import Base
from app.db.models import Language, Verb, VerbConjugation, VerbTranslation
from app.services.curated_conjugations import (
    CuratedConjugationRow,
    InventoryLinkRow,
    build_batch_template_rows,
    canonical_inventory_cefr_levels,
    import_curated_conjugation_rows,
    import_inventory_rows,
    normalize_legacy_inventory_rows,
    summarize_curated_batches,
    validate_curated_batch_rows,
    validate_inventory_rows,
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
        for code, payload in LANGUAGE_DEFINITIONS.items():
            session.add(
                Language(
                    code=code,
                    name=str(payload["name"]),
                    pronoun_set=list(payload["pronoun_set"]),
                    tense_definitions=dict(payload["tense_definitions"]),
                    difficulty_tiers=dict(payload["difficulty_tiers"]),
                )
            )
        await session.commit()
        yield session

    await engine.dispose()


def test_short_tense_inventories_still_have_three_cumulative_levels():
    expected_hard_counts = {"EN": 4, "RU": 3}
    for code, expected_hard_count in expected_hard_counts.items():
        definition = LANGUAGE_DEFINITIONS[code]
        assert len(tenses_for_level(definition, "easy")) == 1
        assert len(tenses_for_level(definition, "medium")) == 2
        assert len(tenses_for_level(definition, "hard")) == expected_hard_count


def _sample_inventory() -> list[InventoryLinkRow]:
    return [
        InventoryLinkRow(
            rank=1,
            batch=1,
            fr_infinitive="être",
            es_infinitive="ser",
            link_order=1,
            legacy_ids=(1,),
            source_es_text="ser, estar",
            cefr_level="A1",
        ),
        InventoryLinkRow(
            rank=1,
            batch=1,
            fr_infinitive="être",
            es_infinitive="estar",
            link_order=2,
            legacy_ids=(1,),
            source_es_text="ser, estar",
            cefr_level="A1",
        ),
    ]


def _filled_template_rows(batch_rows: list[CuratedConjugationRow], *, review_status: str = "reviewed") -> list[CuratedConjugationRow]:
    return [
        replace(
            row,
            conjugated_form=f"{row.infinitive}:{row.tense}:{row.pronoun}",
            review_status=review_status,
            source_note="manual-test",
        )
        for row in batch_rows
    ]


def test_normalize_legacy_inventory_rows_dedupes_and_preserves_order():
    raw_rows = [
        {"ID": "1", "FR": "être ", "ES": "ser, estar", "cefr_level": "A1"},
        {"ID": "2", "FR": "avoir", "ES": "tener, haber", "cefr_level": "A1"},
        {"ID": "3", "FR": "être", "ES": "estar, ser", "cefr_level": "A1"},
        {"ID": "4", "FR": "faire", "ES": "hacer", "cefr_level": "A1"},
    ]

    rows = normalize_legacy_inventory_rows(raw_rows, limit=3, batch_size=2)

    assert [row.fr_infinitive for row in rows[:5]] == ["être", "être", "avoir", "avoir", "faire"]
    assert [row.es_infinitive for row in rows] == ["ser", "estar", "tener", "haber", "hacer"]
    assert rows[0].rank == 1
    assert rows[2].rank == 2
    assert rows[4].rank == 3
    assert rows[4].batch == 2
    assert rows[0].legacy_ids == (1, 3)
    assert {row.cefr_level for row in rows} == {"A1"}


def test_validate_inventory_rows_rejects_duplicate_links():
    duplicate_rows = [
        InventoryLinkRow(1, 1, "être", "ser", 1, (1,), "ser"),
        InventoryLinkRow(1, 1, "être", "ser", 1, (1,), "ser"),
    ]

    errors = validate_inventory_rows(duplicate_rows)

    assert any("Duplicate inventory link" in error for error in errors)


def test_canonical_inventory_level_uses_the_easiest_shared_headword_sense():
    rows = [
        replace(_sample_inventory()[0], cefr_level="B2"),
        InventoryLinkRow(
            rank=2,
            batch=1,
            fr_infinitive="demeurer",
            es_infinitive="ser",
            link_order=1,
            legacy_ids=(2,),
            source_es_text="ser",
            en_infinitive="be",
            cefr_level="A2",
        ),
    ]

    levels = canonical_inventory_cefr_levels(rows)

    assert levels[("FR", "être")] == "B2"
    assert levels[("ES", "ser")] == "A2"
    assert levels[("EN", "be")] == "A2"


def test_build_batch_template_rows_uses_current_training_scope():
    template_rows = build_batch_template_rows(_sample_inventory(), 1)
    expected_count = (
        len(LANGUAGE_DEFINITIONS["FR"]["tense_definitions"]) * len(LANGUAGE_DEFINITIONS["FR"]["pronoun_set"])
        + 2 * len(LANGUAGE_DEFINITIONS["ES"]["tense_definitions"]) * len(LANGUAGE_DEFINITIONS["ES"]["pronoun_set"])
    )

    assert len(template_rows) == expected_count
    assert all(row.tense in LANGUAGE_DEFINITIONS[row.language_code]["tense_definitions"] for row in template_rows)


def test_build_batch_template_rows_includes_russian_inventory_rows():
    inventory_rows = [replace(_sample_inventory()[0], ru_infinitive="быть")]

    template_rows = build_batch_template_rows(inventory_rows, 1)
    russian_rows = [row for row in template_rows if row.language_code == "RU"]

    assert len(russian_rows) == 18
    assert {row.tense for row in russian_rows} == set(LANGUAGE_DEFINITIONS["RU"]["tense_definitions"])
    assert {row.pronoun for row in russian_rows} == set(LANGUAGE_DEFINITIONS["RU"]["pronoun_set"])


def test_validate_curated_batch_rows_rejects_missing_and_duplicate_slots():
    inventory_rows = _sample_inventory()
    full_rows = _filled_template_rows(build_batch_template_rows(inventory_rows, 1))
    broken_rows = full_rows[:-1] + [full_rows[0]]

    errors = validate_curated_batch_rows(inventory_rows, broken_rows, batch=1)

    assert any("Duplicate conjugation slot" in error for error in errors)
    assert any("Missing conjugation slot" in error for error in errors)


@pytest.mark.asyncio
async def test_import_inventory_rows_creates_separate_spanish_verbs(sqlite_session):
    counts = await import_inventory_rows(sqlite_session, _sample_inventory())
    await sqlite_session.commit()

    verbs = (await sqlite_session.execute(select(Verb).order_by(Verb.language_id, Verb.infinitive))).scalars().all()
    translations = (await sqlite_session.execute(select(VerbTranslation))).scalars().all()

    assert counts["verbs_created"] == 3
    assert {(verb.infinitive, verb.language_id) for verb in verbs}
    assert len(translations) == 4
    assert sum(1 for verb in verbs if verb.infinitive in {"ser", "estar"}) == 2
    assert {verb.cefr_level for verb in verbs} == {"A1"}


@pytest.mark.asyncio
async def test_import_inventory_rows_creates_russian_translations_without_english(sqlite_session):
    inventory_rows = [replace(_sample_inventory()[0], ru_infinitive="быть")]

    counts = await import_inventory_rows(sqlite_session, inventory_rows)
    await sqlite_session.commit()

    verbs = (await sqlite_session.execute(select(Verb))).scalars().all()
    translations = (await sqlite_session.execute(select(VerbTranslation))).scalars().all()

    assert counts["verbs_created"] == 3
    assert any(verb.infinitive == "быть" for verb in verbs)
    assert len(translations) == 6


@pytest.mark.asyncio
async def test_import_curated_conjugation_rows_skips_drafts_and_is_idempotent(sqlite_session):
    inventory_rows = _sample_inventory()
    await import_inventory_rows(sqlite_session, inventory_rows)

    reviewed_row = CuratedConjugationRow(
        language_code="FR",
        infinitive="être",
        mood="Indicatif",
        tense="Présent",
        pronoun="je",
        conjugated_form="suis",
        batch=1,
        review_status="reviewed",
        source_note="manual",
    )
    draft_row = CuratedConjugationRow(
        language_code="FR",
        infinitive="être",
        mood="Indicatif",
        tense="Présent",
        pronoun="tu",
        conjugated_form="es",
        batch=1,
        review_status="draft",
        source_note="manual",
    )

    first_counts = await import_curated_conjugation_rows(sqlite_session, [reviewed_row, draft_row])
    second_counts = await import_curated_conjugation_rows(sqlite_session, [reviewed_row, draft_row])
    await sqlite_session.commit()

    rows = (await sqlite_session.execute(select(VerbConjugation))).scalars().all()

    assert first_counts["conjugations_created"] == 1
    assert second_counts["conjugations_skipped"] == 1
    assert len(rows) == 1
    assert rows[0].verified is True
    assert rows[0].source == "curated_manual_batch_01"


def test_validate_curated_batch_rows_can_require_approved_status():
    inventory_rows = _sample_inventory()
    reviewed_rows = _filled_template_rows(build_batch_template_rows(inventory_rows, 1), review_status="reviewed")

    errors = validate_curated_batch_rows(
        inventory_rows,
        reviewed_rows,
        batch=1,
        minimum_review_status="approved",
    )

    assert any("Missing conjugation slot" in error for error in errors)


@pytest.mark.asyncio
async def test_import_curated_conjugation_rows_can_require_approved(sqlite_session):
    inventory_rows = _sample_inventory()
    await import_inventory_rows(sqlite_session, inventory_rows)

    reviewed_row = CuratedConjugationRow(
        language_code="FR",
        infinitive="être",
        mood="Indicatif",
        tense="Présent",
        pronoun="je",
        conjugated_form="suis",
        batch=1,
        review_status="reviewed",
        source_note="manual",
    )
    approved_row = CuratedConjugationRow(
        language_code="FR",
        infinitive="être",
        mood="Indicatif",
        tense="Présent",
        pronoun="tu",
        conjugated_form="es",
        batch=1,
        review_status="approved",
        source_note="manual",
    )

    counts = await import_curated_conjugation_rows(
        sqlite_session,
        [reviewed_row, approved_row],
        minimum_review_status="approved",
    )
    await sqlite_session.commit()

    rows = (await sqlite_session.execute(select(VerbConjugation))).scalars().all()

    assert counts["conjugations_created"] == 1
    assert len(rows) == 1
    assert rows[0].pronoun == "tu"


@pytest.mark.asyncio
async def test_import_curated_conjugations_can_target_table_languages(sqlite_session):
    rows = [
        CuratedConjugationRow(
            language_code="FR",
            infinitive="prendre",
            mood="Indicatif",
            tense="Présent",
            pronoun="je",
            conjugated_form="prends",
            batch=1,
            review_status="reviewed",
            source_note="manual",
        ),
        CuratedConjugationRow(
            language_code="EN",
            infinitive="take",
            mood="Indicative",
            tense="Present",
            pronoun="I",
            conjugated_form="take",
            batch=1,
            review_status="reviewed",
            source_note="manual",
        ),
        CuratedConjugationRow(
            language_code="EN",
            infinitive="take",
            mood="Indicative",
            tense="Present",
            pronoun="I",
            conjugated_form="take",
            batch=2,
            review_status="reviewed",
            source_note="later duplicate mapping",
        ),
    ]

    first_counts = await import_curated_conjugation_rows(sqlite_session, rows, language_codes={"EN"})
    second_counts = await import_curated_conjugation_rows(sqlite_session, rows, language_codes={"EN"})
    await sqlite_session.commit()

    conjugations = (await sqlite_session.execute(select(VerbConjugation))).scalars().all()
    verbs = (await sqlite_session.execute(select(Verb))).scalars().all()

    assert first_counts["conjugations_created"] == 1
    assert second_counts["conjugations_skipped"] == 1
    assert [row.conjugated_form for row in conjugations] == ["take"]
    assert conjugations[0].source == "curated_manual_batch_02"
    assert [verb.infinitive for verb in verbs] == ["take"]


def test_summarize_curated_batches_tracks_review_depth():
    inventory_rows = _sample_inventory()
    template_rows = build_batch_template_rows(inventory_rows, 1)
    authored_rows = [
        replace(template_rows[0], conjugated_form="suis", review_status="draft"),
        replace(template_rows[1], conjugated_form="es", review_status="reviewed"),
        replace(template_rows[2], conjugated_form="est", review_status="approved"),
    ]

    summary = summarize_curated_batches(inventory_rows, authored_rows)[0]

    assert summary["required_slots"] == len(template_rows)
    assert summary["authored_slots"] == 3
    assert summary["reviewed_slots"] == 1
    assert summary["approved_slots"] == 1
    assert summary["import_ready"] is False
