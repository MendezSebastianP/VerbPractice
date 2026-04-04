<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { fade } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import { playCue } from '../sound';
  import type { RewardState, TranslationState } from '../types';

  export let mode: 'words' | 'verbs';
  export let csrfToken = '';
  export let soundEnabled = false;
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;

  let loading = true;
  let error = '';
  let state: TranslationState | null = null;
  let answer = '';
  let answerInput: HTMLInputElement | null = null;
  let retryButton: HTMLButtonElement | null = null;
  let finishedCard: HTMLElement | null = null;
  let length = 10;
  let direction = mode === 'words' ? 'es_fr' : 'fr_es';
  let justFinished = false;
  let showSetupAfterFinish = false;

  function stateLoader(): Promise<TranslationState> {
    return mode === 'words' ? api.wordsState() : api.verbsState();
  }

  function syncControlsFromState(nextState: TranslationState | null): void {
    if (!nextState) {
      return;
    }
    if (nextState.session) {
      length = nextState.session.length;
      direction = nextState.session.direction;
      return;
    }
    if (nextState.defaults) {
      length = nextState.defaults.length;
      direction = nextState.defaults.direction;
    }
  }

  function showFinishedPrompt(): boolean {
    return Boolean(!state?.session && (justFinished || state?.finished || state?.result?.finished) && !showSetupAfterFinish);
  }

  async function focusPrimaryControl(): Promise<void> {
    await tick();
    if (showFinishedPrompt()) {
      finishedCard?.scrollIntoView({ block: 'center', behavior: 'smooth' });
      retryButton?.focus();
      return;
    }
    if (state?.session && state.question) {
      answerInput?.focus();
    }
  }

  async function load(): Promise<void> {
    loading = true;
    error = '';
    try {
      state = await stateLoader();
      justFinished = Boolean(state?.finished || state?.result?.finished);
      showSetupAfterFinish = false;
      syncControlsFromState(state);
      answer = '';
      if (state?.feedback && state.result) {
        notify(state.feedback, state.result.is_correct ? 'success' : 'info');
      }
      await focusPrimaryControl();
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to load trainer';
    } finally {
      loading = false;
    }
  }

  onMount(load);

  async function startSession(): Promise<void> {
    loading = true;
    error = '';
    try {
      state = mode === 'words'
        ? await api.startWords({ length, direction, csrf_token: csrfToken })
        : await api.startVerbs({ length, direction, csrf_token: csrfToken });
      justFinished = false;
      showSetupAfterFinish = false;
      syncControlsFromState(state);
      answer = '';
      await focusPrimaryControl();
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to start session';
    } finally {
      loading = false;
    }
  }

  async function submitAnswer(reveal = false): Promise<void> {
    if (!state || state.setup) {
      return;
    }
    loading = true;
    error = '';
    try {
      state = reveal
        ? mode === 'words'
          ? await api.revealWords({ answer, csrf_token: csrfToken })
          : await api.revealVerbs({ answer, csrf_token: csrfToken })
        : mode === 'words'
          ? await api.answerWords({ answer, csrf_token: csrfToken })
          : await api.answerVerbs({ answer, csrf_token: csrfToken });
      if (state.feedback) {
        notify(state.feedback, reveal ? 'info' : state.result?.is_correct ? 'success' : 'error');
      }
      const rewardState = state.result?.gamification;
      if (soundEnabled && !reveal) {
        if (rewardState?.leveled_up) {
          playCue('level');
        } else if (rewardState?.unlocked_badges?.length) {
          playCue('badge');
        } else {
          playCue(state.result?.is_correct ? 'success' : 'error');
        }
      }
      justFinished = Boolean(state?.finished || state?.result?.finished);
      showSetupAfterFinish = false;
      syncControlsFromState(state);
      answer = '';
      await focusPrimaryControl();
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to grade answer';
    } finally {
      loading = false;
    }
  }

  async function showHint(): Promise<void> {
    loading = true;
    error = '';
    try {
      state = mode === 'words' ? await api.hintWords(csrfToken) : await api.hintVerbs(csrfToken);
      justFinished = false;
      await focusPrimaryControl();
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to reveal hint';
    } finally {
      loading = false;
    }
  }

  function percentage(): number {
    if (!state?.session || !state.session.progress_total) {
      return 0;
    }
    return (state.session.progress_current / state.session.progress_total) * 100;
  }

  function reward(): RewardState | null {
    return state?.result?.gamification || null;
  }

  function revealSetup(): void {
    showSetupAfterFinish = true;
  }

  async function finishSession(): Promise<void> {
    loading = true;
    error = '';
    try {
      state = mode === 'words' ? await api.finishWords(csrfToken) : await api.finishVerbs(csrfToken);
      justFinished = false;
      showSetupAfterFinish = true;
      syncControlsFromState(state);
      answer = '';
      if (state.feedback) {
        notify(state.feedback, 'info');
      }
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to finish session';
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
          <p class="eyebrow">{state.direction_label}</p>
          <h1>{state.title}</h1>
        </div>
        <div class="pill-row">
          <span class="pill-chip">{state.overview.unlocked} unlocked</span>
          <span class="pill-chip">{state.overview.mastered} mastered</span>
          <span class="pill-chip">pressure {state.overview.avg_probability}</span>
          {#if state.session}
            <span class="pill-chip">combo {state.session.combo}x</span>
          {/if}
        </div>
      </header>

      {#if state.feedback}
        <div class={`feedback-banner ${state.result?.is_correct ? 'success-banner' : 'info-banner'}`}>{state.feedback}</div>
      {/if}

      {#if showFinishedPrompt()}
        <div bind:this={finishedCard} class="feedback-banner success-banner finish-prompt-banner" in:fade={{ duration: 160 }}>
          <div class="finish-prompt-copy">
            <strong>Session complete.</strong>
            <span>Press Enter to restart immediately with the same settings, or use the buttons.</span>
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
              <h2>Momentum from the last answer</h2>
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
            Weighted prompts keep weak translations circulating while mastered items fall back. Start a session and the
            loop will keep you in the same surface with no page reload.
          </p>

          <div class="toggle-cluster">
            <div class="toggle-group">
              <span class="toggle-label">Session length</span>
              <div class="option-row">
                {#each [5, 10, 20] as option}
                  <button class:option-on={length === option} class="option-chip" type="button" on:click={() => (length = option)}>{option} items</button>
                {/each}
              </div>
            </div>

            <div class="toggle-group">
              <span class="toggle-label">Direction</span>
              <div class="option-row">
                {#if mode === 'words'}
                  <button class:option-on={direction === 'es_fr'} class="option-chip" type="button" on:click={() => (direction = 'es_fr')}>Spanish to French</button>
                  <button class:option-on={direction === 'fr_es'} class="option-chip" type="button" on:click={() => (direction = 'fr_es')}>French to Spanish</button>
                {:else}
                  <button class:option-on={direction === 'fr_es'} class="option-chip" type="button" on:click={() => (direction = 'fr_es')}>French to Spanish</button>
                  <button class:option-on={direction === 'es_fr'} class="option-chip" type="button" on:click={() => (direction = 'es_fr')}>Spanish to French</button>
                {/if}
              </div>
            </div>
          </div>

          <div class="metric-grid tight-grid">
            {#each state.overview.focus_items.slice(0, 4) as item}
              <div class="stat-card compact-stat">
                <span>{item.label}</span>
                <strong>{item.probability}</strong>
              </div>
            {/each}
          </div>

          <button class="primary-button" type="button" on:click={startSession}>Launch session</button>
        </article>
      {:else if state.question && state.session}
        <article class="glass-panel strong-panel trainer-card" in:fade={{ duration: 160 }}>
          <div class="progress-shell">
            <div class="progress-top">
              <span>Session progress</span>
              <strong>{state.session.progress_current}/{state.session.progress_total}</strong>
            </div>
            <div class="progress-track"><span class="progress-bar" style={`width: ${percentage()}%`}></span></div>
          </div>

          <div class="question-stage">
            <p class="eyebrow">Prompt</p>
            <h2 class="question-word">{state.question.prompt}</h2>
            <p class="section-copy">Type the strongest translation you know and keep your combo alive.</p>
          </div>

          <form class="answer-form" on:submit|preventDefault={() => submitAnswer(false)}>
            <div class="answer-row">
              <input bind:this={answerInput} bind:value={answer} class="answer-input" placeholder="Type your answer" autocomplete="off" required />
              <button class="primary-button" type="submit" disabled={loading}>Submit</button>
            </div>
          </form>

          <div class="trainer-actions">
            <button class="secondary-button" type="button" on:click={showHint} disabled={loading}>Reveal hint</button>
            <button class="ghost-button" type="button" on:click={() => submitAnswer(true)} disabled={loading}>Show answer</button>
            <button class="ghost-button" type="button" on:click={finishSession} disabled={loading}>Finish session</button>
          </div>

          {#if state.hint}
            <div class="hint-chip">Hint: {state.hint}</div>
          {/if}
        </article>
      {/if}
    </div>
  {/if}
</section>
