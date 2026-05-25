from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from dotenv import dotenv_values
from openai import OpenAI

DEFAULT_MODEL = "gpt-4o"


def build_arg_parser(
    *,
    default_target_code: str | None = None,
    default_target_language: str | None = None,
    default_text_column: str | None = None,
    default_synonyms_column: str | None = None,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Add or refresh a target-language column in the legacy ES/FR word seed CSV."
    )
    parser.add_argument(
        "--input",
        default="app/data/legacy_seed/words/es_fr_top1000.csv",
        help="Input CSV path.",
    )
    parser.add_argument(
        "--output",
        default="app/data/legacy_seed/words/es_fr_top1000.csv",
        help="Output CSV path.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model to use. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=80,
        help="Rows to send per request.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional cap on how many rows to enrich.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate rows even if the target-language column is already populated.",
    )
    parser.add_argument(
        "--target-code",
        default=default_target_code,
        required=default_target_code is None,
        help="ISO-like language code, for example EN or RU.",
    )
    parser.add_argument(
        "--target-language",
        default=default_target_language,
        required=default_target_language is None,
        help="Display name of the target language, for example English or Russian.",
    )
    parser.add_argument(
        "--text-column",
        default=default_text_column,
        required=default_text_column is None,
        help="CSV column name for the target-language headword.",
    )
    parser.add_argument(
        "--synonyms-column",
        default=default_synonyms_column,
        required=default_synonyms_column is None,
        help="CSV column name for the target-language synonyms.",
    )
    return parser


def parse_args(
    *,
    default_target_code: str | None = None,
    default_target_language: str | None = None,
    default_text_column: str | None = None,
    default_synonyms_column: str | None = None,
) -> argparse.Namespace:
    parser = build_arg_parser(
        default_target_code=default_target_code,
        default_target_language=default_target_language,
        default_text_column=default_text_column,
        default_synonyms_column=default_synonyms_column,
    )
    args = parser.parse_args()
    args.target_code = str(args.target_code).upper()
    return args


