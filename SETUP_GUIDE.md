# FastAPI + SPA Setup Guide

## Quick path

```bash
make setup
make run
```

`make setup` now applies Alembic migrations before seeding.

## 1. Start PostgreSQL

```bash
docker run --name verbpractice-pg \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=verbpractice \
  -p 5432:5432 -d postgres:16
```

## 2. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
```

The photo-based Add Word flow (`/app/photo-word`) reads photographed text with
RapidOCR (PP-OCR ONNX models on CPU) — installed automatically with the Python
dependencies, no system packages needed. The first photo per language downloads
its recognition model (~15 MB) into the package cache; run
`make ocr-models` once after install to prefetch all of them so the feature
also works offline. If the models can't be fetched, `/api/words/ocr` responds
`503` and the rest of the app works normally.

The default env keeps `DATABASE_USE_NULL_POOL=true` so async Postgres behaves reliably during local development and test runs.

Context-aware word-sense selection can also run entirely on CPU. Download the
pinned quantized multilingual E5 model once:

```bash
make sense-model
```

The model is stored under `.local/models/` and is not committed. Without it,
trusted dictionary senses still work with a basic lexical ranker. Download and
import sense-linked entries for the words already in the database with:

```bash
make sense-import
```

This uses the native English, French, Spanish, and Russian Wiktionary editions
published as per-word JSONL by Kaikki. It needs internet access only while
building the local dictionary; downloaded data is cached under
`.local/dictionary/`. To import your own normalized file instead, run
`make sense-import SENSE_FILE=your-senses.jsonl`. The JSONL contract is
documented in `app/data/offline_dictionary/README.md`.

Existing lexical cache entries are backfilled as untrusted initial senses;
only dictionary imports are used for automatic contextual selection. Kaikki
translations are imported only when they can be linked to one source sense by
an explicit sense index or a unique lexical match; ambiguous mappings are
skipped. When several imported senses exist, the UI shows the model's
suggestion and lets the user switch the private lookup with one click.
Context, questions, and answers are stored only in per-user lookup rows.

## 3. Initialize schema + seed data

```bash
make migrate
python scripts/seed_from_legacy_csv.py
```

If this database already existed from an older pre-Alembic FastAPI build, adopt it and then apply the admin-role migration:

```bash
make migrate-adopt
```

Use `make migrate-stamp` only when the database already matches the current Alembic head exactly.

To start the manual conjugation workflow:

```bash
python scripts/build_curated_inventory.py
python scripts/generate_conjugation_batch_template.py --batch 1
python scripts/validate_curated_conjugations.py --batch 1 --allow-partial --minimum-review-status reviewed
python scripts/curated_review_report.py
```

This creates a demo user:
- username: `demo`
- password: `demo12345`
- admin access: enabled

Promote another user to admin:

```bash
make grant-admin USER=your_username
```

## 4. Build the SPA

```bash
make spa-build
```

This uses Dockerized Node so you do not need a local Node install just to build the client bundle.

## 5. Run

```bash
uvicorn app.main:app --reload
```

Then open:
- SPA app: `http://127.0.0.1:8000/app`
- SPA admin workbench: `http://127.0.0.1:8000/app/monitor` (admin only)
- Root redirect: `http://127.0.0.1:8000`
- Legacy fallback dashboard: `http://127.0.0.1:8000/legacy`
- Internal monitor: `http://127.0.0.1:8000/admin/monitor` (admin only)
- JSON live feed: `http://127.0.0.1:8000/admin/api/live` (admin only)
- JSON bootstrap: `http://127.0.0.1:8000/api/bootstrap`
- Health: `http://127.0.0.1:8000/healthz`
- Ready check: `http://127.0.0.1:8000/readyz`

## 6. Validate imported data and SPA

```bash
python scripts/validate_seed_data.py
python scripts/validate_curated_conjugations.py --minimum-review-status approved --allow-partial
pytest -q
make spa-check
make e2e
```

Optional browser regression pass:

```bash
make visual-install
RUN_VISUAL_TESTS=1 pytest -q tests/test_visual_regression.py
```

Operational helpers:

```bash
make health
make profile
make backup-db
make curated-report
```

Additional docs:
- `ACCESSIBILITY_AUDIT.md`
- `DEPLOYMENT.md`
