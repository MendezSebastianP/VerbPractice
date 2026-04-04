# VerbPractice — Deep Application Report

## 1. What This App Is

VerbPractice is a **multilingual vocabulary and verb conjugation trainer** built with Django. It helps users learn French and Spanish through three training modes: word translation practice, verb conjugation drills, and an AI chat tutor. The app uses a **spaced-repetition-inspired probabilistic algorithm** that adapts to each user's weaknesses — words/verbs you struggle with appear more often.

The app currently supports **French ↔ Spanish** only, with plans to add English and Russian.

---

## 2. Current Architecture

### Stack
| Layer | Technology |
|-------|-----------|
| Backend | Django 5.0.7 (Python) |
| Database | SQLite3 |
| WebSocket | Django Channels + Daphne (ASGI) + Redis |
| Frontend | Django templates + HTMX + vanilla JS + CSS |
| AI | OpenAI API (GPT-3.5-turbo) via WebSocket streaming |
| Conjugation generation | mlconjug3 (ML-based conjugator) |
| Accent handling | Unidecode + unicodedata |

### Django Apps (5 apps)

| App | Purpose | Models |
|-----|---------|--------|
| `users` | Auth (register, login, logout) | Extends Django User |
| `verbs` | Verb translation practice (flashcard style) | `Verb`, `UserVerb`, `UserConjugation` |
| `word_training` | Vocabulary practice (flashcard style) | `Word`, `UserWord` |
| `verbs_conjugation` | Conjugation table drills | `VerbConjugation`, `ConjugationSession` |
| `chat` | AI chat tutor | No models (WebSocket consumer) |

### Data Sources
- `verbs/data/1000verbs.csv` — 1000 French verbs with Spanish translations
- `verbs/data/11verbs.csv` / `20verbs.csv` — Starter verb sets
- `word_training/data/es_fr_top1000.csv` — Top 1000 Spanish-French words with synonyms
- `verbs_conjugation/data/conjugations.csv` — Pre-generated conjugation forms (via mlconjug3)

---

## 3. Features in Detail

### 3.1 Word Practice (`word_training` app)

**How it works:**
1. User starts with 10 unlocked words from the top-1000 list
2. User picks session length (implicit in session flow) and direction (FR→ES or ES→FR)
3. System selects words using **weighted random sampling without replacement** — higher probability = more likely to appear
4. For each word: show prompt, user types answer, system grades it
5. Grading is 3-tier:
   - Exact match → multiplier `0.7` (word gets easier, appears less)
   - Synonym match → multiplier `0.8` (partial credit)
   - Wrong → multiplier `1.3` (word gets harder, appears more)
6. After session: if average probability of top-5 words drops below threshold (750), unlock 3 new words
7. Hints available: progressive letter reveal

**Data model:** `Word` has `word`, `translation`, `word_sy` (synonyms), `translation_sy`. `UserWord` tracks per-user state: `probability` (1000 default), `unlocked`, `times_correct`.

### 3.2 Verb Translation Practice (`verbs` app)

**Nearly identical to word practice** but for verb infinitives. Same algorithm, same unlock logic. Only difference: no synonym support — grading is binary (correct/wrong, multipliers 0.7/1.3).

**Data model:** `Verb` has `infinitive` and `translation`. `UserVerb` has same fields as `UserWord`.

### 3.3 Verb Conjugation Practice (`verbs_conjugation` app)

**How it works:**
1. User configures session: language (FR/ES), difficulty level (easy/medium/hard/custom), fill level (80%/20%/0% pre-filled), and tenses
2. System selects 5 verbs using weighted sampling based on **aggregated tense difficulty scores**
3. For each verb: show conjugation table with some cells pre-filled (based on fill level)
4. User fills blanks for all 6 pronouns
5. Grading: accent-normalized comparison (é→e, ñ→n, ç→c)
6. Score update per tense: `new_score = current_score * avg_multiplier` where each pronoun contributes 0.7 (correct) or 1.5 (wrong)
7. Overall score = average of all practiced tense scores
8. Bounds: scores clamped to [20, 100,000]
9. Unlock check: if worst-5 practiced verbs average score < 700, unlock 3 new verbs

**Tense organization by difficulty:**

French:
- Easy: Présent, Futur, Passé composé
- Medium: Imparfait, Conditionnel présent, Impératif
- Hard: Subjonctif présent, Passé Simple, Subjonctif imparfait

Spanish:
- Easy: Presente, Futuro, Pretérito perfecto compuesto
- Medium: Pretérito imperfecto, Condicional, Imperativo, Futuro perfecto
- Hard: Subjuntivo presente, Pretérito perfecto simple, Pretérito pluscuamperfecto

**Data model:** `VerbConjugation` stores each individual conjugated form (verb + language + mood + tense + pronoun → conjugated_form). `UserConjugation` stores per-verb per-language progress with a JSON field for tense-level scores. `ConjugationSession` stores session config (not linked to user).

### 3.4 AI Chat Tutor (`chat` app)

**How it works:**
1. WebSocket connection via Django Channels + Redis
2. User sends messages, system streams responses from OpenAI GPT-3.5-turbo
3. Chat history maintained in-memory on the WebSocket consumer
4. Currently a generic assistant — no integration with user's learning data
5. Mode switching (`/mode verb`, `/mode word`) is commented out / unfinished

