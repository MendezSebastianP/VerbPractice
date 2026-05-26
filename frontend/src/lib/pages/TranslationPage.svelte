<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { fade } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import { navigate } from '../router';
  import { playCue } from '../sound';
  import type { LanguageEntry, RewardState, TranslationState, UserSettings, WordSetSummary } from '../types';

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
  let length = 10;
  let direction = mode === 'words' ? 'es_fr' : 'fr_es';
  let justFinished = false;
  let showSetupAfterFinish = false;

  let finishSessionWarning = false;
  let escTimer: ReturnType<typeof setTimeout> | null = null;

  // Ctrl+Space ×2 hint shortcut (ctrlSpaceArmed lights up the Hint button after tap 1)
  let ctrlSpaceCount = 0;
  let ctrlSpaceTimer: ReturnType<typeof setTimeout> | null = null;
  let ctrlSpaceArmed = false;

  // Esc ×2 to "Change settings" when session is done
  let settingsWarning = false;
  let settingsTimer: ReturnType<typeof setTimeout> | null = null;

  // Button refs for programmatic pop animation on keyboard shortcuts
  let lengthChipEls: Array<HTMLButtonElement | null> = [null, null, null];
  let swapButtonEl: HTMLButtonElement | null = null;
  let launchButton: HTMLButtonElement | null = null;
  let hintButton: HTMLButtonElement | null = null;
  let skipButton: HTMLButtonElement | null = null;
  let finishButton: HTMLButtonElement | null = null;
  let changeSettingsButton: HTMLButtonElement | null = null;

  // Static lookup tables
  const LANG_KEY: Record<string, string> = { e: 'EN', s: 'ES', r: 'RU', f: 'FR' };
  const LANG_SHORTCUT: Record<string, string> = { EN: 'E', ES: 'S', RU: 'R', FR: 'F' };
  const LENGTH_OPTS: number[] = [5, 10, 20];

  // Wrong-attempt tracking for the two-strike flow
  let wrongAttempts = 0;
  let currentQuestionId: number | null = null;

  // Preserve last question/session for the session-done overlay
  let prevQuestion: NonNullable<TranslationState['question']> | null = null;
  let prevSession: NonNullable<TranslationState['session']> | null = null;
  $: if (state?.question) prevQuestion = state.question;
  $: if (state?.session) prevSession = state.session;

  // Inline feedback area (reserved top space inside the question card)
  let inlineMsg = '';
  let inlineTone = '';  // 'success' | 'error' | 'info' | ''

  let languages: LanguageEntry[] = [];
  let userSettings: UserSettings | null = null;
  let sourceCode = '';
  let targetCode = '';
  let sourceTileOpen = false;
  let targetTileOpen = false;

  let setScope: WordSetSummary | null = null;

  // Reset wrong-attempt counter when the question changes; let inlineMsg persist as confirmation
  $: {
    const qid = state?.question?.item_id ?? null;
    if (qid !== currentQuestionId) {
      currentQuestionId = qid;
      wrongAttempts = 0;
    }
  }

  function popEl(el: HTMLElement | null): void {
    if (!el) return;
    el.classList.remove('btn-pop');
    void el.offsetWidth; // reflow to restart animation
    el.classList.add('btn-pop');
    el.addEventListener('animationend', () => el.classList.remove('btn-pop'), { once: true });
  }

  function readSetIdFromUrl(): number | null {
    const raw = new URLSearchParams(window.location.search).get('set');
    if (!raw) return null;
    const n = parseInt(raw, 10);
    return Number.isFinite(n) ? n : null;
  }

  function clearScope(): void {
    setScope = null;
    navigate(`/training/${mode}`, { replace: true });
  }

  $: if (sourceCode && targetCode) {
    direction = `${sourceCode.toLowerCase()}_${targetCode.toLowerCase()}`;
  }

  function languageByCode(code: string): LanguageEntry | undefined {
    return languages.find((l) => l.code === code.toUpperCase());
  }

  function computeInitialPair(settings: UserSettings | null, langs: LanguageEntry[]): [string, string] {
    if (settings?.last_practice_pair && /^[a-z]{2}_[a-z]{2}$/.test(settings.last_practice_pair)) {
      const [src, tgt] = settings.last_practice_pair.split('_');
      if (langs.some((l) => l.code === src.toUpperCase()) && langs.some((l) => l.code === tgt.toUpperCase())) {
        return [src.toUpperCase(), tgt.toUpperCase()];
      }
    }
    if (settings?.learning_language && settings?.mother_tongue) {
      return [settings.learning_language.code, settings.mother_tongue.code];
    }
    if (langs.length >= 2) {
      return [langs[0].code, langs[1].code];
    }
    return ['ES', 'FR'];
  }

  function swapDirection(): void {
    const t = sourceCode;
    sourceCode = targetCode;
    targetCode = t;
  }

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

  $: sessionDone = justFinished && !showSetupAfterFinish;

  async function focusPrimaryControl(): Promise<void> {
    await tick();
    if (sessionDone) {
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
      const setId = readSetIdFromUrl();
      const [stateResult, langsResult, settingsResult, setResult] = await Promise.all([
        stateLoader(),
        api.listLanguages().catch(() => ({ languages: [] as LanguageEntry[] })),
        api.getSettings().catch(() => null as UserSettings | null),
        setId ? api.getWordSet(setId).catch(() => null) : Promise.resolve(null),
      ]);
      state = stateResult;
      languages = langsResult.languages;
      userSettings = settingsResult;
      setScope = setResult
        ? {
            id: setResult.id,
            name: setResult.name,
            description: setResult.description,
            icon: setResult.icon,
            kind: setResult.kind,
            owner_user_id: setResult.owner_user_id,
            filter_tag_slugs: setResult.filter_tag_slugs,
            word_count: setResult.word_count,
          }
        : null;
      const [src, tgt] = computeInitialPair(userSettings, languages);
      sourceCode = src;
      targetCode = tgt;
      justFinished = Boolean(state?.finished || state?.result?.finished);
      showSetupAfterFinish = false;
      syncControlsFromState(state);
      answer = '';
      inlineMsg = '';
      inlineTone = '';
      if (state?.feedback && state.result) {
        notify(state.feedback, state.result.is_correct ? 'success' : 'info');
      }
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to load trainer';
    } finally {
      loading = false;
    }
    await focusPrimaryControl();
  }

  onMount(load);

  async function startSession(): Promise<void> {
    loading = true;
    error = '';
    finishSessionWarning = false;
    if (escTimer) { clearTimeout(escTimer); escTimer = null; }
    try {
      const startPayload = {
        length,
        direction,
        csrf_token: csrfToken,
        ...(setScope ? { set_id: setScope.id } : {}),
      };
      state = mode === 'words'
        ? await api.startWords(startPayload)
        : await api.startVerbs(startPayload);
      justFinished = false;
      showSetupAfterFinish = false;
      wrongAttempts = 0;
      inlineMsg = '';
      inlineTone = '';
      syncControlsFromState(state);
      answer = '';
      void api.patchSettings({
        csrf_token: csrfToken,
        last_practice_pair: direction,
        last_practice_mode: mode === 'words' ? 'word_translation' : 'verb_translation',
      }).catch(() => {});
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to start session';
    } finally {
      loading = false;
    }
    await focusPrimaryControl();
  }

  async function submitAnswer(reveal = false): Promise<void> {
    if (!state || state.setup) {
      return;
    }
    loading = true;
    error = '';
    try {
      if (reveal) {
        // "Skip and show" — user explicitly requests the answer
        state = mode === 'words'
          ? await api.revealWords({ answer, csrf_token: csrfToken })
          : await api.revealVerbs({ answer, csrf_token: csrfToken });
        inlineMsg = state.feedback ?? '';
        inlineTone = 'info';
        wrongAttempts = 0;
        if (soundEnabled) playCue('error');
      } else if (wrongAttempts >= 1) {
        // Second attempt: grade it; auto-reveal if still wrong
        const gradeState = mode === 'words'
          ? await api.answerWords({ answer, csrf_token: csrfToken })
          : await api.answerVerbs({ answer, csrf_token: csrfToken });
        if (gradeState.result?.is_correct) {
          state = gradeState;
          inlineMsg = 'Correct!';
          inlineTone = 'success';
          wrongAttempts = 0;
          const rewardState = state.result?.gamification;
          if (soundEnabled) {
            if (rewardState?.leveled_up) playCue('level');
            else if (rewardState?.unlocked_badges?.length) playCue('badge');
            else playCue('success');
          }
        } else {
          // Still wrong — auto-reveal
          state = mode === 'words'
            ? await api.revealWords({ answer, csrf_token: csrfToken })
            : await api.revealVerbs({ answer, csrf_token: csrfToken });
          inlineMsg = state.feedback ?? '';
          inlineTone = 'error';
          wrongAttempts = 0;
          if (soundEnabled) playCue('error');
        }
      } else {
        // First attempt
        state = mode === 'words'
          ? await api.answerWords({ answer, csrf_token: csrfToken })
          : await api.answerVerbs({ answer, csrf_token: csrfToken });
        if (state.result?.is_correct) {
          inlineMsg = 'Correct!';
          inlineTone = 'success';
          const rewardState = state.result?.gamification;
          if (soundEnabled) {
            if (rewardState?.leveled_up) playCue('level');
            else if (rewardState?.unlocked_badges?.length) playCue('badge');
            else playCue('success');
          }
        } else {
          wrongAttempts++;
          // Auto-hint on first wrong (counts as a hint in scoring)
          state = mode === 'words' ? await api.hintWords(csrfToken) : await api.hintVerbs(csrfToken);
          inlineMsg = `Wrong answer, try a last time! hint: ${state.hint}`;
          inlineTone = 'error';
          if (soundEnabled) playCue('error');
        }
      }
      justFinished = Boolean(state?.finished || state?.result?.finished);
      showSetupAfterFinish = false;
      syncControlsFromState(state);
      answer = '';
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to grade answer';
    } finally {
      loading = false;
    }
    await focusPrimaryControl();
  }

  async function showHint(): Promise<void> {
    loading = true;
    error = '';
    try {
      state = mode === 'words' ? await api.hintWords(csrfToken) : await api.hintVerbs(csrfToken);
      inlineMsg = state.hint ? `Hint: ${state.hint}` : 'No hint yet — keep going!';
      inlineTone = 'info';
      justFinished = false;
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to reveal hint';
    } finally {
      loading = false;
    }
    await focusPrimaryControl();
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
    finishSessionWarning = false;
    if (escTimer) { clearTimeout(escTimer); escTimer = null; }
    try {
      state = mode === 'words' ? await api.finishWords(csrfToken) : await api.finishVerbs(csrfToken);
      justFinished = false;
      showSetupAfterFinish = true;
      wrongAttempts = 0;
      inlineMsg = '';
      inlineTone = '';
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

  function handleFinishClick(): void {
    if (loading) return;
    if (finishSessionWarning) {
      finishSessionWarning = false;
      if (escTimer) { clearTimeout(escTimer); escTimer = null; }
      popEl(finishButton);
      void finishSession();
    } else {
      finishSessionWarning = true;
      if (escTimer) clearTimeout(escTimer);
      escTimer = setTimeout(() => { finishSessionWarning = false; }, 2500);
    }
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (loading) return;

    // Enter on setup screen: launch unless the user is typing in a real text field
    if (event.key === 'Enter' && state?.setup && !state?.session && !justFinished && !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
      const active = document.activeElement as HTMLElement | null;
      const tag = active?.tagName;
      const isTyping = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || active?.isContentEditable;
      if (!isTyping) {
        event.preventDefault();
        popEl(launchButton);
        void startSession();
        return;
      }
    }

    // Enter when session-done: retry
    if (event.key === 'Enter' && sessionDone && !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
      if (document.activeElement === retryButton) return;
      event.preventDefault();
      popEl(retryButton);
      void startSession();
      return;
    }

    // Escape when session-done: "Change settings" (double Esc)
    if (event.key === 'Escape' && sessionDone && !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
      event.preventDefault();
      if (settingsWarning) {
        settingsWarning = false;
        if (settingsTimer) { clearTimeout(settingsTimer); settingsTimer = null; }
        popEl(changeSettingsButton);
        revealSetup();
      } else {
        settingsWarning = true;
        if (settingsTimer) clearTimeout(settingsTimer);
        settingsTimer = setTimeout(() => { settingsWarning = false; }, 2500);
      }
      return;
    }

    // Escape during active session: finish (double Esc via handleFinishClick)
    if (event.key === 'Escape' && state?.session && !sessionDone && !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
      event.preventDefault();
      handleFinishClick();
      return;
    }

    // Setup-screen shortcuts (length, lang select, swap)
    if (state?.setup && !state?.session && !justFinished) {
      const active = document.activeElement as HTMLElement | null;
      const isTyping = active?.tagName === 'INPUT' || active?.tagName === 'TEXTAREA';

      // Ctrl+Space: swap languages
      if (event.code === 'Space' && event.ctrlKey && !event.altKey && !event.metaKey) {
        event.preventDefault();
        swapDirection();
        popEl(swapButtonEl);
        return;
      }

      if (!isTyping && !event.ctrlKey && !event.metaKey && !event.altKey) {
        const key = event.key;

        // 1/2/3: session length
        const lengthIdx = ['1', '2', '3'].indexOf(key);
        if (lengthIdx !== -1) {
          event.preventDefault();
          length = LENGTH_OPTS[lengthIdx];
          popEl(lengthChipEls[lengthIdx]);
          return;
        }

        // E/S/R/F: set prompt (source) language
        // Shift+E/S/R/F: set answer (target) language; auto-swap when it would equal source
        const code = LANG_KEY[key.toLowerCase()];
        if (code) {
          event.preventDefault();
          if (event.shiftKey) {
            if (code === sourceCode) sourceCode = targetCode;
            targetCode = code;
          } else {
            if (code === targetCode) targetCode = sourceCode;
            sourceCode = code;
          }
          return;
        }
      }
    }

    // Ctrl+Space ×2 OR F2 → hint (during active session)
    if (state?.session && !sessionDone && !event.altKey && !event.metaKey) {
      if (event.code === 'Space' && event.ctrlKey) {
        event.preventDefault();
        ctrlSpaceCount++;
        if (ctrlSpaceTimer) clearTimeout(ctrlSpaceTimer);
        if (ctrlSpaceCount >= 2) {
          ctrlSpaceCount = 0;
          ctrlSpaceArmed = false;
          popEl(hintButton);
          void showHint();
        } else {
          ctrlSpaceArmed = true;
          ctrlSpaceTimer = setTimeout(() => { ctrlSpaceCount = 0; ctrlSpaceArmed = false; }, 700);
        }
        return;
      }
      if (event.key === 'F2' && !event.ctrlKey && !event.shiftKey) {
        event.preventDefault();
        popEl(hintButton);
        void showHint();
        return;
      }
    }

    // Alt+Enter: skip and show
    if (event.key === 'Enter' && event.altKey && state?.session && !sessionDone && !event.ctrlKey && !event.metaKey) {
      event.preventDefault();
      popEl(skipButton);
      void submitAnswer(true);
      return;
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

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
          {#if setScope}
            <p style="margin-top: 0.25rem; font-size: 0.9rem;">
              Practicing set:
              <strong>{setScope.name}</strong>
              <span style="opacity: 0.7;">({setScope.word_count} words)</span>
              <button
                type="button"
                class="ghost-button"
                on:click={clearScope}
                style="margin-left: 0.5rem; padding: 0.1rem 0.5rem; font-size: 0.75rem;"
              >
                clear scope
              </button>
            </p>
          {/if}
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

      <!-- External feedback only for non-session setup messages -->
      {#if state.feedback && !state.session && !justFinished}
        <div class="feedback-banner info-banner">{state.feedback}</div>
      {/if}

      {#if reward() && !justFinished}
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

      {#if state.setup && (!justFinished || showSetupAfterFinish)}
        <article class="glass-panel strong-panel trainer-card">
          <p class="section-copy">
            Weighted prompts keep weak translations circulating while mastered items fall back. Start a session and the
            loop will keep you in the same surface with no page reload.
          </p>

          <div class="toggle-cluster">
            <div class="toggle-group">
              <span class="toggle-label">Session length</span>
              <div class="option-row">
                {#each LENGTH_OPTS as option, i}
                  <button bind:this={lengthChipEls[i]} class:option-on={length === option} class="option-chip" type="button" on:click={() => { length = option; popEl(lengthChipEls[i]); }}>
                    {option} items
                    <span class="btn-shortcut">{i + 1}</span>
                  </button>
                {/each}
              </div>
            </div>

            <div class="toggle-group">
              <span class="toggle-label">Direction</span>
              <div class="direction-tiles" style="display: flex; align-items: center; gap: 0.75rem;">
                <div style="position: relative; flex: 1;">
                  <button
                    class="option-chip option-on"
                    type="button"
                    on:click={() => { sourceTileOpen = !sourceTileOpen; targetTileOpen = false; }}
                    style="width: 100%; padding: 1rem; font-size: 1.1rem;"
                  >
                    {languageByCode(sourceCode)?.name || sourceCode || '—'}
                    <small style="display: block; opacity: 0.6;">prompt</small>
                    {#if LANG_SHORTCUT[sourceCode]}<span class="btn-shortcut" style="margin-top: 0.2rem;">{LANG_SHORTCUT[sourceCode]}</span>{/if}
                  </button>
                  {#if sourceTileOpen}
                    <div class="glass-panel" style="position: absolute; top: 100%; left: 0; right: 0; z-index: 10; padding: 0.5rem; margin-top: 0.25rem;">
                      {#each languages as lang}
                        <button
                          class="option-chip"
                          type="button"
                          on:click={() => { sourceCode = lang.code; sourceTileOpen = false; }}
                          style="display: block; width: 100%; margin: 0.15rem 0; text-align: left;"
                          disabled={lang.code === targetCode}
                        >
                          {lang.name}
                        </button>
                      {/each}
                    </div>
                  {/if}
                </div>

                <button
                  bind:this={swapButtonEl}
                  class="ghost-button"
                  type="button"
                  aria-label="Swap direction"
                  title="Swap"
                  on:click={() => { swapDirection(); popEl(swapButtonEl); }}
                  style="padding: 0.5rem 0.75rem; font-size: 1.25rem;"
                >
                  ⇄
                  <span class="btn-shortcut" style="display: block; font-size: 0.55rem; margin-top: 0.2rem;">Ctrl+Space</span>
                </button>

                <div style="position: relative; flex: 1;">
                  <button
                    class="option-chip option-on"
                    type="button"
                    on:click={() => { targetTileOpen = !targetTileOpen; sourceTileOpen = false; }}
                    style="width: 100%; padding: 1rem; font-size: 1.1rem;"
                  >
                    {languageByCode(targetCode)?.name || targetCode || '—'}
                    <small style="display: block; opacity: 0.6;">answer</small>
                    {#if LANG_SHORTCUT[targetCode]}<span class="btn-shortcut" style="margin-top: 0.2rem;">Shift+{LANG_SHORTCUT[targetCode]}</span>{/if}
                  </button>
                  {#if targetTileOpen}
                    <div class="glass-panel" style="position: absolute; top: 100%; left: 0; right: 0; z-index: 10; padding: 0.5rem; margin-top: 0.25rem;">
                      {#each languages as lang}
                        <button
                          class="option-chip"
                          type="button"
                          on:click={() => { targetCode = lang.code; targetTileOpen = false; }}
                          style="display: block; width: 100%; margin: 0.15rem 0; text-align: left;"
                          disabled={lang.code === sourceCode}
                        >
                          {lang.name}
                        </button>
                      {/each}
                    </div>
                  {/if}
                </div>
              </div>
            </div>
          </div>

          <p class="eyebrow" style="margin-bottom: 0.1rem;">Top weak words</p>
          <div class="metric-grid tight-grid">
            {#each state.overview.focus_items.filter(i => i.language_pair === direction).slice(0, 4) as item}
              <div class="stat-card compact-stat">
                <span>{item.language_pair.replace('_', ' → ').toUpperCase()}</span>
                <strong style="font-size: 0.95rem; letter-spacing: normal; line-height: 1.3;">{item.label}</strong>
                {#if item.translation}
                  <span style="font-size: 0.78rem; color: var(--muted); margin-top: 0.1rem;">{item.translation}</span>
                {/if}
              </div>
            {:else}
              <p class="section-copy" style="grid-column: 1/-1;">No data yet — start a session!</p>
            {/each}
          </div>

          {#if mode === 'words'}
            <div class="sets-teaser">
              <span class="eyebrow">Sets</span>
              <span class="coming-soon-badge">Coming soon</span>
              <p class="section-copy" style="margin-top: 0.25rem; margin-bottom: 0;">Group words into themed sets and practice them separately.</p>
            </div>
          {/if}

          <button bind:this={launchButton} class="primary-button" type="button" on:click={() => { popEl(launchButton); void startSession(); }}>
            Launch session
            <svg class="enter-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="9 10 4 15 9 20"></polyline><path d="M20 4v7a4 4 0 0 1-4 4H4"></path></svg>
          </button>
        </article>
      {:else if (state.question && state.session) || sessionDone}
        {@const dq = state.question ?? prevQuestion}
        {@const ds = state.session ?? prevSession}
        <article class="glass-panel strong-panel trainer-card" in:fade={{ duration: 160 }}>

          <!-- Reserved inline feedback — always occupies space; shows session-done message when finished -->
          <div
            class="session-msg"
            class:has-msg={!!inlineMsg || sessionDone}
            class:msg-success={sessionDone || inlineTone === 'success'}
            class:msg-error={!sessionDone && inlineTone === 'error'}
            class:msg-info={!sessionDone && inlineTone === 'info'}
          >
            {#if sessionDone}
              <span>Session complete — jump back in!</span>
            {:else if inlineMsg}
              <span>{inlineMsg}</span>
            {/if}
          </div>

          <!-- Progress + question: blurred when session is done -->
          <div class:done-blur={sessionDone}>
            <div class="progress-shell">
              <div class="progress-top">
                <span>Session progress</span>
                <strong>{ds?.progress_current ?? 0}/{ds?.progress_total ?? 0}</strong>
              </div>
              <div class="progress-track"><span class="progress-bar" style={`width: ${ds?.progress_total ? (ds.progress_current / ds.progress_total) * 100 : 0}%`}></span></div>
            </div>

            <div class="question-stage">
              <p class="eyebrow">Prompt</p>
              <h2 class="question-word">{dq?.prompt ?? ''}</h2>
              <p class="section-copy">Type the strongest translation you know and keep your combo alive.</p>
            </div>
          </div>

          <!-- Answer row: input blurred when done, submit button becomes Retry -->
          <form class="answer-form" on:submit|preventDefault={() => sessionDone ? startSession() : submitAnswer(false)}>
            <div class="answer-row">
              <input
                bind:this={answerInput}
                bind:value={answer}
                class="answer-input"
                class:done-blur={sessionDone}
                placeholder="Type your answer"
                autocomplete="off"
                disabled={sessionDone || loading}
                required={!sessionDone}
              />
              <button class="primary-button" type="submit" disabled={loading} bind:this={retryButton}>
                {#if sessionDone}
                  Retry session
                {:else}
                  Submit
                {/if}
                <svg class="enter-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="9 10 4 15 9 20"></polyline><path d="M20 4v7a4 4 0 0 1-4 4H4"></path></svg>
              </button>
            </div>
          </form>

          <!-- Actions: session controls when active; change-settings when done -->
          {#if sessionDone}
            <div class="trainer-actions">
              <button
                bind:this={changeSettingsButton}
                class="secondary-button"
                class:finish-warn={settingsWarning}
                type="button"
                on:click={() => { popEl(changeSettingsButton); revealSetup(); }}
                disabled={loading}
              >
                Change settings
                <span class="btn-shortcut">{settingsWarning ? 'Esc ×1' : 'Esc ×2'}</span>
              </button>
            </div>
          {:else}
            <div class="trainer-actions">
              <button bind:this={hintButton} class="secondary-button" class:hint-armed={ctrlSpaceArmed} type="button" on:click={() => { popEl(hintButton); void showHint(); }} disabled={loading}>
                Hint
                <span class="btn-shortcut">F2 / Ctrl+Space {ctrlSpaceArmed ? '×1' : '×2'}</span>
              </button>
              <button bind:this={skipButton} class="ghost-button" type="button" on:click={() => { popEl(skipButton); void submitAnswer(true); }} disabled={loading}>
                Skip and show
                <span class="btn-shortcut">Alt+Enter</span>
              </button>
              <button
                bind:this={finishButton}
                class={`ghost-button${finishSessionWarning ? ' finish-warn' : ''}`}
                type="button"
                on:click={handleFinishClick}
                disabled={loading}
              >
                Finish session
                <span class="btn-shortcut">{finishSessionWarning ? 'Esc ×1' : 'Esc ×2'}</span>
              </button>
            </div>
          {/if}
        </article>
      {/if}
    </div>
  {/if}
</section>

<style>
  .trainer-shell {
    max-width: 660px;
    margin-inline: auto;
    width: 100%;
  }

  .sets-teaser {
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 0.85rem 1rem;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
  }

  .coming-soon-badge {
    font-size: 0.6rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    font-family: var(--mono, monospace);
    color: var(--accent-strong);
    border: 1px solid var(--accent);
    border-radius: 99px;
    padding: 0.15rem 0.5rem;
    opacity: 0.8;
  }

  /* Keyboard shortcut pop — spring bounce on programmatic trigger */
  @keyframes btn-pop {
    0%   { transform: scale(1); }
    30%  { transform: scale(0.88); }
    65%  { transform: scale(1.08); }
    100% { transform: scale(1); }
  }

  .btn-pop {
    animation: btn-pop 0.24s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  /* Click press ripple for all buttons */
  button:active:not(:disabled) {
    transform: scale(0.93);
    transition: transform 0.07s ease-out;
  }

  .progress-bar {
    transition: width 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  }

  .enter-icon {
    display: inline-block;
    vertical-align: middle;
    margin-left: 0.35rem;
    flex-shrink: 0;
  }

  .btn-shortcut {
    font-size: 0.6rem;
    letter-spacing: 0.04em;
    opacity: 0.55;
    margin-left: 0.4rem;
    padding: 0.1rem 0.3rem;
    border: 1px solid currentColor;
    border-radius: 3px;
    font-family: var(--mono, monospace);
    vertical-align: middle;
    display: inline-block;
    flex-shrink: 0;
  }

  .finish-warn {
    color: var(--danger) !important;
    border-color: var(--danger) !important;
  }

  /* Reserved inline feedback area at top of the question card */
  .session-msg {
    min-height: 2.25rem;
    display: flex;
    align-items: center;
    padding: 0.4rem 0.75rem;
    border-radius: 10px;
    font-size: 0.875rem;
    font-weight: 500;
    border: 1px solid transparent;
    transition: background 0.18s, border-color 0.18s, color 0.18s;
  }

  .session-msg.has-msg.msg-success {
    color: var(--success);
    background: color-mix(in srgb, var(--success) 12%, transparent);
    border-color: color-mix(in srgb, var(--success) 35%, transparent);
  }

  .session-msg.has-msg.msg-error {
    color: var(--danger);
    background: color-mix(in srgb, var(--danger) 12%, transparent);
    border-color: color-mix(in srgb, var(--danger) 35%, transparent);
  }

  .session-msg.has-msg.msg-info {
    color: var(--muted);
    background: color-mix(in srgb, var(--accent-soft) 180%, transparent);
    border-color: var(--line);
  }

  /* Hint button pulses after first Ctrl+Space tap */
  .hint-armed {
    border-color: var(--accent, #6c63ff) !important;
    color: var(--accent, #6c63ff) !important;
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent, #6c63ff) 25%, transparent);
    transition: border-color 0.15s, color 0.15s, box-shadow 0.15s;
  }

  /* Blur effect on question/input when session is done */
  .done-blur {
    filter: blur(3px);
    opacity: 0.35;
    pointer-events: none;
    user-select: none;
    transition: filter 0.25s, opacity 0.25s;
  }
</style>
