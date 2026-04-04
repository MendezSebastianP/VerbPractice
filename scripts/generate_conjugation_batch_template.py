from __future__ import annotations

import argparse
from pathlib import Path

from app.services.curated_conjugations import (
    batch_conjugations_path,
    batch_manifest_path,
    build_batch_manifest_rows,
    build_batch_template_rows,
    inventory_path,
    load_inventory_rows,
    write_conjugation_rows,
    write_inventory_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate manifest and manual conjugation template for a batch.")
    parser.add_argument("--batch", type=int, required=True, help="Batch number to generate.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output files.")
    return parser.parse_args()


def ensure_writable(path: Path, force: bool) -> None:
    if path.exists() and not force:
        raise SystemExit(f"Refusing to overwrite existing file without --force: {path}")


def main() -> None:
    args = parse_args()
    inventory_rows = load_inventory_rows(inventory_path())
    manifest_rows = build_batch_manifest_rows(inventory_rows, args.batch)
    if not manifest_rows:
        raise SystemExit(f"Batch {args.batch:02d} does not exist in the normalized inventory.")

    manifest_path = batch_manifest_path(args.batch)
    template_path = batch_conjugations_path(args.batch)
    ensure_writable(manifest_path, args.force)
    ensure_writable(template_path, args.force)

    write_inventory_rows(manifest_path, manifest_rows)
    write_conjugation_rows(template_path, build_batch_template_rows(inventory_rows, args.batch))
    print(f"Wrote manifest: {manifest_path}")
    print(f"Wrote template: {template_path}")


if __name__ == "__main__":
    main()
