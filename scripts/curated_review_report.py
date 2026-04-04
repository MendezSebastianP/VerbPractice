from __future__ import annotations

from app.services.curated_conjugations import (
    discover_batch_conjugation_files,
    inventory_path,
    load_conjugation_rows,
    load_inventory_rows,
    summarize_curated_batches,
)


def main() -> None:
    inventory_rows = load_inventory_rows(inventory_path())
    authored_rows = []
    for batch_file in discover_batch_conjugation_files():
        authored_rows.extend(load_conjugation_rows(batch_file))

    print("Curated batch trust report")
    print()
    print(
        f"{'Batch':>5} {'Required':>8} {'Authored':>8} {'Reviewed':>9} {'Approved':>9} "
        f"{'Auth %':>7} {'Rev %':>7} {'App %':>7} {'Ready':>7}"
    )
    print("-" * 82)
    for row in summarize_curated_batches(inventory_rows, authored_rows):
        print(
            f"{row['batch']:>5} {row['required_slots']:>8} {row['authored_slots']:>8} "
            f"{row['reviewed_slots']:>9} {row['approved_slots']:>9} {row['authored_pct']:>7} "
            f"{row['reviewed_pct']:>7} {row['approved_pct']:>7} {str(row['import_ready']):>7}"
        )


if __name__ == "__main__":
    main()