**Planned vision:** AI uses knowledge of user's weak words/tenses to create targeted exercises. Output would be structured (points, scores) that feed back into the probability system. If user struggles with a word or tense, AI insists on testing it.

---

## 4. Core Algorithms

### 4.1 Weighted Random Selection (Used Everywhere)

```
Input: pool of (item_id, probability_weight) pairs, desired count N
1. Normalize weights to sum to 1.0
2. For each pick (up to N):
   a. Generate random float r in [0, 1)
   b. Walk through pool accumulating weights until acc >= r
   c. Select that item, remove from pool
   d. Re-normalize remaining weights
Output: list of N selected item IDs
```

Higher probability = more likely to be picked. Items the user struggles with get higher probability, so they appear more often. This is the heart of the spaced repetition system.

**Complexity:** O(N * pool_size) — fine for sessions of 5-20 items from pools of 10-1000.

### 4.2 Probability Adjustment

| Context | Correct | Synonym | Wrong |
|---------|---------|---------|-------|
| Word practice | ×0.7 | ×0.8 | ×1.3 |
| Verb translation | ×0.7 | N/A | ×1.3 |
| Conjugation (per pronoun) | ×0.7 | N/A | ×1.5 |

Bounds: probability clamped to [20, 100,000]. Default starting value: 1000.

### 4.3 Unlock Logic

**Word/Verb translation:** Average probability of top-5 performing items < 750 → unlock 3 new items.

**Conjugation:** Average overall_score of worst-5 practiced verbs < 700 → unlock 3 new verbs.

Note: "top-5 by probability" in translation means the 5 with lowest difficulty (best performing), since they sort `-probability` and lower = better mastered. The conjugation unlock sorts differently (worst first), checking if the user is good enough even at their weakest verbs.

### 4.4 Accent Normalization

Used for grading: both user input and correct answer are normalized before comparison.
- Unicode NFD decomposition to separate base chars from combining marks
- Strip all combining marks (category `Mn`)
- Special cases: ñ→n, ç→c, œ→oe, æ→ae
- Lowercase + strip whitespace

This means "être" matches "etre", "niño" matches "nino", etc.

---

## 5. Current Data Pipeline

### Words
- Source: `es_fr_top1000.csv` (Spanish-French, with synonyms)
- Loaded directly into `Word` model
- No management command found for loading (likely done manually or via Django admin/shell)

### Verbs
- Source: `1000verbs.csv` (French infinitive + Spanish translation)
- Loaded into `Verb` model

### Conjugations
- Generated using `mlconjug3` library (ML-based French/Spanish conjugator)
- Management command: `generate_conjugations_fixed` → outputs CSV
- Management command: `load_conjugations_fixed` → imports CSV into `VerbConjugation`
- Shortcut command: `init_verbs` → generates + loads 11 essential verbs in one step
- Error logs saved to `conjugation_errors_*.txt`

### Data Quality Issues
- mlconjug3 has known inaccuracies for irregular verbs
- Multiple fix iterations documented (error files, `CONJUGATION_FIX_REPORT.md`)
- Missing conjugations for core verbs (être, avoir, aller) required manual fixes
- ~10% error rate on auto-translated word lists makes the app unreliable

---

## 6. Frontend Architecture

- **Base template:** `layout.html` with navbar (Home, Verbs, Words, Conjugation, Chat, Login/Register)
- **Styling:** Single `style.css` with gradient backgrounds, custom button class (`.button-68`)
- **Interactivity:** HTMX for partial page updates + vanilla JS for conjugation table, chat, and form dynamics
- **Chat:** WebSocket with streaming response rendering (chunks appended to placeholder div)
- **Conjugation UI:** AJAX-driven — fetch verb via `/api/get-verb/`, submit via `/api/submit-answers/`, render table client-side
- **No frontend framework** — everything is server-rendered with sprinkles of JS

---

## 7. Weaknesses and Pain Points

### 7.1 Architecture

| Issue | Details |
|-------|---------|
| **Massive code duplication** | `verbs/services.py` and `word_training/services.py` are nearly identical. `TrainingEngine`, `preselect_*`, `add_new_*`, `init_user_*` are copy-pasted with minor name changes. |
| **Scattered model ownership** | `UserConjugation` lives in `verbs/models.py` but is consumed by `verbs_conjugation/views.py`. `VerbConjugation` lives in `verbs_conjugation/models.py` but is imported by `verbs/services.py`. Circular dependency pattern. |
| **No unified "language" concept** | Language is hardcoded as `'FR'`/`'ES'` strings scattered across views, services, and templates. Adding EN or RU means touching dozens of files. |
| **Session state fragility** | Training state stored in Django session (dict in DB). No model to track session history, no recovery from corruption, no analytics. |
| **`ConjugationSession` model is orphaned** | It exists in models but is never actually used in views — session config goes into `request.session` instead. |
| **No user profile or dashboard** | No way to see progress over time, streaks, weak areas, or learning stats. |
| **Mood-tense mapping duplicated 4 times** | The same `mood_mapping` dict is defined in `verbs/services.py`, `verbs_conjugation/views.py` (twice), and implicitly in the tense level definitions. |

### 7.2 Data Quality

