SHELL := /bin/bash

.DEFAULT_GOAL := up

VENV_DIR ?= .venv
VENV_BIN := $(VENV_DIR)/bin
PYTHON := $(VENV_BIN)/python
PIP := $(VENV_BIN)/pip
PYTEST := $(VENV_BIN)/pytest
UVICORN := $(VENV_BIN)/uvicorn
ALEMBIC := $(VENV_BIN)/alembic
DOCKER := docker

APP_MODULE ?= app.main:app
# Bind to all interfaces by default so the app is reachable from other devices
# on the LAN (e.g. testing on your phone). Override with HOST=127.0.0.1 to
# restrict to loopback only.
HOST ?= 0.0.0.0
PORT ?= 8000
SPA_PORT ?= 5173
NODE_IMAGE ?= node:20
FRONTEND_DIR ?= frontend
PROFILE_ITERATIONS ?= 12
BACKUP_DIR ?= backups
REVISION ?=
USER ?=
BASELINE_REVISION ?= 1f460095e63c

POSTGRES_CONTAINER ?= verbpractice-pg
POSTGRES_IMAGE ?= postgres:16
POSTGRES_USER ?= postgres
POSTGRES_PASSWORD ?= postgres
POSTGRES_DB ?= verbpractice
POSTGRES_PORT ?= 5432

.PHONY: help up venv install ocr-models sense-model sense-import check-venv env db-up db-wait db-down db-logs init-db migrate migrate-adopt migrate-stamp migration seed inventory batch-template import-curated validate-curated curated-report grant-admin spa-install spa-check spa-build visual-install e2e visual-check setup run health profile backup-db test validate smoke clean

help:
	@printf "Important targets:\n"
	@printf "  make            Bootstrap everything, then start the app (default: 'up')\n"
	@printf "  make up         Full build (env + install + db + migrate + seed + SPA) then run\n"
	@printf "  make venv       Create the local virtual environment\n"
	@printf "  make install    Install app + dev dependencies into .venv\n"
	@printf "  make env        Create .env from .env.example if missing\n"
	@printf "  make db-up      Start the PostgreSQL Docker container\n"
	@printf "  make db-wait    Wait until PostgreSQL is ready to accept connections\n"
	@printf "  make db-down    Stop the PostgreSQL Docker container\n"
	@printf "  make db-logs    Follow PostgreSQL container logs\n"
	@printf "  make migrate    Apply Alembic migrations to the configured database\n"
	@printf "  make migrate-adopt Adopt an existing pre-Alembic FastAPI database, then apply deltas\n"
	@printf "  make migrate-stamp Mark an existing database as already migrated\n"
	@printf "  make sense-model Download the pinned CPU-only word-sense model\n"
	@printf "  make sense-import Import trusted Kaikki/Wiktionary senses for existing words\n"
	@printf "  make sense-import SENSE_FILE=file.jsonl Import a custom normalized sense file\n"
	@printf "  make migration REVISION='message'  Create a new Alembic migration\n"
	@printf "  make init-db    Legacy direct schema creation helper (prefer migrate)\n"
	@printf "  make seed       Import legacy CSV data into the new schema\n"
	@printf "  make inventory  Build the normalized curated verb inventory\n"
	@printf "  make batch-template BATCH=1  Generate a manifest + conjugation template for a batch\n"
	@printf "  make import-curated [BATCH=1] Import approved curated conjugation rows\n"
	@printf "  make validate-curated [BATCH=1] Validate curated batch files\n"
	@printf "  make curated-report Show authored/reviewed/approved coverage for curated batches\n"
	@printf "  make grant-admin USER=demo  Promote an existing user to admin\n"
	@printf "  make spa-install Install SPA dependencies with Dockerized Node\n"
	@printf "  make spa-check  Run Svelte + TypeScript checks for the SPA\n"
	@printf "  make spa-build  Build the SPA bundle served at /app\n"
	@printf "  make visual-install Install the Chromium browser used by screenshot regression tests\n"
	@printf "  make setup      Full local bootstrap: env + install + db + schema + seed + spa build\n"
	@printf "  make dev        Run FastAPI + Vite watcher together (auto-rebuild on .svelte changes)\n"
	@printf "  make run        Run FastAPI only on http://$(HOST):$(PORT)\n"
	@printf "  make health     Check /healthz and /readyz against the running app\n"
	@printf "  make profile    Profile the main endpoints (PROFILE_ITERATIONS=$(PROFILE_ITERATIONS))\n"
	@printf "  make backup-db  Create a PostgreSQL dump in $(BACKUP_DIR)\n"
	@printf "  make e2e        Run API end-to-end tests\n"
	@printf "  make visual-check Run browser screenshot regression tests\n"
	@printf "  make test       Run unit tests\n"
	@printf "  make validate   Run data validation script + tests\n"
	@printf "  make smoke      Import the FastAPI app as a quick startup check\n"
	@printf "  make clean      Remove Python cache files\n"

