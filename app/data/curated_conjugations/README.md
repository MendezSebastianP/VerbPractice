# Curated Conjugations

This directory holds the repo-backed source of truth for the manual conjugation pipeline.

Files:
- `normalized_verb_inventory.csv`: canonical French-first inventory, normalized to the first 1000 unique French infinitives from the legacy list.
- `batches/batch_XX_manifest.csv`: generated batch manifest for one 50-verb French batch.
- `batches/batch_XX_conjugations.csv`: manually filled conjugation rows for that batch.

Workflow:
1. `python scripts/build_curated_inventory.py`
2. `python scripts/generate_conjugation_batch_template.py --batch 1`
3. Fill `batch_01_conjugations.csv` manually.
4. `python scripts/validate_curated_conjugations.py --batch 1`
5. Review the filled rows and mark them `reviewed`.
6. `python scripts/import_curated_conjugations.py --batch 1`
