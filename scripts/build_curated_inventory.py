from __future__ import annotations

from pathlib import Path

from app.services.curated_conjugations import (
    normalize_legacy_inventory_rows,
    parse_legacy_verb_rows,
    validate_inventory_rows,
    write_inventory_rows,
    inventory_path,
)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    legacy_path = repo_root / "app" / "data" / "legacy_seed" / "verbs" / "1000verbs.csv"

    raw_rows = parse_legacy_verb_rows(legacy_path)
    inventory_rows = normalize_legacy_inventory_rows(raw_rows, limit=1000, batch_size=50)
    errors = validate_inventory_rows(inventory_rows)
    if errors:
        raise SystemExit("\n".join(["Normalized inventory validation failed:", *errors]))

    write_inventory_rows(inventory_path(), inventory_rows)

    unique_french = len({row.fr_infinitive for row in inventory_rows})
    unique_spanish = len({row.es_infinitive for row in inventory_rows})
    max_batch = max((row.batch for row in inventory_rows), default=0)
    print(f"Wrote normalized inventory to {inventory_path()}")
    print(f"French master verbs: {unique_french}")
    print(f"Linked Spanish infinitives: {unique_spanish}")
    print(f"Inventory rows: {len(inventory_rows)}")
    print(f"Batches: {max_batch}")


if __name__ == "__main__":
    main()
