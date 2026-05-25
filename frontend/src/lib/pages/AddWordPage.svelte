<script lang="ts">
  import { onMount } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import type {
    AddWordResponse,
    AddedWordNotFound,
    AddedWordResult,
    LanguageEntry,
    UserSettings,
  } from '../types';

  export let csrfToken = '';
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;

  let loading = true;
  let error = '';
  let languages: LanguageEntry[] = [];
  let settings: UserSettings | null = null;

  let inputText = '';
  let contextHint = '';
  let learningLangCode = '';
  let adding = false;

  let result: AddedWordResult | null = null;
  let notFound: AddedWordNotFound | null = null;
  let expanding = false;
  let reportTarget: { entry_type: 'lexical' | 'native'; entry_id: number } | null = null;
  let reportReason = '';

  $: motherTongueName = settings?.mother_tongue?.name ?? '—';
  $: motherTongueCode = settings?.mother_tongue?.code ?? '';
  $: detectedMismatch =
    !!result &&
    !!result.detected_input_language &&
    result.detected_input_language.toUpperCase() !== result.learning_language_code.toUpperCase() &&
    result.detected_input_language.toUpperCase() !== motherTongueCode.toUpperCase();

  function isFoundResult(payload: AddWordResponse): payload is AddedWordResult {
    return payload.status !== 'not_found';
  }

  async function load(): Promise<void> {
    loading = true;
    error = '';
    try {
      const [langs, s] = await Promise.all([api.listLanguages(), api.getSettings()]);
      languages = langs.languages;
      settings = s;
      learningLangCode = s.learning_language?.code ?? '';
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to load';
    } finally {
      loading = false;
    }
  }

  async function addWord(textOverride?: string): Promise<void> {
    const text = (textOverride ?? inputText).trim();
    if (!text) {
      return;
    }
    if (!settings?.mother_tongue) {
      notify('Set your mother tongue in Settings first.', 'error');
      return;
    }
    if (!learningLangCode) {
      notify('Pick a target language.', 'error');
      return;
    }
    adding = true;
    result = null;
    notFound = null;
    try {
      const response = await api.addWord({
        input_text: text,
        context: contextHint.trim() || undefined,
        learning_lang_code: learningLangCode,
        csrf_token: csrfToken,
      });
      if (isFoundResult(response)) {
        result = response;
        inputText = '';
        contextHint = '';
        if (response.status === 'corrected') {
          notify(`Corrected "${response.original_input}" → "${response.text}".`, 'info');
        } else {
          notify(`Added "${response.text}".`, 'success');
        }
      } else {
        notFound = response;
        inputText = text;
      }
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to add word', 'error');
    } finally {
      adding = false;
    }
  }

  async function expand(): Promise<void> {
    if (!result) {
      return;
    }
    expanding = true;
    try {
      const { extended_content } = await api.expandWord(result.word_id, csrfToken);
      result = { ...result, lexical: { ...result.lexical, extended_content } };
      notify('Added more info.', 'success');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to expand', 'error');
    } finally {
      expanding = false;
    }
  }

  async function submitReport(): Promise<void> {
    if (!result || !reportTarget) {
      return;
    }
    try {
      await api.reportTranslation(result.word_id, {
        entry_type: reportTarget.entry_type,
        entry_id: reportTarget.entry_id,
        reason: reportReason.trim() || undefined,
        csrf_token: csrfToken,
      });
      reportTarget = null;
      reportReason = '';
      notify('Thanks — queued for review.', 'success');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to submit report', 'error');
    }
  }

  function resetForAnother(): void {
    result = null;
    notFound = null;
    reportTarget = null;
    reportReason = '';
    inputText = '';
    contextHint = '';
  }

  function reportDefinition(): void {
    if (!result) {
      return;
    }
    reportTarget = { entry_type: 'lexical', entry_id: result.lexical.id };
  }

  function trySuggestion(s: string): void {
    inputText = s;
    void addWord(s);
  }

  function languageName(code: string): string {
    return languages.find((l) => l.code === code.toUpperCase())?.name ?? code;
  }

  function swapDetected(): void {
    if (!result || !result.detected_input_language) {
      return;
    }
    const newTarget = result.detected_input_language.toUpperCase();
    if (newTarget === motherTongueCode.toUpperCase()) {
      notify('Detected mother tongue — pick a different target.', 'error');
      return;
    }
    learningLangCode = newTarget;
    void addWord(result.original_input || result.text);
  }

  onMount(load);
