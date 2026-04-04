from __future__ import annotations

import argparse
from pathlib import Path

from app.services.curated_conjugations import (
    batch_conjugations_path,
    discover_batch_conjugation_files,
    inventory_path,
    load_conjugation_rows,
    load_inventory_rows,
    validate_curated_batch_rows,
    validate_inventory_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate curated conjugation inventory and authored batch files.")
    parser.add_argument("--batch", type=int, help="Validate a single batch file.")
    parser.add_argument(
        "--reviewed-only",
        action="store_true",
        help="Validate only reviewed rows instead of all authored rows.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Do not require every slot in the batch to be present.",
    )
    parser.add_argument(
        "--minimum-review-status",
        choices=["reviewed", "approved"],
        help="Only validate rows at or above this review state.",
    )
    return parser.parse_args()


def collect_batch_files(batch: int | None) -> list[Path]:
    if batch is not None:
        path = batch_conjugations_path(batch)
        if not path.exists():
            raise SystemExit(f"Batch file not found: {path}")
        return [path]
    return discover_batch_conjugation_files()


def main() -> None:
    args = parse_args()
    inventory_rows = load_inventory_rows(inventory_path())
    errors = validate_inventory_rows(inventory_rows)

    batch_files = collect_batch_files(args.batch)
    if not batch_files:
        if errors:
            raise SystemExit("\n".join(errors))
        print("Inventory is valid. No authored batch conjugation files were found yet.")
        return

    for batch_file in batch_files:
        batch_rows = load_conjugation_rows(batch_file)
        if not batch_rows:
            errors.append(f"Batch file is empty: {batch_file}")
            continue
        batch_number = batch_rows[0].batch
        errors.extend(
            validate_curated_batch_rows(
                inventory_rows,
                batch_rows,
                batch=batch_number,
                reviewed_only=args.reviewed_only,
                require_complete=not args.allow_partial,
                minimum_review_status=args.minimum_review_status,
            )
        )

    if errors:
        raise SystemExit("\n".join(errors))

    print("Curated conjugation validation passed.")


if __name__ == "__main__":
    main()
