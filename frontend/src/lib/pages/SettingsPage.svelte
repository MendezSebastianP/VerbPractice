<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import { navigate } from '../router';
  import { onboarding, restartOnboarding } from '../onboardingStore';
  import { FEATURE_CHAIN, chainComplete } from '../components/onboarding/onboarding';
  import type {
    LanguageEntry,
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

  let loading = true;
  let error = '';
  let settings: UserSettings | null = null;
  let languages: LanguageEntry[] = [];

  let motherTongueCode = '';
  let learningLanguageCode = '';
  let displayMode: TranslationDisplayMode = 'partial';
  let forceUnlock = false;
  let showShortcuts = true;

  let advancedOpen = false;

  // --- tutorial ------------------------------------------------------------
  let confirmingRestart = false;

  $: tutorialDone = chainComplete($onboarding);
  $: tutorialProgress = `${$onboarding.completed.length} of ${FEATURE_CHAIN.length} drills`;

  async function requestRestart(): Promise<void> {
    // Restarting re-locks drills, so it asks once before doing it.
    if (!confirmingRestart) {
      confirmingRestart = true;
      return;
    }
    confirmingRestart = false;
    // Wait for the server: the reset also abandons any running drill, and
    // navigating before that lands on the old session's game screen.
    await restartOnboarding();
    notify('Tutorial restarted from the beginning.', 'success');
    navigate('/training/words');
  }
  let savingTimer: ReturnType<typeof setTimeout> | null = null;
  let savingState: 'idle' | 'saving' | 'saved' | 'error' = 'idle';
  let hydrated = false;

  async function load(): Promise<void> {
    loading = true;
    error = '';
    try {
      const [s, langs] = await Promise.all([api.getSettings(), api.listLanguages()]);
      settings = s;
      languages = langs.languages;
      motherTongueCode = s.mother_tongue?.code ?? '';
      learningLanguageCode = s.learning_language?.code ?? '';
      displayMode = s.translation_display_mode;
      forceUnlock = s.force_unlock_added_words;
      showShortcuts = s.show_shortcuts;
      onShowShortcuts(showShortcuts);
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

  // Must be a reactive declaration, not a function called from the template:
  // `{statusLabel()}` reads no reactive variable in the expression itself, so
  // Svelte never re-rendered it and the chip stayed blank through every save.
  $: statusLabel = savingState === 'saving'
    ? 'Saving…'
    : savingState === 'saved'
      ? 'Saved'
      : savingState === 'error'
        ? 'Save failed'
        : '';

  onMount(load);
</script>

{#if loading}
  <section class="settings-shell">
    <div class="glass-panel skeleton-card tall-skeleton"></div>
  </section>
{:else if error}
  <section class="settings-shell">
    <div class="glass-panel">
      <div class="feedback-banner error-banner">{error}</div>
    </div>
  </section>
{:else if settings}
  <section class="settings-shell" in:fade={{ duration: 180 }}>
    <article class="glass-panel strong-panel">
      <div class="section-head">
        <div>
          <p class="eyebrow">Player console</p>
          <h1 class="settings-title">Settings</h1>
        </div>
        <span class="save-chip" role="status" aria-live="polite">{statusLabel}</span>
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

      <div class="tutorial-block" data-tour="resume-tutorial">
        <div class="tutorial-copy">
          <p class="eyebrow">Tutorial</p>
          <p class="tutorial-state">
            {#if $onboarding.skipped}
              Skipped — every drill is open. Start it again any time.
            {:else if tutorialDone}
              Finished — {tutorialProgress} done.
            {:else}
              In progress — {tutorialProgress} done.
            {/if}
          </p>
        </div>

        <div class="tutorial-actions">
          {#if confirmingRestart}
            <span class="tutorial-warn">This re-locks the drills and replays the guided tours.</span>
            <button class="ghost-button" type="button" on:click={() => (confirmingRestart = false)}>Cancel</button>
            <button class="primary-button" type="button" on:click={requestRestart}>Restart it</button>
          {:else}
            <button class="ghost-button" type="button" on:click={requestRestart}>Start the tutorial again</button>
          {/if}
        </div>
      </div>

      <div class="settings-logout-row">
        <button class="ghost-button" type="button" on:click={onLogout}>Logout</button>
      </div>
    </article>
  </section>
{/if}

<style>
  .settings-shell {
    max-width: 720px;
    margin-inline: auto;
    width: 100%;
  }

  .settings-title {
    font-family: var(--marquee);
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin: 0.3rem 0 0;
    color: var(--text);
  }

  :global(html[data-theme='arcade']) .settings-title {
    font-size: 1rem;
    line-height: 1.6;
    text-shadow: 0 0 12px color-mix(in srgb, var(--accent) 90%, transparent);
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

  .settings-logout-row {
    display: flex;
    justify-content: flex-end;
    margin-top: 1rem;
  }

  /* Tutorial controls. Also the anchor the "you can come back to it" pointer
     lands on right after someone skips. */
  .tutorial-block {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-top: 1.25rem;
    padding: 0.85rem 1rem;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: color-mix(in srgb, var(--surface) 60%, transparent);
  }

  .tutorial-state {
    margin: 0.2rem 0 0;
    font-size: 0.85rem;
    color: var(--muted);
  }

  .tutorial-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
  }

  .tutorial-warn {
    font-size: 0.78rem;
    color: var(--danger);
    max-width: 18rem;
  }

  @media (max-width: 480px) {
    .shortcut-setting-row {
      align-items: flex-start;
    }

    .tutorial-block,
    .tutorial-actions {
      align-items: stretch;
    }
  }
</style>
