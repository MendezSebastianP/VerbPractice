<script lang="ts">
  import { href } from '../router';
  import ConjugationPage from './ConjugationPage.svelte';
  import TranslationPage from './TranslationPage.svelte';
  import type { ThemeName } from '../types';

  export let routePath = '/training/verbs';
  export let csrfToken = '';
  export let soundEnabled = false;
  export let theme: ThemeName = 'light';
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;

  type VerbView = 'translation' | 'conjugation';

  let view: VerbView = routePath === '/training/conjugation'
    || routePath.startsWith('/training/verbs/conjugation')
    || new URLSearchParams(window.location.search).get('mode') === 'tables'
    ? 'conjugation'
    : 'translation';
  let lastRoutePath = routePath;
  let tableSessionActive = false;

  $: if (routePath !== lastRoutePath) {
    lastRoutePath = routePath;
    tableSessionActive = false;
    view = routePath === '/training/conjugation' || routePath.startsWith('/training/verbs/conjugation')
      ? 'conjugation'
      : 'translation';
  }

  function openView(nextView: VerbView): void {
    view = nextView;
    tableSessionActive = false;
    const query = nextView === 'conjugation' ? '?mode=tables' : '';
    window.history.replaceState({}, '', `${href('/training/verbs')}${query}`);
  }
</script>

<section class="verb-lab-shell">
  {#if !tableSessionActive}
    <header class="glass-panel verb-lab-header">
    <div class="verb-lab-copy">
      <p class="eyebrow">Verb lab</p>
      <h1>Choose how you want to train verbs.</h1>
      <p class="section-copy">Four languages, one route. Switch drills here without losing either session.</p>
    </div>

    <div class="verb-mode-switch" role="tablist" aria-label="Verb workspace mode">
      <button
        class:verb-mode-on={view === 'translation'}
        class="verb-mode-button"
        type="button"
        role="tab"
        aria-selected={view === 'translation'}
        aria-label="Verb translation"
        on:click={() => openView('translation')}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M5 7.5h8M5 12h6M5 16.5h8" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="1.8"></path>
          <path d="M15 7.5h4v4" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8"></path>
          <path d="m19 7.5-6.5 7" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="1.8"></path>
        </svg>
        <span>Translate</span>
        <small>Infinitive recall</small>
      </button>

      <button
        class:verb-mode-on={view === 'conjugation'}
        class="verb-mode-button"
        type="button"
        role="tab"
        aria-selected={view === 'conjugation'}
        aria-label="Conjugation tables"
        on:click={() => openView('conjugation')}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect x="4.5" y="5.5" width="15" height="13" rx="2.5" fill="none" stroke="currentColor" stroke-width="1.8"></rect>
          <path d="M4.5 10h15M10 5.5v13M15 10v8.5" fill="none" stroke="currentColor" stroke-width="1.8"></path>
        </svg>
        <span>Fill tables</span>
        <small>Tense by tense</small>
      </button>
    </div>
    </header>
  {/if}

  {#if view === 'translation'}
    <TranslationPage mode="verbs" {csrfToken} {soundEnabled} {theme} {notify} />
  {:else}
    <ConjugationPage {csrfToken} {soundEnabled} {notify} onSessionActiveChange={(active) => (tableSessionActive = active)} />
  {/if}
</section>