venv:
	@if [ -x "$(PYTHON)" ]; then \
		printf "Virtual environment already exists at $(VENV_DIR)\n"; \
	else \
		python3 -m venv $(VENV_DIR); \
	fi

install: venv
	$(PIP) install -e '.[dev]'

ocr-models: check-venv
	$(PYTHON) -c "from app.services.ocr_service import OCR_LANG_BY_CODE, _get_engine; \
	[_get_engine(key) for key in dict.fromkeys(OCR_LANG_BY_CODE.values())]; \
	print('OCR models ready.')"

sense-model: check-venv
	$(PYTHON) scripts/download_offline_sense_model.py

sense-import: migrate
	@if [ -n "$(SENSE_FILE)" ]; then \
		$(PYTHON) scripts/import_offline_senses.py "$(SENSE_FILE)"; \
	else \
		$(PYTHON) scripts/import_kaikki_senses.py; \
	fi

check-venv:
	@if [ ! -x "$(PYTHON)" ]; then \
		printf "Virtual environment is missing. Run 'make install' first.\n"; \
		exit 1; \
	fi

env:
	@if [ -f .env ]; then \
		printf ".env already exists\n"; \
	else \
		cp .env.example .env; \
		printf "Created .env from .env.example\n"; \
	fi

db-up:
	@if docker ps -a --format '{{.Names}}' | grep -qx '$(POSTGRES_CONTAINER)'; then \
		docker start $(POSTGRES_CONTAINER); \
	else \
		docker run --name $(POSTGRES_CONTAINER) \
			-e POSTGRES_USER=$(POSTGRES_USER) \
			-e POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) \
			-e POSTGRES_DB=$(POSTGRES_DB) \
			-p $(POSTGRES_PORT):5432 \
			-d $(POSTGRES_IMAGE); \
	fi

db-wait:
	@printf "Waiting for PostgreSQL to become ready"
	@for i in $$(seq 1 30); do \
		if docker exec $(POSTGRES_CONTAINER) pg_isready -U $(POSTGRES_USER) -d $(POSTGRES_DB) >/dev/null 2>&1; then \
			printf "\nPostgreSQL is ready.\n"; \
			exit 0; \
		fi; \
		printf "."; \
		sleep 1; \
	done; \
	printf "\nPostgreSQL did not become ready in time.\n"; \
	exit 1

db-down:
	@if docker ps -a --format '{{.Names}}' | grep -qx '$(POSTGRES_CONTAINER)'; then \
		docker stop $(POSTGRES_CONTAINER); \
	else \
		printf "Container $(POSTGRES_CONTAINER) does not exist\n"; \
	fi

db-logs:
	docker logs -f $(POSTGRES_CONTAINER)

init-db: check-venv db-up db-wait
	$(PYTHON) -m app.db.init_db

migrate: check-venv db-up db-wait
	$(ALEMBIC) upgrade head

migrate-adopt: check-venv db-up db-wait
	$(ALEMBIC) stamp $(BASELINE_REVISION)
	$(ALEMBIC) upgrade head

migrate-stamp: check-venv db-up db-wait
	$(ALEMBIC) stamp head

migration: check-venv db-up db-wait
	@if [ -z "$(REVISION)" ]; then \
		printf "Provide a revision message, for example: make migration REVISION='add admin roles'\n"; \
		exit 1; \
	fi
	$(ALEMBIC) revision --autogenerate -m "$(REVISION)"

seed: migrate
	$(PYTHON) scripts/seed_from_legacy_csv.py

inventory: check-venv
	$(PYTHON) scripts/build_curated_inventory.py

BATCH ?=

batch-template: check-venv
	@if [ -z "$(BATCH)" ]; then \
		printf "Provide a batch number, for example: make batch-template BATCH=1\n"; \
		exit 1; \
	fi
	$(PYTHON) scripts/generate_conjugation_batch_template.py --batch $(BATCH)

