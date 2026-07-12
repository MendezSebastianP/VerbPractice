# Frontend Redesign — Follow-up for Fable

Context: Claude Code applied the design direction from `VerbPractice Frontend Redesign/` (the
Clean/"Frost" light theme and the Arcade dark theme) to the real Svelte SPA in `frontend/`. The
`.dc.html` files there were prototypes built with Claude's design-canvas tool, not something we
ship — they were translated into `frontend/src/app.css` design tokens + per-page Svelte/Tailwind
markup. This file lists what was *not* pixel-matched or fully built, and why, so a follow-up Fable
session has a concrete punch list instead of having to re-diff the whole app.

> **Update (2026-07-11, Fable session):** the §4 "real gaps" and §5 quick wins below are now
> built and verified end-to-end (Playwright drive: fresh user → sessions → level-up → community).
> Done items are marked ✅ DONE with notes; the rest of the list is unchanged. New code:
> `lib/profile.ts` (live profile store), `lib/fx.ts` + `components/GameFx.svelte` (reward
> effects layer), `lib/badges.ts` (icon slug → emoji), `pages/CommunityPage.svelte` (+ route +
> nav link). A repo verify skill now exists at `.claude/skills/verify/SKILL.md`.

> **Update 3 (2026-07-11, third Fable pass):** user feedback round. The launch transition was
> "still wrong" — root cause: Svelte scopes `@keyframes`, so the tile dissolve/answer-wave
> animations referenced from inline styles silently never ran (the overlay popped fully-formed).
> Fixed with `-global-` keyframes; the tile dissolve is now THE launch transition in **all**
> themes (theme-tinted palettes) and the vignette tile wave plays on right/wrong in all themes.
> Also: removed the floating "+N XP" text (covered the prompt; nav counter still ticks), Home
> redesigned as a tall single column (stage cards with themed Play controls, slim play log,
> compact queue, settings last), Add Word's primary action is now the themed TRANSLATE control,
> every user page is a ≤720px tall column (phone-friendly; two-row topbar under 900px), and a
> **public `/playground`** route (no login) hosts experiments: 3 correct-answer feedback options
> and 3 logo options awaiting a pick. ~~The green "Correct!" text stays until an option is
> chosen.~~ **Picked & shipped:** feedback option A ("Check draw" — underline surge + self-drawing
> checkmark, no text on correct) and logo option 2 ("VP monogram" — badge with hover notch-fill in
> the nav bar + SVG favicon). Both marked "✓ shipped" in /playground.

> **Update 2 (2026-07-11, second Fable pass):** the user flagged that the first pass did not
> apply the actual designs (play button, launch transition, etc.). Root cause: `Clean Mode.dc.html`
> and `VerbPractice App.dc.html` are the **final integrated designs** (interactive prototypes with
> the chosen effects built in); only the two "Options" files are stale galleries. The Words flow
> and dashboard were re-ported from the real designs — see the rewritten §1 below, the Words
> trainer rebuild (Word Rush menu with sliding difficulty selector + stars, dropdown language
> selects, side progress rails, underline input, Stage Clear screen with score/dots/Replay/Menu),
> and the two-column dashboard (stage cards + play log | player console + queue). Verified in both
> themes with Playwright screenshots against the mockups.

## 1. Animation/interaction choices — ✅ RESOLVED (2026-07-11, second Fable pass)

**Correction to the earlier record:** the two "Options" files are indeed old A/B exploration
galleries, but the *final choices were already integrated* into the two main design files —
`Clean Mode.dc.html` (light) and `VerbPractice App.dc.html` (arcade), which link to each other as
the mode toggle. The first pass missed this and shipped generic defaults. The second pass ported
the real designs into `TranslationPage.svelte` + `PlayMist.svelte` / `PlayGrid.svelte`:

- ✅ **PLAY control** — light/dark: the mist-wipe canvas pill (pointer wipes the frost, mist
  slowly regrows, click releases falling droplets). Arcade: the 3D-tilted 10×4 pixel grid with
  pointer-proximity glow and a blinking "CLICK THE GRID TO START" caption.
- ✅ **Launch transition ("after pushing play")** — light/dark: droplet splash → menu blurs out
  (`focusOut`) → session blurs in (`focusIn`). Arcade: full-screen pixel-dissolve overlay
  (16×10 purple cells, radial stagger) that covers the launch and fades to reveal the session
  (drop-in scale entrance). The API call runs behind the effect.
- ✅ **Answer feedback ("liquid glass" wave)** — light/dark: the masked radial wave-ring wash
  (blue on correct, rose on wrong). Arcade: the 22×11 cell-wave ripple + neon border flash +
  particle burst at the input on correct, prompt **glitch** (RGB-split skew) on wrong. Card shake
  on wrong in both (subtle clean / violent arcade). These layer with the GameFx XP pops.
- ✅ **Arcade grid-floor footer** (animated perspective grid) and a clean "water line" footer
  strip — added app-wide via `App.svelte` (`.page-floor`).
- **Page transitions between nav routes** (`Transition Options.dc.html` §11/§12): still the plain
  140ms crossfade (12a) + the sliding nav pill, which together already match "12b + 12a combine
  well". The only genuinely still-open taste decision from the galleries.