def load_api_key() -> str:
    env = dotenv_values(".env")
    api_key = str(env.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is missing in .env")
    return api_key


def ordered_headers(
    existing_headers: list[str],
    *,
    text_column: str,
    synonyms_column: str,
) -> list[str]:
    headers = list(existing_headers)
    if text_column not in headers:
        insert_at = next(
            (index for index, header in enumerate(headers) if header.endswith(" synonyms")),
            len(headers),
        )
        headers.insert(insert_at, text_column)
    if synonyms_column not in headers:
        last_synonym_index = max(
            (index for index, header in enumerate(headers) if header.endswith(" synonyms")),
            default=-1,
        )
        headers.insert(last_synonym_index + 1, synonyms_column)
    return headers


def read_rows(path: Path, *, text_column: str, synonyms_column: str) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise SystemExit(f"CSV has no header row: {path}")
        headers = ordered_headers(
            list(reader.fieldnames),
            text_column=text_column,
            synonyms_column=synonyms_column,
        )
        rows = []
        for row in reader:
            normalized = {key: (value or "").strip() for key, value in row.items()}
            normalized.setdefault(text_column, "")
            normalized.setdefault(synonyms_column, "")
            rows.append(normalized)
        return headers, rows


def should_translate(row: dict[str, str], *, text_column: str, force: bool) -> bool:
    if force:
        return True
    return not row.get(text_column, "").strip()


def build_prompt_items(
    rows: list[tuple[int, dict[str, str]]],
    *,
    target_text_column: str,
    target_synonyms_column: str,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for line_no, row in rows:
        item: dict[str, object] = {"line_no": line_no}
        for key, value in row.items():
            if key in {target_text_column, target_synonyms_column}:
                continue
            if value:
                item[key.replace(" ", "_")] = value
        items.append(item)
    return items


def system_prompt(
    *,
    target_language: str,
    target_code: str,
    text_column: str,
    synonyms_column: str,
) -> str:
    extra_rules: list[str] = []
    if target_code == "RU":
        extra_rules.append("Use standard modern Russian spelling in Cyrillic. Do not transliterate.")
    return (
        "You are a careful multilingual lexicographer extending a learner seed file.\n"
        f"For each row, infer the best {target_language} headword or short phrase that matches the "
        "shared dominant sense of the existing row entries.\n"
        f"Return 0 to 3 {target_language} synonyms only when they are genuinely useful alternatives "
        "or nearby equivalents for the same sense.\n"
        "Rules:\n"
        "- Preserve the same sense as the row. Do not switch to a different meaning.\n"
        "- Use natural lowercase except proper nouns, acronyms, or standard casing.\n"
        "- Keep phrases short and idiomatic.\n"
        "- Prefer singular nouns unless the row is inherently plural.\n"
        f"- Do not repeat the main {target_language} headword inside {synonyms_column}.\n"
        "- If there is no good synonym, return an empty array.\n"
        + ("\n".join(f"- {rule}" for rule in extra_rules) + ("\n" if extra_rules else ""))
        + "- Output strict JSON with an items array of objects: "
        f"{{line_no, {text_column}, {synonyms_column}}}.\n"
    )


def fetch_batch(
    client: OpenAI,
    *,
    model: str,
    batch_rows: list[tuple[int, dict[str, str]]],
    target_language: str,
    target_code: str,
    text_column: str,
    synonyms_column: str,
) -> dict[int, dict[str, str]]:
    system = system_prompt(
        target_language=target_language,
        target_code=target_code,
        text_column=text_column,
        synonyms_column=synonyms_column,
    )
    user = json.dumps(
        {"items": build_prompt_items(batch_rows, target_text_column=text_column, target_synonyms_column=synonyms_column)},
        ensure_ascii=False,
    )

    for attempt in range(3):
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content or "{}"
        payload = json.loads(content)
        items = payload.get("items")
        if not isinstance(items, list):
            raise RuntimeError("Model response missing items list")

        result: dict[int, dict[str, str]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                line_no = int(item["line_no"])
            except (KeyError, TypeError, ValueError):
                continue
            translated = str(item.get(text_column) or "").strip()
            if not translated:
                continue
            raw_synonyms = item.get(synonyms_column) or []
            synonyms: list[str] = []
            if isinstance(raw_synonyms, list):
                for raw in raw_synonyms[:3]:
                    text = str(raw or "").strip()
                    if text and text.casefold() != translated.casefold():
                        synonyms.append(text)
            result[line_no] = {
                text_column: translated,
                synonyms_column: ";".join(dict.fromkeys(synonyms)),
            }

        expected = {line_no for line_no, _ in batch_rows}
        if expected.issubset(result):
            return result

        missing = sorted(expected - set(result))
        if attempt == 2:
            raise RuntimeError(f"Model response missing line numbers: {missing}")
        time.sleep(2 * (attempt + 1))

    raise RuntimeError("Unreachable retry loop")


def write_rows(path: Path, *, headers: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})


def main(
    *,
    default_target_code: str | None = None,
    default_target_language: str | None = None,
    default_text_column: str | None = None,
    default_synonyms_column: str | None = None,
) -> None:
    args = parse_args(
        default_target_code=default_target_code,
        default_target_language=default_target_language,
        default_text_column=default_text_column,
        default_synonyms_column=default_synonyms_column,
    )
    input_path = Path(args.input)
    output_path = Path(args.output)
    headers, rows = read_rows(
        input_path,
        text_column=args.text_column,
        synonyms_column=args.synonyms_column,
    )
    pending = [
        (idx, row)
        for idx, row in enumerate(rows, start=2)
        if should_translate(row, text_column=args.text_column, force=args.force)
    ]
    if args.limit > 0:
        pending = pending[: args.limit]

    if not pending:
        print(f"No rows need {args.target_language} enrichment.")
        if input_path != output_path:
            write_rows(output_path, headers=headers, rows=rows)
        return

    client = OpenAI(api_key=load_api_key())
    for start in range(0, len(pending), args.batch_size):
        batch = pending[start : start + args.batch_size]
        enriched = fetch_batch(
            client,
            model=args.model,
            batch_rows=batch,
            target_language=args.target_language,
            target_code=args.target_code,
            text_column=args.text_column,
            synonyms_column=args.synonyms_column,
        )
        for line_no, updates in enriched.items():
            row = rows[line_no - 2]
            row.update(updates)
        print(
            f"Enriched rows {batch[0][0]}-{batch[-1][0]} "
            f"({min(start + len(batch), len(pending))}/{len(pending)})"
        )

    write_rows(output_path, headers=headers, rows=rows)
    print(f"Wrote enriched seed to {output_path}")


if __name__ == "__main__":
    main()
