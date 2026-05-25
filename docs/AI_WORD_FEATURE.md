# AI word feature — how it works

This is a behavioral reference, not a code dive. Source of truth: [app/services/word_ai_service.py](../app/services/word_ai_service.py), [app/routers/words.py](../app/routers/words.py).

---

## a) Prompt engineering and what the database holds

### The three prompts

We use **three** distinct prompts against `gpt-4o`, all forced to JSON mode where applicable. The exact text of each system prompt, as sent to the API today:

#### Prompt 1 — full-add (system message)

> You are a careful bilingual lexicographer. The user is learning **{target_language_name}** (their target language) and their mother tongue is **{mother_tongue_name}**. When given a single word or short phrase, return a strict JSON object with these keys:
>   - `canonical_text`: the word's canonical form in the target language (lowercase, stripped of articles/punctuation, with diacritics restored).
>   - `definition`: a clear definition written ENTIRELY in the target language, suitable for a learner. 1-2 sentences.
>   - `synonyms`: array of up to 5 objects, each `{text: target-language synonym, gloss: short mother-tongue gloss for that synonym}`.
>   - `examples`: array of up to 3 short example sentences in the target language.
>   - `native_translation`: the most direct translation into the mother tongue.
>   - `native_note`: optional short note in the mother tongue with usage caveats (false friends, register, regional notes). Empty string if none.
>
> Always return valid JSON with exactly these keys. No prose outside the JSON object.

User message format:
> `Word/phrase: {input_text}`
> `Context: {context_hint}`  ← only included if the user supplied context

#### Prompt 2 — native-only (system message)

> You are a careful bilingual lexicographer. The user is learning **{target_language_name}** and their mother tongue is **{mother_tongue_name}**. The {target_language_name}-side lexical entry already exists in our database. Return a strict JSON object with these keys:
>   - `native_translation`: the most direct translation into the mother tongue.
>   - `native_note`: optional usage note in the mother tongue. Empty string if none.
>
> Always return valid JSON. No prose outside the JSON object.

User message format: same as above.

#### Prompt 3 — expand / "More info" (system message)

> You are an expert in **{target_language_name}**. Given a word and its existing definition, append additional learning content in the target language: etymology (if interesting), register (formal/informal/slang), regional variants, common collocations, and 1-2 advanced example sentences. Plain text, no JSON, no headings, max 250 words.

User message format:
> `Word: {word.text}`
> `Existing definition: {lexical.definition}`

Source of truth for the live prompt text: [app/services/word_ai_service.py](../app/services/word_ai_service.py). If you ever change a prompt there, please mirror the change here so the doc stays honest.

### When each prompt fires

- **Prompt 1 (full-add)** fires when the word has never been seen by anyone for this target language. Most expensive call.
- **Prompt 2 (native-only)** fires when the lexical entry already exists but the user's specific mother tongue hasn't been translated yet. 5–10× cheaper than prompt 1.
- **Prompt 3 (expand)** fires on every "More info" click. Each click **appends** to `extended_content` rather than replacing.

The optional context the user provides on the Add Word page is concatenated into the **user message** (not the system prompt) for prompts 1 and 2 — the model sees `Word/phrase: bank\nContext: riverside, not financial`. Expand does not get the context, only the word + its existing definition.

### What gets stored (split cache)

The cache is split into two layers per word, by design:

- **`word_lexical_entries`** — one row per `Word`. Holds the target-language-side content: definition, synonyms (with mother-tongue glosses), examples, the appended `extended_content` from "More info", source label, flag count, timestamps. This row is **shared across all users learning that language**. Two users learning EN will reuse the same definition and synonyms for "ephemeral".

- **`word_native_translations`** — one row per `(word, native_language)`. Holds the mother-tongue translation + optional note. A FR user and an ES user learning EN each have their own row here, but they share the EN-side lexical entry above.

- **`words`** itself is the index — `(text, language_id)` unique. The user adds "ephemeral" with `learning_lang_code=EN`, we store `Word(text="ephemeral", language_id=EN)`, plus the lexical entry, plus the native translation for their mother tongue.

- **`user_added_words`** — the priority queue marker. Holds `(user_id, word_id, language_pair, context_hint, added_at)`. This is what makes the word jump the unlock line ahead of the default verb list in the user's next practice session. One row per user per pair.

- If the user has **"force-unlock added words"** on in Settings, we *also* insert directly into `user_progress` with `unlocked=True, probability=1000`. They never sit in the priority queue.

### Caching savings (concrete example)

User A is native-FR, learning EN. Adds "ephemeral":
- No `Word` row exists → fires **full-add prompt** (~500–1500 tokens out).
- Creates: `Word(EN, "ephemeral")`, `WordLexicalEntry`, `WordNativeTranslation(FR)`.

User B is native-ES, learning EN. Adds "ephemeral":
- `Word` row exists. `WordLexicalEntry` exists. `WordNativeTranslation(ES)` does not.
- Fires **native-only prompt** (~50–200 tokens out). 5–10× cheaper.
- Creates: `WordNativeTranslation(ES)`. No duplicate lexical work.

User C is native-RU, learning FR. Adds "éphémère":
- Completely separate language, completely separate cache. Full-add prompt runs.

---

## b) What happens when the user misspells the input word

