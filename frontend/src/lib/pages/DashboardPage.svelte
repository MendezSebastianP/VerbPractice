<script lang="ts">
  import { onMount } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import { navigate } from '../router';
  import type {
    DashboardPayload,
    LanguageEntry,
    PriorityQueueEntry,
    ThemeName,
    TranslationDisplayMode,
    UserSettings,
  } from '../types';

  export let csrfToken = '';
  export let theme: ThemeName = 'light';
  export let onTheme: (theme: ThemeName) => Promise<void> | void;
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;

  type ModeCard = DashboardPayload['mode_cards'][number];

  let loading = true;
  let error = '';
  let data: DashboardPayload | null = null;
  let settings: UserSettings | null = null;
  let languages: LanguageEntry[] = [];
  let priorityQueue: PriorityQueueEntry[] = [];

  let motherTongueCode = '';
  let learningLanguageCode = '';
  let displayMode: TranslationDisplayMode = 'partial';
  let forceUnlock = false;

  let advancedOpen = false;
  let savingTimer: ReturnType<typeof setTimeout> | null = null;
  let savingState: 'idle' | 'saving' | 'saved' | 'error' = 'idle';
  let hydrated = false;

  function mergedFocusItems(cards: ModeCard[]) {
    const byKey = new Map<string, ModeCard['focus_items'][number]>();
    for (const card of cards) {
      for (const item of card.focus_items) {
        const key = `${item.item_type}:${item.label}:${item.language_pair}`;
        const existing = byKey.get(key);
        if (!existing || item.probability > existing.probability) {
          byKey.set(key, item);
        }
      }
    }
    return [...byKey.values()].sort((l, r) => r.probability - l.probability).slice(0, 6);
  }

  function verbLabCards(cards: ModeCard[]): ModeCard[] {
    const verbCards = cards.filter((c) => c.mode === 'verb_translation' || c.mode === 'conjugation');
    if (!verbCards.length) return cards;

    const combined: ModeCard = {
      mode: 'verb_lab',
      title: 'Verb Lab',
      href: '/training/verbs',
      description: 'Verb translation drills and tense tables in one workspace.',
      pair_label: verbCards.map((c) => c.pair_label).find(Boolean) || 'Verb workspace',
      total: verbCards.reduce((s, c) => s + c.total, 0),
      unlocked: verbCards.reduce((s, c) => s + c.unlocked, 0),
      mastered: verbCards.reduce((s, c) => s + c.mastered, 0),
      practiced: verbCards.reduce((s, c) => s + c.practiced, 0),
      avg_probability: Math.round(
        verbCards.reduce((s, c) => s + c.avg_probability * Math.max(c.total, 1), 0)
          / verbCards.reduce((s, c) => s + Math.max(c.total, 1), 0),
      ),
      focus_items: mergedFocusItems(verbCards),
    };

    const output: ModeCard[] = [];
    let inserted = false;
    for (const card of cards) {
      if (card.mode === 'verb_translation' || card.mode === 'conjugation') {
        if (!inserted) {
          output.push(combined);
          inserted = true;
        }
        continue;
      }
      output.push(card);
    }
    return output;
  }

  function sessionLabel(mode: string): string {
    if (mode === 'word_translation') return 'Words';
    if (mode === 'verb_translation') return 'Verb Lab · Translation';
    if (mode === 'conjugation') return 'Verb Lab · Tables';
    return mode.replace('_', ' ');
  }

  $: cards = data ? verbLabCards(data.mode_cards) : [];

  async function load(): Promise<void> {
    loading = true;
    error = '';
    try {
      const [d, s, langs, queue] = await Promise.all([
        api.dashboard(),
        api.getSettings(),
        api.listLanguages(),
        api.priorityQueue().catch(() => ({ entries: [] as PriorityQueueEntry[] })),
      ]);
      data = d;
      settings = s;
      languages = langs.languages;
      priorityQueue = queue.entries;
      motherTongueCode = s.mother_tongue?.code ?? '';
      learningLanguageCode = s.learning_language?.code ?? '';
      displayMode = s.translation_display_mode;
      forceUnlock = s.force_unlock_added_words;
      hydrated = true;
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to load home';
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
        if (savingState === 'saved') savingState = 'idle';
      }, 1200);
    } catch (err) {
      savingState = 'error';
      notify(err instanceof ApiError ? err.message : 'Unable to save settings', 'error');
    }
  }

  function scheduleSave(): void {
    if (!hydrated) return;
    if (savingTimer) clearTimeout(savingTimer);
    savingTimer = setTimeout(() => void persist(), 400);
  }

  function swapPair(): void {
    const next = motherTongueCode;
    motherTongueCode = learningLanguageCode;
    learningLanguageCode = next;
  }

  $: motherTongueCode, learningLanguageCode, displayMode, forceUnlock, scheduleSave();

  function statusLabel(): string {
    if (savingState === 'saving') return 'Saving…';
    if (savingState === 'saved') return 'Saved';
    if (savingState === 'error') return 'Save failed';
    return '';
  }

  onMount(load);