| Issue | Details |
|-------|---------|
| **~10% translation error rate** | Auto-translated word lists (likely via `translate` or similar library) produce wrong translations. Unacceptable for a learning tool. |
| **mlconjug3 inaccuracies** | ML-based conjugator misses irregular forms. Required multiple fix rounds and manual corrections. |
| **No validation pipeline** | No automated way to verify translations or conjugations are correct. Errors discovered only when users encounter them. |
| **CSV as source of truth** | Conjugation data lives in CSV files. DB can be rebuilt from CSV, but CSV edits are manual and error-prone. |
| **No provenance tracking** | Can't tell which translations were human-verified vs auto-generated. |

### 7.3 Scalability

| Issue | Details |
|-------|---------|
| **SQLite** | Single-writer, no concurrent access. Fine for single user, breaks under load. |
| **In-memory chat history** | Chat messages stored on WebSocket consumer instance. Lost on disconnect, no persistence, no multi-device. |
| **No caching** | Redis is used only for Channels. No caching of conjugation lookups, user state, or frequently accessed data. |
| **Synchronous views** | All training views are synchronous Django views. The conjugation API does multiple DB queries per request with no optimization. |

### 7.4 UX

| Issue | Details |
|-------|---------|
| **No mobile optimization** | CSS has basic responsive styles but no mobile-first design. Conjugation table is especially problematic on small screens. |
| **Fill level is cosmetic** | The "80% filled" difficulty setting only pre-fills cells in the UI — backend still grades all pronouns. No server-side enforcement. |
| **Debug info in production** | `training_session` view always includes `debug_info` with internal scores and config. Many `print()` statements throughout views. |
| **No keyboard navigation** | Conjugation table requires mouse clicks. No Tab-through-cells, no Enter-to-submit flow. |
| **No progress feedback between sessions** | User has no idea how they're improving over time. |

### 7.5 Security

| Issue | Details |
|-------|---------|
| **`@csrf_exempt` on `submit_answers`** | CSRF protection disabled on the answer submission endpoint. |
| **No rate limiting** | API endpoints have no throttling. |
| **OpenAI key in settings** | Loaded from `.env` (good) but no key rotation or usage limits. |
| **No input sanitization on chat** | User messages go directly to OpenAI without any filtering. |

---

## 8. What Works Well

Despite the issues above, several things are solid foundations worth preserving:

- **The probability algorithm is sound.** Weighted random selection with dynamic re-normalization is an effective approach to spaced repetition. The multiplier system (0.7/1.3/1.5) creates a natural learning curve.
- **The unlock system is well-designed.** Progressive unlock prevents overwhelm. The threshold-based check (top-5 average) ensures users demonstrate competence before getting new material.
- **Accent normalization is thorough.** The NFD-based approach with special character handling is correct and prevents frustrating false negatives.
- **The conjugation data model is flexible.** Storing individual conjugated forms (verb + mood + tense + pronoun) allows arbitrary tense/mood combinations.
- **HTMX was a good choice for the training flow.** Partial page updates make the flashcard experience snappy without a full SPA framework.
- **The tense difficulty tiering is pedagogically correct.** Easy/medium/hard tense groupings match real-world usage frequency.

---

## 9. Refactor Ideas and Considerations

### 9.1 Solving the Data Quality Problem

This is the **#1 blocker**. Options:

**Option A: AI Agent Pipeline**
- Use GPT-4 / Claude to generate translations and conjugations
- Batch process: send verb list → get structured JSON back with all conjugations
- Pros: High accuracy for common languages, handles irregular verbs well, can do EN/RU too
- Cons: Cost (tokens), needs validation layer, API rate limits
- Hybrid approach: AI generates → human spot-checks a sample → flag confidence levels

**Option B: Web Scraping (WordReference, Wiktionary)**
- Scrape conjugation tables from WordReference (FR, ES, EN)
- Wiktionary has structured data for Russian conjugations
- Pros: Human-verified data, free, comprehensive
- Cons: Fragile (site structure changes), legal gray area, rate limiting, parsing complexity
- Note: WordReference has API-unfriendly ToS

**Option C: Structured Linguistic Databases**
- Use existing open datasets: Lexique (French), DRAE data (Spanish), OpenRussian.org
- Wiktionary dumps (structured XML with conjugation templates)
- UniMorph project (morphological data for 100+ languages)
- Pros: Free, structured, linguistically validated
- Cons: Integration work, format varies by source

**Recommended approach: C + A.** Use structured databases (UniMorph, Wiktionary dumps) as primary source, with AI as fallback/validator for gaps. Store a `verified` flag on each entry.

### 9.2 Language Extensibility

Current approach of hardcoding `'FR'`/`'ES'` everywhere must be replaced with:

- A `Language` model or config that defines: code, name, pronoun set, tense definitions, difficulty tiers, mood mappings
- All language-specific data (tense names, moods, pronouns, difficulty levels) should be data-driven, not code-driven
- The algorithm layer should be completely language-agnostic — it only sees scores and probabilities

### 9.3 Unifying the Training Engine

The duplicated `TrainingEngine` in verbs and words should become one generic engine:

```
GenericTrainingEngine(user, item_type, direction)
  - preselect(count) → weighted random selection
  - grade(answer, correct, synonyms?) → multiplier
  - update_score(item_id, multiplier)
  - check_unlock()
```

Both `Word` and `Verb` implement a common interface (prompt field, answer field, synonyms).

### 9.4 Stack Decision: Two Best Options

Since the refactor is AI-assisted, the migration cost of a full stack change is low. Both options below share a common foundation:

