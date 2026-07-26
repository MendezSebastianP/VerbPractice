from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.db.models import Language, Word
from app.db.session import AsyncSessionLocal
try:
    from scripts.import_offline_senses import import_file
except ModuleNotFoundError:  # Direct execution: python scripts/import_kaikki_senses.py
    from import_offline_senses import import_file


SUPPORTED_TARGET_CODES = {"en": "EN", "es": "ES", "fr": "FR", "ru": "RU"}
_TOKEN_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)
_INDEX_RE = re.compile(r"^\d+(?:-\d+)?$")


@dataclass(frozen=True, slots=True)
class Edition:
    root: str
    language_path: str


EDITIONS = {
    "EN": Edition("https://kaikki.org/dictionary", "English"),
    "ES": Edition("https://kaikki.org/eswiktionary", "Español"),
    "FR": Edition("https://kaikki.org/frwiktionary", "Français"),
    "RU": Edition("https://kaikki.org/ruwiktionary", "Русский"),
}


def _component(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def word_url(code: str, word: str) -> str:
    edition = EDITIONS[code]
    return (
        f"{edition.root}/{_component(edition.language_path)}/meaning/"
        f"{_component(word[:1])}/{_component(word[:2])}/{_component(word)}.jsonl"
    )


def _cache_path(cache_dir: Path, code: str, word: str) -> Path:
    digest = hashlib.sha256(word.encode("utf-8")).hexdigest()
    return cache_dir / code.lower() / f"{digest}.jsonl"


def _fetch_word(
    *,
    code: str,
    word: str,
    cache_dir: Path,
    refresh: bool,
) -> tuple[str, str, str]:
    destination = _cache_path(cache_dir, code, word)
    missing = destination.with_suffix(".missing")
    if not refresh:
        if destination.is_file():
            return code, word, "cached"
        if missing.is_file():
            return code, word, "missing"

    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        word_url(code, word),
        headers={
            "Accept": "application/x-ndjson, application/json",
            "User-Agent": "VerbPractice offline dictionary bootstrap",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read()
            if not payload.strip():
                raise ValueError("empty response")
            temporary = destination.with_suffix(".tmp")
            temporary.write_bytes(payload)
            os.replace(temporary, destination)
            missing.unlink(missing_ok=True)
            return code, word, "downloaded"
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                missing.touch()
                destination.unlink(missing_ok=True)
                return code, word, "missing"
            if attempt == 2:
                return code, word, f"failed: HTTP {exc.code}"
        except (OSError, ValueError) as exc:
            if attempt == 2:
                return code, word, f"failed: {exc}"
        time.sleep(0.5 * (attempt + 1))
    return code, word, "failed"


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.casefold()))


def parse_sense_indices(value: object, sense_count: int) -> list[int]:
    if isinstance(value, int):
        return [value - 1] if 1 <= value <= sense_count else []
    if not isinstance(value, str):
        return []
    indices: set[int] = set()
    for raw_part in value.replace("–", "-").split(","):
        part = raw_part.strip()
        if not _INDEX_RE.fullmatch(part):
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start, end = int(start_text), int(end_text)
            for number in range(start, end + 1):
                if 1 <= number <= sense_count:
                    indices.add(number - 1)
        else:
            number = int(part)
            if 1 <= number <= sense_count:
                indices.add(number - 1)
    return sorted(indices)


