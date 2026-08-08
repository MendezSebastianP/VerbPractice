<script lang="ts">
  import { onMount, tick } from 'svelte';
  import CoachTour from '../components/onboarding/CoachTour.svelte';
  import type { TourStep } from '../components/onboarding/CoachTour.svelte';
  import FeatureStage from '../components/onboarding/FeatureStage.svelte';
  import OnboardingChecklist from '../components/onboarding/OnboardingChecklist.svelte';
  import type { ChecklistStep } from '../components/onboarding/OnboardingChecklist.svelte';
  import {
    FEATURE_CHAIN,
    FEATURE_TOURS,
    INTRO_TOUR,
    chainComplete,
    currentFeature,
    emptyState,
    featureById,
    isComplete,
    isUnlocked,
    markComplete,
    markTourSeen,
    unlockedByCompleting,
  } from '../components/onboarding/onboarding';
  import type { FeatureId, OnboardingState } from '../components/onboarding/onboarding';
  import { href } from '../router';

  // ------------------------------------------------------------------- state
  let state: OnboardingState = emptyState();
  let activeId: FeatureId = 'words';
  let toast = '';
  let toastTimer = 0;
  let simEl: HTMLElement | null = null;

  $: activeFeature = featureById(activeId);
  $: nextUp = currentFeature(state);
  $: allDone = chainComplete(state);

  $: checklistSteps = FEATURE_CHAIN.map(
    (feature): ChecklistStep => ({
      id: feature.id,
      label: feature.checklistLabel,
      hint: feature.checklistHint,
      cta: feature.cta,
      done: isComplete(state, feature.id),
      href: feature.route,
    }),
  );

  function say(message: string): void {
    toast = message;
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => (toast = ''), 4200);
  }

  // ------------------------------------------------------------------- tours
  let introTour: CoachTour;
  let featureTour: CoachTour;
  let featureTourSteps: TourStep[] = [];
  let pendingTourFor: FeatureId | null = null;
  let tourRunning = false;

  /** Fire a feature's tour the first time it is opened, unless the user opted out. */
  async function maybeStartFeatureTour(id: FeatureId): Promise<void> {
    if (state.skipped || tourRunning || state.seenTours.includes(id)) {
      return;
    }
    pendingTourFor = id;
    featureTourSteps = FEATURE_TOURS[id];
    tourRunning = true;
    // Let the new stage render so the tour can resolve its anchors.
    await tick();
    await new Promise((resolve) => window.setTimeout(resolve, 120));
    featureTour?.start();
  }

  function settleFeatureTour(): void {
    if (pendingTourFor) {
      state = markTourSeen(state, pendingTourFor);
      pendingTourFor = null;
    }
    tourRunning = false;
  }

  async function startIntro(): Promise<void> {
    tourRunning = true;
    await tick();
    await new Promise((resolve) => window.setTimeout(resolve, 150));
    introTour?.start();
  }

  function onIntroDone(seen: boolean): void {
    state = markTourSeen(state, 'intro');
    tourRunning = false;
    if (seen) {
      // The learner lands on Words, so its tour follows straight on.
      void maybeStartFeatureTour(activeId);
    }
  }

  // ------------------------------------------------------------------ actions
  function openFeature(id: FeatureId): void {
    if (!isUnlocked(state, id)) {
      const feature = featureById(id);
      say(`${feature.label} is locked — finish ${feature.requires} first.`);
      return;
    }
    activeId = id;
    void maybeStartFeatureTour(id);
  }

  function completeFeature(event: CustomEvent<{ id: FeatureId }>): void {
    const id = event.detail.id;
    if (isComplete(state, id)) {
      return;
    }
    state = markComplete(state, id);

    const opened = unlockedByCompleting(id);
    if (opened && !state.skipped) {
      say(`${opened.label} unlocked.`);
    } else if (!opened) {
      say('That is the whole chain — everything is open now.');
    }
  }

  function onChecklistAction(event: CustomEvent<{ id: string }>): void {
    openFeature(event.detail.id as FeatureId);
  }

  function skipTutorial(): void {
    state = { ...state, skipped: true };
    say('Tutorial skipped — every drill is open.');
  }

  function unskipTutorial(): void {
    state = { ...state, skipped: false };
    if (!isUnlocked(state, activeId)) {
      activeId = currentFeature(state)?.id ?? 'words';
    }
    say('Guided order back on.');
  }

  function resetSim(): void {
    state = emptyState();
    activeId = 'words';
    toast = '';
    tourRunning = false;
    pendingTourFor = null;
    void startIntro();
  }

  function replayIntro(): void {
    state = { ...state, seenTours: state.seenTours.filter((id) => id !== 'intro') };
    void startIntro();
  }

  onMount(() => {
    void startIntro();
    return () => window.clearTimeout(toastTimer);
  });