import-curated: migrate
	@if [ -n "$(BATCH)" ]; then \
		$(PYTHON) scripts/import_curated_conjugations.py --batch $(BATCH); \
	else \
		$(PYTHON) scripts/import_curated_conjugations.py; \
	fi

validate-curated: check-venv
	@if [ -n "$(BATCH)" ]; then \
		$(PYTHON) scripts/validate_curated_conjugations.py --batch $(BATCH); \
	else \
		$(PYTHON) scripts/validate_curated_conjugations.py; \
	fi

curated-report: check-venv
	$(PYTHON) scripts/curated_review_report.py

grant-admin: check-venv
	@if [ -z "$(USER)" ]; then \
		printf "Provide a username, for example: make grant-admin USER=demo\n"; \
		exit 1; \
	fi
	$(PYTHON) scripts/grant_admin.py $(USER)

spa-install:
	$(DOCKER) run --rm \
		-u $$(id -u):$$(id -g) \
		-v $(CURDIR)/$(FRONTEND_DIR):/app \
		-w /app \
		$(NODE_IMAGE) \
		bash -lc "npm install"

spa-check: spa-install
	$(DOCKER) run --rm \
		-u $$(id -u):$$(id -g) \
		-v $(CURDIR)/$(FRONTEND_DIR):/app \
		-w /app \
		$(NODE_IMAGE) \
		bash -lc "npm run check"

spa-build: spa-install
	$(DOCKER) run --rm \
		-u $$(id -u):$$(id -g) \
		-v $(CURDIR)/$(FRONTEND_DIR):/app \
		-w /app \
		$(NODE_IMAGE) \
		bash -lc "npm run build"

visual-install: check-venv
	$(PYTHON) -m playwright install chromium

setup: env install db-up seed spa-build
	@printf "VerbPractice is ready.\n"

# Default target: bring the whole app up from a clean checkout in one command.
# `setup` builds everything (env, deps, database, migrations, seed data, SPA
# bundle); then we hand off to `run` to start the server. Both `setup` and the
# seed step are idempotent, so re-running `make` is safe.
up: setup
	@printf "\nStarting VerbPractice on http://$(HOST):$(PORT) (Ctrl+C to stop)...\n"
	@$(MAKE) run

dev: check-venv db-up db-wait migrate
	@printf "Dev mode: FastAPI + Svelte auto-builder running — refresh browser after saves (Ctrl+C stops both)\n"
	@$(UVICORN) $(APP_MODULE) --reload --host $(HOST) --port $(PORT) & \
	UVICORN_PID=$$!; \
	node $(FRONTEND_DIR)/watch.mjs; \
	kill $$UVICORN_PID 2>/dev/null; wait $$UVICORN_PID 2>/dev/null; true

run: check-venv
	$(UVICORN) $(APP_MODULE) --reload --host $(HOST) --port $(PORT)

HEALTH_HOST ?= 127.0.0.1

health:
	curl -fsS http://$(HEALTH_HOST):$(PORT)/healthz && printf "\n"
	curl -fsS http://$(HEALTH_HOST):$(PORT)/readyz && printf "\n"

profile: check-venv
	$(PYTHON) scripts/profile_endpoints.py --iterations $(PROFILE_ITERATIONS)

backup-db:
	BACKUP_DIR=$(BACKUP_DIR) POSTGRES_CONTAINER=$(POSTGRES_CONTAINER) POSTGRES_USER=$(POSTGRES_USER) POSTGRES_DB=$(POSTGRES_DB) bash scripts/backup_postgres.sh

e2e: check-venv
	$(PYTEST) -q tests/test_e2e_flows.py

visual-check: check-venv spa-build
	RUN_VISUAL_TESTS=1 $(PYTEST) -q tests/test_visual_regression.py

test: check-venv
	$(PYTEST) -q

validate: check-venv
	$(PYTHON) scripts/validate_seed_data.py
	$(PYTHON) scripts/validate_curated_conjugations.py --minimum-review-status approved --allow-partial
	$(PYTEST) -q
	$(MAKE) spa-check

smoke: check-venv
	$(PYTHON) -c "from app.main import app; print(f'FastAPI app loaded: {app.title}')"

clean:
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	find . -name '*.pyc' -delete
