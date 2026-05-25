# VerbPractice refactor — shipped and deferred

Last updated: 2026-05-25

The full plan that drove this change lives at `/home/trotaevil/.claude/plans/i-am-working-in-idempotent-tide.md`.

## 1. Shipped in this iteration

- **Phase 1 — Dashboard slim-down (UI-only)**: `frontend/src/lib/pages/DashboardPage.svelte` no longer renders the daily cockpit eyebrow, weekly challenge, reward layer, focus queue, tutor memory, leaderboards, or circle. Hero now shows just "Welcome back, {username}" + tracked/mastered counts. Mode cards + today's momentum + recent sessions remain.
- **Phase 8a — Multilingual schema generalization**:
  - `app/core/languages.py` gained `EN` and `RU` entries plus helpers `language_display_name()` and `format_direction_label()`.
  - `app/schemas/training.py` `TranslationSessionStart.direction` is now a regex-validated string (`^[a-z]{2}_[a-z]{2}$`) instead of a 2-value Literal. Same for `ConjugationSessionStart.language`.
  - `app/services/training_service.py` deleted `TRANSLATION_BASE_LANGUAGE_BY_MODE`. New helper `_resolve_inventory_language(db, mode, direction)` derives the inventory language by checking which side of the pair has rows. All three callers updated.
  - `app/routers/api.py` four hardcoded "Spanish → French" / "French → Spanish" labels replaced with `format_direction_label(direction)`.
- **Phase 2 — Settings table + API + page**:
  - `UserPreference` extended with: `mother_tongue_language_id`, `learning_language_id`, `translation_display_mode` (`mother_full` | `partial` | `learning_full`), `force_unlock_added_words`, `last_practice_pair`, `last_practice_mode`.
  - `app/routers/settings.py` new — `GET /api/settings`, `PATCH /api/settings`, `GET /api/languages`.
  - `frontend/src/lib/pages/SettingsPage.svelte` new — prefs form + add-word form + priority queue list. Wired into `App.svelte` at `/settings` and a NavBar link added.
- **Phase 8b — Direction tile chooser**:
  - `frontend/src/lib/pages/TranslationPage.svelte` two static buttons replaced with: two language tiles (source/target) with a swap (⇄) button between. Pre-selection cascades: `last_practice_pair` → `(learning, mother)` from settings → first available pair. Each session start fires `PATCH /api/settings` to persist `last_practice_pair` and `last_practice_mode`.
- **Phase 3 — AI word addition (split cache)**:
  - New tables: `word_lexical_entries` (per word_id, the target-language definition/synonyms/examples), `word_native_translations` (per word + native lang), `user_added_words` (priority queue), `translation_reports`.
  - `app/services/word_ai_service.py` new — `translate_word()` does split-cache lookup, only calls AI for missing pieces. Uses `gpt-4o` with `response_format=json_object`. Includes `expand_word()` for "More info".
  - `app/routers/words.py` new — `POST /api/words/add`, `GET /api/words/priority-queue`, `POST /api/words/{id}/expand`, `POST /api/words/{id}/report`.
  - All wired into `app/main.py`.
- **Phase 4 — Priority pool unlock**: `app/services/training_service.py::_unlock_next_items` now fills the next unlock slots from `UserAddedWord` first (oldest first), then falls back to the default sequential unlock for the remainder.
- **Phase 5 — Feedback buttons**: SettingsPage's "last added" panel exposes "More info" (calls `/expand`, appends to `extended_content`) and "Report definition" / "Report translation" buttons (open a small reason input, post to `/report`).
- **Phase 6 — Admin user inspector**:
  - `app/routers/admin.py` adds `GET /admin/users`, `GET /admin/users/{id}/inspect`, `POST /admin/reports/{id}/resolve`.
  - **Open access (no auth)**: these three routes intentionally do NOT use `require_admin_context` — user wanted to hit them directly in local dev without logging in. The legacy `/admin/monitor*` routes remain admin-gated. Tighten before any non-local deployment.
  - Templates: `app/templates/admin/users_list.html`, `app/templates/admin/user_inspect.html`.
  - Manual refresh model (no polling). Inspector shows profile, all unlocked progress rows (sorted by probability desc — weakest at top), priority queue still pending, and a reports table with dismiss/regenerate/delete buttons.
- **Phase 7 — This file.**
- **Schema migration**: `alembic/versions/a1b2c3d4e5f6_word_ai_and_settings.py` adds all new columns/tables in one transaction. Has matching `downgrade()`.

---

## Iteration 2 (2026-05-25): prompt redesign, tags, word sets

