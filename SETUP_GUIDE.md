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

The photo-based Add Word flow (`/app/photo-word`) reads TV-subtitle photos with a
local Tesseract OCR install. Install the binary plus the language packs for the
four supported languages:

```bash
sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-fra tesseract-ocr-spa tesseract-ocr-rus
```

Without them, `/api/words/ocr` responds `503` and the rest of the app works normally.

The default env keeps `DATABASE_USE_NULL_POOL=true` so async Postgres behaves reliably during local development and test runs.

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