def match_sense_text(selector: str, definitions: list[str]) -> list[int]:
    selector_sequence = _TOKEN_RE.findall(selector.casefold())
    selector_tokens = set(selector_sequence)
    if not selector_tokens:
        return []
    phrase_matches: list[tuple[int, int]] = []
    fallback_scores: list[tuple[float, float, int]] = []
    for index, definition in enumerate(definitions):
        definition_sequence = _TOKEN_RE.findall(definition.casefold())
        definition_tokens = set(definition_sequence)
        overlap = selector_tokens & definition_tokens
        coverage = len(overlap) / len(selector_tokens)
        union = selector_tokens | definition_tokens
        jaccard = len(overlap) / len(union) if union else 0.0
        fallback_scores.append((coverage, jaccard, index))
        width = len(selector_sequence)
        for start in range(len(definition_sequence) - width + 1):
            if definition_sequence[start : start + width] == selector_sequence:
                phrase_matches.append((start, index))
                break

    if phrase_matches:
        phrase_matches.sort()
        best_position = phrase_matches[0][0]
        best = [index for position, index in phrase_matches if position == best_position]
        return best if len(best) == 1 else []

    fallback_scores.sort(reverse=True)
    if not fallback_scores or fallback_scores[0][0] < 0.6:
        return []
    if (
        len(fallback_scores) > 1
        and fallback_scores[0][:2] == fallback_scores[1][:2]
    ):
        return []
    return [fallback_scores[0][2]]


def _translation_indices(translation: dict, definitions: list[str]) -> list[int]:
    indices = parse_sense_indices(
        translation.get("sense_index"),
        len(definitions),
    )
    if indices:
        return indices
    selector = str(translation.get("sense") or "").strip()
    if selector:
        return match_sense_text(selector, definitions)
    return [0] if len(definitions) == 1 else []


def _examples(sense: dict) -> list[str]:
    output: list[str] = []
    for item in sense.get("examples") or []:
        if not isinstance(item, dict) or item.get("type") != "example":
            continue
        text = str(item.get("text") or "").strip()
        if text and len(text) <= 300 and text not in output:
            output.append(text)
    return output[:3]


def _synonyms(sense: dict) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for item in sense.get("synonyms") or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("word") or "").strip()
        if text and not any(existing["text"] == text for existing in output):
            output.append({"text": text})
    return output[:5]


def normalize_payload(
    *,
    code: str,
    requested_word: str,
    payload: bytes,
    source_version: str,
) -> list[dict]:
    records: list[dict] = []
    seen_keys: set[str] = set()
    for raw_line in payload.splitlines():
        if not raw_line.strip():
            continue
        entry = json.loads(raw_line)
        if str(entry.get("lang_code") or "").casefold() != code.casefold():
            continue
        senses = entry.get("senses") or []
        if not isinstance(senses, list):
            continue
        definitions = [
            str((sense.get("glosses") or [""])[0]).strip()
            if isinstance(sense, dict)
            else ""
            for sense in senses
        ]
        translations_by_sense: list[dict[str, list[str]]] = [
            {} for _ in definitions
        ]
        for translation in entry.get("translations") or []:
            if not isinstance(translation, dict):
                continue
            target_code = SUPPORTED_TARGET_CODES.get(
                str(translation.get("lang_code") or "").casefold()
            )
            translated_word = str(translation.get("word") or "").strip()
            if not target_code or target_code == code or not translated_word:
                continue
            for sense_index in _translation_indices(translation, definitions):
                target_words = translations_by_sense[sense_index].setdefault(
                    target_code, []
                )
                if translated_word not in target_words and len(target_words) < 3:
                    target_words.append(translated_word)

        part_of_speech = str(entry.get("pos") or "").strip() or None
        canonical_word = str(entry.get("word") or requested_word).strip().casefold()
        for sense_index, (sense, definition, translations) in enumerate(
            zip(senses, definitions, translations_by_sense, strict=True),
            start=1,
        ):
            if not definition or not translations or not isinstance(sense, dict):
                continue
            fingerprint = hashlib.sha256(
                f"{code}\0{canonical_word}\0{part_of_speech}\0{definition}".encode(
                    "utf-8"
                )
            ).hexdigest()[:24]
            sense_key = f"kaikki:{code.lower()}:{fingerprint}"
            if sense_key in seen_keys:
                continue
            seen_keys.add(sense_key)
            records.append(
                {
                    "language": code,
                    "word": canonical_word,
                    "sense_key": sense_key,
                    "part_of_speech": part_of_speech,
                    "definition": definition,
                    "synonyms": _synonyms(sense),
                    "examples": _examples(sense),
                    "translations": translations,
                    "source": "kaikki_wiktionary",
                    "source_version": source_version,
                    "is_primary": False,
                    "_source_order": (len(records), sense_index),
                }
            )
    if records:
        records[0]["is_primary"] = True
    for record in records:
        record.pop("_source_order", None)
    return records