- **Prompt redesign (#2, #3, #7, #8)** — full-add prompt now returns a `status` field driving four downstream paths:
  - `exact`: normal happy path.
  - `corrected`: AI fixed a typo; frontend shows pre-saved "Corrected '{original}' → '{canonical}'" banner; the word is still saved under the corrected canonical form.
  - `ambiguous`: same payload, but `native_translations` is filled with multiple senses (1–3).
  - `not_found`: AI returns only `status` + up to 3 `suggestions`; nothing saved; frontend renders pre-saved "We couldn't find that word" with clickable suggestion chips that re-submit.
  - Synonyms now explicitly capped at 0–5 with "do NOT invent or pad" instructions. Examples 1–3, same rule.
  - Native translations changed from a single string to an **array of 1–3 entries**, each with its own translation + optional sense note (literal/figurative/regional).
  - New `detected_input_language` field — when user types e.g. "telefono" with target=FR, AI reports `ES`; frontend shows a "That looked like Spanish. Switch target?" chip with a one-click swap.
  - Prompt now explicitly says "if the user's context contains grammatical errors, silently use the correct form — do not mirror their mistakes" (fixes the patate `un patate` / `une patate` bug).
- **Schema (`b2c3d4e5f6a7_multi_translation_tags_sets.py`)**:
  - `word_native_translations`: dropped `unique(word_id, lang)`; new unique on `(word_id, lang, translation)`; added `priority int` for ordering.
  - New `tags`, `word_tags` tables. Seed includes 41 curated tags across thematic / grammatical / difficulty kinds.
  - New `word_sets` + `word_set_members` tables (`kind` = manual | smart; smart sets use `filter_tag_ids` JSON column).
- **Tag auto-suggestion**: AI prompt requests `suggested_tags` from the curated vocabulary only (`CURATED_TAG_VOCABULARY` in `word_ai_service.py`). Service writes them into `word_tags` with `source='ai_suggested'`.
- **Word sets feature**:
  - `app/routers/tags.py` — `GET /api/tags` (grouped by kind).
  - `app/routers/word_sets.py` — full CRUD: list / create / read / update / delete + add/remove members (manual only).
  - Smart sets resolve at query time via "word has ALL of these tag IDs".
  - New `SetsPage.svelte` at `/sets` — card grid, "+ New set" modal with kind toggle + tag chip selector for smart sets.
  - NavBar gained "Sets" link.
- **Trainer integration**:
  - `TranslationStartPayload` accepts optional `set_id`.
  - `start_translation_session` + `_select_weighted_items` filter the candidate pool to set members when scoped.
  - `TranslationPage` reads `?set=N` query param, fetches the set details, shows a "Practicing set: {name} (n words) [clear scope]" chip above the trainer.
  - "Practice" button on each set card navigates to `/training/words?set=<id>`.
- **Doc**: `docs/AI_WORD_FEATURE.md` already includes the exact prompts (Iteration 1). **Iteration 2 prompts are not yet mirrored there — update before next session.**

### Iteration 2 — deliberately deferred

- **Manual-set word picker**: API supports adding/removing words from manual sets, but there's no UI flow yet to search the inventory and add a word from outside the SetsPage detail view. Today the only place that creates manual-set members is hitting `POST /api/word-sets/{id}/words` directly. Add an "Add to set: …" dropdown to AddWordPage and a "Browse and pick words" picker on the SetsPage detail view.
- **Smart-set unlock cascade**: scoped sessions only sample from `UserProgress` rows whose item_id is in the set. If none of the set's words are unlocked yet, the user sees an empty session. Consider auto-unlocking the next N set members on a scoped session start.
- **AI prompt doc drift**: `docs/AI_WORD_FEATURE.md` still shows iteration-1 prompts. Mirror the new ones.
- **Translation regenerate (admin)** still works but only generates a single native row; admin's "Regenerate" action no longer uses the array shape end-to-end. Low priority since admin tooling is local-only.
- **Display mode UI in trainer**: settings has `translation_display_mode` but the trainer doesn't yet branch its question rendering by mode. AddWordPage shows everything; trainer still shows just the prompt/answer.

## 2. Dead code / deferred cleanup

UI-only Phase 1 left the dashboard backend completely intact. None of this is harmful, but cleaning it later will reduce DB writes and serialized payload size on every dashboard load:

- `app/services/gamification.py` — entire file, still imported by `app/routers/api.py:63` and serializes `gamification` blob into `/api/dashboard`. Removable when we're sure none of it comes back.
- `app/services/dashboard_service.py::recent_chat_messages()` and focus-queue helpers — same status.
- DB tables: `weekly_challenges`, `user_challenge_progress`, `xp_events`, `friend_links`, `badge_definitions`, `user_badges` — orphaned but intact. Future migration to drop them.
- API endpoints: `POST /api/community/friends`, `DELETE /api/community/friends/{id}` (api.py:996 area) — still reachable, no frontend caller.
- `award_xp()` writes on every practice answer — harmless wasted work; UI no longer renders the result.

Other deferred surface:

- **EN/RU word data** — `Language` rows exist (`EN`, `RU`), but `words` / `word_translations` tables have zero rows for them. User said they'll populate CSVs later. The seed script (`scripts/seed_from_legacy_csv.py`) already reads `LANGUAGE_DEFINITIONS` so it'll create the rows next time it runs. Word/verb data still needs to be hand-curated.
- **EN/RU verb conjugation** — deferred. No `verbs` / `verb_conjugations` rows for EN or RU. EN is small (3 simple tenses defined); RU needs aspect/gender/case design work.
- **Translation feedback buttons in trainer flow** — Phase 5 wired the buttons only into the SettingsPage "last added" panel. They are NOT yet shown on the practice page when a user sees a question's expected answer. To extend: the trainer flow's reveal/answer feedback needs to know the underlying `WordLexicalEntry.id` and `WordNativeTranslation.id` for the current item, and surface "More info" / "Report" inline. Backend endpoints (`/api/words/{id}/expand`, `/api/words/{id}/report`) work as-is.
- **Empty-pool error handling** — Phase 8b plan called for `POST /api/translation/start` returning `400 {error: "no_words_for_pair"}` when neither side of the chosen direction has inventory. Not implemented — current behavior is that `_resolve_inventory_language` falls back to source-side, `_select_weighted_items` returns empty list, and the frontend just shows no question. Workable but not friendly.
- **`_translation_defaults` in `app/routers/api.py`** — still hardcodes `es_fr` for words and `fr_es` for verbs as fallback defaults. Should ideally read from `UserPreference` to default to the user's learning ↔ mother pair, but that's a deeper integration. The tile chooser already does the right thing on the frontend.

## 3. Known limitations

- **No advisory locking** on first-time word add — if two users request the same brand-new word simultaneously, both may trigger a full AI call. Accepted per plan.
- **`flag_count` is recorded** on `WordLexicalEntry` / `WordNativeTranslation` rows but there's no automatic hide-at-threshold logic. Admin action is the only path to remove/regenerate flagged entries.
- **Single learning language per user** — `UserPreference.learning_language_id` is one value. Multi-target practice would need either a list column or a separate join table.
- **No CSRF on `POST /admin/reports/{id}/resolve` form action** beyond the standard CSRF token submitted as a form field. Admin routes are session-auth + admin-flag gated, which is the project's existing pattern.
- **NavBar always shows "Settings" link**, even on auth pages. Matches the existing pattern for other always-visible links.
- **`/admin/users*` and `/admin/reports/*/resolve` accept any request** (no session/admin required, no CSRF on form). Local dev convenience. Re-gate (`require_admin_context` + CSRF) before exposing the host.

## 4. Open questions for next session

- **Prompt-engineering pass for word AI**: ships with `gpt-4o` and a first-draft prompt. Need to test on:
  - Idioms across all FR/ES/EN/RU mother-tongue × learning-language combinations.
  - False friends (e.g. ES "embarazada" vs EN "embarrassed").
  - Polysemes — does the optional `context` field improve disambiguation as expected?
  - Technical/domain terms.
  - Once we have real usage data, compare `gpt-4o` vs `gpt-4o-mini` for cost/quality.
  - Consider adding few-shot examples per language pair.
- **EN/RU word seeding strategy**: user plans to populate CSVs. Once decided, may want a `seed_from_curated_csv` extension or just to use the existing `seed_from_legacy_csv.py` pattern.
- **Force-unlocked direction**: when `force_unlock_added_words=True`, we add a `UserProgress` row with `language_pair = f"{learning}_{mother}"`. If the user practices the reverse direction (`mother_learning`), the force-added word won't appear there. Decide if force-unlock should mirror to both directions.

## 5. How to verify

`alembic upgrade head` first. Then for each phase:

1. **Migration**: `alembic upgrade head` then `alembic downgrade -1` then `alembic upgrade head` again — all should be clean.
2. **Dashboard purge**: load `/dashboard`. Should show only welcome hero + mode cards + today's momentum + recent sessions.
3. **Settings**: `/settings` — set mother tongue = ES, learning = EN, mode = partial. Save, reload, confirm persistence.
4. **AI add (full miss)**: with `OPENAI_API_KEY` set, add the word "ephemeral" with context "academic writing". DB should gain a new `words` row (EN), `word_lexical_entries` row (definition + synonyms + examples in EN), `word_native_translations` row (ES translation), and `user_added_words` row.
5. **AI add (cache hit)**: as a second user with mother tongue FR, add "ephemeral". Only a `word_native_translations(native_language=FR)` row should be added. No new `word` or `word_lexical_entries` row.
6. **Tile chooser**: open `/training/words`. Two language tiles + swap arrow. Pick EN→ES, swap, start. Reload — `last_practice_pair` should restore the choice.
7. **Priority unlock**: as the ES user with the "ephemeral" priority entry, run a word practice session. When an unlock cycle triggers (avg probability of top-5 ≥ 750), "ephemeral" should unlock before the next default Spanish word.
8. **Force unlock**: in `/settings`, toggle "Force-add new words directly". Add another word. Verify a `user_progress(unlocked=true)` row appears immediately without waiting for the unlock cycle.
9. **Feedback**: on the "last added" panel, click "More info" — `extended_content` populates. Click "Report definition" with a reason — `translation_reports(status=pending)` row appears.
10. **Admin inspector**: as an admin user, open `/admin/users`. Pick a user → `/admin/users/{id}/inspect`. In another tab, answer a known word correctly in practice → refresh inspector → that row's `probability` dropped by ×0.7 and `times_correct` incremented. Wrong answer → ×1.3, `times_seen` incremented.
11. **Report resolution**: in the inspector, click "Regenerate" on a pending report → AI re-runs, the cached entry is overwritten, report status flips to `resolved`.
