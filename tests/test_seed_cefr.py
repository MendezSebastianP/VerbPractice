from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from app.core.cefr import CEFR_LEVEL_SET, normalize_cefr_level
from app.core.tags import TAG_BY_SLUG
from app.services.curated_conjugations import load_inventory_rows
from scripts.seed_from_legacy_csv import (
    canonical_legacy_verb_cefr_levels,
    canonical_word_cefr_levels,
    seed_tag_slugs,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
WORD_SEED = REPO_ROOT / "app" / "data" / "legacy_seed" / "words" / "es_fr_top1000.csv"
VERB_SEED_ROOT = REPO_ROOT / "app" / "data" / "legacy_seed" / "verbs"
CURATED_ROOT = REPO_ROOT / "app" / "data" / "curated_conjugations"


def _csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def test_normalize_cefr_level_is_strict_and_canonical():
    assert normalize_cefr_level(" a2 ") == "A2"
    assert normalize_cefr_level("") is None
    with pytest.raises(ValueError, match="Unsupported CEFR level"):
        normalize_cefr_level("easy")


def test_generic_verb_tag_applies_to_words_and_verbs():
    assert TAG_BY_SLUG["verb"].display_name == "Verb"
    assert TAG_BY_SLUG["verb"].applies_to == ("word", "verb")


def test_seed_level_replaces_any_stale_difficulty_tag():
    slugs, level = seed_tag_slugs(
        {"tags": "food;a1;noun_thing", "cefr_level": "B1"}
    )

    assert level == "B1"
    assert slugs == ["food", "noun_thing", "b1"]
    assert TAG_BY_SLUG["b1"].kind == "difficulty"


def test_seed_canonical_levels_choose_the_easiest_shared_headword_sense():
    word_rows = [
        {"spanish": "obra", "english": "work", "tags": "", "cefr_level": "B1"},
        {"spanish": "trabajo", "english": "work", "tags": "", "cefr_level": "A1"},
    ]
    verb_rows = [
        {"FR": "posséder", "ES": "tener", "tags": "", "cefr_level": "B1"},
        {"FR": "avoir", "ES": "tener, haber", "tags": "", "cefr_level": "A1"},
    ]

    assert canonical_word_cefr_levels(word_rows)[("EN", "work")] == "A1"
    assert canonical_legacy_verb_cefr_levels(verb_rows)[("ES", "tener")] == "A1"


def test_every_hand_curated_word_has_one_valid_cefr_level():
    fieldnames, rows = _csv_rows(WORD_SEED)

    assert "cefr_level" in fieldnames
    assert len(rows) == 964
    assert all(row["cefr_level"] in CEFR_LEVEL_SET for row in rows)
    assert Counter(row["cefr_level"] for row in rows) == {
        "A1": 265,
        "A2": 309,
        "B1": 223,
        "B2": 127,
        "C1": 38,
        "C2": 2,
    }


def test_shared_word_headwords_do_not_receive_conflicting_levels():
    _, rows = _csv_rows(WORD_SEED)

    for column in ("spanish", "french", "english", "russian"):
        levels_by_headword: defaultdict[str, set[str]] = defaultdict(set)
        for row in rows:
            levels_by_headword[row[column].strip().casefold()].add(row["cefr_level"])
        conflicts = {
            headword: levels
            for headword, levels in levels_by_headword.items()
            if headword and len(levels) > 1
        }
        assert conflicts == {}


def test_every_legacy_verb_has_one_valid_cefr_level():
    fieldnames, rows = _csv_rows(VERB_SEED_ROOT / "1000verbs.csv")

    assert "cefr_level" in fieldnames
    assert len(rows) == 1130
    assert [int(row["ID"]) for row in rows] == list(range(1, 1131))
    assert all(row["cefr_level"] in CEFR_LEVEL_SET for row in rows)
    assert Counter(row["cefr_level"] for row in rows) == {
        "A1": 117,
        "A2": 313,
        "B1": 421,
        "B2": 241,
        "C1": 35,
        "C2": 3,
    }


def test_legacy_verb_subsets_keep_the_master_levels():
    _, master_rows = _csv_rows(VERB_SEED_ROOT / "1000verbs.csv")
    level_by_id = {row["ID"]: row["cefr_level"] for row in master_rows}

    for filename, expected_size in (("11verbs.csv", 11), ("20verbs.csv", 20)):
        fieldnames, rows = _csv_rows(VERB_SEED_ROOT / filename)
        assert "cefr_level" in fieldnames
        assert len(rows) == expected_size
        assert all(row["cefr_level"] == level_by_id[row["ID"]] for row in rows)


def test_curated_inventory_and_manifests_preserve_master_levels():
    _, legacy_rows = _csv_rows(VERB_SEED_ROOT / "1000verbs.csv")
    level_by_id = {int(row["ID"]): row["cefr_level"] for row in legacy_rows}

    inventory_path = CURATED_ROOT / "normalized_verb_inventory.csv"
    inventory_rows = load_inventory_rows(inventory_path)
    assert len(inventory_rows) == 1303
    assert {row.rank for row in inventory_rows} == set(range(1, 1001))
    assert all(row.cefr_level in CEFR_LEVEL_SET for row in inventory_rows)
    assert all(
        {level_by_id[legacy_id] for legacy_id in row.legacy_ids} == {row.cefr_level}
        for row in inventory_rows
    )

    manifest_rows = []
    for batch in range(1, 21):
        manifest_rows.extend(
            load_inventory_rows(
                CURATED_ROOT / "batches" / f"batch_{batch:02d}_manifest.csv"
            )
        )
    assert manifest_rows == inventory_rows
