from __future__ import annotations

import json

from scripts.import_kaikki_senses import (
    match_sense_text,
    normalize_payload,
    parse_sense_indices,
    word_url,
)


def test_word_url_uses_native_edition_and_url_encoding() -> None:
    assert word_url("RU", "банк").endswith(
        "/%D0%B1/%D0%B1%D0%B0/%D0%B1%D0%B0%D0%BD%D0%BA.jsonl"
    )
    assert "/ruwiktionary/%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9/" in word_url(
        "RU", "банк"
    )


def test_parse_sense_indices_supports_ranges_without_guessing() -> None:
    assert parse_sense_indices("1-3,5", 5) == [0, 1, 2, 4]
    assert parse_sense_indices("all", 5) == []
    assert parse_sense_indices(2, 2) == [1]


def test_text_selector_requires_a_unique_lexical_match() -> None:
    definitions = [
        "A financial institution that accepts deposits.",
        "A branch office of such an institution.",
        "The edge of a river or lake.",
    ]
    assert match_sense_text("institution", definitions) == [0]
    assert match_sense_text("edge of river or lake", definitions) == [2]
    assert match_sense_text("unrelated meaning", definitions) == []
    assert match_sense_text(
        "bank",
        ["A bank for money.", "The bank beside a river."],
    ) == []


def test_normalize_payload_links_only_supported_exact_senses() -> None:
    entry = {
        "lang_code": "es",
        "word": "banco",
        "pos": "noun",
        "senses": [
            {
                "glosses": ["Empresa que ofrece servicios monetarios."],
                "examples": [{"type": "example", "text": "Voy al banco."}],
            },
            {"glosses": ["Mueble alargado usado como asiento."]},
        ],
        "translations": [
            {"lang_code": "fr", "word": "banque", "sense_index": "1"},
            {"lang_code": "en", "word": "bench", "sense_index": "2"},
            {"lang_code": "de", "word": "Bank", "sense_index": "1-2"},
            {"lang_code": "ru", "word": "сомнительно"},
        ],
    }
    records = normalize_payload(
        code="ES",
        requested_word="banco",
        payload=(json.dumps(entry) + "\n").encode(),
        source_version="test",
    )

    assert len(records) == 2
    assert records[0]["is_primary"] is True
    assert records[0]["translations"] == {"FR": ["banque"]}
    assert records[0]["examples"] == ["Voy al banco."]
    assert records[1]["translations"] == {"EN": ["bench"]}
    assert all(record["source"] == "kaikki_wiktionary" for record in records)