**Shared across both stacks:**
- **Python** — your language, no reason to leave it
- **PostgreSQL** — replaces SQLite. Concurrent access, native JSON fields, full-text search, production-ready. Non-negotiable upgrade.
- **SQLAlchemy 2.0 + asyncpg** — async ORM, mature, well-documented, FastAPI's standard pairing. Alembic for migrations.
- **TailwindCSS** — utility-first CSS. Eliminates writing custom CSS for every element. Mobile-first responsive design out of the box. Perfect for AI-assisted development (declarative classes, no naming decisions).
- **Pydantic v2** — data validation for all API inputs/outputs. Shared models between API layer and DB layer.
- **The core algorithms** — probability selection, multiplier scoring, unlock logic, accent normalization. These are pure Python, framework-independent, and they work.

---

#### Stack A: FastAPI + Jinja2 + HTMX + Alpine.js (Recommended)

```
Browser ←→ FastAPI (async Python)
              ├── Jinja2 templates (server-rendered HTML)
              ├── HTMX (partial page swaps, no full reloads)
              ├── Alpine.js (client-side state: conjugation table, form logic)
              ├── SSE (Server-Sent Events for AI chat streaming)
              ├── TailwindCSS (styling)
              ├── SQLAlchemy 2.0 + asyncpg (PostgreSQL)
              └── Pydantic v2 (validation)
```

**How it works:**
- FastAPI serves both HTML pages (via Jinja2) and JSON API endpoints. One server, one process.
- HTMX handles navigation and training flows — click "next word" → server returns HTML fragment → HTMX swaps it in. No JS needed for most interactions.
- Alpine.js handles the few places that need real client-side state: the conjugation table (filling cells, tracking which are answered), session config form (dynamic tense selection), keyboard shortcuts.
- AI chat uses **SSE** (Server-Sent Events) instead of WebSocket. FastAPI has native `StreamingResponse` — you just `yield` chunks as the AI generates them. No Redis, no Channels, no WebSocket infrastructure. The browser uses `EventSource` API (3 lines of JS). This is dramatically simpler than the current Django Channels + Redis + Daphne setup.
- All training endpoints are async — DB queries don't block other requests.

**Why this stack:**

| Advantage | Details |
|-----------|---------|
| **Simplest architecture** | One server, one process, no Redis, no separate WebSocket layer. Everything is FastAPI. |
| **Async by default** | Every route is `async def`. AI streaming, DB queries, and HTTP all non-blocking. Django needs Channels/Daphne for this. |
| **HTMX = fast UX without SPA complexity** | Server renders HTML, HTMX swaps fragments. The training flashcard flow feels instant. No JS bundle, no build step, no hydration. |
| **SSE replaces WebSocket+Redis** | For AI chat streaming, SSE is simpler and sufficient. The browser reconnects automatically. No Redis dependency. |
| **AI-friendly codebase** | Jinja2 templates + HTMX + Tailwind classes are straightforward for AI to generate and modify. No component lifecycle, no state management library, no build toolchain. |
| **Lightweight** | ~5 dependencies for the core stack vs Django's heavier ecosystem. Fast startup, small container. |
| **OpenAPI docs for free** | FastAPI auto-generates interactive API docs. Every endpoint is documented and testable at `/docs`. |

**Tradeoffs:**
- No Django admin panel. You lose the free CRUD interface for managing words/verbs/users. Mitigation: build a simple admin page with HTMX, or use a lightweight tool like SQLAdmin (FastAPI-compatible admin that auto-generates from SQLAlchemy models).
- No Django ORM magic (auto-migrations, model signals). SQLAlchemy is more explicit — you write migrations with Alembic. More control, slightly more work.
- Auth is manual. No `@login_required` decorator out of the box. Use `fastapi-users` library or roll JWT/session auth (straightforward with Pydantic).

**When to pick this:** You want the fastest, leanest Python web app with minimal infrastructure. Best if the app stays relatively content-driven (server renders pages, user fills forms, server grades answers).

---

#### Stack B: FastAPI (API) + Svelte Frontend + TailwindCSS

```
Browser (Svelte SPA) ←→ FastAPI (pure JSON API)
                            ├── REST + WebSocket endpoints
                            ├── SQLAlchemy 2.0 + asyncpg (PostgreSQL)
                            └── Pydantic v2 (validation)

Svelte app:
  ├── SvelteKit or Vite+Svelte
  ├── TailwindCSS
  ├── Stores (reactive state)
  └── Fetch API / WebSocket client
```

**How it works:**
- FastAPI is a **pure API server** — it only returns JSON, never HTML. Clean separation: backend knows nothing about UI.
- Svelte handles all rendering in the browser. Pages, transitions, form state, conjugation table interactions — all client-side.
- The conjugation table becomes a proper interactive component with reactive state: cells track input, show instant visual feedback (green/red), animate transitions between verbs.
- AI chat uses native WebSocket with Svelte stores — real-time, bidirectional, with typing indicators and smooth message streaming.
- SvelteKit provides routing, SSR (optional), and a dev server with hot reload.

