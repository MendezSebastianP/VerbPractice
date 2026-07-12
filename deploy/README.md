# Mini PC deployment

Production runs on the mini PC as a **host-level systemd user service** (no app
container): repo at `~/VerbPractice`, Python venv, Postgres 16 in the
`verbpractice-pg` docker container, public access through the existing
Cloudflare tunnel as **https://vp.sebmendez.dev**.

## Pieces

| File | Purpose |
| --- | --- |
| `verbpractice.service` | Runs uvicorn on `0.0.0.0:8000` with `--proxy-headers`; `Restart=always` + no start-limit so it always comes back |
| `wait_for_pg.sh` | `ExecStartPre`: starts the postgres container and waits (≤30 s) for it to accept connections |
| `verbpractice-deploy.timer` | Fires the deploy check every 60 s (and 90 s after boot) |
| `verbpractice-deploy.service` | Oneshot wrapper around `autodeploy.sh` |
| `autodeploy.sh` | Fetch `origin/main`; when it differs from `.deployed-rev`: hard-reset, reinstall deps / rebuild SPA when needed, migrate, restart, health-check. The marker is written only after a healthy deploy, so **failed deploys retry every minute** instead of sticking |
| `verbpractice-health.timer` | Probes `/healthz` every 2 min |
| `verbpractice-health.service` + `healthcheck.sh` | Restarts the app if the probe fails 3× (catches hangs; skips itself while a deploy holds the lock) |

Auto-deploy is **polling-based**: push to `main` and the mini PC picks it up
within a minute. No public webhook endpoint, no secrets to rotate. Deploys are
also cache-proof: vite emits content-hashed bundle filenames and the FastAPI
shell reads them from the manifest, so browsers/Cloudflare can never serve a
stale bundle after a deploy (hashed assets are `immutable`, the shell is
`no-cache`).

## One-time install (already done)

```bash
mkdir -p ~/.config/systemd/user
cp deploy/verbpractice.service deploy/verbpractice-deploy.service deploy/verbpractice-deploy.timer \
   deploy/verbpractice-health.service deploy/verbpractice-health.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now verbpractice verbpractice-deploy.timer verbpractice-health.timer
loginctl enable-linger            # start at boot without a login
docker update --restart unless-stopped verbpractice-pg
```

`.env` on the mini PC: `APP_ENV=production`, `APP_BASE_URL=https://vp.sebmendez.dev`,
its own `SECRET_KEY`, same `DATABASE_URL`/`OPENAI_API_KEY` as dev.

## Domain wiring

- DNS: `vp.sebmendez.dev` — proxied CNAME to `<tunnel-id>.cfargotunnel.com`
  (same tunnel as kairos).
- Tunnel ingress (Zero Trust dashboard → Networks → Tunnels → public
  hostnames): `vp.sebmendez.dev` → `http://localhost:8000`.
- TLS terminates at Cloudflare; uvicorn trusts `X-Forwarded-*` only from
  `127.0.0.1` (cloudflared).

## Watching it

```bash
journalctl --user -u verbpractice -f            # app logs
journalctl --user -u verbpractice-deploy -n 50  # last deploy runs
systemctl --user list-timers                    # next poll
```

Note: unit-file changes in this directory are *not* applied automatically —
re-copy to `~/.config/systemd/user/` and `systemctl --user daemon-reload`.