## 2. Theme-system decisions that need a sanity check

- **Dark theme has no mockup at all.** Built by extrapolating report.md §9.5's "Dark / Focus /
  Night" table. Worth a real Fable pass if Dark should have its own personality rather than being
  "Light's dark twin." *(Still open.)*
- **Arcade's accent hue changed** from green/cyan to violet/purple (`#a78bfa`/`#7c3aed`) to match
  the mockup and report.md. Flag if unwanted. *(Unchanged.)*
- ✅ **DONE — `--xp` gold token now has a real home.** The nav bar renders a persistent profile
  cluster (streak flame 🔥 + `Lv.N` chip + gold XP counter) on every page, and the same gold is
  used by the floating "+N XP" text, leaderboard XP columns, and legendary badge borders.

## 3. Pages with no dedicated mockup (generic design-system treatment only)

Unchanged — these still deserve bespoke design passes:

- **Add Word** (`AddWordPage.svelte`) — the richest page in the app, never mocked up.
- **AI Tutor / Chat** (`ChatPage.svelte`) — same.
- **Conjugation tables** (`ConjugationPage.svelte`) — the most visually complex remaining surface;
  a bespoke pass here would probably pay off more than anywhere else on this list. (Its setup
  screen did get the Easy/Normal/Insane chip treatment, see §5 ✅.)
- **Admin/Monitor workbench** (`MonitorPage.svelte`) — financials tab is all raw number tables and
  would benefit from real charts (use the `dataviz` skill when you get to it).
- ~~Sets~~ (`SetsPage.svelte`) — reachable since the previous pass; still no bespoke design.

## 4. Real gaps found while reading the code (not just missing polish)

- **Sets wasn't reachable.** Fixed in the previous pass (nav link + real link from Words setup).
- ✅ **DONE — Community/leaderboard UI.** New `CommunityPage.svelte` at `/community` (nav link
  added): weekly challenge card with progress bar, global + weekly leaderboards (medals for top 3,
  your row highlighted), friends-circle management (add/remove by username, error toasts from the
  API surface cleanly), circle leaderboard, unlocked-badge wall with rarity borders, and a recent-XP
  ledger. Uses the existing `api.community` + friend endpoints; no backend changes were needed.
- ✅ **DONE — Persistent streak/level/XP indicator.** `lib/profile.ts` holds a `profile` store
  seeded from the boot payload, re-synced from the dashboard payload, and bumped optimistically as
  rewards land, so the nav readout updates live mid-session. Flame is greyscale at 0 days and grows
  at 5/14-day tiers (pulses in arcade); XP hides below 900px to keep the top bar usable on phones.
  Note: streak/level in the store are *display* state — server truth re-syncs on dashboard load.
- ✅ **DONE — Gamification "loud mode" (report.md §9.6).** Global `GameFx.svelte` layer mounted in
  `App.svelte`, driven by an event store (`lib/fx.ts`) from both trainers:
  - Floating "+N XP" pops anchored to the answer input (gold; pixel font + glow + spark particles
    in arcade).
  - Level-up: full-screen overlay, "LEVEL UP!" + particle burst; tap/Esc/Enter or 2.6s auto-dismiss.
  - Badge unlock: loot-box card-flip reveal with rarity-colored borders (common/rare/epic/legendary).
    Overlays queue so level-up and badges never fight for the screen.
  - Arcade-only "miss" flash (100ms red overlay) on wrong answers.
  - Backend badge/challenge icon slugs (`sprout`, `flame`, `star`, `forge`, `grid`, `flag`, `bolt`,
    `matrix`, `spark`) map to emoji via `lib/badges.ts` — they used to render as literal text.
  - Bug fixed along the way: the session-complete bonus (+25 XP) and badge unlocks also arrive on
    the final *reveal* response, not just correct answers — the reveal path now applies rewards too.
  - `prefers-reduced-motion` disables particles/animations.
  - Sound stays the existing 4 synth cues in `sound.ts` — the richer sample pack is still open.

## 5. Minor consistency follow-ups

- ✅ **DONE — Conjugation queue-length chips** (3/5/8 verbs) reframed as Easy/Normal/Insane to
  match the Words trainer; the `length-chip` styles moved from TranslationPage's scoped CSS into
  `app.css` so both pages share them.
- Both mockups are fixed-width desktop canvases; the single 900px breakpoint was preserved. A real
  mobile pass for the gamified session screen still needs design work. *(Still open.)*
- The Words/Verb-translation trainer now matches the final designs, but **ConjugationPage still
  uses the old presentation** (horizontal progress bar, boxed inputs) — no mockup covers it; §3's
  bespoke-pass note applies. Same for the "session finished" prompt there.
- The dashboard mode-card eyebrows read "Stage 01 · <pair_label>"; the backend pair_label uses
  "<>" where the mockup shows "↔" — cosmetic, backend-side string.
- Renamed "LexArena" → "VerbPractice" in user-facing copy in the previous pass. Flag if "LexArena"
  was actually the intended final brand. *(Unchanged; `lexarena-theme` localStorage key and the npm
  package name still carry the old name internally.)*