**Why Svelte (not React/Vue):**
- **Smallest bundle size** — Svelte compiles to vanilla JS at build time. No virtual DOM, no runtime framework. A Svelte app ships ~5-10x less JS than React equivalent.
- **Simplest reactivity** — `let count = 0; count += 1` is reactive. No `useState`, no `ref()`, no boilerplate. This matters when AI is writing the code.
- **Built-in transitions and animations** — `transition:fade`, `animate:flip` are first-class. The training flow (card flip, score reveal, progress bar) benefits from this.
- **Scoped CSS** — styles in a Svelte component are automatically scoped. No CSS conflicts, no BEM naming.

**Why this stack:**

| Advantage | Details |
|-----------|---------|
| **Richest UX possible** | Smooth page transitions, instant feedback, offline-capable, complex interactive state (conjugation table, drag-and-drop word ordering, etc). |
| **Best for the conjugation table** | A reactive component that tracks 6+ input fields, validates on keystroke, shows hints, animates between verbs — this is where Svelte shines vs server-rendered HTML. |
| **Best for the dashboard** | Charts, progress visualizations, streak counters, animated stats — all native in a SPA. With HTMX you'd need a charting library bolted on. |
| **Best for mobile** | SPA can be wrapped as a PWA (Progressive Web App) with offline support, installable on phone home screen, push notifications. |
| **Clean API contract** | FastAPI serves JSON, Svelte consumes it. The API is reusable — a mobile app, CLI tool, or another frontend could use the same backend. |
| **Parallel development** | Frontend and backend are fully independent. Can work on API endpoints without touching UI and vice versa. |

**Tradeoffs:**
- **Build toolchain** — Svelte needs Node.js, npm, Vite. One more runtime to manage. Two separate dev servers during development.
- **More code overall** — Instead of one Jinja2 template, you write a Svelte component + an API endpoint + a fetch call. Three files instead of one.
- **SEO irrelevant** — This is a login-required learning app, not a content site. SPA's SEO weakness doesn't matter here.
- **AI needs to write two languages** — Python (backend) + Svelte/JS (frontend). More context switching for the AI assistant. HTMX templates are just HTML with attributes.
- **Initial load slower** — Browser downloads the JS bundle before anything renders (mitigated by SvelteKit SSR, but adds complexity).

**When to pick this:** You want a polished, app-like experience with rich interactivity, animations, and eventually a PWA. Best if you plan to add features that are painful in server-rendered HTML: real-time collaboration, complex dashboards, offline mode, drag-and-drop exercises.

---

#### Head-to-Head Comparison

| Dimension | Stack A (FastAPI + HTMX) | Stack B (FastAPI + Svelte) |
|-----------|--------------------------|----------------------------|
| **Complexity** | Low — one server, HTML templates, minimal JS | Medium — two systems (API + SPA), build step, Node.js |
| **UX ceiling** | Good — fast page swaps, some client-side state via Alpine | Excellent — full SPA, smooth transitions, offline, PWA |
| **AI-assistability** | Excellent — HTML + Tailwind classes, no framework concepts | Good — Svelte is simple, but AI writes two codebases |
| **Dev speed** | Fastest — one file per page (template + route) | Moderate — component + API endpoint + types |
| **Mobile** | Responsive HTML, works but not app-like | PWA-capable, installable, offline |
| **AI chat streaming** | SSE (3 lines of JS, no Redis) | WebSocket (more control, typing indicators, richer) |
| **Infrastructure** | FastAPI + PostgreSQL. That's it. | FastAPI + PostgreSQL + Node.js build + static hosting |
| **Dashboard/charts** | Possible but awkward (server-rendered charts or bolt-on library) | Native (Chart.js/D3 as Svelte components) |
| **Conjugation table** | Alpine.js component (workable, ~100 lines JS) | Svelte component (elegant, reactive, ~80 lines) |
| **Bundle size** | Zero JS bundle (HTMX is 14kb, Alpine is 15kb, both from CDN) | ~50-100kb compiled Svelte bundle |
| **Time to first byte** | Instant (server renders HTML) | Slower (download JS → render) |

#### Recommendation

**Start with Stack A (FastAPI + HTMX).** It's faster to build, simpler to maintain, and the UX is more than good enough for a training app where the core interaction is "see prompt → type answer → get feedback." The AI chat streaming via SSE is trivially simple compared to the current Django Channels setup.

If later you find that the conjugation table, dashboard, or mobile experience needs richer interactivity than HTMX + Alpine can deliver, **migrate the frontend to Svelte** while keeping the exact same FastAPI backend. The API endpoints already exist — you just swap who consumes them (Jinja2 templates → Svelte components). This is the beauty of FastAPI as pure API: the migration path from A to B is incremental, not a rewrite.

### 9.5 Visual Identity & Theme System

The current look is a single green gradient with glassmorphism cards. No dark mode, no personality, no visual reward system. The refactor should establish a complete visual identity with three switchable themes.

#### App Name & Branding

Consider renaming the app to something with more identity. Ideas:
- **LexArena** — "lex" (word/law in Latin) + arena (competition space). Fits the arcade angle.
- **VerbQuest** — quest/RPG framing for the learning journey.
- **LingoDuel** — implies challenge, competition.
- **WordForge** — crafting/building metaphor.

The name should work as a logo mark (short, punchy, looks good in a navbar).

#### Three Themes: Light, Dark, Arcade

Implementation: CSS custom properties (variables) on `:root`, switched via a `data-theme` attribute on `<html>`. With Tailwind, use the `dark:` variant plus a custom `arcade:` variant. User preference stored in `localStorage` + user profile DB. Respects `prefers-color-scheme` on first visit.

