<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import type { LanguageEntry, PriorityQueueEntry, TranslationDisplayMode, UserSettings } from '../types';

  export let csrfToken = '';
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;

  let loading = true;
  let error = '';
  let settings: UserSettings | null = null;
  let languages: LanguageEntry[] = [];
  let priorityQueue: PriorityQueueEntry[] = [];

  let motherTongueCode = '';
  let learningLanguageCode = '';
  let displayMode: TranslationDisplayMode = 'partial';
  let forceUnlock = false;

  let savingTimer: ReturnType<typeof setTimeout> | null = null;
  let savingState: 'idle' | 'saving' | 'saved' | 'error' = 'idle';
  let hydrated = false;

  async function load(): Promise<void> {
    loading = true;
    error = '';
    try {
      const [s, langs, queue] = await Promise.all([
        api.getSettings(),
        api.listLanguages(),
        api.priorityQueue().catch(() => ({ entries: [] as PriorityQueueEntry[] })),
      ]);
      settings = s;
      languages = langs.languages;
      priorityQueue = queue.entries;
      motherTongueCode = s.mother_tongue?.code ?? '';
      learningLanguageCode = s.learning_language?.code ?? '';
      displayMode = s.translation_display_mode;
      forceUnlock = s.force_unlock_added_words;
      hydrated = true;
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to load settings';
    } finally {
      loading = false;
    }
  }

  async function persist(): Promise<void> {
    savingState = 'saving';
    try {
      settings = await api.patchSettings({
        csrf_token: csrfToken,
        mother_tongue_code: motherTongueCode || undefined,
        learning_language_code: learningLanguageCode || undefined,
        translation_display_mode: displayMode,
        force_unlock_added_words: forceUnlock,
      });
      savingState = 'saved';
      window.setTimeout(() => {
        if (savingState === 'saved') {
          savingState = 'idle';
        }
      }, 1200);
    } catch (err) {
      savingState = 'error';
      notify(err instanceof ApiError ? err.message : 'Unable to save settings', 'error');
    }
  }

  function scheduleSave(): void {
    if (!hydrated) {
      return;
    }
    if (savingTimer) {
      clearTimeout(savingTimer);
    }
    savingTimer = setTimeout(() => {
      void persist();
    }, 400);
  }

  // Auto-save whenever any controlled field changes
  $: motherTongueCode, learningLanguageCode, displayMode, forceUnlock, scheduleSave();

  function statusLabel(): string {
    if (savingState === 'saving') return 'Saving…';
    if (savingState === 'saved') return 'Saved';
    if (savingState === 'error') return 'Save failed';
    return 'Auto-saves on change';
  }

  onMount(load);
</script>

<style>
  .dashboard-stack {
    max-width: 980px;
    margin-inline: auto;
    width: 100%;
  }
</style>

{#if loading}
  <section class="dashboard-grid loading-grid">
    <div class="glass-panel skeleton-card"></div>
  </section>
{:else if error}
  <section class="glass-panel">
    <div class="feedback-banner error-banner">{error}</div>
  </section>
{:else if settings}
  <section class="dashboard-stack" in:fade={{ duration: 180 }}>
    <article class="glass-panel strong-panel">
      <div class="section-head">
        <div>
          <p class="eyebrow">Profile</p>
          <h1>Settings</h1>
        </div>
        <span class="pill-chip" class:reward-pill={savingState === 'saved'}>{statusLabel()}</span>
      </div>
      <p class="section-copy">
        Your mother tongue and main learning language drive defaults across the app. You can override the target
        language per word in the Add Word page, or pick any pair in the practice tile chooser.
      </p>

      <div class="dashboard-grid compact-dual" style="margin-top: 1rem;">
        <div>
          <label for="mother-tongue" class="eyebrow">Mother tongue</label>
          <select id="mother-tongue" class="answer-input" bind:value={motherTongueCode}>
            <option value="">— pick one —</option>
            {#each languages as lang}
              <option value={lang.code}>{lang.name}</option>
            {/each}
          </select>
        </div>
        <div>
          <label for="learning-lang" class="eyebrow">Main learning language</label>
          <select id="learning-lang" class="answer-input" bind:value={learningLanguageCode}>
            <option value="">— pick one —</option>
            {#each languages as lang}
              <option value={lang.code}>{lang.name}</option>
            {/each}
          </select>
        </div>
      </div>

      <div style="margin-top: 1rem;">
        <p class="eyebrow">Translation display mode</p>
        <div class="tag-row">
          <label class="option-chip" class:active-link={displayMode === 'mother_full'}>
            <input type="radio" bind:group={displayMode} value="mother_full" style="display: none;" />
            Full in mother tongue
          </label>
          <label class="option-chip" class:active-link={displayMode === 'partial'}>
            <input type="radio" bind:group={displayMode} value="partial" style="display: none;" />
            Partial (description in learning + synonyms in mother)
          </label>
          <label class="option-chip" class:active-link={displayMode === 'learning_full'}>
            <input type="radio" bind:group={displayMode} value="learning_full" style="display: none;" />
            Full in learning language
          </label>
        </div>
      </div>

      <div style="margin-top: 1rem; display: flex; align-items: center; gap: 0.75rem;">
        <input id="force-unlock" type="checkbox" bind:checked={forceUnlock} />
        <label for="force-unlock">
          Force-add new words directly to the active pool (skip the priority queue)
        </label>
      </div>
    </article>

    <article class="glass-panel">
      <div class="section-head">
        <div>
          <p class="eyebrow">Queue</p>
          <h2>Priority words waiting to unlock</h2>
        </div>
        <a class="ghost-button" href="/app/#/add-word">+ Add a word</a>
      </div>
      {#if priorityQueue.length === 0}
        <p class="empty-copy">No words in the priority queue. Add words from the Add Word page and they'll appear here until they unlock during practice.</p>
      {:else}
        <div class="list-stack">
          {#each priorityQueue as entry}
            <div class="list-row">
              <div>
                <strong>{entry.word_text}</strong>
                <p>{entry.language_pair}{entry.context_hint ? ` · ${entry.context_hint}` : ''}</p>
              </div>
              <div class="row-metrics">
                <span>{new Date(entry.added_at).toLocaleString()}</span>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </article>
  </section>
{/if}
