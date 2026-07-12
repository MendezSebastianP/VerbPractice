from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.core.languages import LANGUAGE_DEFINITIONS
from app.db.session import AsyncSessionLocal
from app.services.curated_conjugations import (
    batch_conjugations_path,
    discover_batch_conjugation_files,
    import_curated_conjugation_rows,
    import_inventory_rows,
    inventory_path,
    load_conjugation_rows,
    load_inventory_rows,
    validate_curated_batch_rows,
    validate_inventory_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import curated conjugation batches into the database.")
    parser.add_argument("--batch", type=int, help="Import a single batch.")
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip reviewed-batch completeness validation before import.",
    )
    parser.add_argument(
        "--allow-reviewed",
        action="store_true",
        help="Permit reviewed rows in addition to approved rows during import.",
    )
    parser.add_argument(
        "--language",
        action="append",
        choices=sorted(LANGUAGE_DEFINITIONS),
        help="Import conjugations for one language only. Repeat to select multiple languages.",
    )
    parser.add_argument(
        "--skip-inventory",
        action="store_true",
        help="Skip translation inventory import when only table conjugations are needed.",
    )
    return parser.parse_args()


def collect_batch_files(batch: int | None) -> list[Path]:
    if batch is not None:
        path = batch_conjugations_path(batch)
        if not path.exists():
            raise SystemExit(f"Batch file not found: {path}")
        return [path]
    return discover_batch_conjugation_files()


async def main() -> None:
    args = parse_args()
    minimum_review_status = "reviewed" if args.allow_reviewed else "approved"

    inventory_rows = load_inventory_rows(inventory_path())
    errors = validate_inventory_rows(inventory_rows)

    batch_files = collect_batch_files(args.batch)
    batch_rows = []
    for batch_file in batch_files:
        batch_rows.extend(load_conjugation_rows(batch_file))

    if batch_rows and not args.skip_validation:
        for batch_number in sorted({row.batch for row in batch_rows}):
            errors.extend(
                validate_curated_batch_rows(
                    inventory_rows,
                    batch_rows,
                    batch=batch_number,
                    minimum_review_status=minimum_review_status,
                    require_complete=True,
                )
            )

    if errors:
        raise SystemExit("\n".join(errors))

    async with AsyncSessionLocal() as session:
        inventory_counts = (
            {"verbs_created": 0, "translations_created": 0}
            if args.skip_inventory
            else await import_inventory_rows(session, inventory_rows, batch=args.batch)
        )
        conjugation_counts = await import_curated_conjugation_rows(
            session,
            batch_rows,
            batch=args.batch,
            language_codes=set(args.language) if args.language else None,
            skip_drafts=True,
            fail_on_drafts=False,
            minimum_review_status=minimum_review_status,
        )
        await session.commit()

    print("Curated import complete.")
    if args.language:
        print({"languages": sorted(set(args.language))})
    print(inventory_counts)
    print(conjugation_counts)


if __name__ == "__main__":
    asyncio.run(main())
