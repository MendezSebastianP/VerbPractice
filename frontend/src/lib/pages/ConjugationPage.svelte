<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { fade } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import { playCue } from '../sound';
  import { applyReward } from '../profile';
  import { celebrateReward, flashMiss } from '../fx';
  import type { ConjugationState, ConjugationTenseReview, LanguageConfig, RewardState } from '../types';

  export let csrfToken = '';
  export let soundEnabled = false;
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;

  let loading = true;
  let error = '';
  let state: ConjugationState | null = null;
  let language = 'FR';
  let level = 'easy';
  let fillLevel = 'hard';
  let length = 5;
  let retryButton: HTMLButtonElement | null = null;
  let nextTenseButton: HTMLButtonElement | null = null;
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

  const LEVELS = [
    { value: 'easy', label: 'Level 1', note: 'Core tense' },
    { value: 'medium', label: 'Level 2', note: 'Core + intermediate' },
    { value: 'hard', label: 'Level 3', note: 'All tenses' },
    { value: 'custom', label: 'Custom', note: 'Pick your tenses' },
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

  function completeVerbCount(): number {
    const config = currentLanguage();
    if (!config || !selectedTenses.length) {
      return 0;
    }
    return Math.min(...selectedTenses.map((tense) => config.tense_verb_counts[tense] || 0));
  }

  function canStart(): boolean {
    return Boolean(currentLanguage()?.available && selectedTenses.length && completeVerbCount() > 0);
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
  $: currentInputCells = buildInputCells(state?.question, activeTense);
  $: currentActiveCell = currentInputCells.find((cell) => cell.key === activeCellKey) || currentInputCells[0] || null;
  $: currentActiveLabel = currentActiveCell ? `${currentActiveCell.pronoun} -> ${currentActiveCell.tense}` : 'Nothing left to fill';

  function showFinishedPrompt(): boolean {
    return Boolean(
      !state?.session
      && (justFinished || state?.finished || state?.result?.finished)
      && !showSetupAfterFinish,
    );
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

  onMount(load);

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
    showSetupAfterFinish = true;
  }

  async function finishSession(): Promise<void> {
    loading = true;
    error = '';
    try {
      state = await api.finishConjugation(csrfToken);
      activeCellKey = '';
      justFinished = false;
      showSetupAfterFinish = true;
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
    if (event.key !== 'Enter' || loading || (!showFinishedPrompt() && !tenseReview)) {
      return;
    }
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
      return;
    }
    if (document.activeElement === retryButton || document.activeElement === nextTenseButton) {
      return;
    }
    event.preventDefault();
    if (tenseReview) {
      void continueAfterTense();
    } else {
      void startSession();
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
      {:else if state.feedback}
        <div class="feedback-banner info-banner">{state.feedback}</div>
      {/if}

      {#if showFinishedPrompt()}
        <div bind:this={finishedCard} class="feedback-banner success-banner finish-prompt-banner" in:fade={{ duration: 160 }}>
          <div class="finish-prompt-copy">
            <strong>Conjugation run complete.</strong>
            <span>Press Enter to restart with the same settings, or use the buttons.</span>
          </div>

          <div class="trainer-actions finish-prompt-actions">
            <button bind:this={retryButton} class="primary-button" type="button" on:click={startSession} disabled={loading}>
              Try again
            </button>
            <button class="secondary-button" type="button" on:click={revealSetup} disabled={loading}>
              Change settings
            </button>
          </div>
        </div>
      {/if}

      {#if reward() && !showFinishedPrompt()}
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

      {#if !showFinishedPrompt() && state.setup}
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
              <div><strong>Tense level</strong><small>Levels add tenses cumulatively.</small></div>
            </div>
            <div class="level-card-grid">
              {#each LEVELS as item}
                <button
                  class:level-card-on={level === item.value}
                  class="level-card"
                  type="button"
                  disabled={item.value !== 'custom' && !levelAvailable(item.value)}
                  aria-pressed={level === item.value}
                  on:click={() => chooseLevel(item.value)}
                >
                  <span>{item.label}</span>
                  <small>{item.value === 'custom' ? item.note : `${tensesForLevel(currentLanguage(), item.value).length} ${tensesForLevel(currentLanguage(), item.value).length === 1 ? 'tense' : 'tenses'}`}</small>
                </button>
              {/each}
            </div>

            <div class="tense-picker-shell" class:tense-picker-custom={level === 'custom'}>
              <div class="tense-picker-head">
                <span>{level === 'custom' ? 'Pick tenses' : 'Included tenses'}</span>
                <small>{selectedTenses.length} selected · clicking a tense switches to Custom</small>
              </div>
              <div class="tense-wall">
                {#each currentLanguage()?.available_tenses || [] as tense}
                  <button class:option-on={selectedTenses.includes(tense)} class="tense-chip" type="button" on:click={() => toggleTense(tense)}>{tense}</button>
                {/each}
              </div>
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
              <span>{currentLanguage()?.name || language}</span>
              <strong>{selectedTenses.length} {selectedTenses.length === 1 ? 'tense' : 'tenses'} × {length} verbs</strong>
              <small>At least {completeVerbCount()} complete tables available</small>
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
                <small>{tenseReview ? 'All feedback shown · Enter continues' : 'Enter moves top to bottom'}</small>
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
                <button bind:this={nextTenseButton} class="primary-button" type="button" on:click={continueAfterTense} disabled={loading}>
                  {activeTenseIndex < state.question.selected_tenses.length - 1 ? `Next: ${state.question.selected_tenses[activeTenseIndex + 1]}` : 'Finish verb'} <span class="kbd-chip">Enter</span>
                </button>
              {:else}
                <button class="primary-button" type="button" on:click={checkActiveTense} disabled={loading}>Check {activeTense}</button>
              {/if}
              <button class="ghost-button" type="button" on:click={finishSession} disabled={loading}>Finish session</button>
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
  .language-card small,
  .level-card small,
  .launch-summary small {
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

  .language-card-grid,
  .level-card-grid {
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

  .level-card {
    display: flex;
    min-height: 4.25rem;
    flex-direction: column;
    justify-content: center;
    gap: 0.2rem;
    padding: 0.7rem;
    border: 1px solid var(--line);
    border-radius: 14px;
    color: var(--text);
    background: transparent;
  }

  .level-card:disabled {
    cursor: not-allowed;
    opacity: 0.4;
  }

  .level-card-on {
    border-color: color-mix(in srgb, var(--accent) 58%, var(--line));
    color: var(--accent-strong);
    background: var(--accent-soft);
    box-shadow: inset 0 -3px 0 color-mix(in srgb, var(--accent) 42%, transparent);
  }

  .level-card span {
    font-weight: 750;
  }

  .level-card small {
    font-size: 0.68rem;
  }

  .tense-picker-shell {
    padding: 0.85rem;
    border: 1px dashed var(--line-strong);
    border-radius: 16px;
    background:
      radial-gradient(circle at 90% 0%, color-mix(in srgb, var(--accent) 10%, transparent), transparent 42%),
      color-mix(in srgb, var(--surface-strong) 68%, transparent);
  }

  .tense-picker-custom {
    border-style: solid;
    border-color: color-mix(in srgb, var(--accent) 48%, var(--line));
  }

  .tense-picker-head {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.65rem;
    color: var(--text);
    font-size: 0.75rem;
    font-weight: 700;
  }

  .tense-picker-head small {
    color: var(--muted);
    font-weight: 500;
  }

  .tense-wall {
    gap: 0.45rem;
  }

  .tense-chip {
    padding: 0.55rem 0.7rem;
    border-radius: 10px;
    font-size: 0.72rem;
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

  .g1-production-card {
    gap: 1rem;
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
    font: 780 clamp(1.25rem, 3.5vw, 1.85rem)/1 var(--display);
    letter-spacing: -0.035em;
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
    grid-template-columns: auto 7.5rem minmax(0, 1fr);
    gap: 0.55rem;
    align-items: center;
    min-height: 3.2rem;
    padding: 0.45rem 0.55rem;
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
    font-size: 0.86rem;
    font-weight: 820;
  }

  .g1-input-shell {
    position: relative;
    min-width: 0;
  }

  .g1-conj-input {
    width: 100%;
    min-width: 0;
    padding: 0.65rem 0.7rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    outline: none;
    color: white;
    background: rgba(6, 8, 24, 0.72);
    font: 650 0.74rem/1 var(--display);
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
    padding: 0.58rem 0.65rem;
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
    overflow: hidden;
    color: white;
    font-size: 0.72rem;
    text-overflow: ellipsis;
  }

  .g1-locked-guide small,
  .g1-inline-feedback small {
    font: 800 0.42rem/1 var(--mono);
    letter-spacing: 0.08em;
  }

  .g1-inline-feedback > span:first-child {
    display: grid;
    width: 1.35rem;
    height: 1.35rem;
    place-items: center;
    border: 1px solid currentColor;
    border-radius: 50%;
    font: 850 0.65rem/1 var(--mono);
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
    overflow: hidden;
    color: rgba(255, 255, 255, 0.5);
    font-size: 0.64rem;
    text-decoration-color: #ff7188;
    text-decoration-thickness: 2px;
    text-overflow: ellipsis;
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

  :global(html[data-theme='arcade']) .step-number,
  :global(html[data-theme='arcade']) .language-code,
  :global(html[data-theme='arcade']) .launch-summary > span,
  :global(html[data-theme='arcade']) .g1-verb-prompt > div:first-child > strong,
  :global(html[data-theme='arcade']) .g1-verb-prompt > div:nth-child(2) > strong {
    text-shadow: 0 0 9px color-mix(in srgb, var(--accent) 65%, transparent);
  }

  @media (max-width: 760px) {
    .language-card-grid,
    .level-card-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .setup-grid-two {
      grid-template-columns: 1fr;
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

    .tense-picker-head {
      flex-direction: column;
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
    }
  }
</style>
