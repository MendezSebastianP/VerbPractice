# VerbPractice

This repository now centers on the FastAPI application plus a full **single-page frontend**:

- FastAPI (async backend)
- Svelte SPA served at `/app`
- JSON API layer at `/api`
- Legacy Jinja2 + HTMX pages still available as fallback
- SQLAlchemy 2.0 + asyncpg (PostgreSQL-ready)
- SSE chat streaming
- Unified training engine (words, verbs, conjugation)
- Data-driven language definitions (FR/ES seeded in DB)
- Theme system (light/dark/arcade) with redesigned dashboard and training UI
- Session persistence and analytics in DB
- Persistent chat history + learner-aware tutor context
- Admin workbench for runtime monitoring plus word/verb/conjugation CRUD and review
- Expanded gamification: badges, combo tracking, weekly challenges, sound cues, and circle leaderboards
- Health/readiness endpoints, request ID logging, endpoint profiling, and browser screenshot regression checks
- Curated manual conjugation pipeline with normalized inventory, batch templates, validation, and import

## Quick start

1. Bootstrap the full local stack:

```bash
make setup
```

This now:
- creates `.env` if missing
- installs Python dependencies
- starts PostgreSQL
- applies Alembic migrations
- seeds legacy bootstrap data
- builds the SPA bundle

2. Run the app:

```bash
make run
```

Then open `http://127.0.0.1:8000`. The root now redirects into the SPA.

3. If you prefer the manual path, create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Or use `make install`.

4. Copy environment file and edit values:

```bash
cp .env.example .env
```

The default `.env.example` now enables `DATABASE_USE_NULL_POOL=true`, which keeps async PostgreSQL stable in local dev and in route smoke tests.

5. Apply database schema migrations:

```bash
make migrate
```

If you already have a database from an earlier pre-Alembic FastAPI build, adopt it with the baseline revision and then apply the admin-role delta:

```bash
make migrate-adopt
```

Use `make migrate-stamp` only if the database already matches the current Alembic head and you just need to register that fact.

6. Seed language + content data from existing Django CSVs:

```bash
python scripts/seed_from_legacy_csv.py
```

To build the curated manual conjugation inventory:

```bash
python scripts/build_curated_inventory.py
python scripts/generate_conjugation_batch_template.py --batch 1
python scripts/validate_curated_conjugations.py --batch 1 --allow-partial --minimum-review-status reviewed
```

7. Build the SPA bundle:

```bash
make spa-build
```

Useful endpoints while testing:
- SPA app: `http://127.0.0.1:8000/app`
- SPA admin workbench: `http://127.0.0.1:8000/app/monitor` (admin only)
- Legacy HTML fallback: `http://127.0.0.1:8000/legacy`
- Internal monitor: `http://127.0.0.1:8000/admin/monitor` (admin only)
- JSON live feed: `http://127.0.0.1:8000/admin/api/live` (admin only)
- JSON API bootstrap: `http://127.0.0.1:8000/api/bootstrap`
- Health: `http://127.0.0.1:8000/healthz`
- Ready check: `http://127.0.0.1:8000/readyz`

Seeded credentials:
- admin demo user: `demo` / `demo12345`

Promote any existing user to admin:

```bash
make grant-admin USER=your_username
```

## Data pipeline

- `scripts/seed_from_legacy_csv.py` imports:
  - `app/data/legacy_seed/words/es_fr_top1000.csv`
  - `app/data/legacy_seed/verbs/1000verbs.csv`
  - `app/data/legacy_seed/conjugations/conjugations_fixed.csv`
- The word seed CSV now supports:
  - `spanish`, `french`, `english`, `russian`
  - `spanish synonyms`, `french synonyms`, `english synonyms`, `russian synonyms`
  - a manually curated `cefr_level` (`A1` through `C2`)
- Any populated word-language columns are imported pairwise, so the seed can bootstrap:
  - ES ↔ FR
  - ES ↔ EN
  - FR ↔ EN
  - ES ↔ RU
  - FR ↔ RU
  - EN ↔ RU
- Imported records include `source` and `verified` metadata.
- Word and verb records also carry a nullable `cefr_level`. All bundled seed
  rows are manually classified; newly added content stays unclassified until
  reviewed. The rubric and current distribution are in
  [`docs/CEFR_CURATION.md`](docs/CEFR_CURATION.md).
- Curated manual conjugation source lives in:
  - `app/data/curated_conjugations/normalized_verb_inventory.csv`
  - `app/data/curated_conjugations/batches/batch_XX_conjugations.csv`
- The legacy conjugation CSV remains bootstrap data.
- Curated overlay rules are now stricter:
  - `reviewed` means structurally checked and ready for QA
  - `approved` means trusted for production import
  - `make import-curated` imports `approved` rows only by default
  - `python scripts/import_curated_conjugations.py --allow-reviewed` is available for QA environments

Useful curated commands:

```bash
make inventory
make batch-template BATCH=1
make validate-curated BATCH=1
make curated-report
make import-curated BATCH=1
```

To (re)generate the English columns in the legacy word seed CSV:

```bash
.venv/bin/python scripts/enrich_word_seed_with_english.py
```

To add another language column, use the generic enricher. Example for Russian:

```bash
.venv/bin/python scripts/enrich_word_seed_with_russian.py
```

## Tests

```bash
pytest
```

Route smoke coverage now verifies:
- SPA shell routes
- authenticated API bootstrap/dashboard/training routes
- legacy auth/training/chat routes
- internal admin monitor + live JSON feed
- starting word, verb, and conjugation sessions
- filled conjugation table submission
- chat streaming responses
- end-to-end API flows for preferences, community, rewards, health checks, and admin CRUD

SPA validation also includes:

```bash
make spa-check
make spa-build
make e2e
```

Optional heavier QA:

```bash
make visual-install
RUN_VISUAL_TESTS=1 pytest -q tests/test_visual_regression.py
```

The visual suite uses deterministic screenshot baselines stored under `tests/visual_baselines/`.

## Operations

Quick operational helpers:

```bash
make health
make profile
make backup-db
```

Supporting docs:
- `ACCESSIBILITY_AUDIT.md`
- `DEPLOYMENT.md`

The curated pipeline is covered by unit tests for:
- inventory normalization and batching
- batch template scope
- validation failures for duplicate and missing slots
- idempotent curated import with minimum review status handling