</script>

<style>
  .home-stack {
    max-width: 560px;
    margin-inline: auto;
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .home-stack .mode-card-grid {
    grid-template-columns: 1fr;
  }

  .pair-row {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: end;
    gap: 0.5rem;
  }

  .pair-row .answer-input {
    width: 100%;
  }

  .swap-button {
    background: transparent;
    border: 1px solid currentColor;
    border-radius: 999px;
    width: 2.25rem;
    height: 2.25rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    opacity: 0.6;
    transition: opacity 120ms ease;
  }

  .swap-button:hover {
    opacity: 1;
  }

  .advanced-toggle {
    background: transparent;
    border: 0;
    padding: 0.5rem 0;
    cursor: pointer;
    text-align: left;
    font: inherit;
    color: inherit;
    opacity: 0.75;
  }

  .advanced-toggle:hover {
    opacity: 1;
  }

  .advanced-body {
    margin-top: 0.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
  }

  .save-chip {
    min-height: 1.25rem;
    font-size: 0.75rem;
    opacity: 0.7;
  }

  .settings-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }
</style>

{#if loading}
  <section class="dashboard-grid loading-grid">
    <div class="glass-panel skeleton-card"></div>
    <div class="glass-panel skeleton-card"></div>
  </section>
{:else if error}
  <section class="glass-panel">
    <div class="feedback-banner error-banner">{error}</div>
  </section>
{:else if data && settings}
  <section class="home-stack" in:fade={{ duration: 180 }}>
    <article class="glass-panel strong-panel">
      <div class="section-head">
        <p class="eyebrow">Settings</p>
        <span class="save-chip">{statusLabel()}</span>
      </div>

      <div class="settings-row" style="margin-top: 0.85rem;">
        <p class="eyebrow">Theme</p>
        <div class="theme-switcher" role="group" aria-label="Theme switcher">
          <button class:theme-on={theme === 'light'} type="button" aria-label="Sun mode" title="Sun mode" on:click={() => onTheme('light')}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="4.25" fill="none" stroke="currentColor" stroke-width="1.8"></circle>
              <path d="M12 2.75v2.5M12 18.75v2.5M21.25 12h-2.5M5.25 12h-2.5M18.55 5.45l-1.8 1.8M7.25 16.75l-1.8 1.8M18.55 18.55l-1.8-1.8M7.25 7.25l-1.8-1.8" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="1.8"></path>
            </svg>
          </button>
          <button class:theme-on={theme === 'dark'} type="button" aria-label="Moon mode" title="Moon mode" on:click={() => onTheme('dark')}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M15.8 3.8a7.9 7.9 0 1 0 4.4 14.6A8.8 8.8 0 0 1 15.8 3.8Z" fill="none" stroke="currentColor" stroke-linejoin="round" stroke-width="1.8"></path>
            </svg>
          </button>
          <button class:theme-on={theme === 'arcade'} type="button" aria-label="Arcade mode" title="Arcade mode" on:click={() => onTheme('arcade')}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <rect x="4.5" y="6" width="15" height="12" rx="3" fill="none" stroke="currentColor" stroke-width="1.8"></rect>
              <path d="M9 12h4M11 10v4" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="1.8"></path>
              <circle cx="16.5" cy="10.5" r="1" fill="currentColor"></circle>
              <circle cx="14.5" cy="13.5" r="1" fill="currentColor"></circle>
            </svg>
          </button>
        </div>
      </div>

      <p class="eyebrow" style="margin-top: 0.85rem;">Language pair</p>
      <div class="pair-row" style="margin-top: 0.4rem;">
        <div>
          <label for="mother-tongue" class="eyebrow">Mother</label>
          <select id="mother-tongue" class="answer-input" bind:value={motherTongueCode}>
            <option value="">—</option>
            {#each languages as lang}
              <option value={lang.code}>{lang.name}</option>
            {/each}
          </select>
        </div>
        <button
          class="swap-button"
          type="button"
          aria-label="Swap mother tongue and learning language"
          title="Swap"
          on:click={swapPair}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M7 7h12M7 7l3-3M7 7l3 3M17 17H5M17 17l-3-3M17 17l-3 3" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8"/>
          </svg>
        </button>
        <div>
          <label for="learning-lang" class="eyebrow">Learning</label>
          <select id="learning-lang" class="answer-input" bind:value={learningLanguageCode}>
            <option value="">—</option>
            {#each languages as lang}
              <option value={lang.code}>{lang.name}</option>
            {/each}
          </select>
        </div>
      </div>

      <button
        class="advanced-toggle eyebrow"
        type="button"
        aria-expanded={advancedOpen}
        on:click={() => (advancedOpen = !advancedOpen)}
      >
        {advancedOpen ? '▾' : '▸'} Advanced
      </button>

      {#if advancedOpen}
        <div class="advanced-body">
          <div>
            <p class="eyebrow">Translation display mode</p>
            <div class="tag-row">
              <label class="option-chip" class:active-link={displayMode === 'mother_full'}>
                <input type="radio" bind:group={displayMode} value="mother_full" style="display: none;" />
                Full in mother
              </label>
              <label class="option-chip" class:active-link={displayMode === 'partial'}>
                <input type="radio" bind:group={displayMode} value="partial" style="display: none;" />
                Partial
              </label>
              <label class="option-chip" class:active-link={displayMode === 'learning_full'}>
                <input type="radio" bind:group={displayMode} value="learning_full" style="display: none;" />
                Full in learning
              </label>
            </div>
          </div>

          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <input id="force-unlock" type="checkbox" bind:checked={forceUnlock} />
            <label for="force-unlock">Force-add new words directly to the active pool</label>
          </div>
        </div>
      {/if}
    </article>

    <section class="mode-card-grid">
      {#each cards as card, index}
        <button class="mode-card glass-panel" type="button" on:click={() => navigate(card.href)} in:fly={{ y: 16, duration: 180, delay: index * 40 }}>
          <div class="mode-card-top">
            <div>
              <p class="eyebrow">{card.pair_label}</p>
              <h2>{card.title}</h2>
            </div>
            <span class="pill-chip">{card.practiced} practiced</span>
          </div>
          <p class="mode-description">{card.description}</p>
          <div class="metric-grid tight-grid">
            <div class="stat-card compact-stat"><span>Unlocked</span><strong>{card.unlocked}</strong></div>
            <div class="stat-card compact-stat"><span>Mastered</span><strong>{card.mastered}</strong></div>
            <div class="stat-card compact-stat"><span>Pressure</span><strong>{card.avg_probability}</strong></div>
          </div>
          <div class="tag-row">
            {#each card.focus_items.slice(0, 3) as item}
              <span class="mini-tag">{item.label}</span>
            {:else}
              <span class="mini-tag muted-tag">Start a session to surface focus items.</span>
            {/each}
          </div>
        </button>
      {/each}
    </section>

    {#if data.active_sessions.length}
      <article class="glass-panel">
        <div class="section-head"><p class="eyebrow">Resume</p></div>
        <div class="resume-grid">
          {#each data.active_sessions as session}
            <button class="resume-card" type="button" on:click={() => navigate(session.href)}>
              <strong>{session.title}</strong>
              <span>{session.language_pair}</span>
              <span>{session.progress_current}/{session.progress_total}</span>
            </button>
          {/each}
        </div>
      </article>
    {/if}

    <article class="glass-panel">
      <div class="section-head">
        <div>
          <p class="eyebrow">History</p>
          <h2>Recent sessions</h2>
        </div>
      </div>
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Mode</th>
              <th>Pair</th>
              <th>Score</th>
              <th>Completed</th>
            </tr>
          </thead>
          <tbody>
            {#each data.recent_sessions as session}
              <tr>
                <td>{sessionLabel(session.mode)}</td>
                <td>{session.language_pair}</td>
                <td>{session.score === null ? '-' : `${session.score.toFixed(1)}%`}</td>
                <td>{session.completed_at ? new Date(session.completed_at).toLocaleString() : '-'}</td>
              </tr>
            {:else}
              <tr><td colspan="4">No completed sessions yet.</td></tr>
            {/each}
          </tbody>
        </table>
      </div>
    </article>

    <article class="glass-panel">
      <div class="section-head">
        <div>
          <p class="eyebrow">Queue</p>
          <h2>Priority words</h2>
        </div>
        <button class="ghost-button" type="button" on:click={() => navigate('/add-word')}>+ Add</button>
      </div>
      {#if priorityQueue.length === 0}
        <p class="empty-copy">No words queued. Add words from the Add Word page.</p>
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