---

**Theme 1: Light (Clean / Professional)**

The default. For users who want a calm, distraction-free study environment.

| Element | Value |
|---------|-------|
| Background | `#FAFBFC` (near-white with warmth) — flat, no gradient |
| Surface (cards, modals) | `#FFFFFF` with `shadow-sm` and 1px `#E5E7EB` border |
| Primary accent | `#2563EB` (blue-600) — buttons, links, active states |
| Success | `#16A34A` (green-600) — correct answers |
| Error | `#DC2626` (red-600) — wrong answers |
| Text primary | `#111827` (gray-900) |
| Text secondary | `#6B7280` (gray-500) |
| Nav | White bar with subtle bottom shadow, dark text |
| Font | `Inter` for UI, `JetBrains Mono` for conjugation table inputs (monospace aligns cells) |
| Border radius | `8px` cards, `6px` buttons, `4px` inputs — rounded but not bubbly |
| Animations | Minimal — subtle fade on card swap, green/red flash on answer |

Feel: like Notion or Linear. Clean, typographic, content-first.

---

**Theme 2: Dark (Focus / Night)**

For evening study. Reduces eye strain, feels premium.

| Element | Value |
|---------|-------|
| Background | `#0F172A` (slate-900) — deep blue-black, not pure black |
| Surface | `#1E293B` (slate-800) with `#334155` (slate-700) borders |
| Primary accent | `#3B82F6` (blue-500) — slightly brighter than light mode to pop on dark |
| Success | `#22C55E` (green-500) |
| Error | `#EF4444` (red-500) |
| Text primary | `#F1F5F9` (slate-100) |
| Text secondary | `#94A3B8` (slate-400) |
| Nav | `#1E293B` with bottom border `#334155` |
| Inputs | `#0F172A` background with `#475569` borders — recessed feel |
| Correct answer glow | `box-shadow: 0 0 12px rgba(34, 197, 94, 0.3)` |
| Wrong answer glow | `box-shadow: 0 0 12px rgba(239, 68, 68, 0.3)` |

Feel: like GitHub dark or Discord. Professional dark, not gamer-dark.

---

**Theme 3: Arcade (Gamified / Retro)**

The fun mode. Pixel-inspired but modern. Rewards feel like achievements. This is where gamification visuals live strongest.

| Element | Value |
|---------|-------|
| Background | Deep purple-black `#13051F` with subtle scanline overlay (CSS repeating-gradient, 2px lines at 10% opacity) |
| Surface | `#1A0A2E` with neon border glow (`box-shadow: 0 0 8px rgba(139, 92, 246, 0.3), inset 0 1px 0 rgba(255,255,255,0.05)`) |
| Primary accent | `#A855F7` (violet-500) — neon purple for buttons, active states |
| Secondary accent | `#06B6D4` (cyan-500) — for scores, XP, secondary actions |
| Success | `#4ADE80` (green-400) — bright neon green, with glow |
| Error | `#FB7185` (rose-400) — neon pink-red |
| XP/Points color | `#FACC15` (yellow-400) — gold, always. XP numbers in this color. |
| Text primary | `#E2E8F0` |
| Text secondary | `#A78BFA` (violet-400) |
| Font | `Inter` for UI, **`Press Start 2P`** (Google Font) for score displays, XP popups, level-up text. Use sparingly — headers and numbers only, not body text. |
| Nav | Dark with subtle purple underglow (`border-bottom: 2px solid #7C3AED`) |
| Inputs | Dark with purple focus ring (`focus:ring-violet-500`) |
| Card border | Animated gradient border (purple → cyan → purple, slow rotation via `@keyframes`) |
| Correct answer | Green glow pulse + "+10 XP" floating text animation |
| Wrong answer | Red shake + screen flash (subtle, 100ms red overlay at 5% opacity) |
| Level-up | Full-screen overlay with particle burst, "LEVEL UP!" in `Press Start 2P`, golden glow |
| Streak counter | Fire emoji or pixel-flame SVG next to streak number, pulses when streak > 5 |

Feel: like a mix of Duolingo's gamification + retro arcade aesthetics. Think: neon signs in a dark room, pixel art accents, satisfying feedback on every action.

**Scanline overlay CSS:**
```css
[data-theme="arcade"] body::after {
  content: '';
  position: fixed;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.08) 2px,
    rgba(0, 0, 0, 0.08) 4px
  );
  pointer-events: none;
  z-index: 9999;
}
```

**Animated neon border CSS:**
```css
[data-theme="arcade"] .card {
  border: 1px solid transparent;
  background-clip: padding-box;
  position: relative;
}
[data-theme="arcade"] .card::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: inherit;
  background: linear-gradient(
    var(--neon-angle, 0deg),
    #a855f7, #06b6d4, #a855f7
  );
  z-index: -1;
  animation: neon-rotate 4s linear infinite;
}
@keyframes neon-rotate {
  to { --neon-angle: 360deg; }
}
```

---

#### Theme Switcher UI

Three-way toggle in the navbar (or settings). Icons:
- Light: sun icon
- Dark: moon icon
- Arcade: joystick / gamepad icon

Implementation with Tailwind + Alpine.js:
```html
<div x-data="{ theme: localStorage.getItem('theme') || 'light' }"
     x-init="document.documentElement.setAttribute('data-theme', theme)">
  <button @click="theme='light'; localStorage.setItem('theme','light'); $el.closest('[x-data]').__x.$data.theme='light'; document.documentElement.setAttribute('data-theme','light')">
    <!-- sun icon -->
  </button>
  <!-- ... dark, arcade buttons -->
</div>
```