There is **no spelling correction step**. The model is asked to do the right thing with whatever it receives.

The behavior in practice:

1. **Light typo, recognizable** (e.g. `"ephemeral"` typed as `"ephimeral"`): the model's `canonical_text` field will return the correct form (`"ephemeral"`). We store the `Word.text` as `canonical_text`, **not** as what the user typed. So the DB ends up clean, and a second user later adding the correct spelling hits the cache.

2. **Severe typo, unrecognizable** (e.g. `"ephzzzxyz"`): the model has no clear meaning to attach. One of three things happens:
   - It guesses something close and we cache the guess. Bad data — the user should hit "Report" on the result page.
   - It returns a definition like *"this word does not appear to exist in the language"* — odd but technically valid JSON. Stored as-is.
   - It returns invalid JSON or refuses. The service raises `WordAIError("AI returned invalid JSON")`, the API returns HTTP 502, and the user sees an error toast. **Nothing is saved.**

3. **Wrong language** (typed in mother tongue while target language is set to a foreign one): the model usually catches it via the `canonical_text` field — if you type `"casa"` and target=EN, it'll return `canonical_text="house"` and translate accordingly. Not always reliable; this is one of the open questions in [REFACTOR_STATUS.md](REFACTOR_STATUS.md).

4. **Cache collision via canonical_text**: after we get the AI response, we look up `Word(text=canonical_text, language_id=learning_lang)` to see if it already exists. If so, we **reuse** the existing entry and skip creating a duplicate — the user just gets a fast response from cache. This means typing `"Ephemeral"` and `"ephemeral"` and `"ephemerals"` (with the model normalizing to singular) all converge on the same row.

There is currently **no client-side validation** of the input beyond a 1–128 character length check. No "did you mean?" suggestions. No frequency filter to reject nonsense. Worst-case behavior is bounded by the AI's own quality and the user's report ability.

---

## c) How reports work

### What the user sends

When a user clicks **"Report definition"** or **"Report translation"** on the Add Word result page, a modal opens with an optional free-text reason. On submit, the SPA sends a `POST /api/words/{word_id}/report` containing:

- `entry_type`: either `"lexical"` (reporting the target-language definition / synonyms / examples) or `"native"` (reporting the mother-tongue translation).
- `entry_id`: the integer PK of the specific `WordLexicalEntry` or `WordNativeTranslation` row being flagged.
- `reason`: the user's optional explanation, max 512 chars. Often empty.
- `csrf_token`: standard CSRF guard from the session.

The reason `word_id` is in the URL path is for routing convenience; the actual target is identified by `(entry_type, entry_id)` because the same word can have multiple translations across different mother tongues.

### What gets saved

Two things happen atomically on the server:

1. **`flag_count` on the reported entry is incremented.** This is a counter that lives on the `word_lexical_entries` row (if `entry_type=lexical`) or the `word_native_translations` row (if `entry_type=native`). It is currently **passive metadata** — nothing automatically hides or removes entries when the count gets high. It's there so we can see at a glance which entries are most-flagged.

2. **A new `translation_reports` row is inserted** with:
   - `user_id`: who filed the report.
   - `entry_type`, `entry_id`: the same identifier the user submitted.
   - `reason`: the user's text (nullable).
   - `status`: starts as `"pending"`. Transitions to `"dismissed"` or `"resolved"` when admin acts on it.
   - `created_at`: timestamp.
   - `resolved_at`, `resolver_id`: filled when status moves out of pending. (`resolver_id` is currently always `NULL` because the admin endpoints are open-access for local dev — there's no logged-in admin to attribute the action to.)

The endpoint returns `{"ok": true, "report_id": <id>}` and the SPA shows a "thanks — queued for review" toast.

### Admin handling

The admin inspector exposes reports two ways:

- **Per-user view** at `/admin/users/{id}/inspect` — shows the last 50 reports filed by that specific user.
- **Global queue** at `/admin/reports` — shows all reports across all users, filterable by status (`pending` / `dismissed` / `resolved` / `all`).

For each pending report there are three actions:

- **Dismiss** — the user was probably wrong, the translation is fine. Marks status `dismissed`. The entry is **not** modified. `flag_count` stays incremented (intentional — keeps a trail of disputed entries even when dismissed).
- **Delete entry** — actually delete the `WordLexicalEntry` or `WordNativeTranslation` row. Cascade has no effect on `Word` itself. Status → `resolved`. Subsequent users hitting the cache will trigger a fresh AI call.
- **Regenerate** — calls `translate_word(...)` again with `force=True`, which overwrites the cached entries in place using fresh AI output. Uses the **reporter's** mother tongue to drive the native side. Status → `resolved`. The `flag_count` is *not* reset (intentional — visible signal that this entry was previously contested).

There is **no automatic action**. Even if `flag_count` reaches double digits, the entry stays until admin clicks one of the three buttons.

### What we deliberately do not do

- We do not show users each other's reports.
- We do not give the user feedback on whether their report was actioned. (Future work: notify on resolution.)
- We do not let users delete or edit their own reports after submission.
- We do not weight reports by user reputation — every user counts the same.
- We do not auto-hide entries above a `flag_count` threshold. This is intentional to avoid one bad actor (or a wave of users with the same wrong intuition) silently destroying a correct translation. The cost is that admin has to actually look at the queue.
