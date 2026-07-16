<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { fade } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import { navigate } from '../router';
  import { playCue } from '../sound';
  import { applyReward } from '../profile';
  import { celebrateReward, flashMiss, fxQueue, popEl } from '../fx';
  import DirectionPicker from '../components/DirectionPicker.svelte';
  import HelpTip from '../components/HelpTip.svelte';
  import QuickShotIcon from '../components/QuickShotIcon.svelte';
  import PlayClear from '../components/PlayClear.svelte';
  import PlayGrid from '../components/PlayGrid.svelte';
  import PlayMist from '../components/PlayMist.svelte';
  import StageClearRank from '../components/StageClearRank.svelte';
  import StudyPoolBlock from '../components/StudyPoolBlock.svelte';
  import type { LanguageEntry, RewardState, StudyPoolResponse, ThemeName, TranslationState, UserSettings, WordSetSummary } from '../types';

  export let mode: 'words' | 'verbs';
  export let csrfToken = '';
  export let soundEnabled = false;
  export let theme: ThemeName = 'light';
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;
  // Lets a host (VerbLab) collapse its own chrome while a session is running so
  // the game sits at the top of the viewport (as it does for the Words route).
  export let onSessionActiveChange: (active: boolean) => void = () => {};

  let loading = true;
  let error = '';
  let state: TranslationState | null = null;
  let answer = '';
  let answerInput: HTMLInputElement | null = null;
  // Hidden text field focused inside the Play tap so the mobile soft keyboard
  // opens within the user gesture and stays up until the real input mounts.
  let kbdPrimer: HTMLInputElement | null = null;
  let retryButton: HTMLButtonElement | null = null;
  let length = 10;
  let direction = mode === 'words' ? 'es_fr' : 'fr_es';
  let justFinished = false;
  let showSetupAfterFinish = false;
  let studyExpanded = false;
  let studyLoading = false;
  let studyError = '';
  let studyEntries: StudyPoolResponse['entries'] = [];
  let loadedStudyKey = '';

  let finishSessionWarning = false;
  let escTimer: ReturnType<typeof setTimeout> | null = null;

  // Desktop fullscreen. While active the browser owns Esc (it exits
  // fullscreen), so the finish/menu shortcuts move to Ctrl+Space.
  let isFullscreen = false;

  function syncFullscreen(): void {
    isFullscreen = Boolean(document.fullscreenElement);
  }

  async function toggleFullscreen(): Promise<void> {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await document.documentElement.requestFullscreen();
      }
    } catch {
      // Request can be denied (permissions policy) — state stays synced via fullscreenchange.
    }
  }

  // Ctrl+Space ×2 hint shortcut (ctrlSpaceArmed lights up the Hint chip after tap 1)
  let ctrlSpaceCount = 0;
  let ctrlSpaceTimer: ReturnType<typeof setTimeout> | null = null;
  let ctrlSpaceArmed = false;

  // Button refs for programmatic pop animation on keyboard shortcuts
  let directionRef: DirectionPicker | null = null;
  let hintButton: HTMLButtonElement | null = null;
  let skipButton: HTMLButtonElement | null = null;
  let finishButton: HTMLButtonElement | null = null;

  // Themed PLAY controls + launch transition state (per the .dc.html designs)
  let playMistRef: PlayMist | null = null;
  let playClearRef: PlayClear | null = null;
  let playGridRef: PlayGrid | null = null;
  let launching = false;
  let pixelOverlay = false;
  let pixelFade = false;

  // Static lookup tables
  const LANG_KEY: Record<string, string> = { e: 'EN', s: 'ES', r: 'RU', f: 'FR' };
  const LENGTH_OPTS: number[] = [5, 10, 20];
  const LENGTH_TIERS: string[] = ['Easy', 'Normal', 'Insane'];
  const DIFF_STARS: string[] = ['★★☆☆☆', '★★★☆☆', '★★★★★'];

  // Full-screen launch cells keep the same 16 × 10 transition contract in every
  // mode. Clear runs as a left-to-right vector shutter; Dark and Arcade retain
  // their radial dissolve.
  const PIX_PALETTES: Record<string, string[]> = {
    arcade: ['#7c3aed', '#5b21b6', '#8f52f5'],
    light: ['#236249', '#13281e', '#ff4c91'],
    dark: ['#2563eb', '#1d4ed8', '#3b82f6'],
  };
  const PIX_CELLS = (() => {
    const cells: Array<{ ci: number; radialDelay: string; vectorDelay: string }> = [];
    for (let r = 0; r < 10; r++) {
      for (let c = 0; c < 16; c++) {
        const dx = c - 7.5;
        const dy = (r - 4.5) * 1.6;
        cells.push({
          ci: (c + r) % 3,
          radialDelay: (Math.sqrt(dx * dx + dy * dy) * 0.045).toFixed(3),
          vectorDelay: (c * 0.022 + Math.abs(r - 4.5) * 0.012).toFixed(3),
        });
      }
    }
    return cells;
  })();
  $: pixPalette = PIX_PALETTES[theme] ?? PIX_PALETTES.light;

  // Answer-wave cell grid (arcade grading ripple, radial delay from center)
  const WAVE_CELLS = (() => {
    const cells: Array<{ delay: string }> = [];
    for (let r = 0; r < 11; r++) {
      for (let c = 0; c < 22; c++) {
        const dx = c - 10.5;
        const dy = (r - 5) * 1.9;
        cells.push({ delay: (Math.sqrt(dx * dx + dy * dy) * 0.032).toFixed(2) });
      }
    }
    return cells;
  })();

  $: isArcade = theme === 'arcade';
  $: diffIdx = Math.max(0, LENGTH_OPTS.indexOf(length)) ;
  $: itemSingular = mode === 'words' ? 'word' : 'verb';
  $: itemPlural = mode === 'words' ? 'words' : 'verbs';

  // Wrong-attempt tracking for the two-strike flow
  let wrongAttempts = 0;
  let currentQuestionId: number | null = null;

  // ===== Quick-shot: a perfect answer auto-advances without pressing Enter,
  // mirroring the conjugation table. Spent (must press Enter) once an
  // impossible letter is typed for the current prompt. =====
  // Spent is tracked by the item_id it was spent on and DERIVED from the current
  // question, so it re-arms automatically when the prompt changes (a manual
  // reset in a reactive block didn't reliably re-light the icon).
  let quickShotSpentFor: number | null = null;
  let quickShotGuarding = false;
  let quickShotAccepted = false;
  let quickShotExplanationOpen = false;
  let quickShotAdvanceInFlight = false;
  let quickShotComposing = false;
  let quickShotGuardTimer: ReturnType<typeof setTimeout> | null = null;
  let quickShotAcceptedTimer: ReturnType<typeof setTimeout> | null = null;

  // Answers the quick-shot can fire on. Synonyms only count in words mode —
  // the grader ignores them for verbs (see submit_translation_answer).
  $: quickShotAnswers = [
    ...(state?.question?.accepted_answers ?? []),
    ...(mode === 'words' ? (state?.question?.synonym_answers ?? []) : []),
  ];
  $: quickShotSpent = state?.question?.item_id != null && quickShotSpentFor === state.question.item_id;
  $: quickShotReady = Boolean(sessionView && quickShotAnswers.length && !quickShotSpent);

  // Mobile viewport re-centering (keep the prompt + input above the keyboard)
  let mobileCenterFrame: number | null = null;

  // Correct answers this run (drives the Stage Clear score + dots)
  let okRun = 0;

  // Preserve last question/session for the stage-clear screen
  let prevQuestion: NonNullable<TranslationState['question']> | null = null;
  let prevSession: NonNullable<TranslationState['session']> | null = null;
  $: if (state?.question) prevQuestion = state.question;
  $: if (state?.session) prevSession = state.session;

  // Inline feedback area (reserved space under the input)
  let inlineMsg = '';
  let inlineTone = '';  // 'success' | 'error' | 'info' | ''

  // Grading pulse: drives wave ring / cell wave / flash / shake, keyed so
  // rapid answers restart the animations.
  let feedbackPulse: 'success' | 'error' | null = null;
  let pulseSeq = 0;
  let pulseTimer: ReturnType<typeof setTimeout> | null = null;
  function triggerPulse(kind: 'success' | 'error'): void {
    feedbackPulse = null;
    requestAnimationFrame(() => {
      feedbackPulse = kind;
      pulseSeq += 1;
      if (pulseTimer) clearTimeout(pulseTimer);
      pulseTimer = setTimeout(() => { feedbackPulse = null; }, 1100);
    });
  }
  // Pulses are triggered explicitly at each grading site (a reactive statement
  // on inlineTone misses back-to-back identical tones, e.g. two corrects in a
  // row, and the check-draw must replay every time).

  // Arcade: the prompt glitches in place on a wrong answer
  let promptEl: HTMLElement | null = null;
  function glitchPrompt(): void {
    if (!promptEl) return;
    promptEl.classList.remove('prompt-glitch');
    void promptEl.offsetWidth;
    promptEl.classList.add('prompt-glitch');
  }
  $: if (feedbackPulse === 'error' && isArcade) glitchPrompt();

  let languages: LanguageEntry[] = [];
  let userSettings: UserSettings | null = null;
  let sourceCode = '';
  let targetCode = '';

  let setScope: WordSetSummary | null = null;

  // Reset wrong-attempt counter when the question changes; let inlineMsg persist as confirmation
  $: {
    const qid = state?.question?.item_id ?? null;
    if (qid !== currentQuestionId) {
      currentQuestionId = qid;
      wrongAttempts = 0;
      resetQuickShot();
    }
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

  // Top weak words for the current direction (max 4); empty slots are padded so the
  // card keeps a stable height even when a direction has no data yet.
  $: weakItems = state
    ? state.overview.focus_items.filter((i) => i.language_pair === direction).slice(0, 4)
    : [];

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
  $: menuView = Boolean(state?.setup && (!justFinished || showSetupAfterFinish));
  $: sessionView = Boolean(state?.question && state?.session && !sessionDone);
  // Report "in a drill" (session or stage-clear, not the setup menu) so the host
  // can hide its chrome and keep the game/clear screen full-height on mobile.
  $: onSessionActiveChange(sessionView || sessionDone);
  $: ds = state?.session ?? prevSession;
  $: routeCode = (ds?.direction ?? direction).replace('_', ' → ').toUpperCase();
  $: progressPct = ds?.progress_total ? (Math.min(ds.progress_current, ds.progress_total) / ds.progress_total) * 100 : 0;
  $: clearTotal = prevSession?.progress_total ?? 0;
  $: clearScore = clearTotal ? Math.round((okRun / clearTotal) * 100) : 0;

  // ===== Quick-shot helpers =====
  function clearQuickShotTimers(): void {
    if (quickShotGuardTimer) { clearTimeout(quickShotGuardTimer); quickShotGuardTimer = null; }
    if (quickShotAcceptedTimer) { clearTimeout(quickShotAcceptedTimer); quickShotAcceptedTimer = null; }
  }

  function resetQuickShot(): void {
    clearQuickShotTimers();
    quickShotSpentFor = null;
    quickShotGuarding = false;
    quickShotAccepted = false;
    quickShotExplanationOpen = false;
    quickShotAdvanceInFlight = false;
    quickShotComposing = false;
  }

  function normalizeQuickShotAnswer(value: string): string {
    return value
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/\p{M}/gu, '')
      .replaceAll('œ', 'oe')
      .replaceAll('æ', 'ae');
  }

  function armQuickShotGuard(): void {
    quickShotGuarding = true;
    if (quickShotGuardTimer) clearTimeout(quickShotGuardTimer);
    quickShotGuardTimer = setTimeout(() => { quickShotGuarding = false; quickShotGuardTimer = null; }, 600);
  }

  function animateQuickShotAccepted(): void {
    quickShotAccepted = true;
    if (quickShotAcceptedTimer) clearTimeout(quickShotAcceptedTimer);
    quickShotAcceptedTimer = setTimeout(() => { quickShotAccepted = false; quickShotAcceptedTimer = null; }, 520);
  }

  async function autoFireQuickShot(): Promise<void> {
    await tick();
    await submitAnswer(false);
    quickShotAdvanceInFlight = false;
  }

  function processQuickShot(value: string): void {
    if (quickShotComposing || quickShotAdvanceInFlight || quickShotSpent || loading || launching) {
      return;
    }
    const accepted = quickShotAnswers.map(normalizeQuickShotAnswer).filter(Boolean);
    if (!accepted.length) return;
    const draft = normalizeQuickShotAnswer(value);
    if (!draft) return;
    if (accepted.includes(draft)) {
      quickShotExplanationOpen = false;
      quickShotAdvanceInFlight = true;
      armQuickShotGuard();
      animateQuickShotAccepted();
      void autoFireQuickShot();
      return;
    }
    if (!accepted.some((entry) => entry.startsWith(draft))) {
      quickShotSpentFor = state?.question?.item_id ?? null;
    }
  }

  function handleAnswerInput(event: Event): void {
    processQuickShot((event.currentTarget as HTMLInputElement).value);
  }

  function handleAnswerCompositionEnd(event: CompositionEvent): void {
    quickShotComposing = false;
    processQuickShot((event.currentTarget as HTMLInputElement).value);
  }

  // ===== Mobile: keep the prompt + input centered above the keyboard =====
  function usesCompactViewport(): boolean {
    return window.matchMedia('(max-width: 760px) and (hover: none) and (pointer: coarse)').matches;
  }

  // Deadzone scroll: only nudge when the input is actually clipped by the
  // keyboard (or scrolled too high), and only far enough to sit back inside a
  // comfortable band. A fixed-center target here oscillated on real phones —
  // every scroll re-fired visualViewport events and toggled the URL bar.
  function centerGameInViewport(): void {
    if (!usesCompactViewport() || !answerInput || document.activeElement !== answerInput) {
      return;
    }
    const rect = answerInput.getBoundingClientRect();
    const viewport = window.visualViewport;
    const visibleTop = viewport?.offsetTop ?? 0;
    const visibleHeight = viewport?.height ?? window.innerHeight;
    const padTop = 96;   // keep the prompt word above the input on screen
    const padBottom = 28;
    let delta = 0;
    if (rect.bottom > visibleTop + visibleHeight - padBottom) {
      delta = rect.bottom - (visibleTop + visibleHeight - padBottom);
    } else if (rect.top < visibleTop + padTop) {
      delta = rect.top - (visibleTop + padTop);
    }
    if (Math.abs(delta) > 8) {
      window.scrollBy({ top: delta, behavior: 'auto' });
    }
  }

  function scheduleMobileViewportCenter(): void {
    if (mobileCenterFrame !== null) cancelAnimationFrame(mobileCenterFrame);
    mobileCenterFrame = requestAnimationFrame(() => {
      mobileCenterFrame = null;
      centerGameInViewport();
    });
  }

  async function focusPrimaryControl(): Promise<void> {
    await tick();
    if (sessionDone) {
      // Keep the mobile keyboard up on the Stage Clear so Enter/Send replays.
      if (usesCompactViewport()) kbdPrimer?.focus({ preventScroll: true });
      else retryButton?.focus();
      return;
    }
    if (state?.session && state.question) {
      const compact = usesCompactViewport();
      answerInput?.focus({ preventScroll: compact });
      if (compact) scheduleMobileViewportCenter();
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

  onMount(() => {
    syncFullscreen();
    document.addEventListener('fullscreenchange', syncFullscreen);
    // Only 'resize' (keyboard open/close) — reacting to 'scroll' created a
    // scroll→scroll feedback loop that bounced the page between two positions.
    window.visualViewport?.addEventListener('resize', scheduleMobileViewportCenter);
    return () => {
      document.removeEventListener('fullscreenchange', syncFullscreen);
      window.visualViewport?.removeEventListener('resize', scheduleMobileViewportCenter);
      if (mobileCenterFrame !== null) cancelAnimationFrame(mobileCenterFrame);
      clearQuickShotTimers();
      onSessionActiveChange(false);
    };
  });

  // Fetch a fresh session but let the caller decide when to swap it in — the
  // launch transitions depend on applying the new state at an exact moment.
  async function requestSessionState(): Promise<TranslationState | null> {
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
      return mode === 'words'
        ? await api.startWords(startPayload)
        : await api.startVerbs(startPayload);
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to start session';
      return null;
    }
  }

  function applySessionState(next: TranslationState): void {
    state = next;
    justFinished = false;
    showSetupAfterFinish = false;
    wrongAttempts = 0;
    okRun = 0;
    resetQuickShot();
    inlineMsg = '';
    inlineTone = '';
    syncControlsFromState(next);
    answer = '';
    void api.patchSettings({
      csrf_token: csrfToken,
      last_practice_pair: direction,
      last_practice_mode: mode === 'words' ? 'word_translation' : 'verb_translation',
    }).catch(() => {});
    void focusPrimaryControl();
  }

  async function startSession(): Promise<void> {
    loading = true;
    const next = await requestSessionState();
    loading = false;
    if (next) {
      applySessionState(next);
    }
    await focusPrimaryControl();
  }

  async function loadStudyPool(): Promise<void> {
    if (studyLoading) return;
    studyLoading = true;
    studyError = '';
    const key = `${mode}:${direction}`;
    try {
      const response = await api.studyPool({ mode, direction });
      studyEntries = response.entries;
      loadedStudyKey = key;
    } catch (err) {
      studyError = err instanceof ApiError ? err.message : 'Unable to load the study pool';
    } finally {
      studyLoading = false;
    }
  }

  function toggleStudyPool(): void {
    studyExpanded = !studyExpanded;
    if (studyExpanded && loadedStudyKey !== `${mode}:${direction}`) {
      void loadStudyPool();
    }
  }

  $: if (studyExpanded && loadedStudyKey && loadedStudyKey !== `${mode}:${direction}` && !studyLoading) {
    void loadStudyPool();
  }

  function delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  // Launch choreography: the tile dissolve propagates from the center and
  // reaches full cover at ~700ms; the screen swaps behind it, then the cover
  // fades to reveal the session. The API call runs behind the effect.
  async function firePlay(): Promise<void> {
    if (launching || loading) return;
    // Runs synchronously inside the Play tap → opens the soft keyboard in-gesture.
    // Focus transfers to the real answer input once the session mounts.
    if (usesCompactViewport()) kbdPrimer?.focus({ preventScroll: true });
    launching = true;
    try {
      pixelOverlay = true;
      pixelFade = false;
      const [next] = await Promise.all([requestSessionState(), delay(700)]);
      if (next) {
        applySessionState(next);
        await tick();
      }
      pixelFade = true;
      window.setTimeout(() => { pixelOverlay = false; pixelFade = false; }, 600);
    } finally {
      launching = false;
      if (!state?.session) {
        // launch failed — restore the menu controls
        playMistRef?.reset();
        playClearRef?.reset();
        playGridRef?.reset();
        pixelOverlay = false;
        pixelFade = false;
      }
    }
  }

  // Keyboard path (Enter on the menu): trigger the control so its own fire
  // visuals play; the control dispatches `fire` back into firePlay().
  function firePlayViaControl(): void {
    if (launching || loading) return;
    if (isArcade && playGridRef) {
      playGridRef.fire();
      return;
    }
    if (theme === 'light' && playClearRef) {
      playClearRef.fire();
      return;
    }
    if (playMistRef) {
      playMistRef.fire?.();
      return;
    }
    void firePlay();
  }

  async function submitAnswer(reveal = false): Promise<void> {
    if (!state || state.setup || loading) {
      return;
    }
    // Keep validation inside the game UI. Native `required` bubbles can appear
    // after quick-shot clears the field while the same Enter gesture is still
    // resolving; an empty submit should simply keep focus and do nothing.
    if (!reveal && !answer.trim()) {
      answerInput?.focus({ preventScroll: true });
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
        flashMiss();
        // Reveals earn no XP themselves, but the final one can still carry
        // session-complete rewards (bonus XP, badges)
        applyReward(state.result?.gamification);
        celebrateReward(state.result?.gamification);
        if (soundEnabled) playCue('error');
      } else if (wrongAttempts >= 1) {
        // Second attempt: grade it; auto-reveal if still wrong
        const gradeState = mode === 'words'
          ? await api.answerWords({ answer, csrf_token: csrfToken })
          : await api.answerVerbs({ answer, csrf_token: csrfToken });
        if (gradeState.result?.is_correct) {
          state = gradeState;
          // No text on success — the check-draw + tile wave confirm it
          inlineMsg = '';
          inlineTone = '';
          triggerPulse('success');
          wrongAttempts = 0;
          okRun += 1;
          const rewardState = state.result?.gamification;
          applyReward(rewardState);
          celebrateReward(rewardState);
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
          triggerPulse('error');
          wrongAttempts = 0;
          flashMiss();
          applyReward(state.result?.gamification);
          celebrateReward(state.result?.gamification);
          if (soundEnabled) playCue('error');
        }
      } else {
        // First attempt
        state = mode === 'words'
          ? await api.answerWords({ answer, csrf_token: csrfToken })
          : await api.answerVerbs({ answer, csrf_token: csrfToken });
        if (state.result?.is_correct) {
          inlineMsg = '';
          inlineTone = '';
          triggerPulse('success');
          okRun += 1;
          const rewardState = state.result?.gamification;
          applyReward(rewardState);
          celebrateReward(rewardState);
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
          triggerPulse('error');
          flashMiss();
          if (soundEnabled) playCue('error');
        }
      }
      justFinished = Boolean(state?.finished || state?.result?.finished);
      showSetupAfterFinish = false;
      syncControlsFromState(state);
      answer = '';
      // Session just ended: transfer focus to the primer now, while the answer
      // input is still mounted, so the mobile keyboard survives into Stage Clear.
      if (justFinished && usesCompactViewport()) kbdPrimer?.focus({ preventScroll: true });
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
    if (loading || launching) return;
    // A reward overlay (level-up / badge reveal) owns the keyboard until dismissed
    if ($fxQueue.length) return;

    // Enter on setup screen: fire the play control unless typing in a real text field
    if (event.key === 'Enter' && menuView && !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
      const active = document.activeElement as HTMLElement | null;
      const tag = active?.tagName;
      const isTyping = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || active?.isContentEditable;
      if (!isTyping) {
        event.preventDefault();
        firePlayViaControl();
        return;
      }
    }

    // Enter on stage clear: replay
    if (event.key === 'Enter' && sessionDone && !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
      if (document.activeElement === retryButton) return;
      event.preventDefault();
      popEl(retryButton);
      void startSession();
      return;
    }

    // Escape on stage clear: back to menu (single press, per the design).
    // Not in fullscreen — there Esc belongs to the browser (exit fullscreen).
    if (event.key === 'Escape' && sessionDone && !isFullscreen && !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
      event.preventDefault();
      revealSetup();
      return;
    }

    // Ctrl+Space on stage clear while fullscreen: back to menu
    if (isFullscreen && sessionDone && event.code === 'Space' && event.ctrlKey && !event.altKey && !event.metaKey) {
      event.preventDefault();
      revealSetup();
      return;
    }

    // Escape during active session: finish (double Esc via handleFinishClick).
    // In fullscreen the finish shortcut is Ctrl+Space ×2 instead (below).
    if (event.key === 'Escape' && state?.session && !sessionDone && !isFullscreen && !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
      event.preventDefault();
      handleFinishClick();
      return;
    }

    // Setup-screen shortcuts (length, lang select, swap)
    if (menuView) {
      const active = document.activeElement as HTMLElement | null;
      const isTyping = active?.tagName === 'INPUT' || active?.tagName === 'TEXTAREA';

      // Ctrl+Space: swap languages
      if (event.code === 'Space' && event.ctrlKey && !event.altKey && !event.metaKey) {
        event.preventDefault();
        swapDirection();
        directionRef?.popSwap();
        return;
      }

      if (!isTyping && !event.ctrlKey && !event.metaKey && !event.altKey) {
        const key = event.key;

        // 1/2/3: session length (indicator slides)
        const lengthIdx = ['1', '2', '3'].indexOf(key);
        if (lengthIdx !== -1) {
          event.preventDefault();
          length = LENGTH_OPTS[lengthIdx];
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

        if (event.key === 'Escape') {
          directionRef?.closeMenus();
          return;
        }
      }
    }

    // During an active session: Ctrl+Space ×2 finishes when fullscreen (Esc is
    // taken by the browser there), otherwise it double-taps into a hint. F2
    // always hints.
    if (state?.session && !sessionDone && !event.altKey && !event.metaKey) {
      if (event.code === 'Space' && event.ctrlKey) {
        event.preventDefault();
        if (isFullscreen) {
          handleFinishClick();
          return;
        }
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
  <!-- Off-screen primer: focused during the Play tap to raise the mobile
       keyboard in-gesture, then focus moves to the real answer input. -->
  <input
    bind:this={kbdPrimer}
    class="kbd-primer"
    type="text"
    inputmode="text"
    tabindex="-1"
    aria-hidden="true"
    autocomplete="off"
  />
  {#if loading && !state}
    <div class="glass-panel skeleton-card tall-skeleton"></div>
  {:else if error && !state}
    <div class="glass-panel">
      <div class="feedback-banner error-banner">{error}</div>
    </div>
  {:else if state}
    <div class="trainer-stack" in:fade={{ duration: 180 }}>
      {#if setScope}
        <div class="feedback-banner info-banner scope-banner">
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
        </div>
      {/if}

      {#if error}
        <div class="feedback-banner error-banner">{error}</div>
      {/if}

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

      {#if menuView}
        <!-- ===== WORD RUSH MENU (final design from the .dc.html files) ===== -->
        <article class="glass-panel strong-panel trainer-card setup-card">
          <div class="floaty-dot" aria-hidden="true"></div>
          <div class="card-help-row">
            <button
              class="fs-toggle"
              type="button"
              aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
              title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
              on:click={() => void toggleFullscreen()}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                {#if isFullscreen}
                  <path d="M8 3v3a2 2 0 0 1-2 2H3" /><path d="M21 8h-3a2 2 0 0 1-2-2V3" /><path d="M3 16h3a2 2 0 0 1 2 2v3" /><path d="M16 21v-3a2 2 0 0 1 2-2h3" />
                {:else}
                  <path d="M8 3H5a2 2 0 0 0-2 2v3" /><path d="M16 3h3a2 2 0 0 1 2 2v3" /><path d="M8 21H5a2 2 0 0 1-2-2v-3" /><path d="M16 21h3a2 2 0 0 0 2-2v-3" />
                {/if}
              </svg>
            </button>
            <HelpTip label="How sessions work">
              <h4>How a practice session works</h4>
              <p>
                Each session pulls {itemPlural} from your queue using <strong>weighted selection</strong>: weak
                translations come up far more often, while ones you've mastered fade into the background. The loop
                keeps you in the same screen with no page reloads.
              </p>
              <p>Before you start, set two things:</p>
              <ul>
                <li><strong>Session length</strong> — how many prompts this round.</li>
                <li><strong>Direction</strong> — the <em>prompt</em> language and the <em>answer</em> language.</li>
              </ul>
              <p>While answering:</p>
              <ul>
                <li>You get <strong>two tries</strong> per {itemSingular}. After the first wrong answer a hint appears automatically.</li>
                <li><strong>Hint</strong> reveals a clue; <strong>Skip and show</strong> reveals the answer.</li>
                <li>Correct answers build your <strong>combo</strong> and accelerate mastery scoring.</li>
                <li><strong>Finish session</strong> ends the round early.</li>
              </ul>
              <div class="keyboard-shortcut-help">
                <p>Keyboard shortcuts:</p>
                <ul>
                  <li><kbd>1</kbd>/<kbd>2</kbd>/<kbd>3</kbd> — session length</li>
                  <li><kbd>E</kbd>/<kbd>S</kbd>/<kbd>R</kbd>/<kbd>F</kbd> — prompt language · add <kbd>Shift</kbd> for the answer language</li>
                  <li><kbd>Ctrl</kbd>+<kbd>Space</kbd> — swap direction · <kbd>Enter</kbd> — launch</li>
                  <li><kbd>F2</kbd> — hint · <kbd>Alt</kbd>+<kbd>Enter</kbd> — skip · <kbd>Esc</kbd> ×2 — finish</li>
                  <li>In fullscreen <kbd>Esc</kbd> leaves fullscreen, so finish becomes <kbd>Ctrl</kbd>+<kbd>Space</kbd> ×2</li>
                </ul>
              </div>
            </HelpTip>
          </div>

          <div class="menu-head">
            <div>
              <p class="eyebrow">Daily stage · {routeCode}</p>
              <h1 class="menu-title">{mode === 'words' ? 'Word Rush' : 'Verb Rush'}</h1>
            </div>
            <div class="diff-readout">
              <div class="diff-stars">{DIFF_STARS[diffIdx]}</div>
              <div class="diff-name">{LENGTH_TIERS[diffIdx]}</div>
            </div>
          </div>

          <div class="diff-switch">
            <div class="diff-indicator" style={`transform: translateX(calc(${diffIdx * 100}% + ${diffIdx * 10}px));`} aria-hidden="true"></div>
            {#each LENGTH_OPTS as option, i}
              <button class="diff-tile" type="button" on:click={() => (length = option)} aria-pressed={length === option}>
                <span class="diff-tile-head">
                  <span class="diff-tile-tier">{LENGTH_TIERS[i]}</span>
                  <span class="kbd-chip">{i + 1}</span>
                </span>
                <span class="diff-tile-count">{option} {itemPlural}</span>
              </button>
            {/each}
          </div>

          <DirectionPicker
            bind:this={directionRef}
            bind:sourceCode
            bind:targetCode
            {languages}
          />

          <p class="route-label">{languageByCode(sourceCode)?.name || sourceCode} → {languageByCode(targetCode)?.name || targetCode}</p>

          <StudyPoolBlock
            mode={mode}
            expanded={studyExpanded}
            loading={studyLoading}
            error={studyError}
            entries={studyEntries}
            onToggle={toggleStudyPool}
          />

          <div class="play-area">
            {#if isArcade}
              <PlayGrid bind:this={playGridRef} disabled={launching || loading} on:fire={() => void firePlay()} />
            {:else if theme === 'light'}
              <PlayClear bind:this={playClearRef} disabled={launching || loading} on:fire={() => void firePlay()} />
            {:else}
              <PlayMist bind:this={playMistRef} {theme} disabled={launching || loading} on:fire={() => void firePlay()} />
            {/if}
          </div>
          <p class="play-caption" class:blinky={isArcade}>
            {isArcade ? 'CLICK THE GRID TO START' : theme === 'light' ? 'VECTOR GRID · CLICK TO START' : 'Wipe the mist · click to start'}
          </p>

          <div class="kbd-footer">
            <span><span class="kbd-chip">1</span> <span class="kbd-chip">2</span> <span class="kbd-chip">3</span> length</span>
            <span><span class="kbd-chip">Enter</span> start</span>
          </div>
        </article>

        {#if weakItems.length || (mode === 'words' && !setScope)}
          <article class="glass-panel aux-card">
            <p class="eyebrow" style="margin-bottom: 0.5rem;">Top weak {itemPlural}</p>
            <div class="weak-words-area">
              <div class="metric-grid tight-grid">
                {#each weakItems as item}
                  <div class="stat-card compact-stat">
                    <span>{item.language_pair.replace('_', ' → ').toUpperCase()}</span>
                    <strong style="font-size: 0.95rem; letter-spacing: normal; line-height: 1.3;">{item.label}</strong>
                    {#if item.translation}
                      <span style="font-size: 0.78rem; color: var(--muted); margin-top: 0.1rem;">{item.translation}</span>
                    {/if}
                  </div>
                {/each}
                {#each Array(4 - weakItems.length) as _}
                  <div class="stat-card compact-stat ghost-stat" aria-hidden="true"></div>
                {/each}
              </div>
              {#if weakItems.length === 0}
                <p class="section-copy weak-empty">No data yet — start a session!</p>
              {/if}
            </div>
            {#if mode === 'words' && !setScope}
              <div class="sets-teaser">
                <span class="eyebrow">Sets</span>
                <p class="section-copy" style="margin-top: 0.25rem; margin-bottom: 0;">Group words into themed sets and practice them separately.</p>
                <button type="button" class="text-switch sets-teaser-link" on:click={() => navigate('/sets')}>Browse your sets →</button>
              </div>
            {/if}
          </article>
        {/if}
      {:else if sessionView}
        {@const dq = state.question}
        <!-- ===== SESSION (rails, underline input, wave feedback) =====
             Entrance animation lives on the wrapper: toggling the shake class
             on the card would otherwise restart it (one animation shorthand). -->
        <div class:session-in-clean={!isArcade} class:session-in-arcade={isArcade}>
        <article
          class="glass-panel strong-panel session-card"
          class:shake-anim={feedbackPulse === 'error'}
        >
          <!-- progress rail towers -->
          <div class="rail rail-left" aria-hidden="true">
            <div class="rail-fill" style={`height: ${progressPct}%;`}>
              <div class="rail-cap" style={`opacity: ${(ds?.progress_current ?? 0) > 0 ? 1 : 0};`}></div>
            </div>
          </div>
          <div class="rail rail-right" aria-hidden="true">
            <div class="rail-fill" style={`height: ${progressPct}%;`}>
              <div class="rail-cap" style={`opacity: ${(ds?.progress_current ?? 0) > 0 ? 1 : 0};`}></div>
            </div>
          </div>

          <!-- grading feedback: vignette-masked tile wave propagating from center -->
          {#key pulseSeq}
            {#if feedbackPulse}
              <div class="cell-wave" aria-hidden="true">
                {#each WAVE_CELLS as c, i (i)}
                  <div style={`animation: ${theme === 'light' ? 'matcha-cellw' : 'cellw'}-${feedbackPulse} .45s ease-out ${c.delay}s both;`}></div>
                {/each}
              </div>
              {#if isArcade}
                <div class={`edge-flash ${feedbackPulse}`} aria-hidden="true"></div>
              {/if}
            {/if}
          {/key}

          <div class="session-inner">
            <div class="session-top">
              <span class="session-meta">{ds?.progress_current ?? 0}/{ds?.progress_total ?? 0}</span>
              <span class="session-meta">{routeCode}</span>
              <span class="session-top-end">
                {#key ds?.combo}
                  <span class="combo-chip" class:combo-swell={(ds?.combo ?? 0) > 1}>combo ×{ds?.combo ?? 0}</span>
                {/key}
                <button
                  class="fs-toggle fs-toggle-session"
                  type="button"
                  aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
                  title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
                  on:click={() => void toggleFullscreen()}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    {#if isFullscreen}
                      <path d="M8 3v3a2 2 0 0 1-2 2H3" /><path d="M21 8h-3a2 2 0 0 1-2-2V3" /><path d="M3 16h3a2 2 0 0 1 2 2v3" /><path d="M16 21v-3a2 2 0 0 1 2-2h3" />
                    {:else}
                      <path d="M8 3H5a2 2 0 0 0-2 2v3" /><path d="M16 3h3a2 2 0 0 1 2 2v3" /><path d="M8 21H5a2 2 0 0 1-2-2v-3" /><path d="M16 21h3a2 2 0 0 0 2-2v-3" />
                    {/if}
                  </svg>
                </button>
              </span>
            </div>

            {#key dq?.item_id}
              <div
                class="prompt-word"
                class:clear-vector-jolt={feedbackPulse === 'error' && theme === 'light'}
                bind:this={promptEl}
              >{dq?.prompt ?? ''}</div>
            {/key}

            <form class="answer-line-form" novalidate on:submit|preventDefault={() => submitAnswer(false)}>
              <div class="line-input-wrap">
                <div class="line-input-field">
                  <input
                    bind:this={answerInput}
                    bind:value={answer}
                    class="line-input"
                    placeholder={isArcade ? '▊ type your answer' : 'type your answer'}
                    autocomplete="off"
                    autocapitalize="off"
                    spellcheck="false"
                    inputmode="text"
                    enterkeyhint="send"
                    readonly={loading}
                    on:input={handleAnswerInput}
                    on:compositionstart={() => (quickShotComposing = true)}
                    on:compositionend={handleAnswerCompositionEnd}
                    on:focus={() => { quickShotExplanationOpen = false; scheduleMobileViewportCenter(); }}
                  />
                  {#key pulseSeq}
                    {#if feedbackPulse === 'success'}
                      <!-- Check draw (chosen in /playground): underline surges,
                           a checkmark draws itself at the end of the line -->
                      <span class="line-surge" aria-hidden="true"></span>
                      <svg class="check-draw" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M4 12.5 L10 18 L20 6" />
                      </svg>
                      {#if isArcade}
                        <div class="input-burst" aria-hidden="true"></div>
                      {/if}
                    {/if}
                  {/key}
                </div>
                <QuickShotIcon
                  ready={quickShotReady}
                  guarding={quickShotGuarding}
                  accepted={quickShotAccepted}
                  explanationOpen={quickShotExplanationOpen}
                  controls="translation-quick-shot-note"
                  onToggle={() => (quickShotExplanationOpen = !quickShotExplanationOpen)}
                />
              </div>

              {#if quickShotExplanationOpen}
                <div class="quick-shot-note" id="translation-quick-shot-note" role="note">
                  <span>{quickShotReady ? 'QUICK-SHOT ARMED' : 'QUICK-SHOT SPENT'}</span>
                  <strong>{quickShotReady ? 'A perfect answer fires instantly — no Enter needed.' : 'Impossible letter typed — this one now waits for Enter.'}</strong>
                </div>
              {/if}

              <div class="session-msg" class:msg-success={inlineTone === 'success'} class:msg-error={inlineTone === 'error'} class:msg-info={inlineTone === 'info'}>
                {#if inlineMsg}<span>{inlineMsg}</span>{/if}
              </div>

              <div class="kbd-row">
                <button class="kbd-action" type="submit" disabled={loading}>
                  <span class="kbd-chip">Enter</span> submit
                </button>
                <button bind:this={hintButton} class="kbd-action" class:hint-armed={ctrlSpaceArmed} type="button" on:click={() => { popEl(hintButton); void showHint(); }} disabled={loading}>
                  <span class="kbd-chip">F2</span> hint
                </button>
                <button bind:this={skipButton} class="kbd-action" type="button" on:click={() => { popEl(skipButton); void submitAnswer(true); }} disabled={loading}>
                  <span class="kbd-chip">Alt+Enter</span> skip
                </button>
                <button
                  bind:this={finishButton}
                  class="kbd-action"
                  class:finish-warn={finishSessionWarning}
                  type="button"
                  on:click={handleFinishClick}
                  disabled={loading}
                >
                  <span class="kbd-chip" class:kbd-chip-armed={finishSessionWarning}>{isFullscreen ? (finishSessionWarning ? 'Ctrl+Space ×1' : 'Ctrl+Space ×2') : (finishSessionWarning ? 'Esc ×1' : 'Esc ×2')}</span> finish
                </button>
              </div>
            </form>
          </div>
        </article>
        </div>
      {:else if sessionDone}
        <!-- ===== STAGE CLEAR (C1-A rank screen, chosen in /playground2) ===== -->
        <article class="glass-panel strong-panel clear-card" class:session-in-arcade={isArcade} class:clear-in={!isArcade}>
          {#if !isArcade}
            <div class="wave-mask success clear-sweep" aria-hidden="true"><div class="wave-disc"></div></div>
          {/if}
          <StageClearRank
            score={clearScore}
            ok={okRun}
            total={clearTotal}
            bestCombo={prevSession?.best_combo ?? 0}
            unitLabel={itemPlural}
          >
            <button bind:this={retryButton} class="primary-button" type="button" on:click={() => { popEl(retryButton); void startSession(); }} disabled={loading}>
              <svg class="btn-play-glyph" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5.5v13l11-6.5z" /></svg>
              Replay <span class="kbd-chip">Enter</span>
            </button>
            <button class="secondary-button" type="button" on:click={revealSetup} disabled={loading}>
              Menu <span class="kbd-chip">{isFullscreen ? 'Ctrl+Space' : 'Esc'}</span>
            </button>
          </StageClearRank>
        </article>
      {/if}
    </div>
  {/if}

  <!-- Arcade launch: full-screen pixel dissolve -->
  {#if pixelOverlay}
    <div class="pixel-overlay" class:pixel-fade={pixelFade} class:vector-overlay={theme === 'light'} aria-hidden="true">
      {#each PIX_CELLS as c, i (i)}
        <div style={`background: ${pixPalette[c.ci]}; animation: ${theme === 'light' ? 'vector-cellon' : 'cellon'} .32s cubic-bezier(.2,.8,.2,1) ${theme === 'light' ? c.vectorDelay : c.radialDelay}s both;`}></div>
      {/each}
    </div>
  {/if}
</section>

<style>
  .trainer-shell {
    max-width: 720px;
    margin-inline: auto;
    width: 100%;
  }

  /* Focusable but visually hidden. font-size 16px prevents iOS zoom; not
     display:none/visibility:hidden so focusing it can still raise the keyboard. */
  .kbd-primer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: 0;
    border: 0;
    font-size: 16px;
    opacity: 0;
    background: transparent;
    color: transparent;
    caret-color: transparent;
    pointer-events: none;
    z-index: -1;
  }

  .card-help-row {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: -0.5rem;
  }

  /* Fullscreen is a desktop affordance — pointless chrome on phones/tablets */
  .fs-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    flex-shrink: 0;
    border: 1px solid var(--line);
    border-radius: 10px;
    background: transparent;
    color: var(--muted);
    cursor: pointer;
    transition: color 0.2s, border-color 0.2s, background 0.2s;
  }

  .fs-toggle svg {
    width: 17px;
    height: 17px;
  }

  @media (hover: hover) {
    .fs-toggle:hover {
      color: var(--text);
      border-color: color-mix(in srgb, var(--accent) 45%, transparent);
      background: var(--accent-soft);
    }
  }

  @media (pointer: coarse), (max-width: 760px) {
    .fs-toggle {
      display: none;
    }
  }

  .session-top-end {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
  }

  .scope-banner {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.35rem;
  }

  /* ===== Menu (Word Rush) ===== */
  .setup-card {
    position: relative;
  }

  .floaty-dot {
    position: absolute;
    top: 1.1rem;
    right: 4rem;
    width: 15px;
    height: 15px;
    border-radius: 50%;
    background: color-mix(in srgb, var(--accent) 30%, transparent);
    animation: floaty 5s ease-in-out infinite;
    pointer-events: none;
  }

  :global(html[data-theme='arcade']) .floaty-dot {
    border-radius: 0;
    width: 14px;
    height: 14px;
    background: color-mix(in srgb, var(--accent) 50%, transparent);
    animation-duration: 4s;
  }

  @keyframes floaty {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
  }

  .menu-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
  }

  .menu-title {
    font-family: var(--marquee);
    font-size: 1.75rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--text);
    margin: 0.35rem 0 0;
    line-height: 1.2;
  }

  :global(html[data-theme='arcade']) .menu-title {
    font-size: 1.25rem;
    line-height: 1.5;
    text-shadow: 0 0 14px color-mix(in srgb, var(--accent) 95%, transparent);
  }

  .diff-readout {
    text-align: right;
    flex-shrink: 0;
  }

  .diff-stars {
    font-size: 15px;
    letter-spacing: 3px;
    color: var(--accent);
  }

  :global(html[data-theme='arcade']) .diff-stars {
    color: var(--text);
    text-shadow: 0 0 10px color-mix(in srgb, var(--accent) 60%, transparent);
  }

  .diff-name {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--muted);
    margin-top: 5px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-family: var(--mono);
  }

  /* Sliding difficulty selector */
  .diff-switch {
    position: relative;
    display: flex;
    gap: 10px;
    padding: 6px;
    border-radius: 14px;
    border: 1px solid var(--line);
    background: color-mix(in srgb, var(--surface-strong) 55%, transparent);
  }

  .diff-indicator {
    position: absolute;
    top: 6px;
    bottom: 6px;
    left: 6px;
    width: calc((100% - 32px) / 3);
    border-radius: 10px;
    background: color-mix(in srgb, var(--surface-strong) 96%, transparent);
    border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent);
    box-shadow: 0 3px 10px -3px color-mix(in srgb, var(--accent) 35%, transparent);
    pointer-events: none;
    transition: transform 0.35s cubic-bezier(0.25, 0.8, 0.3, 1);
  }

  :global(html[data-theme='arcade']) .diff-indicator {
    background: transparent;
    border: 2px solid var(--accent);
    box-shadow: 0 0 18px color-mix(in srgb, var(--accent) 55%, transparent), inset 0 0 14px color-mix(in srgb, var(--accent) 30%, transparent);
    transition: transform 0.38s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .diff-tile {
    position: relative;
    flex: 1;
    background: transparent;
    border: 0;
    border-radius: 10px;
    padding: 11px 0 10px;
    text-align: center;
    cursor: pointer;
  }

  .diff-tile-head {
    display: flex;
    justify-content: center;
    gap: 8px;
    align-items: center;
  }

  .diff-tile-tier {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    font-family: var(--mono);
  }

  .diff-tile-count {
    display: block;
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text);
    margin-top: 5px;
    font-family: var(--display);
  }

  :global(html[data-theme='arcade']) .diff-tile-count {
    font-family: var(--ui);
  }

  /* Language dropdowns */
  .route-label {
    text-align: center;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--accent-strong);
    letter-spacing: 0.03em;
    margin: 0;
  }

  :global(html[data-theme='arcade']) .route-label {
    font-family: var(--mono);
    font-size: 1.1rem;
    letter-spacing: 2px;
    color: var(--accent);
  }

  .play-area {
    display: flex;
    justify-content: center;
    margin-top: 0.25rem;
  }

  .play-caption {
    text-align: center;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--muted);
    margin: 0.35rem 0 0;
    animation: softpulse 2.6s ease-in-out infinite;
  }

  :global(html[data-theme='arcade']) .play-caption {
    font-size: 0.8rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }

  .play-caption.blinky {
    animation: blinky 1.4s step-end infinite;
  }

  @keyframes softpulse {
    0%, 100% { opacity: 0.45; }
    50% { opacity: 1; }
  }

  @keyframes blinky {
    0%, 49% { opacity: 1; }
    50%, 100% { opacity: 0; }
  }

  .kbd-footer {
    display: flex;
    justify-content: center;
    gap: 22px;
    align-items: center;
    padding-top: 14px;
    border-top: 1px solid var(--line);
    flex-wrap: wrap;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--muted);
  }

  .aux-card {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  /* Top weak words: reserve a stable footprint so the empty state never
     shifts the rest of the card when switching direction/language. */
  .weak-words-area {
    position: relative;
  }

  .weak-words-area .stat-card {
    height: 6.5rem;
    justify-content: center;
    overflow: hidden;
  }

  .weak-words-area .stat-card > span,
  .weak-words-area .stat-card > strong {
    max-width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .ghost-stat {
    visibility: hidden;
  }

  .weak-empty {
    position: absolute;
    inset: 0;
    margin: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
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

  .sets-teaser-link {
    margin-left: auto;
    white-space: nowrap;
  }

  button:active:not(:disabled) {
    transform: scale(0.96);
    transition: transform 0.07s ease-out;
  }

  /* ===== Session ===== */
  .session-card,
  .clear-card {
    position: relative;
    overflow: hidden;
    text-align: center;
  }

  .session-in-clean {
    animation: focus-in 0.48s ease-out both;
  }

  :global(html[data-theme='light']) .session-in-clean {
    animation: clear-vector-session-in 0.48s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  @keyframes clear-vector-session-in {
    0% { opacity: 0; clip-path: inset(0 100% 0 0); transform: translateX(-8px); }
    100% { opacity: 1; clip-path: inset(0 0 0 0); transform: translateX(0); }
  }

  @keyframes focus-in {
    0% { opacity: 0; filter: blur(14px); }
    100% { opacity: 1; filter: blur(0); }
  }

  .session-in-arcade {
    animation: drop-in 0.4s ease-out both;
  }

  @keyframes drop-in {
    0% { transform: scale(1.7); opacity: 0; }
    100% { transform: scale(1); opacity: 1; }
  }

  .clear-in {
    animation: clear-in 0.45s ease-out both;
  }

  @keyframes clear-in {
    0% { opacity: 0; transform: translateY(12px); }
    100% { opacity: 1; transform: translateY(0); }
  }

  .rail {
    position: absolute;
    top: 14px;
    bottom: 14px;
    width: 5px;
    border-radius: 3px;
    background: color-mix(in srgb, var(--accent) 12%, transparent);
    z-index: 2;
  }

  .rail-left { left: 9px; }
  .rail-right { right: 9px; }

  :global(html[data-theme='light']) .session-card {
    border-radius: 10px;
    clip-path: polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 16px 100%, 0 calc(100% - 16px));
  }

  :global(html[data-theme='light']) .rail,
  :global(html[data-theme='light']) .rail-fill,
  :global(html[data-theme='light']) .rail-cap {
    border-radius: 0;
  }

  .rail-fill {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    border-radius: 3px;
    background: linear-gradient(180deg, var(--accent-strong), var(--accent));
    box-shadow: 0 0 10px color-mix(in srgb, var(--accent) 50%, transparent);
    transition: height 0.6s ease;
  }

  .rail-cap {
    position: absolute;
    top: -3px;
    left: -3px;
    right: -3px;
    height: 9px;
    border-radius: 5px;
    background: linear-gradient(180deg, #ffffff, var(--accent-strong));
    box-shadow: 0 0 12px 3px color-mix(in srgb, var(--accent) 85%, transparent), 0 0 30px 8px color-mix(in srgb, var(--accent) 40%, transparent);
    animation: fillhead 1.6s ease-in-out infinite;
    transition: opacity 0.4s;
  }

  @keyframes fillhead {
    0%, 100% { opacity: 0.55; }
    50% { opacity: 1; }
  }

  .session-inner {
    position: relative;
    z-index: 3;
    padding: 0 1.25rem;
  }

  .session-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .session-meta {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: var(--muted);
    font-family: var(--mono);
    text-transform: uppercase;
  }

  .combo-chip {
    display: inline-block;
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--accent-strong);
  }

  :global(html[data-theme='arcade']) .combo-chip {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    text-shadow: 0 0 10px color-mix(in srgb, var(--accent) 90%, transparent);
  }

  :global(html[data-theme='arcade']) .session-meta {
    font-size: 1.05rem;
  }

  .combo-swell {
    animation: cswell 0.5s ease-out;
  }

  @keyframes cswell {
    0% { transform: scale(1); }
    40% { transform: scale(1.28); }
    100% { transform: scale(1); }
  }

  .prompt-word {
    display: inline-block;
    font-family: var(--display);
    font-size: clamp(2.2rem, 6vw, 3rem);
    font-weight: 700;
    color: var(--text);
    margin: 1.1rem 0 1.35rem;
    animation: prompt-blur 0.17s ease-out both;
  }

  :global(html[data-theme='arcade']) .prompt-word {
    font-family: var(--ui);
    font-size: clamp(2.4rem, 6vw, 3.4rem);
    animation: drop-in 0.35s ease-out both;
  }

  @keyframes prompt-blur {
    0% { opacity: 0; filter: blur(10px); }
    100% { opacity: 1; filter: blur(0); }
  }

  :global(html[data-theme='light']) .prompt-word {
    letter-spacing: -0.055em;
  }

  .clear-vector-jolt {
    animation: clear-vector-jolt 420ms ease-out both !important;
  }

  @keyframes clear-vector-jolt {
    0%, 100% { transform: translateX(0) skewX(0); }
    24% { transform: translateX(-8px) skewX(-7deg); }
    52% { transform: translateX(7px) skewX(5deg); }
    74% { transform: translateX(-3px) skewX(-2deg); }
  }

  :global(.prompt-glitch) {
    animation: glitchy 0.5s ease-out !important;
  }

  @keyframes glitchy {
    0%, 100% { transform: translate(0) skewX(0); text-shadow: none; }
    20% { transform: translate(-7px, 1px) skewX(-8deg); text-shadow: 4px 0 var(--danger), -4px 0 var(--accent); }
    45% { transform: translate(6px, -2px); text-shadow: -4px 0 var(--danger), 4px 0 var(--accent); }
    70% { transform: translate(-4px, 1px) skewX(6deg); text-shadow: 3px 0 var(--danger); }
  }

  .answer-line-form {
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .line-input-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
    max-width: 440px;
    margin: 0 auto;
    width: 100%;
  }

  /* Holds the underline input + its success flourishes; the quick-shot icon
     sits beside it (a flex sibling) so it never covers the typed answer. */
  .line-input-field {
    position: relative;
    flex: 1 1 auto;
    min-width: 0;
  }

  .line-input {
    width: 100%;
    box-sizing: border-box;
    background: transparent;
    border: none;
    border-bottom: 2px solid color-mix(in srgb, var(--accent) 35%, transparent);
    padding: 12px 4px;
    color: var(--text);
    font-size: 1.3rem;
    text-align: center;
    outline: none;
    transition: border-color 0.3s, box-shadow 0.3s;
    border-radius: 0;
  }

  .quick-shot-note {
    max-width: 440px;
    margin: 0.6rem auto 0;
    padding: 0.5rem 0.75rem;
    border: 1px solid color-mix(in srgb, var(--accent-2) 40%, transparent);
    border-radius: 10px;
    background: color-mix(in srgb, var(--accent-soft) 60%, transparent);
    display: grid;
    gap: 0.15rem;
    text-align: center;
  }

  .quick-shot-note > span {
    font: 700 0.68rem/1 var(--mono);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--accent-2);
  }

  :global(html[data-theme='light']) .quick-shot-note > span {
    color: var(--danger);
  }

  .quick-shot-note > strong {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text);
  }

  :global(html[data-theme='arcade']) .line-input {
    font-family: var(--mono);
    font-size: 1.5rem;
    letter-spacing: 2px;
    color: var(--accent-strong);
  }

  .line-input:focus {
    border-bottom-color: var(--accent);
    box-shadow: 0 12px 20px -16px color-mix(in srgb, var(--accent) 60%, transparent);
  }

  :global(html[data-theme='light']) .line-input {
    background: color-mix(in srgb, var(--matcha-field) 34%, transparent);
    border-bottom-color: var(--accent);
    font-weight: 650;
  }

  :global(html[data-theme='light']) .line-input:focus {
    border-bottom-color: var(--accent-2);
    box-shadow: inset 0 -3px 0 color-mix(in srgb, var(--accent-2) 55%, transparent);
  }

  /* Check draw — the chosen correct-answer feedback (playground option A) */
  .line-surge {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 2px;
    background: var(--accent);
    pointer-events: none;
    animation: line-surge 0.8s ease-out both;
  }

  @keyframes line-surge {
    0% { opacity: 0; box-shadow: none; }
    25% { opacity: 1; box-shadow: 0 6px 18px -4px var(--accent); }
    100% { opacity: 0; box-shadow: none; }
  }

  .check-draw {
    position: absolute;
    right: 2px;
    top: 50%;
    margin-top: -11px;
    width: 22px;
    height: 22px;
    overflow: visible;
    pointer-events: none;
  }

  .check-draw path {
    fill: none;
    stroke: var(--accent);
    stroke-width: 3.2;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-dasharray: 32;
    stroke-dashoffset: 32;
    filter: drop-shadow(0 0 6px color-mix(in srgb, var(--accent) 60%, transparent));
    animation: check-dash 0.4s 0.1s cubic-bezier(0.3, 0.9, 0.4, 1) forwards;
  }

  @keyframes check-dash {
    to { stroke-dashoffset: 0; }
  }

  @media (max-width: 560px) {
    .check-draw {
      right: 2px;
      width: 18px;
      height: 18px;
      margin-top: -9px;
    }
  }

  .input-burst {
    position: absolute;
    left: 50%;
    top: 0;
    width: 8px;
    height: 8px;
    opacity: 0;
    animation: burst 0.6s ease-out;
    pointer-events: none;
  }

  @keyframes burst {
    0% {
      opacity: 1;
      box-shadow: 0 0 0 2px #cdbcff, 0 0 0 2px #a78bfa, 0 0 0 2px #7c3aed, 0 0 0 2px #cdbcff, 0 0 0 2px #a78bfa, 0 0 0 2px #7c3aed, 0 0 0 2px #cdbcff, 0 0 0 2px #a78bfa;
    }
    100% {
      opacity: 0;
      box-shadow: -70px -54px 0 3px #cdbcff, 64px -60px 0 4px #a78bfa, -84px 10px 0 2px #7c3aed, 78px 6px 0 3px #cdbcff, -46px 58px 0 4px #a78bfa, 52px 50px 0 2px #7c3aed, -8px -74px 0 3px #cdbcff, 6px 66px 0 4px #a78bfa;
    }
  }

  .session-msg {
    min-height: 24px;
    margin-top: 14px;
    font-size: 0.9rem;
    font-weight: 600;
  }

  .session-msg.msg-success { color: var(--success); }
  .session-msg.msg-error { color: var(--danger); }
  .session-msg.msg-info { color: var(--accent-strong); }

  .kbd-row {
    display: flex;
    justify-content: center;
    gap: 18px;
    align-items: center;
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid var(--line);
    flex-wrap: wrap;
  }

  .kbd-action {
    cursor: pointer;
    background: transparent;
    border: none;
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--muted);
    padding: 0;
    display: flex;
    gap: 6px;
    align-items: center;
    transition: color 0.2s;
  }

  .kbd-action:hover:not(:disabled) {
    color: var(--accent-strong);
  }

  .finish-warn {
    color: var(--danger) !important;
  }

  .hint-armed :global(.kbd-chip),
  .kbd-chip-armed {
    color: var(--bg) !important;
    background: var(--accent-strong) !important;
    border-color: var(--accent-strong) !important;
    box-shadow: 0 0 14px color-mix(in srgb, var(--accent) 70%, transparent);
  }

  /* Grading overlays */
  .wave-mask {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 4;
    overflow: hidden;
    border-radius: 18px;
    -webkit-mask-image: radial-gradient(ellipse 76% 72% at 50% 46%, rgba(0,0,0,0) 0%, rgba(0,0,0,.05) 34%, rgba(0,0,0,.45) 58%, #000 82%);
    mask-image: radial-gradient(ellipse 76% 72% at 50% 46%, rgba(0,0,0,0) 0%, rgba(0,0,0,.05) 34%, rgba(0,0,0,.45) 58%, #000 82%);
  }

  .wave-disc {
    position: absolute;
    left: 50%;
    top: 50%;
    width: 180%;
    aspect-ratio: 1 / 1;
    border-radius: 50%;
    filter: blur(6px);
    animation: wave-ring 0.95s ease-out both;
  }

  .wave-mask.success .wave-disc {
    background: radial-gradient(circle, color-mix(in srgb, var(--accent) 0%, transparent) 20%, color-mix(in srgb, var(--accent) 52%, transparent) 38%, color-mix(in srgb, var(--accent-2) 32%, transparent) 58%, transparent 78%);
  }

  .clear-sweep .wave-disc {
    animation-duration: 1.4s;
  }

  @keyframes wave-ring {
    0% { transform: translate(-50%, -50%) scale(0.05); opacity: 0; }
    14% { opacity: 1; }
    100% { transform: translate(-50%, -50%) scale(1); opacity: 0; }
  }

  .cell-wave {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 4;
    display: grid;
    grid-template-columns: repeat(22, 1fr);
    grid-auto-rows: 1fr;
    gap: 2px;
    padding: 3px;
    opacity: 0.9;
    -webkit-mask-image: radial-gradient(ellipse 95% 95% at 50% 50%, rgba(0,0,0,.15) 0%, rgba(0,0,0,.22) 55%, rgba(0,0,0,.6) 82%, #000 97%);
    mask-image: radial-gradient(ellipse 95% 95% at 50% 50%, rgba(0,0,0,.15) 0%, rgba(0,0,0,.22) 55%, rgba(0,0,0,.6) 82%, #000 97%);
  }

  .cell-wave > div {
    border-radius: 1px;
  }

  :global(html[data-theme='light']) .cell-wave > div {
    border-radius: 0;
    clip-path: polygon(0 0, 78% 0, 100% 25%, 100% 100%, 22% 100%, 0 75%);
    transform-origin: center;
  }

  /* Tile colors ride the theme tokens: violet in arcade, sky in light,
     blue in dark; wrong is always the theme's danger red.
     -global- keeps the names unscoped: the cells reference them from inline
     styles (per-cell radial delays), which Svelte's scoping can't rewrite. */
  @keyframes -global-cellw-success {
    0% { background: color-mix(in srgb, var(--accent) 5%, transparent); }
    35% { background: color-mix(in srgb, var(--accent) 60%, transparent); }
    100% { background: color-mix(in srgb, var(--accent) 5%, transparent); }
  }

  @keyframes -global-cellw-error {
    0% { background: color-mix(in srgb, var(--accent) 5%, transparent); }
    35% { background: color-mix(in srgb, var(--danger) 58%, transparent); }
    100% { background: color-mix(in srgb, var(--accent) 5%, transparent); }
  }

  @keyframes -global-matcha-cellw-success {
    0%, 100% { opacity: 0; background: var(--accent); transform: scaleX(0.25); }
    42% { opacity: 0.66; background: var(--accent); transform: scaleX(1); }
  }

  @keyframes -global-matcha-cellw-error {
    0%, 100% { opacity: 0; background: var(--accent-2); transform: scaleX(0.25); }
    42% { opacity: 0.62; background: var(--accent-2); transform: scaleX(1); }
  }

  .edge-flash {
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 5;
    border-radius: 16px;
    opacity: 0;
  }

  .edge-flash.success {
    border: 2px solid var(--accent-strong);
    box-shadow: inset 0 0 60px color-mix(in srgb, var(--accent) 80%, transparent);
    animation: flash-fade 0.6s ease-out;
  }

  .edge-flash.error {
    border: 2px solid var(--danger);
    box-shadow: inset 0 0 60px color-mix(in srgb, var(--danger) 50%, transparent);
    animation: flash-fade 0.5s ease-out;
  }

  @keyframes flash-fade {
    0% { opacity: 1; }
    100% { opacity: 0; }
  }

  @keyframes shake-anim {
    0%, 100% { transform: translate(0, 0); }
    20% { transform: translate(-4px, 1px); }
    45% { transform: translate(4px, -1px); }
    70% { transform: translate(-2px, 1px); }
  }

  .shake-anim {
    animation: shake-anim 0.45s ease-out;
  }

  :global(html[data-theme='light']) .shake-anim {
    animation: none;
  }

  :global(html[data-theme='arcade']) .shake-anim {
    animation-name: shake-arcade;
  }

  @keyframes shake-arcade {
    0%, 100% { transform: translate(0, 0); }
    15% { transform: translate(-9px, 2px); }
    30% { transform: translate(8px, -3px); }
    45% { transform: translate(-6px, 3px); }
    60% { transform: translate(5px, -2px); }
    80% { transform: translate(-3px, 1px); }
  }

  /* ===== Stage clear (content lives in StageClearRank) ===== */
  .clear-card {
    padding-top: 2.5rem;
    padding-bottom: 2.25rem;
  }

  .btn-play-glyph {
    width: 0.8em;
    height: 0.8em;
    margin-right: 0.1em;
    vertical-align: -0.06em;
  }

  /* Keep the rank content above the clear-sweep overlay (z-index 4) */
  .clear-card :global(.rank-clear) {
    position: relative;
    z-index: 5;
  }

  /* ===== Arcade pixel dissolve overlay ===== */
  .pixel-overlay {
    position: fixed;
    inset: 0;
    z-index: 55;
    pointer-events: none;
    display: grid;
    grid-template-columns: repeat(16, 1fr);
    grid-auto-rows: 1fr;
    opacity: 1;
    transition: opacity 0.5s ease;
  }

  .pixel-overlay.pixel-fade {
    opacity: 0;
  }

  /* -global-: referenced from the overlay cells' inline styles */
  @keyframes -global-cellon {
    0% { transform: scale(0); opacity: 0; }
    100% { transform: scale(1); opacity: 1; }
  }

  .vector-overlay > div {
    transform-origin: left center;
  }

  @keyframes -global-vector-cellon {
    0% { transform: scaleX(0); opacity: 0; }
    100% { transform: scaleX(1); opacity: 1; }
  }

  @media (prefers-reduced-motion: reduce) {
    .session-in-clean,
    .session-in-arcade,
    .clear-in,
    .prompt-word,
    .menu-out {
      animation-duration: 1ms;
    }

    .cell-wave,
    .wave-mask,
    .input-burst,
    .floaty-dot {
      display: none;
    }

    .pixel-overlay > div {
      animation-duration: 1ms !important;
      animation-delay: 0ms !important;
    }
  }

  @media (max-width: 560px) {
    .menu-head {
      flex-direction: column;
    }

    .diff-readout {
      text-align: left;
    }
  }
</style>
