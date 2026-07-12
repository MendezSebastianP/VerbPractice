<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { fade } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import { playCue } from '../sound';
  import { applyReward } from '../profile';
  import { celebrateReward, flashMiss, popEl } from '../fx';
  import type { ConjugationState, ConjugationTenseReview, LanguageConfig, RewardState } from '../types';

  export let csrfToken = '';
  export let soundEnabled = false;
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;
  export let onSessionActiveChange: (active: boolean) => void = () => {};

  let loading = true;
  let error = '';
  let state: ConjugationState | null = null;
  let language = 'FR';
  let level = 'easy';
  let fillLevel = 'hard';
  let length = 5;
  let retryButton: HTMLButtonElement | null = null;
  let nextTenseButton: HTMLButtonElement | null = null;
  let finishButton: HTMLButtonElement | null = null;
  let finishedCard: HTMLElement | null = null;
  let selectedTenses: string[] = [];
  let answers: Record<string, Record<string, string>> = {};
  let activeCellKey = '';
  let justFinished = false;
  let showSetupAfterFinish = false;
  let activeTenseIndex = 0;
  let tenseReview: ConjugationTenseReview | null = null;
  let checkedTenses = new Set<string>();
  let tenseScores: Record<string, { correct: number; total: number }> = {};
  let finishSessionWarning = false;
  let escTimer: ReturnType<typeof setTimeout> | null = null;

  const LEVELS = [
    { value: 'easy', label: 'Core', note: 'Start with the essential forms' },
    { value: 'medium', label: 'Expand', note: 'Add everyday range' },
    { value: 'hard', label: 'Master', note: 'Open the complete corpus' },
  ];
  const LENGTH_OPTIONS = [3, 5, 8];

  type InputCell = {
    key: string;
    tense: string;
    pronoun: string;
  };

  let activeTense = '';
  let currentInputCells: InputCell[] = [];
  let currentActiveCell: InputCell | null = null;
  let currentActiveLabel = 'Nothing left to fill';
  let sessionActive = false;
  let sessionDone = false;
  let menuView = false;
  let activeLanguage: LanguageConfig | undefined;

  function currentLanguage(): LanguageConfig | undefined {
    return state?.languages.find((entry) => entry.code === language);
  }

  function tensesForLevel(config: LanguageConfig | undefined, targetLevel: string): string[] {
    if (!config) {
      return [];
    }

    const available = new Set(config.available_tenses || []);
    const easy = (config.difficulty_tiers.easy || []).filter((tense) => available.has(tense));
    const medium = (config.difficulty_tiers.medium || []).filter((tense) => available.has(tense));
    const hard = (config.difficulty_tiers.hard || []).filter((tense) => available.has(tense));

    if (targetLevel === 'easy') {
      return [...easy];
    }
    if (targetLevel === 'medium') {
      return [...easy, ...medium];
    }
    if (targetLevel === 'hard') {
      return [...easy, ...medium, ...hard];
    }
    return [...(config.available_tenses || [])];
  }

  function visibleTenses(): string[] {
    return tensesForLevel(currentLanguage(), level);
  }

  function tensesForTier(config: LanguageConfig | undefined, tierIndex: number): string[] {
    if (!config) {
      return [];
    }
    const available = new Set(config.available_tenses || []);
    const tier = LEVELS[tierIndex]?.value;
    return tier ? (config.difficulty_tiers[tier] || []).filter((tense) => available.has(tense)) : [];
  }

  function tierIsOn(
    tierIndex: number,
    config: LanguageConfig | undefined,
    currentLevel: string,
    currentSelection: string[],
  ): boolean {
    if (currentLevel === 'custom') {
      return tensesForTier(config, tierIndex).some((tense) => currentSelection.includes(tense));
    }
    return LEVELS.findIndex((item) => item.value === currentLevel) >= tierIndex;
  }

  function levelAvailable(targetLevel: string): boolean {
    const tenses = tensesForLevel(currentLanguage(), targetLevel);
    if (!tenses.length) {
      return false;
    }
    if (targetLevel === 'medium') {
      return tenses.length > tensesForLevel(currentLanguage(), 'easy').length;
    }
    if (targetLevel === 'hard') {
      return tenses.length > tensesForLevel(currentLanguage(), 'medium').length;
    }
    return true;
  }

  function canStart(): boolean {
    return Boolean(currentLanguage()?.available && selectedTenses.length);
  }

  function syncSelection(): void {
    if (level !== 'custom') {
      selectedTenses = visibleTenses();
    } else {
      const available = new Set(currentLanguage()?.available_tenses || []);
      selectedTenses = selectedTenses.filter((tense) => available.has(tense));
    }
  }

  function syncControlsFromState(nextState: ConjugationState | null, allowSetupReset = false): void {
    if (!nextState) {
      return;
    }

    if (nextState.session) {
      language = nextState.session.language;
      level = nextState.session.level;
      fillLevel = nextState.session.fill_level;
      length = nextState.session.length;
      selectedTenses = [...nextState.session.selected_tenses];
      return;
    }

    if (!allowSetupReset || nextState.finished) {
      return;
    }

    const firstLanguage = nextState.languages.find((entry) => entry.code === language && entry.available)
      || nextState.languages.find((entry) => entry.available);
    if (firstLanguage) {
      language = firstLanguage.code;
      syncSelection();
    }
  }

  function cellKey(tense: string, pronoun: string): string {
    return encodeURIComponent(`${tense}::${pronoun}`);
  }

  function cellDomId(key: string): string {
    return `conj-${key}`;
  }

  function buildInputCells(question: ConjugationState['question'], tense: string): InputCell[] {
    if (!question || !tense) {
      return [];
    }

    const rowsByPronoun = new Map(question.rows.map((row) => [row.pronoun, row]));
    const cells: InputCell[] = [];
    for (const pronoun of question.pronouns) {
      const row = rowsByPronoun.get(pronoun);
      const cell = row?.cells.find((entry) => entry.tense === tense);
      if (cell?.kind === 'input') {
        cells.push({ key: cellKey(tense, pronoun), tense, pronoun });
      }
    }
    return cells;
  }

  $: activeTense = state?.question?.selected_tenses[activeTenseIndex] || '';
  $: activeLanguage = state?.languages.find((entry) => entry.code === language);
  $: currentInputCells = buildInputCells(state?.question, activeTense);
  $: currentActiveCell = currentInputCells.find((cell) => cell.key === activeCellKey) || currentInputCells[0] || null;
  $: currentActiveLabel = currentActiveCell ? `${currentActiveCell.pronoun} -> ${currentActiveCell.tense}` : 'Nothing left to fill';
  $: sessionActive = Boolean(state?.session && state?.question);
  $: sessionDone = Boolean(!state?.session && (justFinished || state?.finished || state?.result?.finished) && !showSetupAfterFinish);
  $: menuView = Boolean(state?.setup && (!sessionDone || showSetupAfterFinish));
  $: onSessionActiveChange(sessionActive);

  function showFinishedPrompt(): boolean {
    return sessionDone;
  }

  function resetQuestionProgress(nextState: ConjugationState | null): void {
    const selected = nextState?.question?.selected_tenses || [];
    const restoredChecked = (nextState?.session?.checked_tenses || []).filter((tense) => selected.includes(tense));
    checkedTenses = new Set(restoredChecked);
    activeTenseIndex = Math.min(restoredChecked.length, Math.max(0, selected.length - 1));
    tenseReview = null;
    tenseScores = {};
    activeCellKey = '';
  }

  async function load(): Promise<void> {
    loading = true;
    error = '';
    try {
      state = await api.conjugationState();
      justFinished = Boolean(state?.finished || state?.result?.finished);
      showSetupAfterFinish = false;
      syncControlsFromState(state, true);
      answers = {};
      resetQuestionProgress(state);
      if (state.feedback && state.result) {
        notify(state.feedback, state.result.accuracy === 100 ? 'success' : 'info');
      }
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to load conjugation training';
    } finally {
      loading = false;
      await focusPrimaryControl();
    }
  }

  onMount(() => {
    void load();
    return () => {
      if (escTimer) {
        clearTimeout(escTimer);
      }
      onSessionActiveChange(false);
    };
  });

  function focusCellByKey(key: string): void {
    activeCellKey = key;
    const input = document.getElementById(cellDomId(key)) as HTMLInputElement | null;
    input?.focus();
  }

  function focusFirstInput(): void {
    const [firstCell] = currentInputCells;
    if (firstCell) {
      focusCellByKey(firstCell.key);
    }
  }

  async function focusPrimaryControl(): Promise<void> {
    await tick();
    if (showFinishedPrompt()) {
      finishedCard?.scrollIntoView({ block: 'center', behavior: 'smooth' });
      retryButton?.focus();
      return;
    }
    if (tenseReview) {
      nextTenseButton?.focus();
      return;
    }
    focusFirstInput();
  }

  function setAnswer(tense: string, pronoun: string, value: string): void {
    answers = {
      ...answers,
      [tense]: {
        ...(answers[tense] || {}),
        [pronoun]: value,
      },
    };
  }

  function toggleTense(tense: string): void {
    error = '';
    level = 'custom';
    selectedTenses = selectedTenses.includes(tense)
      ? selectedTenses.filter((entry) => entry !== tense)
      : [...selectedTenses, tense];
  }

  function chooseLanguage(code: string): void {
    const next = state?.languages.find((entry) => entry.code === code);
    if (!next?.available) {
      return;
    }
    error = '';
    language = code;
    if (level === 'custom') {
      selectedTenses = tensesForLevel(next, 'easy');
      return;
    }
    if (level !== 'custom' && !levelAvailable(level)) {
      level = 'easy';
    }
    syncSelection();
  }

  function chooseLevel(nextLevel: string): void {
    if (nextLevel !== 'custom' && !levelAvailable(nextLevel)) {
      return;
    }
    error = '';
    level = nextLevel;
    syncSelection();
  }

  function progressPercent(): number {
    if (!state?.session || !state.session.progress_total) {
      return 0;
    }
    return (state.session.progress_current / state.session.progress_total) * 100;
  }

  function reward(): RewardState | null {
    return state?.result?.gamification || null;
  }

  async function startSession(): Promise<void> {
    if (!canStart()) {
      error = level === 'custom' ? 'Choose at least one available tense.' : 'No complete tables are available for this setup.';
      if (sessionDone) {
        justFinished = false;
        showSetupAfterFinish = true;
      }
      return;
    }
    loading = true;
    error = '';
    try {
      state = await api.startConjugation({
        language,
        level,
        fill_level: fillLevel,
        selected_tenses: selectedTenses,
        length,
        csrf_token: csrfToken,
      });
      justFinished = false;
      showSetupAfterFinish = false;
      syncControlsFromState(state);
      answers = {};
      resetQuestionProgress(state);
      void api.patchSettings({
        csrf_token: csrfToken,
        last_practice_mode: 'conjugation',
      }).catch(() => {});
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to start conjugation session';
      if (sessionDone) {
        justFinished = false;
        showSetupAfterFinish = true;
      }
    } finally {
      loading = false;
      await focusPrimaryControl();
    }
  }

  async function submit(): Promise<void> {
    if (!state || state.setup) {
      return;
    }
    loading = true;
    error = '';
    try {
      state = await api.submitConjugation({ answers, csrf_token: csrfToken });
      justFinished = Boolean(state?.finished || state?.result?.finished);
      showSetupAfterFinish = false;
      answers = {};
      resetQuestionProgress(state);
      if (state.feedback) {
        notify(state.feedback, state.result?.accuracy === 100 ? 'success' : 'info');
      }
      const rewardState = state.result?.gamification;
      applyReward(rewardState);
      celebrateReward(rewardState);
      if (state.result?.accuracy !== undefined && state.result.accuracy < 100) {
        flashMiss();
      }
      if (soundEnabled) {
        if (rewardState?.leveled_up) {
          playCue('level');
        } else if (rewardState?.unlocked_badges?.length) {
          playCue('badge');
        } else {
          playCue(state.result?.accuracy === 100 ? 'success' : 'error');
        }
      }
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to grade conjugation answers';
    } finally {
      loading = false;
      await focusPrimaryControl();
    }
  }

  async function checkActiveTense(): Promise<void> {
    const tense = activeTense;
    if (!state?.question || !tense || tenseReview || loading) {
      return;
    }
    loading = true;
    error = '';
    try {
      const review = await api.checkConjugationTense({
        tense,
        answers: answers[tense] || {},
        csrf_token: csrfToken,
      });
      tenseReview = review;
      checkedTenses = new Set([...checkedTenses, tense]);
      tenseScores = {
        ...tenseScores,
        [tense]: { correct: review.correct, total: review.total },
      };
      if (soundEnabled) {
        playCue(review.accuracy === 100 ? 'success' : 'error');
      }
      if (review.accuracy < 100) {
        flashMiss();
      }
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to check this tense';
    } finally {
      loading = false;
      await focusPrimaryControl();
    }
  }

  async function continueAfterTense(): Promise<void> {
    if (!tenseReview || !state?.question || loading) {
      return;
    }
    if (activeTenseIndex < state.question.selected_tenses.length - 1) {
      activeTenseIndex += 1;
      activeCellKey = '';
      tenseReview = null;
      await focusPrimaryControl();
      return;
    }
    await submit();
  }

  function handleCellKeydown(event: KeyboardEvent): void {
    if (event.key !== 'Enter') {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const current = event.currentTarget as HTMLInputElement;
    const currentKey = current.dataset.cellKey;
    const cells = currentInputCells;
    const index = currentKey ? cells.findIndex((cell) => cell.key === currentKey) : -1;
    if (index >= 0 && index < cells.length - 1) {
      focusCellByKey(cells[index + 1].key);
      return;
    }
    void checkActiveTense();
  }

  function revealSetup(): void {
    justFinished = false;
    showSetupAfterFinish = true;
  }

  function handleFinishClick(): void {
    if (loading) {
      return;
    }
    if (finishSessionWarning) {
      finishSessionWarning = false;
      if (escTimer) {
        clearTimeout(escTimer);
        escTimer = null;
      }
      popEl(finishButton);
      void finishSession();
      return;
    }
    finishSessionWarning = true;
    if (escTimer) {
      clearTimeout(escTimer);
    }
    escTimer = setTimeout(() => {
      finishSessionWarning = false;
      escTimer = null;
    }, 2500);
  }

  async function finishSession(): Promise<void> {
    loading = true;
    error = '';
    try {
      state = await api.finishConjugation(csrfToken);
      activeCellKey = '';
      justFinished = false;
      showSetupAfterFinish = true;
      finishSessionWarning = false;
      answers = {};
      resetQuestionProgress(state);
      syncControlsFromState(state);
      if (state.feedback) {
        notify(state.feedback, 'info');
      }
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to finish conjugation session';
    } finally {
      loading = false;
    }
  }

  function handleWindowKeydown(event: KeyboardEvent): void {
    if (loading) {
      return;
    }

    if (menuView && event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey && ['1', '2', '3', '4'].includes(event.key)) {
      event.preventDefault();
      chooseLevel(event.key === '4' ? 'custom' : LEVELS[Number(event.key) - 1].value);
      return;
    }

    const plainKey = !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey;
    if (!plainKey) {
      return;
    }

    if (event.key === 'Escape' && sessionActive) {
      event.preventDefault();
      handleFinishClick();
      return;
    }

    if (event.key === 'Escape' && sessionDone) {
      event.preventDefault();
      revealSetup();
      return;
    }

    if (event.key !== 'Enter') {
      return;
    }

    if (menuView) {
      const active = document.activeElement as HTMLElement | null;
      const isTyping = ['INPUT', 'TEXTAREA', 'SELECT'].includes(active?.tagName || '') || active?.isContentEditable;
      if (!isTyping) {
        event.preventDefault();
        void startSession();
      }
      return;
    }

    if (sessionDone) {
      if (document.activeElement === retryButton) {
        return;
      }
      event.preventDefault();
      void startSession();
      return;
    }

    if (tenseReview) {
      if (document.activeElement === nextTenseButton) {
        return;
      }
      event.preventDefault();
      void continueAfterTense();
    }
  }
</script>

<svelte:window on:keydown={handleWindowKeydown} />

<section class="trainer-shell">
  {#if loading && !state}
    <div class="glass-panel skeleton-card tall-skeleton"></div>
  {:else if error && !state}
    <div class="glass-panel">
      <div class="feedback-banner error-banner">{error}</div>
    </div>
  {:else if state}
    <div class="trainer-stack" in:fade={{ duration: 180 }}>
      {#if error}
        <div class="feedback-banner error-banner">{error}</div>
      {:else if state.feedback && !state.feedback.startsWith('Score:') && !sessionActive && !sessionDone}
        <div class="feedback-banner info-banner">{state.feedback}</div>
      {/if}

      {#if sessionDone}
        <article bind:this={finishedCard} class="glass-panel strong-panel table-clear-card" in:fade={{ duration: 180 }}>
          <div class="table-clear-burst" aria-hidden="true"><i></i><i></i><i></i></div>
          <p class="eyebrow">Table run complete</p>
          <h2>Stage clear</h2>
          <p class="table-clear-score">
            Score {state.result?.session_score ?? 0}% · {state.result?.session_length ?? length} verbs · Best combo ×{state.result?.best_combo ?? 0}
          </p>
          <div class="table-clear-dots" aria-hidden="true">
            {#each Array(state.result?.session_length ?? length) as _, index}
              <span class:table-clear-dot-on={index < Math.round((state.result?.session_length ?? length) * ((state.result?.session_score ?? 0) / 100))}></span>
            {/each}
          </div>
          <div class="table-clear-actions">
            <button bind:this={retryButton} class="primary-button" type="button" on:click={() => { popEl(retryButton); void startSession(); }} disabled={loading}>
              ▶ Replay <span class="kbd-chip">Enter</span>
            </button>
            <button class="secondary-button" type="button" on:click={revealSetup} disabled={loading}>
              Menu <span class="kbd-chip">Esc</span>
            </button>
          </div>
        </article>
      {/if}

      {#if reward() && !sessionDone}
        <article class="glass-panel reward-panel">
          <div class="section-head">
            <div>
              <p class="eyebrow">Reward pulse</p>
              <h2>Table rewards from the last round</h2>
            </div>
            {#if reward()?.gained_xp}
              <span class="pill-chip reward-pill">+{reward()?.gained_xp} XP</span>
            {/if}
          </div>
          <div class="tag-row">
            {#if reward()?.combo}
              <span class="mini-tag">Combo {reward()?.combo}x</span>
            {/if}
            {#if reward()?.best_combo}
              <span class="mini-tag">Best {reward()?.best_combo}x</span>
            {/if}
            {#if reward()?.leveled_up}
              <span class="mini-tag">Level {reward()?.old_level} → {reward()?.new_level}</span>
            {/if}
          </div>
          {#if reward()?.challenge}
            <p class="section-copy">
              {reward()?.challenge?.title}: {reward()?.challenge?.progress}/{reward()?.challenge?.target_value}
            </p>
          {/if}
          {#if reward()?.unlocked_badges?.length}
            <div class="tag-row">
              {#each reward()?.unlocked_badges || [] as badge}
                <span class="mini-tag reward-badge">{badge.title}</span>
              {/each}
            </div>
          {/if}
        </article>
      {/if}

      {#if menuView}
        <article class="glass-panel strong-panel trainer-card table-setup-card">
          <div class="table-setup-lead">
            <div>
              <p class="eyebrow">Build a table run</p>
              <h2>Choose the tense load, then fill every open cell.</h2>
            </div>
            <p class="section-copy">Enter moves down each pronoun, then crosses to the next tense.</p>
          </div>

          <div class="setup-step">
            <div class="setup-step-head">
              <span class="step-number">01</span>
              <div><strong>Language</strong><small>All four corpora are measured live.</small></div>
            </div>
            <div class="language-card-grid">
              {#each state.languages as item}
                <button
                  class:language-card-on={language === item.code}
                  class:language-card-off={!item.available}
                  class="language-card"
                  type="button"
                  disabled={!item.available}
                  aria-pressed={language === item.code}
                  on:click={() => chooseLanguage(item.code)}
                >
                  <span class="language-code">{item.code}</span>
                  <span class="language-card-copy"><strong>{item.name}</strong><small>{item.available ? `${item.verb_count} verbs` : 'Import required'}</small></span>
                  <span class="language-check" aria-hidden="true">{language === item.code ? '✓' : ''}</span>
                </button>
              {/each}
            </div>
          </div>

          <div class="setup-step">
            <div class="setup-step-head">
              <span class="step-number">02</span>
              <div><strong>Climb from core to mastery</strong><small>Each level adds a new tier of tenses.</small></div>
            </div>
            <div class="tense-staircase" aria-label="Cumulative tense levels">
              {#each LEVELS as item, tierIndex}
                {@const tierTenses = tensesForTier(activeLanguage, tierIndex)}
                <div class:stair-on={tierIsOn(tierIndex, activeLanguage, level, selectedTenses)} class:stair-disabled={!tierTenses.length} class="stair-step">
                  <button
                    class="stair-level"
                    type="button"
                    disabled={!tierTenses.length || !levelAvailable(item.value)}
                    aria-label={`Choose level ${tierIndex + 1}: ${item.label}`}
                    aria-pressed={level === item.value}
                    on:click={() => chooseLevel(item.value)}
                  >
                    <strong>L{tierIndex + 1}</strong><span>Alt+{tierIndex + 1}</span>
                  </button>
                  <div class="stair-copy"><strong>{item.label}</strong><small>{item.note}</small></div>
                  <div class="stair-tense-row">
                    {#each tierTenses as tense}
                      <button class:tense-on={selectedTenses.includes(tense)} type="button" on:click={() => toggleTense(tense)}>{tense}</button>
                    {/each}
                  </div>
                </div>
              {/each}
              <button class:custom-on={level === 'custom'} class="custom-route" type="button" on:click={() => chooseLevel('custom')}>
                <span class="custom-spark" aria-hidden="true">✦</span>
                <span><strong>Custom route</strong><small>Touch any tense to rewrite the staircase</small></span>
                <span class="custom-key">Alt+4</span>
              </button>
            </div>
          </div>

          <div class="setup-grid-two">
            <div class="setup-step compact-step">
              <div class="setup-step-head">
                <span class="step-number">03</span>
                <div><strong>Number of verbs</strong><small>Pick the run size.</small></div>
              </div>
              <div class="length-card-row">
                {#each LENGTH_OPTIONS as option}
                  <button class:length-card-on={length === option} class="length-card" type="button" aria-pressed={length === option} on:click={() => (length = option)}>
                    <strong>{option}</strong><span>verbs</span>
                  </button>
                {/each}
              </div>
            </div>

            <div class="setup-step compact-step">
              <div class="setup-step-head">
                <span class="step-number">04</span>
                <div><strong>Table support</strong><small>How many forms are revealed.</small></div>
              </div>
              <div class="support-row">
                <button class:support-on={fillLevel === 'easy'} type="button" on:click={() => (fillLevel = 'easy')}><strong>Guided</strong><small>≈ 70%</small></button>
                <button class:support-on={fillLevel === 'medium'} type="button" on:click={() => (fillLevel = 'medium')}><strong>Hints</strong><small>1 / tense</small></button>
                <button class:support-on={fillLevel === 'hard'} type="button" on:click={() => (fillLevel = 'hard')}><strong>Blank</strong><small>0%</small></button>
              </div>
            </div>
          </div>

          <div class="setup-launch-row">
            <div class="launch-summary">
              <span>{activeLanguage?.name || language}</span>
              <strong>{selectedTenses.length} {selectedTenses.length === 1 ? 'tense' : 'tenses'} × {length} verbs</strong>
            </div>
            <button class="primary-button table-launch-button" type="button" on:click={startSession} disabled={loading || !canStart()}>
              Start table run <span aria-hidden="true">→</span>
            </button>
          </div>
        </article>
      {:else if state.question && state.session}
        {#key `${state.question.verb_id}:${state.session.progress_current}`}
          <article class="glass-panel strong-panel trainer-card g1-production-card">
            <div class="progress-shell">
              <div class="progress-top">
                <span>Verb progress</span>
                <strong>{state.session.progress_current}/{state.session.progress_total}</strong>
              </div>
              <div class="progress-track"><span class="progress-bar" style={`width: ${progressPercent()}%`}></span></div>
            </div>

            <div class="g1-session-frame">
              <div class="g1-utility-row">
                <span><i aria-hidden="true"></i> TABLE SHORTCUTS ON</span>
                <small>{tenseReview ? 'All feedback shown · Enter continues' : 'Enter moves top to bottom'} · Esc ×2 finishes</small>
              </div>

              <div class="g1-tense-strip" aria-label="Tense progress">
                {#each state.question.selected_tenses as tense, tenseIndex}
                  {@const score = tenseScores[tense]}
                  <div class:g1-tense-active={tenseIndex === activeTenseIndex} class:g1-tense-done={checkedTenses.has(tense)} class:g1-tense-review={tenseIndex === activeTenseIndex && tenseReview} class="g1-tense-card">
                    <span>{String(tenseIndex + 1).padStart(2, '0')}</span>
                    <div><strong>{tense}</strong><small>{score ? `${score.correct}/${score.total} correct` : checkedTenses.has(tense) ? 'checked' : tenseIndex === activeTenseIndex ? tenseReview ? 'feedback shown' : 'filling now' : 'waiting'}</small></div>
                    <i aria-hidden="true">{checkedTenses.has(tense) ? '✓' : tenseIndex === activeTenseIndex ? '↓' : '·'}</i>
                  </div>
                {/each}
              </div>

              <div class="g1-verb-prompt">
                <div><span>CURRENT VERB</span><strong>{state.question.verb}</strong></div>
                <div>
                  <span>{activeTense} · {tenseReview ? 'feedback in place' : 'active answer'}</span>
                  {#if tenseReview}
                    <strong class="g1-prompt-score">{tenseReview.correct} / {tenseReview.total} correct</strong>
                    <small>Every result is shown. Enter opens the next tense.</small>
                  {:else}
                    <strong><em>{currentActiveCell?.pronoun || state.question.pronouns[0]}</em> + {state.question.verb}</strong>
                    <small>Locked guides stay visible; only cyan cells receive the pointer.</small>
                  {/if}
                </div>
                <div><span>TENSE</span><strong>{Math.min(activeTenseIndex + 1, state.question.selected_tenses.length)}/{state.question.selected_tenses.length}</strong><small>{tenseReview ? 'checked' : currentActiveLabel}</small></div>
              </div>

              <div class:g1-column-review={tenseReview} class="g1-active-column">
                <div class="g1-column-head">
                  <div><span>{tenseReview ? 'TENSE FEEDBACK' : 'ACTIVE TENSE'} {Math.min(activeTenseIndex + 1, state.question.selected_tenses.length)}/{state.question.selected_tenses.length}</span><strong>{activeTense}</strong></div>
                  <div><strong>{tenseReview ? `${tenseReview.correct}/${tenseReview.total} correct` : `${currentInputCells.length} answers`}</strong><small>{tenseReview ? 'all feedback shown' : 'fill top to bottom'}</small></div>
                </div>

                <div class="g1-column-rows">
                  <span class="g1-column-rail" aria-hidden="true"><i style={`height: ${tenseReview ? 100 : ((Math.max(0, currentInputCells.findIndex((cell) => cell.key === currentActiveCell?.key)) + 1) / Math.max(1, currentInputCells.length)) * 100}%`}></i></span>
                  {#each state.question.rows as row, rowIndex (row.pronoun)}
                    {@const cell = row.cells.find((entry) => entry.tense === activeTense)}
                    {@const feedbackCell = tenseReview?.cells.find((entry) => entry.pronoun === row.pronoun)}
                    {#if cell}
                      <div
                        class:g1-row-active={!tenseReview && currentActiveCell?.tense === cell.tense && currentActiveCell?.pronoun === row.pronoun}
                        class:g1-row-guide={cell.kind === 'prefilled'}
                        class:g1-row-correct={feedbackCell?.kind === 'answer' && feedbackCell.correct === true}
                        class:g1-row-wrong={feedbackCell?.kind === 'answer' && feedbackCell.correct === false}
                        class="g1-column-row"
                        style={`--row-index: ${rowIndex}`}
                      >
                        <span class="g1-row-marker" aria-hidden="true">{cell.kind === 'prefilled' ? '◆' : feedbackCell?.kind === 'answer' ? feedbackCell.correct ? '✓' : '×' : cell.kind === 'missing' ? '–' : currentActiveCell?.tense === cell.tense && currentActiveCell?.pronoun === row.pronoun ? '▶' : Boolean(answers[cell.tense]?.[row.pronoun]?.trim()) ? '✓' : '·'}</span>
                        <label for={!tenseReview && cell.kind === 'input' ? cellDomId(cellKey(cell.tense, row.pronoun)) : undefined}><small>{String(rowIndex + 1).padStart(2, '0')}</small><strong>{row.pronoun}</strong></label>

                        {#if cell.kind === 'missing'}
                          <div class="g1-missing-form">Not used in this tense</div>
                        {:else if cell.kind === 'prefilled'}
                          <div class="g1-locked-guide"><span aria-hidden="true">◆</span><strong>{cell.value}</strong><small>GIVEN GUIDE</small></div>
                        {:else if tenseReview && feedbackCell}
                          {#if feedbackCell.correct}
                            <div class="g1-inline-feedback g1-feedback-correct"><span aria-hidden="true">✓</span><strong>{feedbackCell.answer}</strong><small>RIGHT</small></div>
                          {:else}
                            <div class="g1-inline-feedback g1-feedback-wrong"><span aria-hidden="true">×</span><div><del>{feedbackCell.answer || 'No answer'}</del><strong>{feedbackCell.expected}</strong></div><small>CORRECT</small></div>
                          {/if}
                        {:else}
                          <div class="g1-input-shell">
                            <input
                              id={cellDomId(cellKey(cell.tense, row.pronoun))}
                              class="g1-conj-input"
                              type="text"
                              data-cell-key={cellKey(cell.tense, row.pronoun)}
                              value={answers[cell.tense]?.[row.pronoun] || ''}
                              tabindex={currentActiveCell?.tense === cell.tense && currentActiveCell?.pronoun === row.pronoun ? 0 : -1}
                              disabled={loading}
                              on:focus={() => (activeCellKey = cellKey(cell.tense, row.pronoun))}
                              on:input={(event) => setAnswer(cell.tense, row.pronoun, (event.currentTarget as HTMLInputElement).value)}
                              on:keydown={handleCellKeydown}
                              autocomplete="off"
                              autocapitalize="off"
                              spellcheck="false"
                              placeholder=""
                            />
                            {#if currentActiveCell?.tense === cell.tense && currentActiveCell?.pronoun === row.pronoun}<span>{currentInputCells[currentInputCells.length - 1]?.key === cellKey(cell.tense, row.pronoun) ? 'ENTER = CHECK TENSE' : 'ENTER = NEXT EMPTY ↓'}</span>{/if}
                          </div>
                        {/if}
                      </div>
                    {/if}
                  {/each}
                </div>
              </div>
            </div>

            <div class="trainer-actions g1-actions">
              {#if tenseReview}
                <button bind:this={nextTenseButton} class="primary-button g1-shortcut-action" type="button" on:click={continueAfterTense} disabled={loading}>
                  {activeTenseIndex < state.question.selected_tenses.length - 1 ? `Next: ${state.question.selected_tenses[activeTenseIndex + 1]}` : 'Finish verb'} <span class="kbd-chip">Enter</span>
                </button>
              {:else}
                <button class="primary-button g1-shortcut-action" type="button" on:click={checkActiveTense} disabled={loading}><span class="kbd-chip">Enter</span> Check {activeTense}</button>
              {/if}
              <button bind:this={finishButton} class:finish-warn={finishSessionWarning} class="ghost-button g1-shortcut-action" type="button" on:click={handleFinishClick} disabled={loading}>
                <span class="kbd-chip" class:kbd-chip-armed={finishSessionWarning}>{finishSessionWarning ? 'Esc ×1' : 'Esc ×2'}</span> {finishSessionWarning ? 'again to finish' : 'finish run'}
              </button>
            </div>
          </article>
        {/key}
      {/if}
    </div>
  {/if}
</section>

<style>
  .table-setup-card {
    gap: 1.4rem;
    overflow: hidden;
  }

  .table-setup-lead,
  .setup-launch-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1.25rem;
  }

  .table-setup-lead h2 {
    margin: 0.3rem 0 0;
    font-family: var(--display);
    font-size: clamp(1.25rem, 3vw, 1.8rem);
    line-height: 1.15;
    letter-spacing: -0.035em;
  }

  .table-setup-lead > .section-copy {
    max-width: 16rem;
    text-align: right;
  }

  .setup-step {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    padding-top: 1.1rem;
    border-top: 1px solid var(--line);
  }

  .setup-step-head {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .setup-step-head > div {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }

  .setup-step-head strong {
    font-size: 0.88rem;
    letter-spacing: 0.01em;
  }

  .setup-step-head small,
  .language-card small {
    color: var(--muted);
  }

  .step-number {
    display: grid;
    place-items: center;
    width: 2rem;
    height: 2rem;
    flex: 0 0 auto;
    border: 1px solid color-mix(in srgb, var(--accent) 38%, var(--line));
    border-radius: 10px;
    color: var(--accent-strong);
    background: color-mix(in srgb, var(--accent-soft) 140%, transparent);
    font: 700 0.68rem/1 var(--mono);
  }

  .language-card-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.55rem;
  }

  .language-card {
    position: relative;
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 0.65rem;
    min-width: 0;
    padding: 0.8rem;
    border: 1px solid var(--line);
    border-radius: 16px;
    color: var(--text);
    text-align: left;
    background: color-mix(in srgb, var(--surface-strong) 82%, transparent);
    transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
  }

  .language-card:not(:disabled):hover,
  .language-card-on {
    border-color: color-mix(in srgb, var(--accent) 55%, var(--line));
    background: color-mix(in srgb, var(--accent-soft) 155%, var(--surface-strong));
    transform: translateY(-1px);
  }

  .language-card-off {
    cursor: not-allowed;
    opacity: 0.48;
  }

  .language-code {
    display: grid;
    place-items: center;
    width: 2.2rem;
    height: 2.2rem;
    border-radius: 12px;
    color: var(--accent-strong);
    background: var(--accent-soft);
    font: 800 0.72rem/1 var(--mono);
  }

  .language-card-copy {
    display: flex;
    min-width: 0;
    flex-direction: column;
  }

  .language-card-copy strong,
  .language-card-copy small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .language-card-copy strong {
    font-size: 0.84rem;
  }

  .language-card-copy small {
    font-size: 0.64rem;
  }

  .language-check {
    color: var(--accent-strong);
    font-weight: 800;
  }

  .tense-staircase {
    position: relative;
    display: grid;
    gap: 0.48rem;
    padding-left: 0.2rem;
  }

  .tense-staircase::before {
    position: absolute;
    top: 1.55rem;
    bottom: 3.15rem;
    left: 1.7rem;
    width: 1px;
    content: '';
    background: linear-gradient(var(--accent), color-mix(in srgb, var(--accent) 12%, var(--line)));
  }

  .stair-step {
    position: relative;
    display: grid;
    grid-template-columns: auto minmax(7.5rem, 0.8fr) minmax(0, 2fr);
    gap: 0.75rem;
    align-items: center;
    min-height: 4rem;
    padding: 0.62rem;
    border: 1px solid var(--line);
    border-radius: 15px;
    background: color-mix(in srgb, var(--surface-strong) 64%, transparent);
    transition: border-color 160ms ease, background 160ms ease, transform 160ms ease;
  }

  .stair-step.stair-on {
    border-color: color-mix(in srgb, var(--accent) 62%, var(--line));
    background: color-mix(in srgb, var(--accent-soft) 64%, transparent);
  }

  .stair-step.stair-disabled {
    opacity: 0.4;
  }

  .stair-level {
    z-index: 1;
    display: grid;
    width: 2.45rem;
    min-height: 2.65rem;
    gap: 0.22rem;
    place-items: center;
    padding: 0.3rem;
    border: 1px solid var(--line-strong);
    border-radius: 11px;
    color: var(--muted);
    background: var(--surface-strong);
  }

  .stair-on .stair-level {
    border-color: var(--accent);
    color: var(--accent-strong);
    box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 10%, transparent);
  }

  .stair-level strong {
    font: 800 0.66rem/1 var(--mono);
  }

  .stair-level span,
  .custom-key {
    color: var(--muted);
    font: 700 0.4rem/1 var(--mono);
    white-space: nowrap;
  }

  .stair-copy {
    display: grid;
    align-content: center;
    gap: 0.15rem;
    min-width: 0;
  }

  .stair-copy strong {
    font-size: 0.84rem;
  }

  .stair-copy small {
    color: var(--muted);
    font-size: 0.58rem;
  }

  .stair-tense-row {
    display: flex;
    min-width: 0;
    flex-wrap: wrap;
    gap: 0.4rem;
    align-content: center;
  }

  .stair-tense-row button {
    padding: 0.46rem 0.58rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    color: var(--muted);
    background: color-mix(in srgb, var(--surface-strong) 74%, transparent);
    font-size: 0.62rem;
  }

  .stair-tense-row button.tense-on {
    border-color: color-mix(in srgb, var(--accent) 68%, var(--line));
    color: var(--text);
    background: var(--accent-soft);
  }

  .custom-route {
    display: flex;
    gap: 0.7rem;
    align-items: center;
    margin-left: 0.8rem;
    padding: 0.72rem 0.85rem;
    border: 1px dashed var(--line-strong);
    border-radius: 14px;
    color: var(--muted);
    text-align: left;
    background: transparent;
  }

  .custom-route.custom-on {
    border-style: solid;
    border-color: var(--accent);
    color: var(--text);
    background: var(--accent-soft);
  }

  .custom-route > span:nth-child(2) {
    display: grid;
    flex: 1;
    gap: 0.1rem;
  }

  .custom-route strong {
    font-size: 0.76rem;
  }

  .custom-route small {
    font-size: 0.56rem;
  }

  .custom-spark {
    color: var(--accent-strong);
  }

  .setup-grid-two {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }

  .compact-step {
    min-width: 0;
  }

  .length-card-row,
  .support-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.5rem;
  }

  .length-card,
  .support-row button {
    display: flex;
    min-width: 0;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.05rem;
    min-height: 3.5rem;
    padding: 0.55rem 0.3rem;
    border: 1px solid var(--line);
    border-radius: 13px;
    color: var(--muted);
    background: transparent;
  }

  .length-card strong {
    color: var(--text);
    font: 800 1.15rem/1 var(--display);
  }

  .length-card span,
  .support-row small {
    font-size: 0.65rem;
  }

  .length-card-on,
  .support-row .support-on {
    border-color: color-mix(in srgb, var(--accent) 58%, var(--line));
    color: var(--accent-strong);
    background: var(--accent-soft);
  }

  .support-row strong {
    font-size: 0.72rem;
  }

  .setup-launch-row {
    align-items: center;
    padding: 1rem;
    border: 1px solid color-mix(in srgb, var(--accent) 30%, var(--line));
    border-radius: 18px;
    background: linear-gradient(120deg, color-mix(in srgb, var(--accent-soft) 135%, transparent), transparent);
  }

  .launch-summary {
    display: grid;
    gap: 0.1rem;
  }

  .launch-summary > span {
    color: var(--accent-strong);
    font: 700 0.67rem/1.4 var(--mono);
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .table-launch-button {
    flex: 0 0 auto;
    gap: 0.65rem;
  }

  .table-clear-card {
    position: relative;
    display: grid;
    justify-items: center;
    gap: 0.85rem;
    overflow: hidden;
    padding: clamp(1.5rem, 5vw, 2.7rem);
    text-align: center;
    animation: table-clear-in 420ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  .table-clear-card h2 {
    margin: 0;
    color: var(--text);
    font: 850 clamp(2rem, 7vw, 3.8rem)/0.95 var(--display);
    letter-spacing: -0.06em;
  }

  .table-clear-score {
    margin: 0;
    color: var(--muted);
    font: 700 0.78rem/1.5 var(--mono);
  }

  .table-clear-dots {
    display: flex;
    max-width: 100%;
    flex-wrap: wrap;
    gap: 0.45rem;
    justify-content: center;
  }

  .table-clear-dots span {
    width: 0.62rem;
    height: 0.62rem;
    border: 1px solid var(--line-strong);
    border-radius: 50%;
    background: var(--surface);
  }

  .table-clear-dots .table-clear-dot-on {
    border-color: var(--success);
    background: var(--success);
    box-shadow: 0 0 10px color-mix(in srgb, var(--success) 45%, transparent);
  }

  .table-clear-actions {
    display: flex;
    gap: 0.65rem;
    margin-top: 0.35rem;
  }

  .table-clear-burst {
    position: absolute;
    inset: 50% auto auto 50%;
    z-index: -1;
  }

  .table-clear-burst i {
    position: absolute;
    width: 12rem;
    height: 12rem;
    border: 1px solid color-mix(in srgb, var(--success) 35%, transparent);
    border-radius: 50%;
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.2);
    animation: table-clear-ring 1.4s ease-out both;
  }

  .table-clear-burst i:nth-child(2) { animation-delay: 120ms; }
  .table-clear-burst i:nth-child(3) { animation-delay: 240ms; }

  @keyframes table-clear-in {
    from { opacity: 0; transform: translateY(1rem) scale(0.985); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }

  @keyframes table-clear-ring {
    0% { opacity: 0.7; transform: translate(-50%, -50%) scale(0.2); }
    100% { opacity: 0; transform: translate(-50%, -50%) scale(2.4); }
  }

  .g1-production-card {
    gap: 1rem;
    animation: g1-stage-in 420ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  @keyframes g1-stage-in {
    from { opacity: 0; transform: translateY(0.8rem); }
    to { opacity: 1; transform: translateY(0); }
  }

  .g1-session-frame {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    padding: clamp(0.85rem, 2.5vw, 1.15rem);
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--accent) 38%, rgba(255, 255, 255, 0.14));
    border-radius: 24px;
    color: white;
    background:
      radial-gradient(circle at 92% 0%, color-mix(in srgb, var(--accent) 20%, transparent), transparent 31%),
      color-mix(in srgb, var(--surface-dark) 91%, black 9%);
    box-shadow: 0 24px 55px rgba(5, 8, 20, 0.2);
  }

  .g1-utility-row,
  .g1-column-head,
  .g1-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.8rem;
  }

  .g1-utility-row {
    color: rgba(255, 255, 255, 0.48);
    font: 700 0.5rem/1 var(--mono);
    letter-spacing: 0.1em;
  }

  .g1-utility-row > span {
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }

  .g1-utility-row i {
    width: 0.45rem;
    height: 0.45rem;
    border-radius: 50%;
    background: #55ee9b;
    box-shadow: 0 0 9px #55ee9b;
  }

  .g1-utility-row small {
    font-size: 0.48rem;
    letter-spacing: 0;
  }

  .g1-tense-strip {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(7.5rem, 1fr));
    gap: 0.4rem;
  }

  .g1-tense-card {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 0.45rem;
    align-items: center;
    min-width: 0;
    padding: 0.58rem;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    color: rgba(255, 255, 255, 0.5);
    background: rgba(255, 255, 255, 0.035);
  }

  .g1-tense-card > span {
    color: var(--accent-2);
    font: 750 0.45rem/1 var(--mono);
  }

  .g1-tense-card > div {
    display: grid;
    gap: 0.1rem;
    min-width: 0;
  }

  .g1-tense-card strong,
  .g1-tense-card small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .g1-tense-card strong {
    font-size: 0.62rem;
  }

  .g1-tense-card small {
    font-size: 0.46rem;
  }

  .g1-tense-card > i {
    font-style: normal;
    font-weight: 850;
  }

  .g1-tense-active {
    border-color: var(--accent-2);
    color: white;
    background: color-mix(in srgb, var(--accent) 22%, transparent);
    box-shadow: inset 0 -2px 0 var(--accent-2);
  }

  .g1-tense-done {
    border-color: color-mix(in srgb, #55ee9b 45%, transparent);
    color: #55ee9b;
    background: color-mix(in srgb, #55ee9b 9%, transparent);
    box-shadow: none;
  }

  .g1-tense-review {
    border-color: #f6c84c;
    color: white;
    background: color-mix(in srgb, #f6c84c 12%, transparent);
    box-shadow: inset 0 -2px 0 #f6c84c;
  }

  .g1-verb-prompt {
    display: grid;
    grid-template-columns: minmax(6rem, 0.65fr) minmax(0, 1.8fr) auto;
    gap: 0.8rem;
    align-items: center;
    min-height: 6.2rem;
    padding: 0.8rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    background:
      linear-gradient(rgba(255, 255, 255, 0.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255, 255, 255, 0.025) 1px, transparent 1px),
      rgba(8, 13, 31, 0.54);
    background-size: 24px 24px;
  }

  .g1-verb-prompt > div {
    display: grid;
    gap: 0.16rem;
    min-width: 0;
  }

  .g1-verb-prompt > div:nth-child(2) {
    justify-items: center;
    text-align: center;
  }

  .g1-verb-prompt > div:last-child {
    justify-items: end;
    text-align: right;
  }

  .g1-verb-prompt span,
  .g1-column-head span {
    color: var(--accent-2);
    font: 750 0.48rem/1 var(--mono);
    letter-spacing: 0.1em;
  }

  .g1-verb-prompt > div:first-child > strong {
    font: 820 clamp(1.35rem, 4vw, 2rem)/1 var(--display);
  }

  .g1-verb-prompt > div:nth-child(2) > strong {
    font: 780 clamp(1.08rem, 3.1vw, 1.85rem)/1.08 var(--display);
    letter-spacing: -0.035em;
  }

  .g1-verb-prompt > div:first-child > strong,
  .g1-verb-prompt > div:nth-child(2) > strong {
    max-width: 100%;
    min-width: 0;
    overflow-wrap: anywhere;
  }

  .g1-verb-prompt em {
    color: #f6c84c;
    font-style: normal;
  }

  .g1-verb-prompt .g1-prompt-score {
    color: #f6c84c;
    font-family: var(--mono);
    font-size: clamp(1.05rem, 3vw, 1.45rem);
  }

  .g1-verb-prompt small,
  .g1-column-head small {
    color: rgba(255, 255, 255, 0.5);
    font-size: 0.5rem;
  }

  .g1-active-column {
    width: min(100%, 650px);
    margin-inline: auto;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.025);
  }

  .g1-column-review {
    border-color: color-mix(in srgb, #f6c84c 48%, transparent);
    box-shadow: 0 0 0 3px color-mix(in srgb, #f6c84c 5%, transparent);
  }

  .g1-column-head {
    padding: 0.72rem 0.8rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(255, 255, 255, 0.035);
  }

  .g1-column-head > div {
    display: grid;
    gap: 0.12rem;
  }

  .g1-column-head > div:last-child {
    justify-items: end;
    text-align: right;
  }

  .g1-column-head strong {
    font-size: 0.7rem;
  }

  .g1-column-rows {
    position: relative;
    display: grid;
    gap: 0.36rem;
    padding: 0.65rem 0.65rem 0.65rem 1.1rem;
  }

  .g1-column-rail {
    position: absolute;
    top: 0.8rem;
    bottom: 0.8rem;
    left: 0.55rem;
    width: 2px;
    overflow: hidden;
    background: rgba(255, 255, 255, 0.1);
  }

  .g1-column-rail i {
    display: block;
    width: 100%;
    background: linear-gradient(var(--accent-2), var(--accent));
    transition: height 180ms ease;
  }

  .g1-column-row {
    position: relative;
    display: grid;
    grid-template-columns: auto 9rem minmax(0, 1fr);
    gap: 0.7rem;
    align-items: center;
    min-height: 4rem;
    padding: 0.58rem 0.65rem;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 5px;
    background: rgba(255, 255, 255, 0.025);
    transition: 160ms ease;
  }

  .g1-row-active {
    border-color: var(--accent-2);
    background: color-mix(in srgb, var(--accent) 18%, rgba(255, 255, 255, 0.025));
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 9%, transparent);
    transform: translateX(0.2rem);
  }

  .g1-row-active .g1-row-marker {
    animation: g1-pointer-pulse 1.15s ease-in-out infinite;
  }

  @keyframes g1-pointer-pulse {
    50% { opacity: 0.45; transform: translateX(0.18rem); }
  }

  .g1-row-guide {
    border-color: color-mix(in srgb, #f6c84c 42%, transparent);
    background: color-mix(in srgb, #f6c84c 8%, rgba(255, 255, 255, 0.02));
  }

  .g1-row-correct {
    border-color: color-mix(in srgb, #55ee9b 58%, transparent);
    background: color-mix(in srgb, #55ee9b 10%, rgba(255, 255, 255, 0.02));
  }

  .g1-row-wrong {
    border-color: color-mix(in srgb, #ff7188 62%, transparent);
    background: color-mix(in srgb, #ff7188 10%, rgba(255, 255, 255, 0.02));
  }

  .g1-column-review .g1-column-row {
    animation: g1-verdict-in 240ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
    animation-delay: calc(var(--row-index, 0) * 45ms);
  }

  @keyframes g1-verdict-in {
    from { opacity: 0; transform: translateY(0.3rem); }
    to { opacity: 1; transform: translateY(0); }
  }

  .g1-row-marker {
    width: 0.75rem;
    color: var(--accent-2);
    font: 800 0.56rem/1 var(--mono);
    text-align: center;
  }

  .g1-row-guide .g1-row-marker { color: #f6c84c; }
  .g1-row-correct .g1-row-marker { color: #55ee9b; }
  .g1-row-wrong .g1-row-marker { color: #ff7188; }

  .g1-column-row label {
    display: grid;
    grid-template-columns: 1.5rem 1fr;
    gap: 0.35rem;
    align-items: center;
  }

  .g1-column-row label small {
    color: var(--accent-2);
    font: 750 0.44rem/1 var(--mono);
  }

  .g1-column-row label strong {
    color: white;
    font-size: clamp(1.02rem, 2.4vw, 1.18rem);
    font-weight: 820;
    line-height: 1.15;
  }

  .g1-input-shell {
    position: relative;
    min-width: 0;
  }

  .g1-conj-input {
    width: 100%;
    min-width: 0;
    padding: 0.72rem 0.8rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    outline: none;
    color: white;
    background: rgba(6, 8, 24, 0.72);
    font: 680 0.95rem/1 var(--display);
  }

  .g1-conj-input:focus {
    border-color: var(--accent-2);
    box-shadow: inset 0 -2px 0 var(--accent-2);
  }

  .g1-input-shell > span {
    position: absolute;
    right: 0.35rem;
    bottom: -0.28rem;
    padding: 0.13rem 0.3rem;
    border-radius: 999px;
    color: #191300;
    background: #f6c84c;
    font: 850 0.38rem/1 var(--mono);
  }

  .g1-locked-guide,
  .g1-inline-feedback,
  .g1-missing-form {
    min-width: 0;
    padding: 0.68rem 0.75rem;
    border-radius: 8px;
  }

  .g1-locked-guide,
  .g1-inline-feedback {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 0.55rem;
    align-items: center;
  }

  .g1-locked-guide {
    border: 1px solid color-mix(in srgb, #f6c84c 38%, transparent);
    color: #ffe39a;
    background: color-mix(in srgb, #f6c84c 9%, rgba(6, 8, 24, 0.75));
  }

  .g1-locked-guide > span,
  .g1-locked-guide > small {
    color: #f6c84c;
  }

  .g1-locked-guide strong,
  .g1-inline-feedback strong {
    min-width: 0;
    color: white;
    font-size: clamp(0.92rem, 2.2vw, 1.08rem);
    line-height: 1.2;
    overflow-wrap: anywhere;
  }

  .g1-locked-guide small,
  .g1-inline-feedback small {
    font: 800 0.42rem/1 var(--mono);
    letter-spacing: 0.08em;
  }

  .g1-inline-feedback > span:first-child {
    display: grid;
    width: 1.65rem;
    height: 1.65rem;
    place-items: center;
    border: 1px solid currentColor;
    border-radius: 50%;
    font: 850 0.78rem/1 var(--mono);
  }

  .g1-feedback-correct {
    color: #78f2ad;
    background: color-mix(in srgb, #55ee9b 8%, rgba(6, 8, 24, 0.65));
  }

  .g1-feedback-wrong {
    color: #ff91a3;
    background: color-mix(in srgb, #ff7188 9%, rgba(6, 8, 24, 0.65));
  }

  .g1-feedback-wrong > div {
    display: flex;
    min-width: 0;
    gap: 0.6rem;
    align-items: baseline;
  }

  .g1-feedback-wrong del {
    min-width: 0;
    color: rgba(255, 255, 255, 0.5);
    font-size: 0.84rem;
    text-decoration-color: #ff7188;
    text-decoration-thickness: 2px;
    overflow-wrap: anywhere;
  }

  .g1-feedback-wrong strong::before {
    margin-right: 0.35rem;
    color: #ff91a3;
    content: '→';
  }

  .g1-missing-form {
    color: rgba(255, 255, 255, 0.42);
    background: rgba(6, 8, 24, 0.42);
    font-size: 0.62rem;
  }

  .g1-actions {
    justify-content: flex-end;
  }

  .g1-shortcut-action {
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
  }

  .g1-shortcut-action.finish-warn {
    border-color: #f6c84c;
    color: #f6c84c;
    background: color-mix(in srgb, #f6c84c 10%, transparent);
    box-shadow: 0 0 0 3px color-mix(in srgb, #f6c84c 8%, transparent);
  }

  .g1-shortcut-action .kbd-chip-armed {
    border-color: #f6c84c;
    color: #f6c84c;
  }

  :global(html[data-theme='arcade']) .step-number,
  :global(html[data-theme='arcade']) .language-code,
  :global(html[data-theme='arcade']) .launch-summary > span,
  :global(html[data-theme='arcade']) .g1-verb-prompt > div:first-child > strong,
  :global(html[data-theme='arcade']) .g1-verb-prompt > div:nth-child(2) > strong {
    text-shadow: 0 0 9px color-mix(in srgb, var(--accent) 65%, transparent);
  }

  @media (max-width: 760px) {
    .language-card-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .setup-grid-two {
      grid-template-columns: 1fr;
    }

    .stair-step {
      grid-template-columns: auto minmax(0, 1fr);
    }

    .stair-tense-row {
      grid-column: 2;
    }
  }

  @media (max-width: 560px) {
    .table-setup-lead,
    .setup-launch-row {
      align-items: stretch;
      flex-direction: column;
    }

    .table-setup-lead > .section-copy {
      max-width: none;
      text-align: left;
    }

    .language-card {
      grid-template-columns: auto 1fr;
    }

    .language-check {
      display: none;
    }

    .table-launch-button {
      width: 100%;
    }

    .g1-session-frame {
      border-radius: 18px;
    }

    .g1-utility-row {
      align-items: flex-start;
      flex-direction: column;
    }

    .g1-tense-strip {
      grid-template-columns: 1fr;
    }

    .g1-verb-prompt {
      grid-template-columns: 1fr auto;
      min-height: 0;
    }

    .g1-verb-prompt > div:nth-child(2) {
      grid-column: 1 / -1;
      grid-row: 2;
      padding-top: 0.55rem;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }

    .g1-column-row {
      grid-template-columns: auto 1fr;
    }

    .g1-column-row label strong {
      font-size: 1.08rem;
    }

    .g1-input-shell,
    .g1-locked-guide,
    .g1-inline-feedback,
    .g1-missing-form {
      grid-column: 2;
    }

    .g1-inline-feedback,
    .g1-locked-guide {
      grid-template-columns: auto minmax(0, 1fr);
    }

    .g1-inline-feedback > small,
    .g1-locked-guide > small {
      display: none;
    }

    .g1-feedback-wrong > div {
      align-items: flex-start;
      flex-direction: column;
      gap: 0.15rem;
    }

    .g1-actions {
      align-items: stretch;
      flex-direction: column;
    }

    .g1-actions button {
      width: 100%;
      justify-content: center;
    }

    .table-clear-actions {
      width: 100%;
      flex-direction: column;
    }

    .table-clear-actions button {
      width: 100%;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .g1-production-card,
    .g1-column-review .g1-column-row,
    .g1-row-active .g1-row-marker,
    .table-clear-card,
    .table-clear-burst i {
      animation: none;
    }
  }
</style>
