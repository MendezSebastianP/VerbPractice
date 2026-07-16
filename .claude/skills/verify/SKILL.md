---
name: verify
description: Build, launch, and drive the VerbPractice app (FastAPI + Svelte SPA) to verify changes end-to-end.
---

# Verifying VerbPractice changes

## Build + launch

- SPA: `cd frontend && npm run check && npm run build` — outputs to `frontend/static/spa`, served by FastAPI at `/app` (vite base `/static/spa/`).
- DB: PostgreSQL runs in the `verbpractice-pg` docker container (`make db-up` if stopped). It is usually already running with seeded data.
- Server: `.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8123` (pick a spare port; 8000 is the dev default). Health: `curl http://127.0.0.1:8123/healthz`.

## Drive with Playwright

- Use the repo venv: `.venv/bin/python` has `playwright` (sync API). If Chromium is missing/mismatched: `.venv/bin/playwright install chromium`.
- SPA routes live under `/app` (e.g. `http://127.0.0.1:8123/app/register`).
- Register a throwaway user via `/app/register` (inputs: `input[autocomplete='username']`, two `input[type='password']`, button "Create profile"). A `demo / demo12345` account also exists.
- Words trainer (redesigned per `VerbPractice Frontend Redesign/*.dc.html`): nav "Words" → menu with `.diff-tile` difficulty tiles (first = Easy 5) → PLAY control: `.mist-button` (light/dark mist pill) or `.pg-wrap` (arcade pixel grid); Enter also fires it. Launch plays a transition (~0.8s) before `.line-input` appears.
- In session: prompt is `.prompt-word`, input is `.line-input` (submit with Enter), controls are `.kbd-action` text buttons (submit/hint/skip/finish). You don't know answers, so click the skip action; `.session-msg` shows `prompt → answer` to record and replay correctly next run.
- Session end: `.clear-card` (Stage Clear) appears with Replay (Enter) and Menu (Esc, single press) buttons. A correct final answer ends the session too — don't assume the skip button still exists.
- Reward overlays (`.fx-overlay`, from GameFx.svelte) cover the screen and block clicks; dismiss with Escape (or any click). They can queue (level-up then badges) — dismiss in a loop.
- Gamification math for fresh users: +10 XP per correct, +25 per completed session, level 2 at 100 XP — 3-4 short sessions triggers the level-up overlay; first completed session unlocks the "First Steps" badge overlay.
- Conjugation setup: go directly to `/app/training/verbs/conjugation`.
- Theme switch: dashboard `.theme-switcher` buttons (aria-labels "Sun mode"/"Moon mode"/"Arcade mode").

## Gotchas

- **Svelte scopes `@keyframes`** (renamed to `svelte-<hash>-name`). Any animation name referenced
  from an **inline `style=` attribute** (e.g. per-cell staggered delays) silently never runs —
  declare those keyframes as `@keyframes -global-name { ... }`. This bit us twice (launch tile
  dissolve + answer tile wave rendered as no-ops while looking "done").
- One element = one `animation` shorthand: toggling a `.shake` class on an element whose entrance
  animation also uses `animation:` restarts the entrance when the class is removed. Put entrance
  animations on a wrapper.
- `/app/playground` is public (no auth) — the experiment bench for new UI options.

- QA users pollute the dev DB (and its leaderboard) — use a recognizable prefix.
- `make` targets use Dockerized node for SPA builds; local `npm` in `frontend/` is faster and equivalent.