</script>

{#if loading}
  <section class="dashboard-grid loading-grid">
    <div class="glass-panel skeleton-card tall-skeleton"></div>
  </section>
{:else if error}
  <section class="glass-panel">
    <div class="feedback-banner error-banner">{error}</div>
  </section>
{:else}
  <section class="trainer-shell" in:fade={{ duration: 180 }}>
    <article class="glass-panel strong-panel trainer-card">
      <div class="section-head">
        <div>
          <p class="eyebrow">Vocabulary</p>
          <h1>Add a word</h1>
        </div>
      </div>
      <p class="section-copy">
        Type a word — in your target language or your mother tongue. The AI figures out the right canonical form,
        generates a definition + 1–3 translations, and drops the word into your priority queue.
      </p>

      {#if !settings?.mother_tongue}
        <div class="feedback-banner info-banner" style="margin-top: 0.75rem;">
          Set your mother tongue in <a href="/app/#/settings">Settings</a> first.
        </div>
      {/if}

      <form class="answer-form" on:submit|preventDefault={() => addWord()} style="margin-top: 1rem;">
        <div class="toggle-cluster">
          <div class="toggle-group">
            <span class="toggle-label">Target language</span>
            <div class="option-row">
              {#each languages as lang}
                <button
                  type="button"
                  class:option-on={learningLangCode === lang.code}
                  class="option-chip"
                  on:click={() => (learningLangCode = lang.code)}
                  disabled={settings?.mother_tongue?.code === lang.code}
                  title={settings?.mother_tongue?.code === lang.code ? 'This is your mother tongue' : ''}
                >
                  {lang.name}
                </button>
              {/each}
            </div>
            <p class="section-copy" style="margin-top: 0.4rem; font-size: 0.85rem; opacity: 0.7;">
              The word will be stored in this language; translations go into <strong>{motherTongueName}</strong>.
            </p>
          </div>
        </div>

        <div class="question-stage" style="margin-top: 1.25rem;">
          <p class="eyebrow">Word or short phrase</p>
          <input
            class="answer-input"
            bind:value={inputText}
            type="text"
            placeholder="e.g. ephemeral"
            disabled={adding}
            style="font-size: 1.1rem;"
          />
        </div>

        <div style="margin-top: 0.75rem;">
          <p class="eyebrow">Optional context</p>
          <input
            class="answer-input"
            bind:value={contextHint}
            type="text"
            placeholder="e.g. 'in academic writing' or 'bank — riverside, not financial'"
            disabled={adding}
          />
        </div>

        <div class="hero-actions" style="margin-top: 1rem;">
          <button class="primary-button" type="submit" disabled={adding || !inputText.trim() || !learningLangCode}>
            {adding ? 'Generating…' : 'Add to my queue'}
          </button>
        </div>
      </form>
    </article>

    {#if notFound}
      <article class="glass-panel" in:fly={{ y: 20, duration: 200 }} style="margin-top: 1.5rem;">
        <div class="section-head">
          <div>
            <p class="eyebrow">Not found</p>
            <h2>"{notFound.original_input}"</h2>
          </div>
          <span class="pill-chip">{notFound.learning_language_code}</span>
        </div>
        <p class="section-copy">
          We couldn't find that word in <strong>{languageName(notFound.learning_language_code)}</strong>. Check the
          spelling, or pick one of the suggestions below.
        </p>

        {#if notFound.suggestions.length}
          <p class="eyebrow" style="margin-top: 0.75rem;">Did you mean?</p>
          <div class="tag-row">
            {#each notFound.suggestions as s}
              <button class="option-chip" type="button" on:click={() => trySuggestion(s)}>
                {s}
              </button>
            {/each}
          </div>
        {/if}

        <div class="trainer-actions" style="margin-top: 1rem;">
          <button class="ghost-button" type="button" on:click={resetForAnother}>Start over</button>
        </div>
      </article>
    {/if}

    {#if result}
      <article class="glass-panel" in:fly={{ y: 20, duration: 200 }} style="margin-top: 1.5rem;">
        <div class="section-head">
          <div>
            <p class="eyebrow">
              {result.learning_language_code} → {result.mother_tongue_code}
              {#if result.status === 'corrected'}· corrected{/if}
              {#if result.status === 'ambiguous'}· multiple senses{/if}
            </p>
            <h2>{result.text}</h2>
          </div>
          {#if result.force_unlocked}
            <span class="pill-chip reward-pill">unlocked now</span>
          {:else}
            <span class="pill-chip">queued</span>
          {/if}
        </div>

        {#if result.status === 'corrected'}
          <div class="feedback-banner info-banner" style="margin-top: 0.5rem;">
            We corrected <strong>"{result.original_input}"</strong> → <strong>"{result.text}"</strong>.
          </div>
        {/if}

        {#if detectedMismatch}
          <div class="feedback-banner info-banner" style="margin-top: 0.5rem;">
            That looked like <strong>{languageName(result.detected_input_language ?? '')}</strong>. Want to switch the
            target language and try again?
            <button class="ghost-button" type="button" on:click={swapDetected} style="margin-left: 0.5rem;">
              Switch target → {languageName(result.detected_input_language ?? '')}
            </button>
          </div>
        {/if}

        <div class="list-stack" style="margin-top: 0.5rem;">
          <div>
            <p class="eyebrow">Definition</p>
            <p>{result.lexical.definition}</p>
          </div>

          {#if result.natives.length}
            <div>
              <p class="eyebrow">Translation{result.natives.length > 1 ? 's' : ''}</p>
              <div class="list-stack">
                {#each result.natives as native}
                  <div class="list-row">
                    <div>
                      <strong>{native.translation}</strong>
                      {#if native.note}
                        <p style="opacity: 0.75; margin: 0.15rem 0 0;"><em>{native.note}</em></p>
                      {/if}
                    </div>
                    <div class="row-metrics">
                      <button
                        class="ghost-button"
                        type="button"
                        on:click={() => (reportTarget = { entry_type: 'native', entry_id: native.id })}
                        title="Report this translation"
                        style="font-size: 0.8rem;"
                      >
                        report
                      </button>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}

          {#if result.general_note}
            <div>
              <p class="eyebrow">Note</p>
              <p><em>{result.general_note}</em></p>
            </div>
          {/if}

          {#if result.lexical.synonyms?.length}
            <div>
              <p class="eyebrow">Synonyms</p>
              <div class="tag-row">
                {#each result.lexical.synonyms as syn}
                  <span class="mini-tag" title={syn.gloss || ''}>{syn.text}</span>
                {/each}
              </div>
            </div>
          {/if}

          {#if result.lexical.examples?.length}
            <div>
              <p class="eyebrow">Examples</p>
              <ul style="margin: 0; padding-left: 1.25rem;">
                {#each result.lexical.examples as ex}
                  <li style="margin-bottom: 0.25rem;">{ex}</li>
                {/each}
              </ul>
            </div>
          {/if}

          {#if result.suggested_tags?.length}
            <div>
              <p class="eyebrow">Tags</p>
              <div class="tag-row">
                {#each result.suggested_tags as t}
                  <span class="mini-tag">{t}</span>
                {/each}
              </div>
            </div>
          {/if}

          {#if result.lexical.extended_content}
            <div>
              <p class="eyebrow">More info</p>
              <p style="white-space: pre-wrap;">{result.lexical.extended_content}</p>
            </div>
          {/if}
        </div>

        <div class="trainer-actions" style="margin-top: 1rem;">
          <button class="secondary-button" type="button" on:click={expand} disabled={expanding}>
            {expanding ? 'Loading…' : 'More info'}
          </button>
          <button
            class="ghost-button"
            type="button"
            on:click={reportDefinition}
          >
            Report definition
          </button>
          <button class="ghost-button" type="button" on:click={resetForAnother}>
            Add another
          </button>
        </div>

        {#if reportTarget}
          <div class="glass-panel" style="margin-top: 0.75rem; padding: 0.75rem;">
            <p class="eyebrow">
              Reporting the {reportTarget.entry_type === 'lexical' ? 'definition' : 'translation'}
            </p>
            <input
              class="answer-input"
              bind:value={reportReason}
              type="text"
              placeholder="Optional: what's wrong?"
            />
            <div class="hero-actions" style="margin-top: 0.5rem;">
              <button class="primary-button" type="button" on:click={submitReport}>Submit</button>
              <button
                class="ghost-button"
                type="button"
                on:click={() => {
                  reportTarget = null;
                  reportReason = '';
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        {/if}
      </article>
    {/if}
  </section>
{/if}