---

#### Shared Design Principles (All Themes)

Regardless of theme, these UX patterns stay consistent:

1. **Card-based layout** — Every interaction lives in a card. Training questions, conjugation tables, chat, session config. Cards have consistent padding (1.5rem), radius (12px), and shadow depth per theme.

2. **Responsive grid** — Mobile-first. Single column on phone, two-column on tablet (sidebar + main), three-column on desktop (sidebar + main + stats). Conjugation table scrolls horizontally on mobile, shows all columns on desktop.

3. **Input focus states** — Thick colored ring on focus (blue/purple depending on theme). Essential for the conjugation table where users Tab through cells.

4. **Answer feedback animation** — On submit:
   - Correct: cell/card flashes green (200ms), input border turns green, checkmark icon appears
   - Wrong: cell/card shakes (CSS `@keyframes shake`, 300ms), input border turns red, correct answer fades in below
   - In arcade mode: add the XP popup and sound effects (optional, user can mute)

5. **Progress bar** — Horizontal bar at the top of training sessions. Shows current position (e.g., "3/10 words"). Fills left-to-right. Color matches theme accent. In arcade mode: segmented like a health/XP bar with glow.

6. **Typography scale:**
   - Score/XP numbers: `text-3xl font-bold` (or `Press Start 2P` in arcade)
   - Question prompt (the word to translate): `text-2xl font-semibold`
   - Body text: `text-base` (16px)
   - Labels/secondary: `text-sm text-secondary`
   - Conjugation table cells: `text-sm font-mono` (monospace for alignment)

7. **Transition on theme switch** — `transition: background-color 300ms, color 300ms` on body and major surfaces. Theme switch should feel smooth, not jarring.

---

### 9.6 Gamification System

The arcade theme is the visual shell, but gamification mechanics should work across all themes (just displayed differently). In light/dark mode, gamification is present but subtle (numbers, badges). In arcade mode, it's loud (animations, sounds, particles).

#### XP (Experience Points)

Every correct action earns XP. This is the universal reward currency.

| Action | XP Earned |
|--------|-----------|
| Correct word (exact match) | +10 XP |
| Correct word (synonym) | +7 XP |
| Correct conjugation pronoun | +5 XP per pronoun (up to +30 for full table) |
| Perfect conjugation table (all 6 correct) | +50 XP (bonus) |
| Complete a session | +25 XP |
| First session of the day | +50 XP (daily bonus) |
| Streak bonus (consecutive days) | +10 XP per streak day (day 5 = +50 extra) |

XP is separate from the probability system. Probability drives what you practice; XP drives motivation.

#### Levels

Total XP maps to a level. Simple curve:

```
Level 1:    0 XP
Level 2:    100 XP
Level 3:    250 XP
Level 4:    500 XP
Level 5:    1,000 XP
...
Level N:    roughly XP = 50 * N^1.8
```

Each level-up triggers a visual reward (bigger in arcade mode: particle burst, sound, full-screen overlay). In light/dark mode: a toast notification with confetti icon.

Level is displayed in the navbar next to the username: `Lv.12 username` or as a badge.

#### Streaks

Consecutive days of practice. Resets if the user misses a full calendar day.

- Displayed as a flame icon + number in the navbar or dashboard
- Streak milestones (7, 14, 30, 60, 100 days) unlock badges
- In arcade mode: flame grows bigger/more animated at higher streaks
- Streak freeze: user gets 1 free "freeze" per week (can miss one day without breaking streak). Earned or bought with XP.

#### Achievements / Badges

Unlockable badges displayed on the user's profile/dashboard. Examples:

| Badge | Condition | Icon idea |
|-------|-----------|-----------|
| First Steps | Complete first session | Baby footprint |
| Polyglot Beginner | Practice 2 different languages | Globe |
| Century | Learn 100 words | "100" in bold |
| Grammar Nerd | Master 5 tenses | Open book |
| Perfect Run | Complete a session with 100% accuracy | Star |
| Night Owl | Practice after midnight | Moon |
| Speed Demon | Answer 10 words in under 30 seconds | Lightning bolt |
| Comeback Kid | Resume after 7+ days inactive | Phoenix |
| Verb Slayer | Master 50 verb conjugations | Sword |
| The Irregular | Master all irregular verbs in one language | Puzzle piece |

Badges are stored in DB. Unlocked badges trigger a notification. In arcade mode: badge reveal has a "loot box" style animation (card flip, glow, rarity border).

#### Combo System (Arcade-specific)

Consecutive correct answers build a combo counter:

```
1 correct:  "1x"
3 correct:  "3x COMBO" (text scales up slightly)
5 correct:  "5x COMBO!" (text glows, XP multiplier 1.5x)
10 correct: "10x COMBO!!" (screen border glows, XP multiplier 2x)
```

On wrong answer: combo resets with a "BREAK" flash. This encourages focus and rewards flow state.

#### Weekly Challenge

One global challenge per week, same for all users:
- "Master 5 new Spanish verbs in Subjuntivo"
- "Get 50 consecutive correct word translations"
- "Practice every day this week"

Completing the challenge gives bonus XP + an exclusive weekly badge.