async def load_existing_words(codes: set[str]) -> list[tuple[str, str]]:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(Word.id, Language.code, Word.text)
                .join(Word, Word.language_id == Language.id)
                .where(Language.code.in_(codes))
                .order_by(Word.id)
            )
        ).all()
    unique: dict[tuple[str, str], tuple[str, str]] = {}
    for _, raw_code, raw_word in rows:
        code = str(raw_code).upper()
        word = str(raw_word)
        unique.setdefault((code, word.casefold()), (code, word))
    return sorted(unique.values())


def _write_normalized_file(
    *,
    words: list[tuple[str, str]],
    cache_dir: Path,
    output: Path,
    source_version: str,
) -> dict[str, int]:
    counts = {"records": 0, "invalid_files": 0}
    temporary = output.with_suffix(".tmp")
    output.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("w", encoding="utf-8") as destination:
        for code, word in words:
            path = _cache_path(cache_dir, code, word)
            if not path.is_file():
                continue
            try:
                records = normalize_payload(
                    code=code,
                    requested_word=word,
                    payload=path.read_bytes(),
                    source_version=source_version,
                )
            except (json.JSONDecodeError, UnicodeError, ValueError):
                counts["invalid_files"] += 1
                continue
            for record in records:
                destination.write(
                    json.dumps(record, ensure_ascii=False, separators=(",", ":"))
                    + "\n"
                )
                counts["records"] += 1
    os.replace(temporary, output)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download per-word Kaikki/Wiktionary data and import supported, "
            "sense-linked translations into the local dictionary."
        )
    )
    parser.add_argument(
        "--languages",
        default="EN,ES,FR,RU",
        help="Comma-separated source language codes (default: EN,ES,FR,RU)",
    )
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".local/dictionary/kaikki"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".local/dictionary/kaikki-senses.jsonl"),
    )
    args = parser.parse_args()

    codes = {
        code.strip().upper()
        for code in args.languages.split(",")
        if code.strip()
    }
    unsupported = codes - set(EDITIONS)
    if unsupported:
        raise SystemExit(f"Unsupported language codes: {', '.join(sorted(unsupported))}")
    if not 1 <= args.concurrency <= 16:
        raise SystemExit("--concurrency must be between 1 and 16")

    words = asyncio.run(load_existing_words(codes))
    if not words:
        raise SystemExit("No existing words found. Run the database seed first.")
    print(
        f"Preparing trusted dictionary data for {len(words)} existing words "
        f"({', '.join(sorted(codes))})."
    )

    fetch_counts: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(
                _fetch_word,
                code=code,
                word=word,
                cache_dir=args.cache_dir,
                refresh=args.refresh,
            )
            for code, word in words
        ]
        for completed, future in enumerate(as_completed(futures), start=1):
            code, word, status = future.result()
            category = status.split(":", 1)[0]
            fetch_counts[category] = fetch_counts.get(category, 0) + 1
            if status.startswith("failed:"):
                print(f"Warning: {code} {word!r}: {status}")
            if completed % 100 == 0 or completed == len(futures):
                print(f"Dictionary files: {completed}/{len(futures)}")

    source_version = f"live-{datetime.now(UTC).date().isoformat()}"
    normalized_counts = _write_normalized_file(
        words=words,
        cache_dir=args.cache_dir,
        output=args.output,
        source_version=source_version,
    )
    if normalized_counts["records"] == 0:
        raise SystemExit(
            "No sense-linked translations were found; nothing was imported."
        )
    imported = asyncio.run(import_file(args.output.resolve()))
    print(
        json.dumps(
            {
                "dictionary_files": fetch_counts,
                "normalized": normalized_counts,
                "imported": imported,
                "output": str(args.output),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
