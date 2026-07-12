<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { fade } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import { playCue } from '../sound';
  import { applyReward } from '../profile';
  import { celebrateReward, flashMiss } from '../fx';
  import type { ConjugationState, LanguageConfig, RewardState } from '../types';

  export let csrfToken = '';
  export let soundEnabled = false;
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;

  let loading = true;
  let error = '';
  let state: ConjugationState | null = null;
  let language = 'FR';
  let level = 'easy';
  let fillLevel = 'easy';
  let length = 5;
  let retryButton: HTMLButtonElement | null = null;
  let submitButton: HTMLButtonElement | null = null;
  let finishedCard: HTMLElement | null = null;
  let selectedTenses: string[] = [];
  let answers: Record<string, Record<string, string>> = {};
  let activeCellKey = '';
  let justFinished = false;
  let showSetupAfterFinish = false;

  type InputCell = {
    key: string;
    tense: string;
    pronoun: string;
  };

  function currentLanguage(): LanguageConfig | undefined {
    return state?.languages.find((entry) => entry.code === language);
  }

  function visibleTenses(): string[] {
    const config = currentLanguage();
    if (!config) {
      return [];
    }

    const easy = config.difficulty_tiers.easy || [];
    const medium = config.difficulty_tiers.medium || [];
    const hard = config.difficulty_tiers.hard || [];

    if (level === 'easy') {
      return [...easy];
    }
    if (level === 'medium') {
      return [...easy, ...medium];
    }
    return [...easy, ...medium, ...hard];
  }

  function syncSelection(): void {
    if (level !== 'custom') {
      selectedTenses = visibleTenses();
    } else {
      const available = new Set(visibleTenses());
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

    const firstLanguage = nextState.languages[0];
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

  function inputCells(): InputCell[] {
    if (!state?.question) {
      return [];
    }

    const rowsByPronoun = new Map(state.question.rows.map((row) => [row.pronoun, row]));
    const cells: InputCell[] = [];
    for (const tense of state.question.selected_tenses) {
      for (const pronoun of state.question.pronouns) {
        const row = rowsByPronoun.get(pronoun);
        const cell = row?.cells.find((entry) => entry.tense === tense);
        if (cell?.kind === 'input') {
          cells.push({ key: cellKey(tense, pronoun), tense, pronoun });
        }
      }
    }
    return cells;
  }

  function activeCell(): InputCell | null {
    const cells = inputCells();
    const [firstCell] = cells;
    if (!firstCell) {
      return null;
    }
    return cells.find((cell) => cell.key === activeCellKey) || firstCell;
  }

  function activeLabel(): string {
    const cell = activeCell();
    return cell ? `${cell.pronoun} -> ${cell.tense}` : 'Nothing left to fill';
  }

  function isActivePronoun(pronoun: string): boolean {
    return activeCell()?.pronoun === pronoun;
  }

  function isActiveTense(tense: string): boolean {
    return activeCell()?.tense === tense;
  }

  function isActiveCell(tense: string, pronoun: string): boolean {
    const cell = activeCell();
    return cell?.tense === tense && cell.pronoun === pronoun;
  }

  function hasTypedAnswer(tense: string, pronoun: string): boolean {
    return Boolean(getAnswer(tense, pronoun).trim());
  }

  function showFinishedPrompt(): boolean {
    return Boolean(!state?.session && (justFinished || state?.finished || state?.result?.finished) && !showSetupAfterFinish);
  }

  async function load(): Promise<void> {
    loading = true;
    error = '';
    try {
      state = await api.conjugationState();
      activeCellKey = '';
      justFinished = Boolean(state?.finished || state?.result?.finished);
      showSetupAfterFinish = false;
      syncControlsFromState(state, true);
      answers = {};
      if (state.feedback && state.result) {
        notify(state.feedback, state.result.accuracy === 100 ? 'success' : 'info');
      }
      await focusPrimaryControl();
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to load conjugation training';
    } finally {
      loading = false;
    }
  }

  onMount(load);

  function focusCellByKey(key: string): void {
    activeCellKey = key;
    const input = document.getElementById(cellDomId(key)) as HTMLInputElement | null;
    input?.focus();
  }

  function focusFirstInput(): void {
    const [firstCell] = inputCells();
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

  function getAnswer(tense: string, pronoun: string): string {
    return answers[tense]?.[pronoun] || '';
  }

  function toggleTense(tense: string): void {
    level = 'custom';
    selectedTenses = selectedTenses.includes(tense)
      ? selectedTenses.filter((entry) => entry !== tense)
      : [...selectedTenses, tense];
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
      activeCellKey = '';
      justFinished = false;
      showSetupAfterFinish = false;
      syncControlsFromState(state);
      answers = {};
      await focusPrimaryControl();
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to start conjugation session';
    } finally {
      loading = false;
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
      activeCellKey = '';
      justFinished = Boolean(state?.finished || state?.result?.finished);
      showSetupAfterFinish = false;
      answers = {};
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
      await focusPrimaryControl();
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to grade conjugation answers';
    } finally {
      loading = false;
    }
  }

  function handleCellKeydown(event: KeyboardEvent): void {
    if (event.key !== 'Enter') {
      return;
    }
    event.preventDefault();
    const current = event.currentTarget as HTMLInputElement;
    const currentKey = current.dataset.cellKey;
    const cells = inputCells();
    const index = currentKey ? cells.findIndex((cell) => cell.key === currentKey) : -1;
    if (index >= 0 && index < cells.length - 1) {
      focusCellByKey(cells[index + 1].key);
      return;
    }
    void submit();
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
    if (event.key !== 'Enter' || loading || !showFinishedPrompt()) {
      return;
    }
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
      return;
    }
    if (document.activeElement === retryButton) {
      return;
    }
    event.preventDefault();
    void startSession();
  }
</script>

<svelte:window on:keydown={handleWindowKeydown} />

<section class="trainer-shell">
  {#if loading && !state}
    <div class="glass-panel skeleton-card tall-skeleton"></div>
  {:else if error}
    <div class="glass-panel">
      <div class="feedback-banner error-banner">{error}</div>
    </div>
  {:else if state}
    <div class="trainer-stack" in:fade={{ duration: 180 }}>
      <header class="trainer-head glass-panel">
        <div>
          <p class="eyebrow">Tense tables</p>
          <h1>{state.title}</h1>
        </div>
        <div class="pill-row">
          <span class="pill-chip">{state.overview.unlocked} unlocked</span>
          <span class="pill-chip">{state.overview.practiced} practiced</span>
          <span class="pill-chip">{state.overview.mastered} mastered</span>
          {#if state.session}
            <span class="pill-chip">combo {state.session.combo}x</span>
          {/if}
        </div>
      </header>

      {#if state.feedback}
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
        <article class="glass-panel strong-panel trainer-card">
          <p class="section-copy">
            Choose a language, set the tense depth, and run a full-table drill. Press Enter to move down the pronouns,
            then into the next tense, and submit on the last editable cell.
          </p>

          <div class="toggle-cluster">
            <div class="toggle-group">
              <span class="toggle-label">Language</span>
              <div class="option-row wrap-row">
                {#each state.languages as item}
                  <button class:option-on={language === item.code} class="option-chip" type="button" on:click={() => { language = item.code; syncSelection(); }}>{item.name}</button>
                {/each}
              </div>
            </div>

            <div class="toggle-group">
              <span class="toggle-label">Difficulty</span>
              <div class="option-row wrap-row">
                {#each ['easy', 'medium', 'hard', 'custom'] as item}
                  <button class:option-on={level === item} class="option-chip" type="button" on:click={() => { level = item; syncSelection(); }}>{item[0].toUpperCase()}{item.slice(1)}</button>
                {/each}
              </div>
            </div>

            <div class="toggle-group">
              <span class="toggle-label">Prefill level</span>
              <div class="option-row wrap-row">
                <button class:option-on={fillLevel === 'easy'} class="option-chip" type="button" on:click={() => (fillLevel = 'easy')}>80% visible</button>
                <button class:option-on={fillLevel === 'medium'} class="option-chip" type="button" on:click={() => (fillLevel = 'medium')}>20% visible</button>
                <button class:option-on={fillLevel === 'hard'} class="option-chip" type="button" on:click={() => (fillLevel = 'hard')}>0% visible</button>
              </div>
            </div>

            <div class="toggle-group">
              <span class="toggle-label">Queue length</span>
              <div class="option-row wrap-row">
                {#each [3, 5, 8] as option, i}
                  <button class:option-on={length === option} class="option-chip length-chip" type="button" on:click={() => (length = option)}>
                    <span class="length-tier">{['Easy', 'Normal', 'Insane'][i]}</span>
                    <strong class="length-count">{option} verbs</strong>
                  </button>
                {/each}
              </div>
            </div>
          </div>

          <div class="tense-wall">
            {#each visibleTenses() as tense}
              <button class:option-on={selectedTenses.includes(tense)} class="tense-chip" type="button" on:click={() => toggleTense(tense)}>{tense}</button>
            {/each}
          </div>

          <button class="primary-button" type="button" on:click={startSession}>Start conjugation run</button>
        </article>
      {:else if state.question && state.session}
        {#key `${state.question.verb_id}:${state.session.progress_current}`}
          <article class="glass-panel strong-panel trainer-card">
            <div class="progress-shell">
              <div class="progress-top">
                <span>Verb progress</span>
                <strong>{state.session.progress_current}/{state.session.progress_total}</strong>
              </div>
              <div class="progress-track"><span class="progress-bar" style={`width: ${progressPercent()}%`}></span></div>
            </div>

            <div class="question-stage">
              <p class="eyebrow">Current verb</p>
              <h2 class="question-word">{state.question.verb}</h2>
              <div class="tag-row">
                {#each state.question.selected_tenses as tense}
                  <span class="mini-tag">{tense}</span>
                {/each}
              </div>
              <div class="conjugation-guide-row">
                <p class="section-copy">
                  Enter moves down the pronouns first, then jumps to the next tense, and submits on the final editable cell.
                </p>
                <span class="guide-chip">Focus: {activeLabel()}</span>
              </div>
            </div>

            <div class="table-scroll">
              <table class="data-table conjugation-table">
                <thead>
                  <tr>
                    <th>Pronoun</th>
                    {#each state.question.selected_tenses as tense}
                      <th class:table-axis-active={isActiveTense(tense)}>{tense}</th>
                    {/each}
                  </tr>
                </thead>
                <tbody>
                  {#each state.question.rows as row (row.pronoun)}
                    <tr class:table-row-active={isActivePronoun(row.pronoun)}>
                      <td class="pronoun-cell" class:pronoun-cell-active={isActivePronoun(row.pronoun)}>{row.pronoun}</td>
                      {#each row.cells as cell (`${row.pronoun}:${cell.tense}`)}
                        <td
                          class:table-col-active={isActiveTense(cell.tense)}
                          class:table-cell-active={isActiveCell(cell.tense, row.pronoun)}
                          class:table-cell-prefilled={cell.kind === 'prefilled'}
                          class:table-cell-filled={cell.kind === 'input' && hasTypedAnswer(cell.tense, row.pronoun)}
                        >
                          {#if cell.kind === 'missing'}
                            <span class="muted-dash">-</span>
                          {:else if cell.kind === 'prefilled'}
                            <span class="prefilled-chip prefilled-static">{cell.value}</span>
                          {:else}
                            <input
                              id={cellDomId(cellKey(cell.tense, row.pronoun))}
                              class="conj-input"
                              class:conj-input-filled={hasTypedAnswer(cell.tense, row.pronoun)}
                              class:conj-input-active={isActiveCell(cell.tense, row.pronoun)}
                              type="text"
                              data-cell-key={cellKey(cell.tense, row.pronoun)}
                              value={getAnswer(cell.tense, row.pronoun)}
                              on:focus={() => (activeCellKey = cellKey(cell.tense, row.pronoun))}
                              on:input={(event) => setAnswer(cell.tense, row.pronoun, (event.currentTarget as HTMLInputElement).value)}
                              on:keydown={handleCellKeydown}
                              autocomplete="off"
                              autocapitalize="off"
                              spellcheck="false"
                              placeholder="Type form"
                            />
                          {/if}
                        </td>
                      {/each}
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>

            <div class="trainer-actions">
              <button bind:this={submitButton} class="primary-button" type="button" on:click={submit} disabled={loading}>Submit and continue</button>
              <button class="ghost-button" type="button" on:click={finishSession} disabled={loading}>Finish session</button>
            </div>
          </article>
        {/key}
      {/if}
    </div>
  {/if}
</section>
