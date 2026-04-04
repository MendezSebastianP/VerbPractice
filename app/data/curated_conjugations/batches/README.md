# Batch Files

Generated files for the manual conjugation workflow live here.

- `batch_XX_manifest.csv`: derived from the normalized inventory for one 50-verb French batch
- `batch_XX_conjugations.csv`: manual conjugation entries for that batch

Review states:
- `draft`: authored but not trusted
- `reviewed`: self-reviewed and safe for QA environments
- `approved`: trusted for production import

Production imports now expect `approved` rows by default. Use reviewed imports only for QA passes.

Generate a new batch scaffold with:

```bash
python scripts/generate_conjugation_batch_template.py --batch 1
```

Validate and inspect trust coverage with:

```bash
python scripts/validate_curated_conjugations.py --batch 1 --minimum-review-status reviewed --allow-partial
python scripts/curated_review_report.py
```