#### Leaderboard (Optional / Future)

If the app ever has multiple users:
- Weekly XP leaderboard
- Per-language leaderboard
- Friends-only leaderboard
- Shows top 10 + your position

---

#### Gamification in Light/Dark vs Arcade — Visual Difference

| Element | Light/Dark Mode | Arcade Mode |
|---------|----------------|-------------|
| XP earned | Small "+10 XP" text below answer, fades in | Floating "+10 XP" pops up and floats upward, golden glow |
| Level up | Toast notification: "Level 5 reached!" | Full-screen overlay, particle burst, "LEVEL UP!" in pixel font, sound effect |
| Streak | Flame icon + number in navbar, static | Animated flame, pulses, grows with streak length |
| Combo | Counter in corner, subtle | Large center display, scaling text, screen glow at 10x |
| Correct answer | Green border + checkmark | Green flash + screen shake + particle sparks |
| Wrong answer | Red border + show correct answer | Red shake + "MISS" text + combo break animation |
| Badge unlock | Slide-in notification card | Card flip animation with rarity glow (common/rare/epic/legendary borders) |
| Session complete | Summary card with stats | "STAGE CLEAR" screen with score breakdown, star rating (1-3 stars based on accuracy) |
| Daily bonus | "Welcome back!" toast | Coin-drop animation, slot-machine style XP reveal |

---

#### Sound Design (Arcade Mode Only, Mutable)

Optional sound effects triggered by events. Users can toggle on/off in settings. Keep sounds short (< 500ms), subtle, and satisfying.

| Event | Sound idea |
|-------|-----------|
| Correct answer | Soft "ding" / coin collect |
| Wrong answer | Low "buzz" / soft thud |
| Combo break | Glass break (short) |
| 5x combo | Power-up chime |
| 10x combo | Ascending arpeggio |
| Level up | Fanfare (1 second) |
| Badge unlock | Chest-open / achievement sound |
| Session complete | Victory jingle (2 seconds) |
| Streak milestone | Fire whoosh |

Use the Web Audio API or short MP3/OGG files (< 10kb each). Total sound pack under 100kb.

### 9.7 AI Chat Integration Vision

The current chat is a disconnected generic chatbot. The refactored version should:

1. **Know the user's state:** Access weak words, low-score tenses, recently practiced items
2. **Generate targeted exercises:** "Conjugate *aller* in the subjunctive" (because user's subjonctif score for aller is 1500)
3. **Return structured data:** AI response includes a JSON payload with scores/points alongside the human-readable text
4. **Feed back into the system:** Chat exercise results update the same probability/score system used by the structured training modes
5. **Contextual conversations:** AI speaks in the target language, mixing in words the user is learning, adjusting difficulty to their level

### 9.8 Missing Features Worth Adding in the Refactor

- **User dashboard** — progress charts, weak areas, streaks, total words mastered
- **Spaced repetition timing** — current system has no time dimension. Items that haven't been seen in days should get a probability boost (forgetting curve)
- **Listening/pronunciation** — text-to-speech for target language words (browser API or cloud TTS)
- **Sentence context** — show example sentences using the word/verb being practiced
- **Import/export** — let users add custom word lists or export their progress
- **Multi-device sync** — requires real database and user session management

---

## 10. Database Schema Vision (for refactor)

```
Language (code, name, pronoun_set[], tense_definitions{}, difficulty_tiers{})

Word (text, language_id)
WordTranslation (word_id, target_language_id, translation, synonyms[], verified, source)

Verb (infinitive, language_id)
VerbTranslation (verb_id, target_language_id, translation, verified, source)
VerbConjugation (verb_id, mood, tense, pronoun, conjugated_form, verified, source)

UserProgress (user_id, item_type, item_id, language_pair, probability, times_seen, times_correct, last_seen, streak)

TrainingSession (user_id, mode, language_pair, config{}, started_at, completed_at, score)
SessionItem (session_id, item_id, answer, correct, multiplier_applied, timestamp)
```

Key changes from current:
- `Language` as first-class entity (not hardcoded strings)
- `verified` + `source` on all content (track data provenance)
- Unified `UserProgress` instead of separate `UserVerb`/`UserWord`/`UserConjugation`
- `TrainingSession` + `SessionItem` for history and analytics (replaces `request.session` state)
- `last_seen` enables time-based spaced repetition

---

## 11. Summary of Priorities for the Refactor

| Priority | Item | Why |
|----------|------|-----|
| **P0** | Fix data quality / build reliable data pipeline | App is useless if 10% of answers are wrong |
| **P0** | Unify language model (make it data-driven) | Prerequisite for adding EN/RU |
| **P1** | Merge duplicated training engines | Reduce maintenance burden, single source of truth for algorithms |
| **P1** | Replace SQLite with PostgreSQL | Production readiness, concurrent users |
| **P1** | Clean up frontend (Tailwind or similar, responsive design) | UX is the stated goal |
| **P2** | Add user dashboard and progress tracking | Core value proposition for a learning app |
| **P2** | Integrate AI chat with learning state | The killer feature that differentiates this app |
| **P2** | Add time-based spaced repetition | Significantly improves learning outcomes |
| **P3** | Session persistence in DB (not request.session) | Reliability, analytics, multi-device |
| **P3** | Security fixes (CSRF, rate limiting, input sanitization) | Required before any public deployment |