</script>

<section class="pg3-shell">
  <header class="pg3-hero">
    <p class="eyebrow">Playground 3 · First-run onboarding</p>
    <h1>The whole first run, working end to end.</h1>
    <p class="hero-lede">
      Drills open one at a time in a fixed order: Words, then Add Word, then verb translation, then
      verb tables. A short intro tour runs once, each drill has its own tour the first time you open
      it, and the checklist carries an escape hatch for anyone who would rather not be led. Click
      through it below — nothing here touches your account.
    </p>
    <div class="hero-links">
      <a class="text-switch" href={href('/training/words')}>Open the real trainer →</a>
      <span>Concept bench · no data is written</span>
    </div>
  </header>

  <div class="sim-bar">
    <div class="sim-copy">
      <p class="sim-kicker">Simulator</p>
      <p class="sim-state">
        {#if state.skipped}
          Tutorial skipped — all four drills open.
        {:else if allDone}
          All four finished.
        {:else}
          Next up: <strong>{nextUp?.label}</strong> · {state.completed.length} of {FEATURE_CHAIN.length} done
        {/if}
      </p>
    </div>
    <div class="sim-actions">
      <button class="ghost-button" type="button" on:click={replayIntro}>Replay intro tour</button>
      <button class="ghost-button" type="button" on:click={resetSim}>Reset to a new account</button>
    </div>
  </div>

  <!-- ============================================================ simulator -->
  <div class="sim-frame" bind:this={simEl}>
    <nav class="sim-rail" aria-label="Drills" data-tour="rail">
      {#each FEATURE_CHAIN as feature (feature.id)}
        {@const unlocked = isUnlocked(state, feature.id)}
        {@const complete = isComplete(state, feature.id)}
        <button
          type="button"
          class="rail-link"
          class:link-active={activeId === feature.id}
          class:link-locked={!unlocked}
          aria-current={activeId === feature.id ? 'page' : undefined}
          aria-disabled={!unlocked ? 'true' : undefined}
          title={unlocked ? feature.label : `Unlocks after ${feature.requires}`}
          on:click={() => openFeature(feature.id)}
        >
          {#if complete}
            <svg class="rail-tick" viewBox="0 0 16 16" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M3 8.4l3.2 3.2L13 5" />
            </svg>
          {:else if !unlocked}
            <svg class="rail-lock" viewBox="0 0 16 16" width="11" height="11" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="3.2" y="7" width="9.6" height="6.4" rx="1.6" />
              <path d="M5.6 7V5.2a2.4 2.4 0 0 1 4.8 0V7" />
            </svg>
          {/if}
          <span>{feature.label}</span>
        </button>
      {/each}
    </nav>

    <div class="sim-body">
      <div class="sim-checklist" data-tour="checklist">
        <OnboardingChecklist
          steps={checklistSteps}
          variant="card"
          dismissible={false}
          skipped={state.skipped}
          on:action={onChecklistAction}
          on:skip={skipTutorial}
          on:unskip={unskipTutorial}
        />
      </div>

      {#key activeId}
        <FeatureStage
          feature={activeFeature}
          done={isComplete(state, activeId)}
          tablesUnlocked={isUnlocked(state, 'verb-tables')}
          on:complete={completeFeature}
          on:switchTo={(event) => openFeature(event.detail.id)}
        />
      {/key}
    </div>

    {#if toast}
      <p class="sim-toast" role="status">{toast}</p>
    {/if}
  </div>

  <!-- ================================================================ notes -->
  <section class="pg3-block">
    <h2>What is actually stored</h2>
    <p class="block-copy">
      One JSON blob per user — the whole mechanism runs off this. Watch it change as you click
      through the simulator above.
    </p>
    <pre class="state-dump">{JSON.stringify(state, null, 2)}</pre>
    <aside class="note">
      <strong>To make it real:</strong> add an <code>onboarding</code> JSON column to
      <code>user_preferences</code> (there is precedent — <code>trainer_setups</code> is already
      one), ship it in <code>_bootstrap_payload</code>, and write it back through the existing
      <code>PATCH /api/settings</code>. <code>completed</code> can be seeded from
      <code>_metric_snapshot</code> so accounts that predate the feature do not start from zero.
    </aside>
  </section>

  <section class="pg3-block">
    <h2>Three things worth deciding</h2>
    <ul class="decide-list">
      <li>
        <strong>The intro hands straight off to the Words tour.</strong> Three intro steps then
        three Words steps — six in a row on a brand-new account. It reads as a guided arrival
        rather than two separate interruptions, but if that is still too much, the alternative is
        to end after the intro and hold the Words tour until the learner starts a round.
      </li>
      <li>
        <strong>Verb tables is gated inside the page, not by route.</strong> Translate and Fill
        tables are two tabs of <code>/training/verbs</code>, so the lock lives on the tab — you can
        see it greyed out in the verb translation screen above.
      </li>
      <li>
        <strong>The browser lock is cosmetic.</strong> The API still answers to anyone who calls it
        directly. If the gate is meant to hold, the start-session endpoints need the same check
        server-side; if it is only there to pace people, the UI lock is enough.
      </li>
    </ul>
  </section>
</section>

<CoachTour
  bind:this={introTour}
  steps={INTRO_TOUR}
  tone="intro"
  root={simEl}
  finishLabel="Show me Words"
  on:finish={() => onIntroDone(true)}
  on:skip={() => onIntroDone(false)}
/>

<CoachTour
  bind:this={featureTour}
  steps={featureTourSteps}
  tone="feature"
  root={simEl}
  on:finish={settleFeatureTour}
  on:skip={settleFeatureTour}
/>

<style>
  .pg3-shell {
    max-width: 62rem;
    margin: 0 auto;
    padding: 1.5rem 1rem 4rem;
    display: grid;
    gap: 1.2rem;
  }

  .pg3-hero h1 {
    margin: 0.35rem 0 0.6rem;
    font-size: clamp(1.6rem, 4vw, 2.3rem);
    line-height: 1.15;
  }

  .hero-lede {
    margin: 0 0 0.9rem;
    max-width: 46rem;
    font-size: 0.95rem;
    line-height: 1.6;
    color: var(--muted, #666);
  }

  .hero-links {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.9rem;
    font-size: 0.78rem;
    color: var(--muted, #666);
  }

  .text-switch {
    color: var(--accent-strong, var(--accent, #4c8));
    font-size: 0.82rem;
    font-weight: 600;
    text-decoration: none;
  }

  .text-switch:hover {
    text-decoration: underline;
  }

  /* ---- simulator controls ---- */
  .sim-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    padding: 0.65rem 0.85rem;
    border-radius: 12px;
    border: 1px dashed var(--line-strong, rgba(0, 0, 0, 0.18));
  }

  .sim-kicker {
    margin: 0 0 0.1rem;
    font-size: 0.66rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent-strong, var(--accent, #4c8));
    font-weight: 700;
  }

  .sim-state {
    margin: 0;
    font-size: 0.83rem;
    color: var(--muted, #666);
  }

  .sim-state strong {
    color: var(--text, #111);
  }

  .sim-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  .ghost-button {
    padding: 0.4rem 0.8rem;
    border-radius: 9px;
    border: 1px solid var(--line-strong, rgba(0, 0, 0, 0.2));
    background: transparent;
    color: var(--text, #111);
    font: inherit;
    font-size: 0.78rem;
    cursor: pointer;
    transition: background 0.15s, transform 0.07s;
  }

  .ghost-button:hover {
    background: var(--accent-soft, rgba(0, 0, 0, 0.06));
  }

  .ghost-button:active {
    transform: scale(0.96);
  }

  /* ---- the fake app ---- */
  .sim-frame {
    display: grid;
    gap: 0.9rem;
    padding: 0.9rem;
    border-radius: 18px;
    border: 1px solid var(--line, rgba(0, 0, 0, 0.14));
    background: color-mix(in srgb, var(--surface, #fff) 55%, transparent);
  }

  .sim-rail {
    display: flex;
    flex-wrap: wrap;
    gap: 0.2rem;
    padding: 0.32rem;
    border-radius: 999px;
    border: 1px solid var(--line, rgba(0, 0, 0, 0.14));
    background: var(--surface, rgba(255, 255, 255, 0.7));
  }

  .rail-link {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.42rem 0.9rem;
    border: 1px solid transparent;
    border-radius: 999px;
    background: transparent;
    color: var(--text, #111);
    font: inherit;
    font-size: 0.83rem;
    cursor: pointer;
    transition: background 0.15s, color 0.15s, opacity 0.15s;
  }

  .rail-link:hover {
    background: var(--accent-soft, rgba(0, 0, 0, 0.05));
  }

  .rail-link.link-active {
    background: var(--accent, #4c8);
    color: var(--bg, #fff);
  }

  /* Locked links stay focusable and explain themselves on click — a disabled
     button would be silent to a screen reader and to the mouse alike. */
  .rail-link.link-locked {
    opacity: 0.42;
    cursor: not-allowed;
  }

  .rail-link.link-locked:hover {
    opacity: 0.6;
    background: transparent;
  }

  .rail-tick {
    color: var(--accent, #4c8);
  }

  .link-active .rail-tick {
    color: var(--bg, #fff);
  }

  .sim-body {
    display: grid;
    gap: 0.8rem;
  }

  .sim-toast {
    margin: 0;
    padding: 0.55rem 0.8rem;
    border-radius: 10px;
    border: 1px solid var(--accent, #4c8);
    background: var(--accent-soft, rgba(0, 0, 0, 0.06));
    font-size: 0.82rem;
    font-weight: 500;
  }

  /* ---- notes ---- */
  .pg3-block {
    display: grid;
    gap: 0.7rem;
    padding: 1.1rem 1.2rem;
    border-radius: 16px;
    border: 1px solid var(--line, rgba(0, 0, 0, 0.12));
    background: color-mix(in srgb, var(--surface, #fff) 55%, transparent);
  }

  .pg3-block h2 {
    margin: 0;
    font-size: 1.1rem;
  }

  .block-copy {
    margin: 0;
    font-size: 0.85rem;
    line-height: 1.55;
    color: var(--muted, #666);
  }

  .state-dump {
    margin: 0;
    padding: 0.75rem 0.85rem;
    border-radius: 11px;
    background: var(--surface-dark, #111);
    color: var(--bg-soft, #eee);
    font-family: var(--mono, monospace);
    font-size: 0.76rem;
    line-height: 1.5;
    overflow-x: auto;
  }

  .note {
    margin: 0;
    padding: 0.7rem 0.85rem;
    border-left: 3px solid var(--accent, #4c8);
    border-radius: 0 9px 9px 0;
    background: color-mix(in srgb, var(--accent, #4c8) 7%, transparent);
    font-size: 0.8rem;
    line-height: 1.55;
    color: var(--muted, #555);
  }

  .note strong {
    color: var(--text, #111);
  }

  .note code,
  .decide-list code {
    font-family: var(--mono, monospace);
    font-size: 0.76rem;
  }

  .decide-list {
    margin: 0;
    padding-left: 1.1rem;
    display: grid;
    gap: 0.5rem;
    font-size: 0.83rem;
    line-height: 1.55;
    color: var(--muted, #666);
  }

  .decide-list strong {
    color: var(--text, #111);
  }

  @media (max-width: 640px) {
    .sim-bar,
    .sim-actions {
      align-items: stretch;
    }

    .rail-link {
      padding: 0.42rem 0.7rem;
      font-size: 0.78rem;
    }
  }
</style>
