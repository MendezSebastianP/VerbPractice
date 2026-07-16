<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import { navigate } from '../router';
  import { setProfile } from '../profile';
  import PlayClear from '../components/PlayClear.svelte';
  import PlayGrid from '../components/PlayGrid.svelte';
  import PlaySaffronRelay from '../components/PlaySaffronRelay.svelte';
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
  export let onShowShortcuts: (visible: boolean) => void = () => {};
  export let onLogout: () => Promise<void> | void;
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
  let showShortcuts = true;

  let advancedOpen = false;
  let savingTimer: ReturnType<typeof setTimeout> | null = null;
  let savingState: 'idle' | 'saving' | 'saved' | 'error' = 'idle';
  let hydrated = false;

  const QUEUE_PREVIEW = 4;
  const LOG_PREVIEW = 5;

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

  function scoreColor(score: number | null): string {
    if (score === null) return 'var(--muted)';
    if (score >= 80) return 'var(--accent-strong)';
    if (score >= 50) return 'var(--muted)';
    return 'var(--danger)';
  }

  // Small pause so the control's fire flash is visible before the route swap
  function queueNav(href: string): void {
    window.setTimeout(() => navigate(href), 230);
  }

  $: cards = data ? verbLabCards(data.mode_cards) : [];
  $: isArcade = theme === 'arcade';

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
      setProfile(d.user.profile);
      motherTongueCode = s.mother_tongue?.code ?? '';
      learningLanguageCode = s.learning_language?.code ?? '';
      displayMode = s.translation_display_mode;
      forceUnlock = s.force_unlock_added_words;
      showShortcuts = s.show_shortcuts;
      onShowShortcuts(showShortcuts);
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
        show_shortcuts: showShortcuts,
      });
      onShowShortcuts(settings.show_shortcuts);
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

  $: motherTongueCode, learningLanguageCode, displayMode, forceUnlock, showShortcuts, scheduleSave();

  function statusLabel(): string {
    if (savingState === 'saving') return 'Saving…';
    if (savingState === 'saved') return 'Saved';
    if (savingState === 'error') return 'Save failed';
    return '';
  }

  onMount(load);
</script>

