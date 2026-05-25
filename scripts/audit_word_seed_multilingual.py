from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from dotenv import dotenv_values
from openai import OpenAI

DEFAULT_MODEL = "gpt-4o"
HEADERS = [
    "spanish",
    "french",
    "english",
    "russian",
    "spanish synonyms",
    "french synonyms",
    "english synonyms",
    "russian synonyms",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the multilingual legacy word seed and emit suggested corrections."
    )
    parser.add_argument(
        "--input",
        default="app/data/legacy_seed/words/es_fr_top1000.csv",
        help="Input CSV path.",
    )
    parser.add_argument(
        "--output-json",
        default="/tmp/word_seed_multilingual_audit.json",
        help="Where to write the collected audit suggestions as JSON.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="Rows to review per model request.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional cap on rows to review.",
    )
    parser.add_argument(
        "--start-line",
        type=int,
        default=2,
        help="Original CSV line number to start at.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model to use. Default: {DEFAULT_MODEL}",
    )
    return parser.parse_args()


def load_api_key() -> str:
    env = dotenv_values(".env")
    api_key = str(env.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is missing in .env")
    return api_key


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            normalized = {key: (value or "").strip() for key, value in row.items()}
            rows.append(normalized)
        return rows


def build_items(batch_rows: list[tuple[int, dict[str, str]]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for line_no, row in batch_rows:
        item = {"line_no": str(line_no)}
        for header in HEADERS:
            item[header.replace(" ", "_")] = row.get(header, "")
        items.append(item)
    return items


def fetch_batch(
    client: OpenAI,
    *,
    model: str,
    batch_rows: list[tuple[int, dict[str, str]]],
) -> list[dict[str, object]]:
    system = (
        "You are a careful multilingual lexicographer auditing a seed CSV with columns in Spanish, French, "
        "English, and Russian.\n"
        "Your task is to review each row conservatively and flag a row ONLY if one or more entries are clearly "
        "wrong, misleading, unidiomatic, cross-sense, malformed, or obviously weaker than a high-confidence correction.\n"
        "Check both the main headwords and the synonym lists.\n"
        "Keep one dominant shared sense per row.\n"
        "Do not propose stylistic churn. If a row is acceptable, omit it.\n"
        "For Russian, use standard modern Cyrillic spellings. For French, keep accents and ligatures where appropriate.\n"
        "When you flag a row, return the full corrected values for every column, even if only one field changed.\n"
        "Synonym fields should be semicolon-delimited strings with only same-sense alternatives; drop bad synonyms instead of padding.\n"
        "Output strict JSON with a single key corrections, where corrections is an array of objects:\n"
        "{line_no, reason, spanish, french, english, russian, spanish_synonyms, french_synonyms, english_synonyms, russian_synonyms}\n"
    )
    user = json.dumps({"rows": build_items(batch_rows)}, ensure_ascii=False)

    for attempt in range(3):
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        payload = json.loads(response.choices[0].message.content or "{}")
        corrections = payload.get("corrections")
        if isinstance(corrections, list):
            return corrections
        if attempt == 2:
            raise RuntimeError("Model response missing corrections list")
        time.sleep(2 * (attempt + 1))
    raise RuntimeError("Unreachable retry loop")


def main() -> None:
    args = parse_args()
    rows = read_rows(Path(args.input))
    indexed_rows = list(enumerate(rows, start=2))
    indexed_rows = [item for item in indexed_rows if item[0] >= args.start_line]
    if args.limit > 0:
        indexed_rows = indexed_rows[: args.limit]

    client = OpenAI(api_key=load_api_key())
    all_corrections: list[dict[str, object]] = []

    for start in range(0, len(indexed_rows), args.batch_size):
        batch = indexed_rows[start : start + args.batch_size]
        corrections = fetch_batch(client, model=args.model, batch_rows=batch)
        all_corrections.extend(corrections)
        print(
            f"Audited rows {batch[0][0]}-{batch[-1][0]} "
            f"({min(start + len(batch), len(indexed_rows))}/{len(indexed_rows)}) "
            f"corrections={len(corrections)}"
        )

    payload = {
        "input": args.input,
        "model": args.model,
        "reviewed_rows": len(indexed_rows),
        "corrections": all_corrections,
    }
    Path(args.output_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote audit suggestions to {args.output_json}")


if __name__ == "__main__":
    main()
