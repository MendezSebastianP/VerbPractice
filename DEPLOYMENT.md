# Deployment And Backup

> The mini PC production setup (systemd units, auto-deploy timer, Cloudflare
> tunnel at vp.sebmendez.dev) is documented in [deploy/README.md](deploy/README.md).

## Baseline Production Shape
- Run FastAPI behind a reverse proxy such as Nginx or Caddy.
- Keep PostgreSQL outside the app process and enable daily backups.
- Build the SPA bundle before deploys with `make spa-build`.
- Point health checks to `/healthz` and readiness checks to `/readyz`.
- Prefetch the photo-OCR models once after installing deps: `make ocr-models`
  (RapidOCR downloads ~15 MB per language on first use otherwise).

## Environment
- `APP_ENV=production`
- `APP_BASE_URL=https://your-domain`
- `SECRET_KEY=<strong random value>`
- `DATABASE_URL=<managed postgres url>`
- `DATABASE_USE_NULL_POOL=false`
- `LOG_LEVEL=INFO`
- `REQUEST_ID_HEADER=X-Request-ID`
- `OPENAI_API_KEY=<if AI tutor is enabled>`

## Recommended Release Flow
1. Pull the new code.
2. Rebuild the SPA bundle with `make spa-build`.
3. Reinstall Python deps with `make install`.
4. Ensure the schema is current with `make migrate`.
5. Run `make test` and `make spa-check`.
6. Restart the FastAPI service.
7. Confirm `/healthz` and `/readyz` both pass.

If you are adopting Alembic on an already-running database that came from the earlier `create_all` flow, run `make migrate-adopt` once so the baseline schema is stamped and the admin-role delta is applied. Use `make migrate-stamp` only when the live schema already matches the current Alembic head exactly.

## Reverse Proxy Notes
- Forward `X-Forwarded-For`, `X-Forwarded-Proto`, and `X-Request-ID`.
- Cache `/static/*` aggressively.
- Do not cache `/api/*`.
- Keep HTTPS termination at the proxy.
- Nginx only: raise the body limit for photo OCR uploads (`/api/words/ocr` accepts
  up to 8 MB, but Nginx defaults `client_max_body_size` to 1 MB — set it to `10m`).
  Caddy needs no change.

## Backup Strategy
- Run a nightly logical backup:

```bash
BACKUP_DIR=backups ./scripts/backup_postgres.sh
```

- Keep at least:
  - 7 daily backups
  - 4 weekly backups
  - 3 monthly backups
- Store backups off-machine if the deployment matters.

## Restore Drill
1. Create a fresh PostgreSQL database.
2. Restore the latest `.dump` file with `pg_restore`.
3. Run `make migrate` to bring the schema to the current release.
4. Start the app and confirm `/readyz`.

Example restore:

```bash
pg_restore -U postgres -d verbpractice backups/verbpractice_YYYYMMDD_HHMMSS.dump
```

## Logging And Observability
- Every request now carries a request ID in the response header.
- Access logs include method, path, status, and duration.
- Unhandled exceptions are logged with the request ID so they can be traced.

## Things Still Worth Adding Later
- External error tracking.
- Metrics export for Prometheus or an APM tool.
- Automated restore verification in CI or staging.