{#if loading}
  <section class="home-shell">
    <div class="glass-panel skeleton-card tall-skeleton"></div>
  </section>
{:else if error}
  <section class="home-shell">
    <div class="glass-panel">
      <div class="feedback-banner error-banner">{error}</div>
    </div>
  </section>
{:else if data && settings}
  <section class="home-shell" in:fade={{ duration: 180 }}>
    <div class="home-stack">
      {#if data.active_sessions.length}
        <article class="glass-panel">
          <p class="eyebrow" style="margin-bottom: 0.6rem;">Resume</p>
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

      {#each cards as card, index (card.mode)}
        <article class="glass-panel strong-panel stage-card">
          <div class="stage-top">
            <div>
              <p class="eyebrow">Stage {String(index + 1).padStart(2, '0')} · {card.pair_label}</p>
              <h2 class="stage-title">{card.title}</h2>
            </div>
            <span class="pill-chip">{card.practiced} practiced</span>
          </div>
          <p class="mode-description">{card.description}</p>
          <div class="stage-stats">
            <div class="stage-stat">
              <span>Unlocked</span>
              <strong>{card.unlocked}</strong>
            </div>
            <div class="stage-stat">
              <span>Mastered</span>
              <strong>{card.mastered}</strong>
            </div>
            <div class="stage-stat stat-pressure">
              <span>Pressure</span>
              <strong>{card.avg_probability}</strong>
            </div>
          </div>
          <div class="stage-play">
            {#if isArcade}
              <PlayGrid label="PLAY" rows={3} cell={16} gap={5} fontSize={11} resetAfterFire on:fire={() => queueNav(card.href)} />
            {:else if theme === 'light'}
              <PlayClear label="PLAY" rows={3} cell={16} gap={5} fontSize={11} resetAfterFire on:fire={() => queueNav(card.href)} />
            {:else}
              <PlaySaffronRelay label="PLAY" width={205} height={58} fontSize={11} resetAfterFire on:fire={() => queueNav(card.href)} />
            {/if}
          </div>
        </article>
      {/each}

      <article class="glass-panel">
        <div class="section-head">
          <p class="eyebrow">Play log · Recent sessions</p>
        </div>
        {#if data.recent_sessions.length}
          <div class="log-list">
            {#each data.recent_sessions.slice(0, LOG_PREVIEW) as session}
              <div class="log-row">
                <span class="log-mode">{sessionLabel(session.mode)}</span>
                <span class="pill-chip log-pair">{session.language_pair}</span>
                <span class="log-score" style={`color: ${scoreColor(session.score)};`}>
                  {session.score === null ? '—' : `${session.score.toFixed(1)}%`}
                </span>
                <span class="log-when">{session.completed_at ? new Date(session.completed_at).toLocaleString() : '—'}</span>
              </div>
            {/each}
          </div>
        {:else}
          <p class="empty-copy">No completed sessions yet — press play above.</p>
        {/if}
      </article>

      <article class="glass-panel">
        <div class="section-head">
          <p class="eyebrow">Queue · Priority words</p>
          <button class="ghost-button queue-add" type="button" on:click={() => navigate('/add-word')}>+ Add</button>
        </div>
        {#if priorityQueue.length === 0}
          <p class="empty-copy">No words queued. Add words from the Add Word page.</p>
        {:else}
          <div class="list-stack">
            {#each priorityQueue.slice(0, QUEUE_PREVIEW) as entry}
              <div class="list-row">
                <div class="queue-item-main">
                  <div class="queue-item-head">
                    <span class="queue-word">{entry.word_text}</span>
                    <span class="pill-chip queue-pair-chip">{entry.language_pair}</span>
                  </div>
                  {#if entry.context_hint}
                    <p class="queue-note">&ldquo;{entry.context_hint}&rdquo;</p>
                  {/if}
                </div>
                <div class="row-metrics">
                  <span>{new Date(entry.added_at).toLocaleDateString()}</span>
                </div>
              </div>
            {/each}
          </div>
          {#if priorityQueue.length > QUEUE_PREVIEW}
            <button class="text-switch more-note" type="button" on:click={() => navigate('/add-word')}>
              +{priorityQueue.length - QUEUE_PREVIEW} more in Add Word →
            </button>
          {/if}
        {/if}
      </article>

      <article class="glass-panel strong-panel">
        <div class="section-head">
          <p class="eyebrow">Player console · Settings</p>
          <span class="save-chip">{statusLabel()}</span>
        </div>

        <div class="settings-row" style="margin-top: 0.85rem;">
          <p class="eyebrow">Theme</p>
          <div class="theme-switcher" role="group" aria-label="Theme switcher">
            <button class:theme-on={theme === 'light'} type="button" aria-label="Clear mode" title="Clear mode" on:click={() => onTheme('light')}>
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

        <div class="settings-row shortcut-setting-row">
          <div class="shortcut-setting-copy">
            <p class="eyebrow">Interface</p>
            <strong>Show shortcuts</strong>
            <small>Display keyboard hints beside controls. Shortcuts keep working when hidden.</small>
          </div>
          <label class="setting-switch">
            <input
              type="checkbox"
              bind:checked={showShortcuts}
              aria-label="Show keyboard shortcuts"
              on:change={(event) => onShowShortcuts((event.currentTarget as HTMLInputElement).checked)}
            />
            <span aria-hidden="true"><i></i></span>
            <em>{showShortcuts ? 'Shown' : 'Hidden'}</em>
          </label>
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
                  Full in mother tongue
                </label>
                <label class="option-chip" class:active-link={displayMode === 'partial'}>
                  <input type="radio" bind:group={displayMode} value="partial" style="display: none;" />
                  Partial
                </label>
                <label class="option-chip" class:active-link={displayMode === 'learning_full'}>
                  <input type="radio" bind:group={displayMode} value="learning_full" style="display: none;" />
                  Full in learning language
                </label>
              </div>
            </div>

            <div style="display: flex; align-items: center; gap: 0.6rem;">
              <input id="force-unlock" type="checkbox" bind:checked={forceUnlock} />
              <label for="force-unlock">Force-add new words directly to the active pool</label>
            </div>
          </div>
        {/if}

        <div class="dashboard-logout-row">
          <button class="ghost-button" type="button" on:click={onLogout}>Logout</button>
        </div>
      </article>
    </div>
  </section>
{/if}

<style>
  .home-shell {
    max-width: 720px;
    margin-inline: auto;
    width: 100%;
  }

  .home-stack {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  /* Stage cards — the hero of the page */
  .stage-card {
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
  }

  .stage-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .stage-title {
    font-family: var(--marquee);
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin: 0.3rem 0 0;
    color: var(--text);
  }

  :global(html[data-theme='arcade']) .stage-title {
    font-size: 1rem;
    line-height: 1.6;
    text-shadow: 0 0 12px color-mix(in srgb, var(--accent) 90%, transparent);
  }

  .stage-stats {
    display: flex;
    gap: 1.75rem;
    flex-wrap: wrap;
  }

  .stage-stat {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
  }

  .stage-stat span {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    font-family: var(--mono);
    color: var(--muted);
  }

  .stage-stat strong {
    font-family: var(--display);
    font-size: 1.35rem;
    line-height: 1;
    color: var(--text);
  }

  :global(html[data-theme='arcade']) .stage-stat strong {
    font-family: var(--mono);
    font-size: 1.6rem;
  }

  .stat-pressure strong {
    color: var(--danger);
  }

  .stage-play {
    display: flex;
    justify-content: center;
    padding-top: 0.35rem;
  }

  /* Play log — slim rows instead of a table */
  .log-list {
    display: flex;
    flex-direction: column;
    margin-top: 0.5rem;
  }

  .log-row {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.55rem 0.25rem;
    border-bottom: 1px solid var(--line);
    min-width: 0;
  }

  .log-row:last-child {
    border-bottom: 0;
  }

  .log-mode {
    font-weight: 600;
    color: var(--text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .log-pair {
    padding: 0 0.5rem;
    font-size: 0.62rem;
    flex-shrink: 0;
  }

  .log-score {
    margin-left: auto;
    font-family: var(--mono);
    font-weight: 700;
    font-size: 0.9rem;
    flex-shrink: 0;
  }

  .log-when {
    font-size: 0.72rem;
    color: var(--muted);
    flex-shrink: 0;
  }

  .queue-add {
    padding: 0.35rem 0.85rem;
    font-size: 0.8rem;
  }

  .more-note {
    margin-top: 0.6rem;
    color: var(--muted);
    font-size: 0.8rem;
  }

  .queue-item-main {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 0;
  }

  .queue-item-head {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    min-width: 0;
  }

  .queue-word {
    font-weight: 600;
    color: var(--text);
  }

  .queue-pair-chip {
    padding: 0 0.5rem;
    font-size: 0.7rem;
  }

  .queue-note {
    font-style: italic;
    color: var(--muted);
    font-size: 0.85rem;
    margin: 0;
  }

  /* Player console */
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
    border: 1px solid var(--line);
    border-radius: 999px;
    width: 2.25rem;
    height: 2.25rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: var(--accent);
    transition: background-color 200ms ease, color 200ms ease, transform 300ms ease, border-color 200ms ease;
  }

  .swap-button:hover {
    background: var(--accent);
    color: white;
    border-color: transparent;
    transform: rotate(180deg);
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

  .shortcut-setting-row {
    margin-top: 0.85rem;
    padding: 0.8rem 0;
    border-top: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
  }

  .shortcut-setting-copy {
    display: grid;
    gap: 0.18rem;
  }

  .shortcut-setting-copy p {
    margin: 0;
  }

  .shortcut-setting-copy strong {
    color: var(--text);
    font-size: 0.95rem;
  }

  .shortcut-setting-copy small {
    max-width: 25rem;
    color: var(--muted);
    font-size: 0.78rem;
    line-height: 1.45;
  }

  .setting-switch {
    display: grid;
    justify-items: center;
    gap: 0.3rem;
    flex: 0 0 auto;
    cursor: pointer;
  }

  .setting-switch input {
    position: absolute;
    width: 1px;
    height: 1px;
    opacity: 0;
  }

  .setting-switch > span {
    position: relative;
    width: 3.15rem;
    height: 1.72rem;
    border: 1px solid var(--line-strong);
    border-radius: 999px;
    background: color-mix(in srgb, var(--surface-strong) 86%, black);
    transition: border-color 160ms ease, background 160ms ease;
  }

  .setting-switch i {
    position: absolute;
    top: 0.2rem;
    left: 0.2rem;
    width: 1.2rem;
    height: 1.2rem;
    border-radius: 50%;
    background: var(--muted);
    transition: transform 180ms cubic-bezier(.2, .8, .2, 1), background 160ms ease;
  }

  .setting-switch input:checked + span {
    border-color: color-mix(in srgb, var(--accent) 72%, white);
    background: color-mix(in srgb, var(--accent) 28%, var(--surface-strong));
  }

  .setting-switch input:checked + span i {
    transform: translateX(1.42rem);
    background: var(--accent-strong);
  }

  .setting-switch input:focus-visible + span {
    outline: 3px solid color-mix(in srgb, var(--accent) 35%, transparent);
    outline-offset: 3px;
  }

  .setting-switch em {
    color: var(--muted);
    font-size: 0.7rem;
    font-style: normal;
    font-weight: 750;
  }

  .dashboard-logout-row {
    display: flex;
    justify-content: flex-end;
    margin-top: 1rem;
  }

  @media (max-width: 480px) {
    .log-when {
      display: none;
    }

    .shortcut-setting-row {
      align-items: flex-start;
    }
  }
</style>
