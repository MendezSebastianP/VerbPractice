<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { fade } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import { playCue } from '../sound';
  import { applyReward } from '../profile';
  import { celebrateReward, flashMiss, popEl, releaseCelebrations } from '../fx';
  import QuickShotIcon from '../components/QuickShotIcon.svelte';
  import StageClearRank from '../components/StageClearRank.svelte';
  import StudyPoolBlock from '../components/StudyPoolBlock.svelte';
  import type { ConjugationState, ConjugationTenseReview, ConjugationTrainerSetup, LanguageConfig, RewardState, StudyPoolResponse, ThemeName } from '../types';

  export let csrfToken = '';
  export let soundEnabled = false;
  export let theme: ThemeName = 'light';
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
  // Off-screen text field kept focused on mobile so the soft keyboard stays up
  // through the tense-review and stage-clear screens — the user can press the
  // keyboard's Enter/Send to continue or replay without re-tapping.
  let kbdPrimer: HTMLInputElement | null = null;
  let selectedTenses: string[] = [];
  let answers: Record<string, Record<string, string>> = {};
  let activeCellKey = '';
  let justFinished = false;
  let showSetupAfterFinish = false;
  let studyExpanded = false;
  let studyLoading = false;
  let studyError = '';
  let studyEntries: StudyPoolResponse['entries'] = [];
  let loadedStudyKey = '';
  let activeTenseIndex = 0;
  let tenseReview: ConjugationTenseReview | null = null;
  let checkedTenses = new Set<string>();
  let tenseScores: Record<string, { correct: number; total: number }> = {};
  let finishSessionWarning = false;
  let escTimer: ReturnType<typeof setTimeout> | null = null;
  let shortcutsExpanded = false;
  let isFullscreen = false;
  let mobileCenterFrame: number | null = null;
  let quickShotSpent = new Set<string>();
  let quickShotGuarding = false;
  let quickShotAccepted = false;
  let quickShotExplanationOpen = false;
  let quickShotAdvanceInFlight = false;
  let quickShotComposing = false;
  let autoAdvanceTimer: ReturnType<typeof setTimeout> | null = null;
  let autoAdvancing = false;
  let emptyEnterGuardUntil = 0;
  let quickShotGuardTimer: ReturnType<typeof setTimeout> | null = null;
  let quickShotAcceptedTimer: ReturnType<typeof setTimeout> | null = null;

  const LEVELS = [
    { value: 'easy', label: 'Core', note: 'Start with the essential forms' },
    { value: 'medium', label: 'Expand', note: 'Add everyday range' },
    { value: 'hard', label: 'Master', note: 'Open the complete corpus' },
  ];
  const LENGTH_OPTIONS = [3, 5, 8];
  const LANGUAGE_SHORTCUTS: Record<string, string> = { EN: 'E', ES: 'S', FR: 'F', RU: 'R' };
  const FILL_LEVEL_SHORTCUTS: Record<string, string> = { hard: 'Shift+1', medium: 'Shift+2', easy: 'Shift+3' };

  type InputCell = {
    key: string;
    tense: string;
    pronoun: string;
    acceptedAnswers: string[];
  };

  type FormGroup = {
    representative: string;
    pronouns: string[];
  };

  const GROUP_COLORS: Record<ThemeName, string[]> = {
    light: ['#76ddff', '#f8cc63', '#7ee7a8', '#ff8da1', '#b7a0ff', '#f0a1d6'],
    arcade: ['#76ddff', '#f8cc63', '#7ee7a8', '#ff8da1', '#b7a0ff', '#f0a1d6'],
    dark: ['#e6a528', '#d75b4b', '#d8b56c', '#c87846', '#b79972', '#b9695c'],
  };

  let activeTense = '';
  let currentInputCells: InputCell[] = [];
  let currentActiveCell: InputCell | null = null;
  let quickShotReady = false;
  let activeFormGroups: FormGroup[] = [];
  let uniformFormLayout = false;
  let clusteredFormLayout = false;
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

    if (!allowSetupReset) {
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
        cells.push({
          key: cellKey(tense, pronoun),
          tense,
          pronoun,
          acceptedAnswers: cell.accepted_answers || [],
        });
      }
    }
    return cells;
  }

  $: activeTense = state?.question?.selected_tenses[activeTenseIndex] || '';
  $: activeLanguage = state?.languages.find((entry) => entry.code === language);
  $: activeFormGroups = state?.question?.form_groups[activeTense] || [];
  $: uniformFormLayout = activeFormGroups.length === 1 && activeFormGroups[0].pronouns.length > 1;
  $: clusteredFormLayout = activeFormGroups.length > 1 && activeFormGroups.some((group) => group.pronouns.length > 1);
  $: currentInputCells = buildInputCells(state?.question, activeTense);
  $: currentActiveCell = currentInputCells.find((cell) => cell.key === activeCellKey) || currentInputCells[0] || null;
  // Position of the active answer within the tense — drives the mobile "N/total"
  // badge on the compact one-cell-at-a-time layout.
  $: activeInputIndex = Math.max(0, currentInputCells.findIndex((cell) => cell.key === currentActiveCell?.key));
  $: quickShotReady = Boolean(
    currentActiveCell?.acceptedAnswers.length
    && !quickShotSpent.has(currentActiveCell.key),
  );
  $: sessionActive = Boolean(state?.session && state?.question);
  $: sessionDone = Boolean(justFinished && !state?.session && !showSetupAfterFinish);
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
    resetQuickShotProgress();
  }

  // A flawless tense shows its review for a beat and moves on by itself; a tense
  // with any miss stays put so the user can read the corrections before Enter.
  const AUTO_ADVANCE_MS = 1000;
  const EMPTY_ENTER_GUARD_MS = 1000;

  function clearAutoAdvance(): void {
    if (autoAdvanceTimer) {
      clearTimeout(autoAdvanceTimer);
      autoAdvanceTimer = null;
    }
    autoAdvancing = false;
  }

  function clearQuickShotTimers(): void {
    if (quickShotGuardTimer) {
      clearTimeout(quickShotGuardTimer);
      quickShotGuardTimer = null;
    }
    if (quickShotAcceptedTimer) {
      clearTimeout(quickShotAcceptedTimer);
      quickShotAcceptedTimer = null;
    }
  }

  function resetQuickShotProgress(): void {
    clearQuickShotTimers();
    clearAutoAdvance();
    quickShotSpent = new Set<string>();
    quickShotGuarding = false;
    quickShotAccepted = false;
    quickShotExplanationOpen = false;
    quickShotAdvanceInFlight = false;
    quickShotComposing = false;
  }

  function armEmptyEnterGuard(): void {
    emptyEnterGuardUntil = Date.now() + EMPTY_ENTER_GUARD_MS;
  }

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
      // Fullscreen can be denied by browser or embedding permissions.
    }
  }

  function usesCompactViewport(): boolean {
    return window.matchMedia('(max-width: 760px) and (hover: none) and (pointer: coarse)').matches;
  }

  // Deadzone scroll: only nudge when the active cell is actually clipped by the
  // keyboard (or scrolled too high), and only far enough to sit back inside a
  // comfortable band. A fixed-center target here oscillated on real phones —
  // every scroll re-fired visualViewport events and toggled the URL bar.
  function centerFocusedCellInViewport(): void {
    if (!usesCompactViewport()) {
      return;
    }
    const input = document.activeElement as HTMLInputElement | null;
    if (!input?.classList.contains('g1-conj-input')) {
      return;
    }
    const target = input.closest('.g1-column-row') || input;
    const rect = target.getBoundingClientRect();
    const viewport = window.visualViewport;
    const visibleTop = viewport?.offsetTop ?? 0;
    const visibleHeight = viewport?.height ?? window.innerHeight;
    const padTop = 40;   // the verb hero above the cell is short; keep a little headroom
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
    if (mobileCenterFrame !== null) {
      cancelAnimationFrame(mobileCenterFrame);
    }
    mobileCenterFrame = requestAnimationFrame(() => {
      mobileCenterFrame = null;
      centerFocusedCellInViewport();
    });
  }

  // Re-apply the setup saved on the last session start (server-side), so a
  // recurring drill — e.g. "only past tenses in EN" — needs no reconfiguring.
  function applySavedSetup(saved: ConjugationTrainerSetup | undefined | null): void {
    if (!state || state.session || !saved) {
      return;
    }
    const savedLanguage = state.languages.find((entry) => entry.code === saved.language && entry.available);
    if (savedLanguage) {
      language = savedLanguage.code;
    }
    if (saved.level && (saved.level === 'custom' || LEVELS.some((item) => item.value === saved.level))) {
      level = saved.level;
    }
    if (saved.fill_level && ['easy', 'medium', 'hard'].includes(saved.fill_level)) {
      fillLevel = saved.fill_level;
    }
    if (saved.length && LENGTH_OPTIONS.includes(saved.length)) {
      length = saved.length;
    }
    if (level === 'custom' && Array.isArray(saved.selected_tenses)) {
      const available = new Set(currentLanguage()?.available_tenses || []);
      const restored = saved.selected_tenses.filter((tense) => available.has(tense));
      if (restored.length) {
        selectedTenses = restored;
        return;
      }
      level = 'easy'; // saved tenses no longer exist — fall back to Core
    }
    syncSelection();
  }

  async function load(): Promise<void> {
    loading = true;
    error = '';
    try {
      const [stateResult, settingsResult] = await Promise.all([
        api.conjugationState(),
        api.getSettings().catch(() => null),
      ]);
      state = stateResult;
      // Stage Clear belongs only to the immediate final-submit response. A
      // fresh visit always recovers to setup when no session is active.
      justFinished = false;
      showSetupAfterFinish = false;
      syncControlsFromState(state, true);
      applySavedSetup(settingsResult?.trainer_setups?.conjugation);
      answers = {};
      emptyEnterGuardUntil = 0;
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
    syncFullscreen();
    document.addEventListener('fullscreenchange', syncFullscreen);
    // Only 'resize' (keyboard open/close) — reacting to 'scroll' created a
    // scroll→scroll feedback loop that bounced the page between two positions.
    window.visualViewport?.addEventListener('resize', scheduleMobileViewportCenter);
    return () => {
      if (escTimer) {
        clearTimeout(escTimer);
      }
      if (mobileCenterFrame !== null) {
        cancelAnimationFrame(mobileCenterFrame);
      }
      clearQuickShotTimers();
      clearAutoAdvance();
      document.removeEventListener('fullscreenchange', syncFullscreen);
      window.visualViewport?.removeEventListener('resize', scheduleMobileViewportCenter);
      onSessionActiveChange(false);
    };
  });

  function focusCellByKey(key: string, caretAtEnd = false): void {
    activeCellKey = key;
    quickShotExplanationOpen = false;
    const input = document.getElementById(cellDomId(key)) as HTMLInputElement | null;
    if (!input) {
      return;
    }
    const compact = usesCompactViewport();
    input.focus({ preventScroll: compact });
    if (caretAtEnd) {
      const end = input.value.length;
      input.setSelectionRange(end, end);
    }
    if (compact) {
      scheduleMobileViewportCenter();
      void tick().then(() => {
        const current = document.getElementById(cellDomId(key)) as HTMLInputElement | null;
        if (current && document.activeElement !== current) {
          current.focus({ preventScroll: true });
        }
        if (caretAtEnd && current) {
          const end = current.value.length;
          current.setSelectionRange(end, end);
        }
        scheduleMobileViewportCenter();
      });
    }
  }

  function focusFirstInput(): void {
    const [firstCell] = currentInputCells;
    if (firstCell) {
      focusCellByKey(firstCell.key);
    }
  }

  async function focusPrimaryControl(): Promise<void> {
    await tick();
    const compact = usesCompactViewport();
    if (showFinishedPrompt()) {
      finishedCard?.scrollIntoView({ block: 'center', behavior: compact ? 'auto' : 'smooth' });
      // Keep the keyboard up on mobile so Enter/Send replays the run.
      if (compact) kbdPrimer?.focus({ preventScroll: true });
      else retryButton?.focus();
      return;
    }
    if (tenseReview) {
      // Keep the keyboard up on mobile so Enter/Send continues to the next tense.
      if (compact) kbdPrimer?.focus({ preventScroll: true });
      else nextTenseButton?.focus();
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

  function normalizeQuickShotAnswer(value: string): string {
    return value
      .trim()
      .toLowerCase()
      .normalize('NFD')
      .replace(/\p{M}/gu, '')
      .replaceAll('œ', 'oe')
      .replaceAll('æ', 'ae');
  }

  function spendQuickShot(key: string): void {
    quickShotSpent = new Set([...quickShotSpent, key]);
  }

  function armQuickShotGuard(): void {
    quickShotGuarding = true;
    if (quickShotGuardTimer) {
      clearTimeout(quickShotGuardTimer);
    }
    quickShotGuardTimer = setTimeout(() => {
      quickShotGuarding = false;
      quickShotGuardTimer = null;
    }, 600);
  }

  function animateQuickShotAccepted(): void {
    quickShotAccepted = true;
    if (quickShotAcceptedTimer) {
      clearTimeout(quickShotAcceptedTimer);
    }
    quickShotAcceptedTimer = setTimeout(() => {
      quickShotAccepted = false;
      quickShotAcceptedTimer = null;
    }, 520);
  }

  async function advanceAfterQuickShot(key: string): Promise<void> {
    await tick();
    const cells = currentInputCells;
    const index = cells.findIndex((cell) => cell.key === key);
    if (index >= 0 && index < cells.length - 1) {
      focusCellByKey(cells[index + 1].key);
    } else if (index === cells.length - 1) {
      await checkActiveTense();
    }
    quickShotAdvanceInFlight = false;
  }

  function processQuickShot(cell: InputCell, value: string): void {
    if (quickShotComposing || quickShotAdvanceInFlight || quickShotSpent.has(cell.key)) {
      return;
    }

    const draft = normalizeQuickShotAnswer(value);
    if (!draft) {
      return;
    }
    const accepted = cell.acceptedAnswers.map(normalizeQuickShotAnswer).filter(Boolean);
    if (!accepted.length) {
      return;
    }
    if (accepted.includes(draft)) {
      quickShotExplanationOpen = false;
      quickShotAdvanceInFlight = true;
      armQuickShotGuard();
      animateQuickShotAccepted();
      void advanceAfterQuickShot(cell.key);
      return;
    }
    if (!accepted.some((answer) => answer.startsWith(draft))) {
      spendQuickShot(cell.key);
    }
  }

  function handleAnswerInput(
    event: Event,
    tense: string,
    pronoun: string,
    acceptedAnswers: string[],
  ): void {
    const value = (event.currentTarget as HTMLInputElement).value;
    const cell = { key: cellKey(tense, pronoun), tense, pronoun, acceptedAnswers };
    setAnswer(tense, pronoun, value);
    processQuickShot(cell, value);
  }

  function handleAnswerCompositionEnd(
    event: CompositionEvent,
    tense: string,
    pronoun: string,
    acceptedAnswers: string[],
  ): void {
    quickShotComposing = false;
    const value = (event.currentTarget as HTMLInputElement).value;
    const cell = { key: cellKey(tense, pronoun), tense, pronoun, acceptedAnswers };
    setAnswer(tense, pronoun, value);
    processQuickShot(cell, value);
  }

  function linkedFormValue(tense: string, linkedTo: string | undefined, fallback: string | null): string {
    return linkedTo ? answers[tense]?.[linkedTo] || fallback || '' : fallback || '';
  }

  function sharedFormLabel(groupSize: number, groupCount: number): string {
    return groupCount === 1
      ? `All ${groupSize} pronouns · type once`
      : `${groupSize} pronouns share this form`;
  }

  function formGroupIndex(representative: string | null): number {
    return Math.max(0, activeFormGroups.findIndex((group) => group.representative === representative));
  }

  function formGroupLetter(index: number): string {
    return String.fromCharCode(65 + Math.min(index, 25));
  }

  function formGroupColor(index: number): string {
    const palette = GROUP_COLORS[theme] ?? GROUP_COLORS.light;
    return palette[index % palette.length];
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
    // Runs inside the launch tap → opens the soft keyboard in-gesture; focus
    // moves to the first cell once the table mounts.
    if (usesCompactViewport()) kbdPrimer?.focus({ preventScroll: true });
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
      emptyEnterGuardUntil = 0;
      resetQuestionProgress(state);
      void api.patchSettings({
        csrf_token: csrfToken,
        last_practice_mode: 'conjugation',
        trainer_setup: {
          mode: 'conjugation',
          setup: { language, level, fill_level: fillLevel, length, selected_tenses: selectedTenses },
        },
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

  function currentStudyKey(): string {
    return `${language}:${selectedTenses.join('|')}`;
  }

  async function loadStudyPool(): Promise<void> {
    if (studyLoading) return;
    studyLoading = true;
    studyError = '';
    const key = currentStudyKey();
    try {
      const response = await api.studyPool({ mode: 'conjugation', language, tenses: selectedTenses });
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
    if (studyExpanded && loadedStudyKey !== currentStudyKey()) {
      void loadStudyPool();
    }
  }

  $: if (studyExpanded && loadedStudyKey && loadedStudyKey !== currentStudyKey() && !studyLoading) {
    void loadStudyPool();
  }

  async function submit(protectNextEmptyAnswer = false): Promise<void> {
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
      if (protectNextEmptyAnswer && state?.session && state?.question) {
        armEmptyEnterGuard();
      } else {
        emptyEnterGuardUntil = 0;
      }
      if (state.feedback) {
        notify(state.feedback, state.result?.accuracy === 100 ? 'success' : 'info');
      }
      const rewardState = state.result?.gamification;
      applyReward(rewardState);
      celebrateReward(rewardState);
      // Run over: surface any level-up buffered during play as a toast on the
      // results screen — never mid-run, where it would eat the next Enter.
      if (justFinished) releaseCelebrations();
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
    // Transfer focus to the primer now, while the answer cell is still mounted
    // and the keyboard is open, so the soft keyboard survives into the review.
    if (usesCompactViewport()) kbdPrimer?.focus({ preventScroll: true });
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
      } else {
        autoAdvancing = true;
        autoAdvanceTimer = setTimeout(() => {
          autoAdvanceTimer = null;
          autoAdvancing = false;
          void continueAfterTense();
        }, AUTO_ADVANCE_MS);
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
    const protectNextEmptyAnswer = tenseReview.accuracy === 100;
    // Enter during the auto-advance window should skip the wait, not double-advance.
    clearAutoAdvance();
    if (activeTenseIndex < state.question.selected_tenses.length - 1) {
      if (protectNextEmptyAnswer) {
        armEmptyEnterGuard();
      } else {
        emptyEnterGuardUntil = 0;
      }
      activeTenseIndex += 1;
      activeCellKey = '';
      quickShotExplanationOpen = false;
      tenseReview = null;
      await focusPrimaryControl();
      return;
    }
    await submit(protectNextEmptyAnswer);
  }

  function handleCellKeydown(event: KeyboardEvent): void {
    const current = event.currentTarget as HTMLInputElement;
    const currentKey = current.dataset.cellKey;
    const cells = currentInputCells;
    const index = currentKey ? cells.findIndex((cell) => cell.key === currentKey) : -1;

    if (event.key === 'Backspace' && current.value === '' && index > 0) {
      event.preventDefault();
      event.stopPropagation();
      focusCellByKey(cells[index - 1].key, true);
      return;
    }

    if (event.key !== 'Enter' || event.isComposing || quickShotComposing) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    if (quickShotGuarding || quickShotAdvanceInFlight) {
      return;
    }
    // A flawless tense advances after one second. If the learner presses Enter
    // from muscle memory just after that transition, do not submit or skip the
    // new tense's still-empty first field.
    if (!current.value.trim() && Date.now() < emptyEnterGuardUntil) {
      return;
    }
    quickShotExplanationOpen = false;
    if (index > 0 && current.value === '') {
      const previous = cells[index - 1];
      const previousValue = answers[previous.tense]?.[previous.pronoun] || '';
      current.value = previousValue;
      setAnswer(cells[index].tense, cells[index].pronoun, previousValue);
    }
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
      releaseCelebrations();
      finishSessionWarning = false;
      answers = {};
      emptyEnterGuardUntil = 0;
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
    if (
      event.key === 'F11'
      && !event.altKey
      && !event.ctrlKey
      && !event.metaKey
      && !event.shiftKey
    ) {
      event.preventDefault();
      void toggleFullscreen();
      return;
    }

    if (loading) {
      return;
    }

    if (menuView) {
      const active = document.activeElement as HTMLElement | null;
      const isTyping = ['INPUT', 'TEXTAREA', 'SELECT'].includes(active?.tagName || '') || active?.isContentEditable;
      const digitKey = event.code.startsWith('Digit') ? event.code.slice(-1) : event.key;

      if (!isTyping && event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey && ['1', '2', '3', '4'].includes(digitKey)) {
        event.preventDefault();
        chooseLevel(digitKey === '4' ? 'custom' : LEVELS[Number(digitKey) - 1].value);
        return;
      }

      if (!isTyping && !event.altKey && event.shiftKey && event.ctrlKey && !event.metaKey && /^[0-9]$/.test(digitKey)) {
        const tenseIndex = digitKey === '0' ? 9 : Number(digitKey) - 1;
        const tense = currentLanguage()?.available_tenses[tenseIndex];
        if (tense) {
          event.preventDefault();
          toggleTense(tense);
          return;
        }
      }

      if (!isTyping && event.shiftKey && !event.altKey && !event.ctrlKey && !event.metaKey && ['1', '2', '3'].includes(digitKey)) {
        event.preventDefault();
        fillLevel = (['hard', 'medium', 'easy'] as const)[Number(digitKey) - 1];
        return;
      }

      if (!isTyping && !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
        const languageCode = Object.keys(LANGUAGE_SHORTCUTS).find(
          (code) => LANGUAGE_SHORTCUTS[code].toLowerCase() === event.key.toLowerCase(),
        );
        if (languageCode) {
          event.preventDefault();
          chooseLanguage(languageCode);
          return;
        }

        const lengthIndex = ['1', '2', '3'].indexOf(digitKey);
        if (lengthIndex >= 0) {
          event.preventDefault();
          length = LENGTH_OPTIONS[lengthIndex];
          return;
        }
      }
    }

    if (
      isFullscreen
      && event.code === 'Space'
      && event.ctrlKey
      && !event.altKey
      && !event.metaKey
      && !event.shiftKey
    ) {
      if (sessionActive) {
        event.preventDefault();
        handleFinishClick();
        return;
      }
      if (sessionDone) {
        event.preventDefault();
        revealSetup();
        return;
      }
    }

    const plainKey = !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey;
    if (!plainKey) {
      return;
    }

    if (event.key === 'Escape' && isFullscreen) {
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
  <!-- Off-screen primer keeps the mobile keyboard up across the review / stage
       clear so Enter/Send can continue or replay without re-tapping. -->
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
      {#if error}
        <div class="feedback-banner error-banner">{error}</div>
      {:else if state.feedback && !state.feedback.startsWith('Score:') && !sessionActive && !sessionDone}
        <div class="feedback-banner info-banner">{state.feedback}</div>
      {/if}

      {#if sessionDone}
        <article bind:this={finishedCard} class="glass-panel strong-panel table-clear-card" in:fade={{ duration: 180 }}>
          <p class="eyebrow">Table run complete</p>
          <StageClearRank
            score={state.result?.session_score ?? 0}
            ok={Math.round((state.result?.session_length ?? length) * ((state.result?.session_score ?? 0) / 100))}
            total={state.result?.session_length ?? length}
            bestCombo={state.result?.best_combo ?? 0}
            unitLabel="verbs"
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
            <div class="table-setup-side">
              <button
                class="table-fs-toggle"
                type="button"
                aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
                title={isFullscreen ? 'Exit fullscreen (F11)' : 'Fullscreen (F11)'}
                on:click={() => void toggleFullscreen()}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  {#if isFullscreen}
                    <path d="M8 3v3a2 2 0 0 1-2 2H3M21 8h-3a2 2 0 0 1-2-2V3M3 16h3a2 2 0 0 1 2 2v3M16 21v-3a2 2 0 0 1 2-2h3" />
                  {:else}
                    <path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3" />
                  {/if}
                </svg>
                <kbd class="kbd-chip">F11</kbd>
              </button>
              <p class="section-copy">Enter moves down each pronoun, then crosses to the next tense.</p>
            </div>
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
                  <span class="language-card-tools"><kbd class="setup-keycap">{LANGUAGE_SHORTCUTS[item.code]}</kbd><span class="language-check" aria-hidden="true">{language === item.code ? '✓' : ''}</span></span>
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
                    <strong>L{tierIndex + 1}</strong><kbd class="setup-keycap">Alt+{tierIndex + 1}</kbd>
                  </button>
                  <div class="stair-copy"><strong>{item.label}</strong><small>{item.note}</small></div>
                  <div class="stair-tense-row">
                    {#each tierTenses as tense}
                      <button class:tense-on={selectedTenses.includes(tense)} type="button" aria-pressed={selectedTenses.includes(tense)} on:click={() => toggleTense(tense)}>{#if selectedTenses.includes(tense)}<i class="tense-check" aria-hidden="true">✓</i>{/if}<span>{tense}</span></button>
                    {/each}
                  </div>
                </div>
              {/each}
              <button class:custom-on={level === 'custom'} class="custom-route" type="button" on:click={() => chooseLevel('custom')}>
                <span class="custom-spark" aria-hidden="true">✦</span>
                <span><strong>Custom route</strong><small>Touch any tense to rewrite the staircase</small></span>
                <kbd class="setup-keycap custom-key">Alt+4</kbd>
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
                {#each LENGTH_OPTIONS as option, optionIndex}
                  <button class:length-card-on={length === option} class="length-card" type="button" aria-pressed={length === option} on:click={() => (length = option)}>
                    <kbd class="setup-keycap">{optionIndex + 1}</kbd><strong>{option}</strong><span>verbs</span>
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
                <button class:support-on={fillLevel === 'easy'} type="button" on:click={() => (fillLevel = 'easy')}><kbd class="setup-keycap">{FILL_LEVEL_SHORTCUTS.easy}</kbd><strong>Guided</strong><small>≈ 70%</small></button>
                <button class:support-on={fillLevel === 'medium'} type="button" on:click={() => (fillLevel = 'medium')}><kbd class="setup-keycap">{FILL_LEVEL_SHORTCUTS.medium}</kbd><strong>Hints</strong><small>1 / tense</small></button>
                <button class:support-on={fillLevel === 'hard'} type="button" on:click={() => (fillLevel = 'hard')}><kbd class="setup-keycap">{FILL_LEVEL_SHORTCUTS.hard}</kbd><strong>Blank</strong><small>0%</small></button>
              </div>
            </div>
          </div>

          <StudyPoolBlock
            mode="conjugation"
            expanded={studyExpanded}
            loading={studyLoading}
            error={studyError}
            entries={studyEntries}
            onToggle={toggleStudyPool}
          />

          <div class="setup-launch-row">
            <div class="launch-summary">
              <span>{activeLanguage?.name || language}</span>
              <strong>{selectedTenses.length} {selectedTenses.length === 1 ? 'tense' : 'tenses'} × {length} verbs</strong>
            </div>
            <button class="primary-button table-launch-button" type="button" on:click={startSession} disabled={loading || !canStart()}>
              Start table run <kbd class="setup-keycap setup-keycap-launch">Enter</kbd><span aria-hidden="true">→</span>
            </button>
          </div>

          <div class="setup-shortcut-footer" aria-label="Table setup shortcuts">
            <span><kbd>E/S/F/R</kbd> language</span>
            <span><kbd>Alt+1…4</kbd> tense route</span>
            <span><kbd>1/2/3</kbd> run size</span>
            {#if shortcutsExpanded}
              <span><kbd>Ctrl+Shift+1…0</kbd> individual tenses</span>
              <span><kbd>Shift+1…3</kbd> support</span>
              <span><kbd>Enter</kbd> start</span>
            {/if}
            <button class="shortcut-footer-toggle" type="button" aria-expanded={shortcutsExpanded} on:click={() => (shortcutsExpanded = !shortcutsExpanded)}>
              {shortcutsExpanded ? 'Fewer shortcuts' : 'All shortcuts…'}
            </button>
          </div>
        </article>
      {:else if state.question && state.session}
        {#key `${state.question.verb_id}:${state.session.progress_current}`}
          <article class="glass-panel strong-panel trainer-card g1-production-card">
            <div class="progress-shell">
              <div class="progress-top">
                <span>Verb progress</span>
                <div class="g1-progress-end">
                  <strong>{state.session.progress_current}/{state.session.progress_total}</strong>
                  <button
                    class="table-fs-toggle table-fs-toggle-game"
                    type="button"
                    aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
                    title={isFullscreen ? 'Exit fullscreen (F11)' : 'Fullscreen (F11)'}
                    on:click={() => void toggleFullscreen()}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      {#if isFullscreen}
                        <path d="M8 3v3a2 2 0 0 1-2 2H3M21 8h-3a2 2 0 0 1-2-2V3M3 16h3a2 2 0 0 1 2 2v3M16 21v-3a2 2 0 0 1 2-2h3" />
                      {:else}
                        <path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3" />
                      {/if}
                    </svg>
                    <kbd class="kbd-chip">F11</kbd>
                  </button>
                </div>
              </div>
              <div class="progress-track"><span class="progress-bar" style={`width: ${progressPercent()}%`}></span></div>
            </div>

            <div class="g1-session-frame">
              <!-- H1-B1 (chosen in /playground2): named segment strip + one
                   big active-tense marquee instead of three shrunken cards -->
              <div class="g1-strip-block">
                <!-- Desktop shows the tense once: as the big active segment in the
                     strip below. The marquee name only surfaces on mobile, where
                     the strip itself is hidden. -->
                <div class="g1-strip-head">
                  <strong class="g1-strip-name">{activeTense}</strong>
                </div>
                <div
                  class="g1-name-strip"
                  class:g1-strip-many={state.question.selected_tenses.length > 5}
                  role="img"
                  aria-label={`Tense ${Math.min(activeTenseIndex + 1, state.question.selected_tenses.length)} of ${state.question.selected_tenses.length}: ${activeTense}`}
                >
                  {#each state.question.selected_tenses as tense, tenseIndex}
                    {@const score = tenseScores[tense]}
                    <span
                      class="g1-seg"
                      class:g1-seg-done={checkedTenses.has(tense) && tenseIndex !== activeTenseIndex}
                      class:g1-seg-active={tenseIndex === activeTenseIndex}
                      title={score ? `${tense} — ${score.correct}/${score.total} correct` : tense}
                    >{tense}</span>
                  {/each}
                </div>
              </div>

              <div class="g1-hero">
                {#if !tenseReview}
                  <span class="g1-hero-tense" aria-hidden="true">{Math.min(activeTenseIndex + 1, state.question.selected_tenses.length)}/{state.question.selected_tenses.length} tense</span>
                {/if}
                {#if !tenseReview && currentInputCells.length > 1}
                  <span class="g1-hero-count" aria-hidden="true">{activeInputIndex + 1}/{currentInputCells.length}</span>
                {/if}
                <span>Current verb</span>
                <strong>{state.question.verb}</strong>
                {#if tenseReview}
                  <em class="g1-hero-review">{tenseReview.correct}/{tenseReview.total} correct · all feedback shown</em>
                {:else}
                  <em><b>{currentActiveCell?.pronoun || state.question.pronouns[0]}</b> + {state.question.verb}</em>
                {/if}
              </div>

              <div class:g1-column-review={tenseReview} class:g1-layout-u1={uniformFormLayout} class:g1-layout-c1={clusteredFormLayout} class="g1-active-column">
                <div class="g1-column-head">
                  <div><span>{tenseReview ? 'TENSE FEEDBACK' : 'ACTIVE TENSE'} {Math.min(activeTenseIndex + 1, state.question.selected_tenses.length)}/{state.question.selected_tenses.length}</span></div>
                  <div><strong>{tenseReview ? `${tenseReview.correct}/${tenseReview.total} correct` : `${currentInputCells.length} unique ${currentInputCells.length === 1 ? 'answer' : 'answers'}`}</strong><small>{tenseReview ? 'all feedback shown' : uniformFormLayout ? 'one form · type once for the whole tense' : clusteredFormLayout ? 'color-linked form groups' : 'fill top to bottom'}</small></div>
                </div>

                {#if uniformFormLayout}
                  <div class="u1-form-notice">
                    <span>TYPE ONCE</span>
                    <div><strong>One form completes all {activeFormGroups[0].pronouns.length} pronouns.</strong><small>The first row is graded; every linked row mirrors it live.</small></div>
                    <em>1 GRADED ANSWER</em>
                  </div>
                {:else if clusteredFormLayout}
                  <div class="c1-form-key" aria-label="Pronoun form groups">
                    {#each activeFormGroups as group, groupIndex}
                      <span style={`--group-color: ${formGroupColor(groupIndex)}`}><i>{formGroupLetter(groupIndex)}</i><strong>{group.pronouns.join(' · ')}</strong></span>
                    {/each}
                    <small>{activeFormGroups.length} distinct forms · {state.question.pronouns.length} pronouns</small>
                  </div>
                {/if}

                <div class="g1-column-rows">
                  <span class:g1-column-rail-uniform={uniformFormLayout} class:g1-column-rail-hidden={clusteredFormLayout} class="g1-column-rail" aria-hidden="true"><i style={`height: ${tenseReview ? 100 : ((Math.max(0, currentInputCells.findIndex((cell) => cell.key === currentActiveCell?.key)) + 1) / Math.max(1, currentInputCells.length)) * 100}%`}></i></span>
                  {#each state.question.rows as row, rowIndex (row.pronoun)}
                    {@const cell = row.cells.find((entry) => entry.tense === activeTense)}
                    {@const feedbackCell = tenseReview?.cells.find((entry) => entry.pronoun === row.pronoun)}
                    {#if cell}
                      {@const groupIndex = formGroupIndex(cell.representative)}
                      <div
                        class:g1-row-active={!tenseReview && currentActiveCell?.tense === cell.tense && currentActiveCell?.pronoun === row.pronoun}
                        class:g1-row-guide={cell.kind === 'prefilled'}
                        class:g1-row-linked={cell.kind === 'linked'}
                        class:g1-row-representative={cell.kind === 'input' && cell.group_size > 1}
                        class:g1-row-clustered={clusteredFormLayout && cell.kind !== 'missing'}
                        class:g1-row-correct={(feedbackCell?.kind === 'answer' || feedbackCell?.kind === 'linked') && feedbackCell.correct === true}
                        class:g1-row-wrong={(feedbackCell?.kind === 'answer' || feedbackCell?.kind === 'linked') && feedbackCell.correct === false}
                        class="g1-column-row"
                        style={`--row-index: ${rowIndex}; --group-color: ${formGroupColor(groupIndex)}`}
                      >
                        <span class="g1-row-marker" aria-hidden="true">{feedbackCell?.kind === 'answer' || feedbackCell?.kind === 'linked' ? feedbackCell.correct ? '✓' : '×' : clusteredFormLayout && cell.kind !== 'missing' ? formGroupLetter(groupIndex) : cell.kind === 'prefilled' ? '◆' : cell.kind === 'linked' ? '=' : cell.kind === 'missing' ? '–' : currentActiveCell?.tense === cell.tense && currentActiveCell?.pronoun === row.pronoun ? '▶' : Boolean(answers[cell.tense]?.[row.pronoun]?.trim()) ? '✓' : '·'}</span>
                        <label for={!tenseReview && cell.kind === 'input' ? cellDomId(cellKey(cell.tense, row.pronoun)) : undefined}><small>{String(rowIndex + 1).padStart(2, '0')}</small><strong>{row.pronoun}</strong></label>

                        {#if cell.kind === 'missing'}
                          <div class="g1-missing-form">Not used in this tense</div>
                        {:else if cell.kind === 'prefilled'}
                          <div class="g1-locked-guide"><span aria-hidden="true">◆</span><strong>{cell.value}</strong><small>GIVEN GUIDE</small></div>
                        {:else if tenseReview && feedbackCell}
                          <!-- Linked cells are shown like any other answer — the
                               "same checked answer as X" note was redundant clutter. -->
                          {#if feedbackCell.correct}
                            <div class="g1-inline-feedback g1-feedback-correct"><span aria-hidden="true">✓</span><strong>{feedbackCell.answer || feedbackCell.expected}</strong><small>RIGHT</small></div>
                          {:else}
                            <div class="g1-inline-feedback g1-feedback-wrong"><span aria-hidden="true">×</span><div><del>{feedbackCell.answer || 'No answer'}</del><strong>{feedbackCell.expected}</strong></div><small>CORRECT</small></div>
                          {/if}
                        {:else if cell.kind === 'linked'}
                          <div class:g1-linked-guide={cell.prefilled} class="g1-linked-form">
                            <span aria-hidden="true">=</span>
                            <div>
                              <strong class:g1-linked-empty={!linkedFormValue(cell.tense, cell.linked_to, cell.value)}>{linkedFormValue(cell.tense, cell.linked_to, cell.value) || 'Same answer'}</strong>
                              <small>same as {cell.linked_to}</small>
                            </div>
                            <em>{cell.group_count === 1 ? 'ONE FORM · WHOLE TENSE' : 'LOCKED · SHARED FORM'}</em>
                          </div>
                        {:else}
                          <div class="g1-input-shell">
                            {#if cell.group_size > 1 || clusteredFormLayout}
                              <small class="g1-group-badge">{clusteredFormLayout ? `Group ${formGroupLetter(groupIndex)} · ${cell.group_size} ${cell.group_size === 1 ? 'pronoun' : 'pronouns'}` : sharedFormLabel(cell.group_size, cell.group_count)}</small>
                            {/if}
                            <div
                              class:g1-input-control-active={currentActiveCell?.tense === cell.tense && currentActiveCell?.pronoun === row.pronoun}
                              class="g1-input-control"
                            >
                              <input
                                id={cellDomId(cellKey(cell.tense, row.pronoun))}
                                class="g1-conj-input"
                                type="text"
                                data-cell-key={cellKey(cell.tense, row.pronoun)}
                                value={answers[cell.tense]?.[row.pronoun] || ''}
                                tabindex={currentActiveCell?.tense === cell.tense && currentActiveCell?.pronoun === row.pronoun ? 0 : -1}
                                disabled={loading}
                                inputmode="text"
                                enterkeyhint={currentInputCells[currentInputCells.length - 1]?.key === cellKey(cell.tense, row.pronoun) ? 'done' : 'next'}
                                on:focus={() => {
                                  activeCellKey = cellKey(cell.tense, row.pronoun);
                                  quickShotExplanationOpen = false;
                                }}
                                on:input={(event) => handleAnswerInput(event, cell.tense, row.pronoun, cell.accepted_answers || [])}
                                on:compositionstart={() => (quickShotComposing = true)}
                                on:compositionend={(event) => handleAnswerCompositionEnd(event, cell.tense, row.pronoun, cell.accepted_answers || [])}
                                on:keydown={handleCellKeydown}
                                autocomplete="off"
                                autocapitalize="off"
                                spellcheck="false"
                                placeholder=""
                              />
                              {#if currentActiveCell?.tense === cell.tense && currentActiveCell?.pronoun === row.pronoun}
                                <QuickShotIcon
                                  ready={quickShotReady}
                                  guarding={quickShotGuarding}
                                  accepted={quickShotAccepted}
                                  explanationOpen={quickShotExplanationOpen}
                                  controls={`quick-shot-note-${cellKey(cell.tense, row.pronoun)}`}
                                  onToggle={() => (quickShotExplanationOpen = !quickShotExplanationOpen)}
                                />
                              {/if}
                            </div>
                            {#if quickShotExplanationOpen && currentActiveCell?.tense === cell.tense && currentActiveCell?.pronoun === row.pronoun}
                              <div class="g1-quick-shot-note" id={`quick-shot-note-${cellKey(cell.tense, row.pronoun)}`} role="note">
                                <span>{quickShotReady ? 'QUICK-SHOT ARMED' : 'QUICK-SHOT SPENT'}</span>
                                <strong>{quickShotReady ? 'A perfect first attempt advances instantly.' : 'This answer now waits for Enter.'}</strong>
                                <p>{quickShotReady ? 'One impossible letter spends the charge for this cell.' : 'Correct it normally. The next cell starts fully charged.'}</p>
                              </div>
                            {/if}
                          </div>
                        {/if}
                      </div>
                    {/if}
                  {/each}
                </div>
              </div>

              <div class="g1-utility-line">
                {#if tenseReview}
                  {#if autoAdvancing}
                    <span class="auto-adv-note">clean sweep · advancing</span><i aria-hidden="true"></i><span><b>Enter</b> skip ahead</span>
                  {:else}
                    <span><b>Enter</b> continue</span>
                  {/if}
                {:else}
                  <span><b>Enter</b> next · empty repeats · last row checks</span><i aria-hidden="true"></i><span><b>Backspace</b> back</span>
                {/if}
                <i aria-hidden="true"></i>
                <span><b>{isFullscreen ? 'Ctrl+Space ×2' : 'Esc ×2'}</b> finish</span>
              </div>
            </div>

            <div class="trainer-actions g1-actions">
              {#if tenseReview}
                <button bind:this={nextTenseButton} class="primary-button g1-shortcut-action" class:auto-adv-pending={autoAdvancing} type="button" on:click={() => void continueAfterTense()} disabled={loading}>
                  {activeTenseIndex < state.question.selected_tenses.length - 1 ? `Next: ${state.question.selected_tenses[activeTenseIndex + 1]}` : 'Finish verb'} <span class="kbd-chip">Enter</span>
                </button>
              {:else}
                <button class="primary-button g1-shortcut-action" type="button" on:click={checkActiveTense} disabled={loading}><span class="kbd-chip">Enter</span> Check {activeTense}</button>
              {/if}
              <button bind:this={finishButton} class:finish-warn={finishSessionWarning} class="ghost-button g1-shortcut-action" type="button" on:click={handleFinishClick} disabled={loading}>
                <span class="kbd-chip" class:kbd-chip-armed={finishSessionWarning}>{isFullscreen ? (finishSessionWarning ? 'Ctrl+Space ×1' : 'Ctrl+Space ×2') : (finishSessionWarning ? 'Esc ×1' : 'Esc ×2')}</span> {finishSessionWarning ? 'again to finish' : 'finish run'}
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
    font-size: clamp(1.4rem, 3vw, 2rem);
    line-height: 1.15;
    letter-spacing: -0.035em;
  }

  .table-setup-side {
    display: grid;
    justify-items: end;
    gap: 0.55rem;
  }

  .table-setup-side .section-copy {
    max-width: 16rem;
    margin: 0;
    font-size: 0.86rem;
    text-align: right;
  }

  .table-fs-toggle {
    display: inline-flex;
    min-height: 2.35rem;
    align-items: center;
    justify-content: center;
    gap: 0.45rem;
    padding: 0.45rem 0.62rem;
    border: 1px solid var(--line-strong);
    border-radius: 10px;
    color: var(--muted);
    background: color-mix(in srgb, var(--surface-strong) 78%, transparent);
    transition: border-color 150ms ease, color 150ms ease, transform 150ms ease;
  }

  .table-fs-toggle:hover {
    border-color: color-mix(in srgb, var(--accent) 62%, var(--line));
    color: var(--accent-strong);
    transform: translateY(-1px);
  }

  .table-fs-toggle svg {
    width: 1.05rem;
    height: 1.05rem;
  }

  .table-fs-toggle .kbd-chip {
    font-size: 0.62rem;
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
    font-size: 1.05rem;
    letter-spacing: 0.01em;
  }

  .setup-step-head small,
  .language-card small {
    color: var(--muted);
    font-size: 0.8rem;
  }

  .step-number {
    display: grid;
    place-items: center;
    width: 2.1rem;
    height: 2.1rem;
    flex: 0 0 auto;
    border: 1px solid color-mix(in srgb, var(--accent) 38%, var(--line));
    border-radius: 10px;
    color: var(--accent-strong);
    background: color-mix(in srgb, var(--accent-soft) 140%, transparent);
    font: 700 0.78rem/1 var(--mono);
  }

  .language-card-grid {
    display: grid;
    /* 2×2 at trainer width — full language names beat a cramped 4-up row */
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
    width: 2.4rem;
    height: 2.4rem;
    border-radius: 12px;
    color: var(--accent-strong);
    background: var(--accent-soft);
    font: 800 0.85rem/1 var(--mono);
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
    font-size: 1rem;
  }

  .language-card-copy small {
    font-size: 0.8rem;
  }

  .language-card-tools {
    display: grid;
    justify-items: end;
    gap: 0.3rem;
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
    left: 1.95rem;
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
    width: 3rem;
    min-height: 3rem;
    gap: 0.26rem;
    place-items: center;
    padding: 0.35rem;
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
    font: 800 0.85rem/1 var(--mono);
  }

  .stair-level .setup-keycap,
  .custom-key {
    color: var(--muted);
    font: 700 0.68rem/1 var(--mono);
    white-space: nowrap;
  }

  .stair-copy {
    display: grid;
    align-content: center;
    gap: 0.15rem;
    min-width: 0;
  }

  .stair-copy strong {
    font-size: 1.02rem;
  }

  .stair-copy small {
    color: var(--muted);
    font-size: 0.82rem;
    line-height: 1.35;
  }

  .stair-tense-row {
    display: flex;
    min-width: 0;
    flex-wrap: wrap;
    gap: 0.4rem;
    align-content: center;
  }

  .stair-tense-row button {
    display: inline-flex;
    gap: 0.4rem;
    align-items: center;
    min-height: 2.75rem;
    padding: 0.6rem 0.85rem;
    border: 1px solid var(--line);
    border-radius: 10px;
    color: var(--muted);
    background: color-mix(in srgb, var(--surface-strong) 74%, transparent);
    font-size: 0.95rem;
    font-weight: 500;
    transition: border-color 160ms ease, background 160ms ease, color 160ms ease;
  }

  @media (hover: hover) {
    .stair-tense-row button:hover {
      border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
      color: var(--text);
    }
  }

  .stair-tense-row button.tense-on {
    border-color: color-mix(in srgb, var(--accent) 68%, var(--line));
    color: var(--text);
    background: var(--accent-soft);
    font-weight: 600;
  }

  .tense-check {
    color: var(--accent-strong);
    font-style: normal;
    font-weight: 800;
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
    font-size: 0.95rem;
  }

  .custom-route small {
    font-size: 0.78rem;
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
    gap: 0.16rem;
    min-height: 4.25rem;
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
    font-size: 0.8rem;
  }

  .length-card-on,
  .support-row .support-on {
    border-color: color-mix(in srgb, var(--accent) 58%, var(--line));
    color: var(--accent-strong);
    background: var(--accent-soft);
  }

  .support-row strong {
    font-size: 0.9rem;
  }

  .setup-keycap,
  .setup-shortcut-footer kbd {
    display: inline-grid;
    width: fit-content;
    place-items: center;
    padding: 0.24rem 0.42rem;
    border: 1px solid var(--line-strong);
    border-radius: 6px;
    color: color-mix(in srgb, var(--accent-strong) 55%, var(--muted));
    background: color-mix(in srgb, var(--surface-strong) 82%, transparent);
    font: 750 0.68rem/1 var(--mono);
    white-space: nowrap;
  }

  :global(html[data-theme='arcade']) .setup-keycap,
  :global(html[data-theme='arcade']) .setup-shortcut-footer kbd {
    font-size: 1.05rem;
  }

  /* Keycap hints are desktop affordances — free the space on touch */
  @media (pointer: coarse) {
    .setup-keycap {
      display: none;
    }
  }

  .language-card-on .setup-keycap,
  .stair-on .setup-keycap,
  .custom-on .setup-keycap,
  .length-card-on .setup-keycap,
  .support-on .setup-keycap {
    border-color: color-mix(in srgb, var(--accent) 48%, var(--line));
    color: var(--accent-strong);
  }

  .setup-keycap-launch {
    border-color: currentColor;
    color: inherit;
    background: color-mix(in srgb, currentColor 10%, transparent);
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
    font: 700 0.78rem/1.4 var(--mono);
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  :global(html[data-theme='arcade']) .launch-summary > span {
    font-size: 1.05rem;
  }

  .table-launch-button {
    flex: 0 0 auto;
    gap: 0.65rem;
  }

  .setup-shortcut-footer {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem 1.1rem;
    align-items: center;
    justify-content: center;
    padding-top: 0.2rem;
    color: var(--muted);
    font: 600 0.78rem/1.5 var(--ui);
  }

  .setup-shortcut-footer span {
    display: inline-flex;
    gap: 0.4rem;
    align-items: center;
  }

  .shortcut-footer-toggle {
    padding: 0.3rem 0.6rem;
    border: 0;
    background: transparent;
    color: var(--accent-strong);
    font-size: 0.78rem;
    font-weight: 600;
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  /* On touch the keycaps are hidden, so the expander has nothing to reveal */
  @media (pointer: coarse) {
    .setup-shortcut-footer {
      display: none;
    }
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

  .btn-play-glyph {
    width: 0.8em;
    height: 0.8em;
    margin-right: 0.1em;
    vertical-align: -0.06em;
  }

  /* Focusable but visually hidden; font-size 16px avoids iOS focus-zoom, and it
     is not display:none/visibility:hidden so focus can hold the keyboard open. */
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

  @keyframes table-clear-in {
    from { opacity: 0; transform: translateY(1rem) scale(0.985); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }

  .g1-production-card {
    gap: 1rem;
    animation: g1-stage-in 420ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  .g1-progress-end {
    display: flex;
    align-items: center;
    gap: 0.65rem;
  }

  .table-fs-toggle-game {
    min-height: 2rem;
    padding: 0.32rem 0.48rem;
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

  .g1-column-head,
  .g1-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.8rem;
  }

  /* ===== H1-B1 strip: named segments + active-tense marquee ===== */
  .g1-strip-block {
    display: grid;
    gap: 0.45rem;
    margin-bottom: -0.6rem; /* pull the hero closer to the tense text */
  }

  /* Hidden on desktop — the enlarged active segment below is the single tense
     reference. The mobile media query re-enables this as the big title. */
  .g1-strip-head {
    display: none;
    align-items: baseline;
    justify-content: center;
    gap: 1rem;
  }

  .g1-strip-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #f6c84c;
    font: 800 1.25rem/1.1 var(--display);
    text-shadow: 0 0 16px color-mix(in srgb, #f6c84c 45%, transparent);
  }

  .g1-name-strip {
    display: flex;
    align-items: center; /* inactive segs stay compact pills beside the big active one */
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  .g1-seg {
    flex: 1 1 0;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-align: center;
    padding: 0.42rem 0.55rem;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 6px;
    color: rgba(255, 255, 255, 0.6);
    background: rgba(255, 255, 255, 0.05);
    font-size: 0.78rem;
    font-weight: 600;
    transition: border-color 160ms ease, background 160ms ease, color 160ms ease;
  }

  .g1-strip-many .g1-seg {
    flex-basis: 5.5rem;
  }

  .g1-seg-done {
    border-color: #55ee9b;
    color: #78f2ad;
    background: color-mix(in srgb, #55ee9b 14%, transparent);
    box-shadow: 0 0 8px color-mix(in srgb, #55ee9b 25%, transparent);
  }

  /* The active segment doubles as the big in-game tense reference: plain
     glowing text (no pill, no pulse) in the marquee-name gold, enlarged. */
  .g1-seg-active {
    border-color: transparent;
    color: #f6c84c;
    background: none;
    font: 800 2rem/1.05 var(--display);
    padding: 0 0.4rem;
    text-shadow: 0 0 16px color-mix(in srgb, #f6c84c 45%, transparent);
  }

  /* ===== H1-B verb hero ===== */
  .g1-hero {
    position: relative;
    display: grid;
    gap: 0.3rem;
    justify-items: center;
    padding: 1.1rem 0.8rem 1rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    text-align: center;
    background:
      linear-gradient(rgba(255, 255, 255, 0.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255, 255, 255, 0.025) 1px, transparent 1px),
      rgba(8, 13, 31, 0.54);
    background-size: 24px 24px;
  }

  .g1-hero > span {
    color: rgba(255, 255, 255, 0.66);
    font: 700 0.72rem/1 var(--mono);
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }

  .g1-hero > strong {
    max-width: 100%;
    min-width: 0;
    overflow-wrap: anywhere;
    font: 820 clamp(1.7rem, 5vw, 2.4rem)/1.05 var(--ui);
  }

  .g1-hero > em {
    color: rgba(255, 255, 255, 0.8);
    font-size: 1.05rem;
    font-style: normal;
  }

  .g1-hero > em b {
    color: #f6c84c;
    font-weight: 800;
  }

  /* Position badges for the compact mobile layout — hidden on wide screens where
     the whole tense column is visible at once. */
  .g1-hero-count,
  .g1-hero-tense {
    position: absolute;
    top: 0.55rem;
    display: none;
    color: var(--accent-2);
    font: 800 0.78rem/1 var(--mono);
    letter-spacing: 0.06em;
    font-variant-numeric: tabular-nums;
  }

  .g1-hero-count {
    right: 0.7rem;
  }

  .g1-hero-tense {
    left: 0.7rem;
    color: #f6c84c;
  }

  .g1-hero-review {
    color: #f6c84c !important;
    font-family: var(--mono);
    font-variant-numeric: tabular-nums;
  }

  /* ===== bottom utility line ===== */
  .g1-utility-line {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-wrap: wrap;
    gap: 0.7rem;
    color: rgba(255, 255, 255, 0.72);
    font-size: 0.78rem;
  }

  .g1-utility-line b {
    color: white;
    font-weight: 700;
  }

  .g1-utility-line i {
    width: 1px;
    height: 0.9rem;
    background: rgba(255, 255, 255, 0.18);
  }

  /* Auto-advance after a flawless tense: a quiet pulse marks the ~1s wait. */
  .auto-adv-note {
    color: var(--success);
    font-weight: 650;
    animation: auto-adv-breathe 1s ease-in-out infinite;
  }

  .auto-adv-pending {
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--success) 45%, transparent);
  }

  @keyframes auto-adv-breathe {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.55; }
  }

  @media (prefers-reduced-motion: reduce) {
    .auto-adv-note {
      animation: none;
    }
  }

  .g1-column-head span {
    color: var(--accent-2);
    font: 750 0.7rem/1.2 var(--mono);
    letter-spacing: 0.1em;
  }

  .g1-column-head small {
    color: rgba(255, 255, 255, 0.72);
    font-size: 0.75rem;
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
    font-size: 0.9rem;
  }

  .u1-form-notice {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 0.7rem;
    align-items: center;
    margin: 0.65rem 0.65rem 0;
    padding: 0.65rem 0.75rem;
    border: 1px solid color-mix(in srgb, #f6c84c 34%, transparent);
    border-radius: 10px;
    background: color-mix(in srgb, #f6c84c 7%, rgba(6, 8, 24, 0.48));
  }

  .u1-form-notice > span {
    color: #f6c84c;
    font: 850 0.66rem/1.2 var(--mono);
    letter-spacing: 0.08em;
  }

  .u1-form-notice > div {
    display: grid;
    min-width: 0;
    gap: 0.12rem;
  }

  .u1-form-notice strong {
    color: white;
    font-size: 0.85rem;
  }

  .u1-form-notice small {
    color: rgba(255, 255, 255, 0.7);
    font-size: 0.7rem;
  }

  .u1-form-notice em {
    color: #f6c84c;
    font: 780 0.6rem/1.2 var(--mono);
    font-style: normal;
    white-space: nowrap;
  }

  .c1-form-key {
    display: flex;
    flex-wrap: wrap;
    gap: 0.42rem;
    align-items: center;
    padding: 0.65rem 0.65rem 0;
  }

  .c1-form-key > span {
    display: inline-flex;
    min-width: 0;
    gap: 0.38rem;
    align-items: center;
    padding: 0.34rem 0.48rem;
    border: 1px solid color-mix(in srgb, var(--group-color) 52%, transparent);
    border-radius: 999px;
    color: var(--group-color);
    background: color-mix(in srgb, var(--group-color) 8%, rgba(6, 8, 24, 0.45));
  }

  .c1-form-key i {
    display: grid;
    width: 1.4rem;
    height: 1.4rem;
    place-items: center;
    border: 1px solid currentColor;
    border-radius: 50%;
    font: 850 0.6rem/1 var(--mono);
    font-style: normal;
  }

  .c1-form-key strong {
    min-width: 0;
    color: white;
    font-size: 0.78rem;
    overflow-wrap: anywhere;
  }

  .c1-form-key > small {
    margin-left: auto;
    color: rgba(255, 255, 255, 0.66);
    font: 720 0.66rem/1.2 var(--mono);
    white-space: nowrap;
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

  .g1-column-rail-uniform {
    overflow: visible;
    background: color-mix(in srgb, var(--accent-2) 22%, transparent);
    box-shadow: 0 0 10px color-mix(in srgb, var(--accent-2) 18%, transparent);
  }

  .g1-column-rail-uniform i {
    height: 100% !important;
  }

  .g1-column-rail-hidden {
    display: none;
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

  .g1-row-clustered {
    border-color: color-mix(in srgb, var(--group-color) 34%, rgba(255, 255, 255, 0.09));
    border-left-width: 3px;
    border-left-color: var(--group-color);
    background: color-mix(in srgb, var(--group-color) 5%, rgba(255, 255, 255, 0.018));
  }

  .g1-row-clustered.g1-row-active {
    border-color: var(--group-color);
    background: color-mix(in srgb, var(--group-color) 12%, rgba(255, 255, 255, 0.025));
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--group-color) 9%, transparent);
  }

  .g1-row-guide {
    border-color: color-mix(in srgb, #f6c84c 42%, transparent);
    background: color-mix(in srgb, #f6c84c 8%, rgba(255, 255, 255, 0.02));
  }

  .g1-row-linked {
    border-color: color-mix(in srgb, var(--accent-2) 24%, rgba(255, 255, 255, 0.09));
    background: color-mix(in srgb, var(--accent) 5%, rgba(255, 255, 255, 0.018));
  }

  /* U1 (one graded answer — every pronoun shares the form): the mirror rows
     only echo what's being typed, so they recede — gray and slightly out of
     focus — leaving the input row as the only sharp element in the column.
     Review mode is excluded: feedback rows must stay fully legible. */
  .g1-layout-u1:not(.g1-column-review) .g1-column-row.g1-row-linked {
    opacity: 0.45;
    filter: grayscale(0.9) blur(0.7px);
    transition: opacity 160ms ease, filter 160ms ease;
  }

  .g1-row-representative {
    border-left-color: var(--accent-2);
  }

  .g1-row-clustered.g1-row-representative {
    border-left-color: var(--group-color);
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
    width: 1rem;
    color: var(--accent-2);
    font: 800 0.7rem/1 var(--mono);
    text-align: center;
  }

  .g1-row-guide .g1-row-marker { color: #f6c84c; }
  .g1-row-linked .g1-row-marker { color: color-mix(in srgb, var(--accent-2) 75%, white); }
  .g1-row-clustered .g1-row-marker {
    display: grid;
    width: 1.45rem;
    height: 1.45rem;
    place-items: center;
    border: 1px solid var(--group-color);
    border-radius: 6px;
    color: var(--group-color);
    background: color-mix(in srgb, var(--group-color) 8%, transparent);
  }
  .g1-row-correct .g1-row-marker {
    border-color: #55ee9b;
    color: #55ee9b;
    background: color-mix(in srgb, #55ee9b 8%, transparent);
  }

  .g1-row-wrong .g1-row-marker {
    border-color: #ff7188;
    color: #ff7188;
    background: color-mix(in srgb, #ff7188 8%, transparent);
  }

  .g1-column-row label {
    display: grid;
    grid-template-columns: 1.5rem 1fr;
    gap: 0.35rem;
    align-items: center;
  }

  .g1-column-row label small {
    color: var(--accent-2);
    font: 750 0.68rem/1 var(--mono);
  }

  .g1-row-clustered label small {
    color: var(--group-color);
  }

  .g1-column-row label strong {
    color: white;
    font-size: clamp(1.02rem, 2.4vw, 1.18rem);
    font-weight: 820;
    line-height: 1.15;
  }

  .g1-input-shell {
    position: relative;
    display: grid;
    gap: 0.3rem;
    min-width: 0;
  }

  .g1-input-control {
    min-width: 0;
  }

  .g1-input-control-active {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 36px;
    gap: 0.5rem;
    align-items: center;
  }

  .g1-group-badge {
    width: fit-content;
    color: color-mix(in srgb, var(--accent-2) 78%, white);
    font: 800 0.68rem/1.2 var(--mono);
    letter-spacing: 0.07em;
    text-transform: uppercase;
  }

  .g1-row-clustered .g1-group-badge {
    color: var(--group-color);
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

  .g1-row-clustered .g1-conj-input:focus {
    border-color: var(--group-color);
    box-shadow: inset 0 -2px 0 var(--group-color);
  }

  .g1-quick-shot-note {
    display: grid;
    gap: 0.25rem;
    padding: 0.62rem 0.7rem;
    border: 1px solid color-mix(in srgb, var(--accent) 48%, transparent);
    border-radius: 8px;
    color: white;
    background: color-mix(in srgb, var(--surface-dark) 92%, black);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.26);
    animation: g1-shot-note-in 140ms ease-out both;
  }

  .g1-quick-shot-note > span {
    color: var(--accent-2);
    font: 800 0.7rem/1 var(--mono);
    letter-spacing: 0.08em;
  }

  .g1-quick-shot-note strong {
    font-size: 0.78rem;
    line-height: 1.25;
  }

  .g1-quick-shot-note p {
    margin: 0;
    color: rgba(255, 255, 255, 0.66);
    font-size: 0.7rem;
    line-height: 1.35;
  }

  @keyframes g1-shot-note-in {
    from { opacity: 0; transform: translateY(-0.2rem); }
    to { opacity: 1; transform: translateY(0); }
  }

  .g1-linked-form {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 0.6rem;
    align-items: center;
    min-width: 0;
    padding: 0.62rem 0.72rem;
    border: 1px dashed color-mix(in srgb, var(--accent-2) 32%, transparent);
    border-radius: 8px;
    color: color-mix(in srgb, var(--accent-2) 78%, white);
    background: color-mix(in srgb, var(--accent) 7%, rgba(6, 8, 24, 0.62));
  }

  .g1-linked-form > span {
    display: grid;
    width: 1.55rem;
    height: 1.55rem;
    place-items: center;
    border: 1px solid currentColor;
    border-radius: 50%;
    font: 850 0.68rem/1 var(--mono);
  }

  .g1-linked-form > div {
    display: grid;
    min-width: 0;
    gap: 0.1rem;
  }

  .g1-linked-form strong {
    min-width: 0;
    color: white;
    font-size: clamp(0.9rem, 2.2vw, 1.05rem);
    line-height: 1.15;
    overflow-wrap: anywhere;
  }

  .g1-linked-form .g1-linked-empty {
    color: rgba(255, 255, 255, 0.62);
    font-style: italic;
    font-weight: 620;
  }

  .g1-linked-form small,
  .g1-linked-form em {
    font: 780 0.6rem/1.25 var(--mono);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .g1-linked-form small {
    color: color-mix(in srgb, var(--accent-2) 68%, white);
  }

  .g1-linked-form em {
    color: rgba(255, 255, 255, 0.66);
    font-style: normal;
    text-align: right;
  }

  .g1-row-clustered .g1-linked-form:not(.g1-linked-guide):not(.g1-linked-correct):not(.g1-linked-wrong) {
    border-color: color-mix(in srgb, var(--group-color) 38%, transparent);
    color: var(--group-color);
    background: color-mix(in srgb, var(--group-color) 6%, rgba(6, 8, 24, 0.62));
  }

  .g1-row-clustered .g1-linked-form:not(.g1-linked-guide):not(.g1-linked-correct):not(.g1-linked-wrong) small {
    color: color-mix(in srgb, var(--group-color) 72%, white);
  }

  .g1-linked-guide {
    border-color: color-mix(in srgb, #f6c84c 42%, transparent);
    color: #f6c84c;
    background: color-mix(in srgb, #f6c84c 7%, rgba(6, 8, 24, 0.62));
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
    font: 800 0.62rem/1.2 var(--mono);
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
    color: rgba(255, 255, 255, 0.6);
    background: rgba(6, 8, 24, 0.42);
    font-size: 0.8rem;
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

  /* Matcha Overdrive · Bio Pulse. The production table keeps its exact grid,
     row heights, padding, and state machine; only the Clear skin changes. */
  :global(html[data-theme='light']) .g1-session-frame {
    border-color: var(--accent);
    border-radius: 28px;
    color: var(--text);
    background:
      radial-gradient(circle at 92% 0%, color-mix(in srgb, var(--accent-2) 11%, transparent), transparent 31%),
      linear-gradient(rgba(19, 40, 30, 0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(19, 40, 30, 0.04) 1px, transparent 1px),
      var(--matcha-panel);
    background-size: auto, 24px 24px, 24px 24px, auto;
    box-shadow: 0 24px 55px -34px rgba(19, 40, 30, 0.58);
  }

  :global(html[data-theme='light']) .g1-utility-line,
  :global(html[data-theme='light']) .g1-column-head small,
  :global(html[data-theme='light']) .g1-hero > span,
  :global(html[data-theme='light']) .g1-hero > em {
    color: var(--muted);
  }

  :global(html[data-theme='light']) .g1-hero > span {
    font-size: 1rem;
    font-weight: 400;
  }

  :global(html[data-theme='light']) .g1-strip-name,
  :global(html[data-theme='light']) .g1-hero > em b,
  :global(html[data-theme='light']) .g1-hero-count,
  :global(html[data-theme='light']) .g1-hero-tense,
  :global(html[data-theme='light']) .g1-hero-review {
    color: var(--accent) !important;
    text-shadow: none;
  }

  :global(html[data-theme='light']) .g1-seg {
    border-color: color-mix(in srgb, var(--accent) 28%, transparent);
    border-radius: 999px;
    color: var(--muted);
    background: color-mix(in srgb, var(--matcha-field) 44%, transparent);
  }

  :global(html[data-theme='light']) .g1-seg-done {
    border-color: color-mix(in srgb, var(--accent) 58%, transparent);
    color: var(--accent-strong);
    background: color-mix(in srgb, var(--accent) 10%, var(--matcha-panel));
    box-shadow: none;
  }

  :global(html[data-theme='light']) .g1-seg-active {
    border-color: transparent;
    color: var(--accent);
    background: none;
    box-shadow: none;
    text-shadow: none;
  }

  :global(html[data-theme='light']) .g1-hero {
    border-color: color-mix(in srgb, var(--accent) 26%, transparent);
    border-radius: 20px;
    background:
      linear-gradient(rgba(19, 40, 30, 0.045) 1px, transparent 1px),
      linear-gradient(90deg, rgba(19, 40, 30, 0.045) 1px, transparent 1px),
      color-mix(in srgb, var(--matcha-field) 38%, var(--matcha-panel));
    background-size: 24px 24px;
  }

  :global(html[data-theme='light']) .g1-hero > strong {
    color: var(--text);
    font-family: var(--display);
    letter-spacing: -0.055em;
  }

  :global(html[data-theme='light']) .g1-utility-line b,
  :global(html[data-theme='light']) .g1-column-head strong,
  :global(html[data-theme='light']) .g1-column-row label strong,
  :global(html[data-theme='light']) .u1-form-notice strong,
  :global(html[data-theme='light']) .c1-form-key strong,
  :global(html[data-theme='light']) .g1-linked-form strong,
  :global(html[data-theme='light']) .g1-locked-guide strong,
  :global(html[data-theme='light']) .g1-inline-feedback strong,
  :global(html[data-theme='light']) .g1-quick-shot-note {
    color: var(--text);
  }

  :global(html[data-theme='light']) .g1-utility-line i,
  :global(html[data-theme='light']) .g1-column-rail {
    background: color-mix(in srgb, var(--accent) 18%, transparent);
  }

  :global(html[data-theme='light']) .g1-column-head span,
  :global(html[data-theme='light']) .g1-column-row label small,
  :global(html[data-theme='light']) .g1-group-badge,
  :global(html[data-theme='light']) .g1-row-marker {
    color: var(--accent);
  }

  :global(html[data-theme='light']) .g1-active-column {
    border-color: color-mix(in srgb, var(--accent) 34%, transparent);
    border-radius: 20px;
    background: color-mix(in srgb, var(--matcha-field) 24%, transparent);
  }

  :global(html[data-theme='light']) .g1-column-review {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent-2) 12%, transparent);
  }

  :global(html[data-theme='light']) .g1-column-head {
    border-bottom-color: color-mix(in srgb, var(--accent) 22%, transparent);
    background: color-mix(in srgb, var(--matcha-field) 44%, transparent);
  }

  :global(html[data-theme='light']) .u1-form-notice {
    border-color: color-mix(in srgb, var(--accent) 38%, transparent);
    border-radius: 14px;
    background: color-mix(in srgb, var(--accent) 8%, var(--matcha-panel));
  }

  :global(html[data-theme='light']) .u1-form-notice > span,
  :global(html[data-theme='light']) .u1-form-notice em,
  :global(html[data-theme='light']) .g1-row-guide .g1-row-marker,
  :global(html[data-theme='light']) .g1-linked-guide,
  :global(html[data-theme='light']) .g1-locked-guide > span,
  :global(html[data-theme='light']) .g1-locked-guide > small {
    color: var(--accent);
  }

  :global(html[data-theme='light']) .u1-form-notice small,
  :global(html[data-theme='light']) .c1-form-key > small,
  :global(html[data-theme='light']) .g1-quick-shot-note p,
  :global(html[data-theme='light']) .g1-linked-form .g1-linked-empty,
  :global(html[data-theme='light']) .g1-linked-form em,
  :global(html[data-theme='light']) .g1-missing-form,
  :global(html[data-theme='light']) .g1-feedback-wrong del {
    color: var(--muted);
  }

  :global(html[data-theme='light']) .c1-form-key > span {
    border-color: color-mix(in srgb, var(--group-color) 50%, var(--accent));
    color: color-mix(in srgb, var(--group-color) 58%, var(--matcha-ink));
    background: color-mix(in srgb, var(--group-color) 7%, var(--matcha-panel));
  }

  :global(html[data-theme='light']) .g1-column-rail i {
    background: linear-gradient(var(--accent-2), var(--accent));
  }

  :global(html[data-theme='light']) .g1-column-row {
    border-color: color-mix(in srgb, var(--accent) 18%, transparent);
    border-radius: 14px;
    color: var(--text);
    background: color-mix(in srgb, var(--matcha-field) 25%, transparent);
  }

  :global(html[data-theme='light']) .g1-row-active {
    border-color: var(--accent);
    background: color-mix(in srgb, var(--matcha-field) 70%, transparent);
    box-shadow: inset 0 0 0 3px color-mix(in srgb, var(--accent-2) 34%, transparent);
    transform: none;
  }

  :global(html[data-theme='light']) .g1-row-clustered {
    border-color: color-mix(in srgb, var(--group-color) 48%, var(--accent));
    border-left-color: color-mix(in srgb, var(--group-color) 62%, var(--matcha-ink));
    background: color-mix(in srgb, var(--group-color) 6%, var(--matcha-panel));
  }

  :global(html[data-theme='light']) .g1-row-clustered.g1-row-active {
    border-color: color-mix(in srgb, var(--group-color) 62%, var(--matcha-ink));
    background: color-mix(in srgb, var(--group-color) 10%, var(--matcha-panel));
    box-shadow: inset 0 0 0 3px color-mix(in srgb, var(--accent-2) 34%, transparent);
  }

  :global(html[data-theme='light']) .g1-row-guide,
  :global(html[data-theme='light']) .g1-row-linked {
    border-color: color-mix(in srgb, var(--accent) 34%, transparent);
    background: color-mix(in srgb, var(--accent) 7%, var(--matcha-panel));
  }

  :global(html[data-theme='light']) .g1-row-correct {
    border-color: color-mix(in srgb, var(--success) 58%, transparent);
    background: color-mix(in srgb, var(--success) 9%, var(--matcha-panel));
  }

  :global(html[data-theme='light']) .g1-row-wrong {
    border-color: color-mix(in srgb, var(--accent-2) 76%, var(--danger));
    background: color-mix(in srgb, var(--accent-2) 10%, var(--matcha-panel));
  }

  :global(html[data-theme='light']) .g1-row-clustered .g1-row-marker {
    border-color: currentColor;
    border-radius: 50%;
    color: color-mix(in srgb, var(--group-color) 60%, var(--matcha-ink));
    background: color-mix(in srgb, var(--group-color) 8%, var(--matcha-panel));
  }

  :global(html[data-theme='light']) .g1-row-correct .g1-row-marker {
    border-color: var(--success);
    color: var(--success);
    background: color-mix(in srgb, var(--success) 8%, var(--matcha-panel));
  }

  :global(html[data-theme='light']) .g1-row-wrong .g1-row-marker {
    border-color: var(--danger);
    color: var(--danger);
    background: color-mix(in srgb, var(--accent-2) 10%, var(--matcha-panel));
  }

  :global(html[data-theme='light']) .g1-conj-input {
    border-color: color-mix(in srgb, var(--accent) 42%, transparent);
    border-radius: 14px;
    color: var(--text);
    background: var(--matcha-panel);
  }

  :global(html[data-theme='light']) .g1-conj-input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent-2) 28%, transparent);
  }

  :global(html[data-theme='light']) .g1-row-clustered .g1-conj-input:focus {
    border-color: color-mix(in srgb, var(--group-color) 58%, var(--matcha-ink));
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent-2) 28%, transparent);
  }

  :global(html[data-theme='light']) .g1-quick-shot-note,
  :global(html[data-theme='light']) .g1-linked-form,
  :global(html[data-theme='light']) .g1-locked-guide,
  :global(html[data-theme='light']) .g1-inline-feedback,
  :global(html[data-theme='light']) .g1-missing-form {
    border-radius: 14px;
  }

  :global(html[data-theme='light']) .g1-quick-shot-note {
    border-color: color-mix(in srgb, var(--accent) 42%, transparent);
    background: var(--matcha-panel);
    box-shadow: 0 10px 24px -18px rgba(19, 40, 30, 0.48);
  }

  :global(html[data-theme='light']) .g1-quick-shot-note > span,
  :global(html[data-theme='light']) .g1-linked-form,
  :global(html[data-theme='light']) .g1-linked-form small {
    color: var(--accent);
  }

  :global(html[data-theme='light']) .g1-linked-form {
    border-color: color-mix(in srgb, var(--accent) 34%, transparent);
    background: color-mix(in srgb, var(--accent) 6%, var(--matcha-panel));
  }

  :global(html[data-theme='light']) .g1-row-clustered .g1-linked-form:not(.g1-linked-guide):not(.g1-linked-correct):not(.g1-linked-wrong) {
    border-color: color-mix(in srgb, var(--group-color) 48%, var(--accent));
    color: color-mix(in srgb, var(--group-color) 58%, var(--matcha-ink));
    background: color-mix(in srgb, var(--group-color) 6%, var(--matcha-panel));
  }

  :global(html[data-theme='light']) .g1-row-clustered .g1-linked-form:not(.g1-linked-guide):not(.g1-linked-correct):not(.g1-linked-wrong) small {
    color: color-mix(in srgb, var(--group-color) 58%, var(--matcha-ink));
  }

  :global(html[data-theme='light']) .g1-linked-guide,
  :global(html[data-theme='light']) .g1-locked-guide {
    border-color: color-mix(in srgb, var(--accent) 38%, transparent);
    background: color-mix(in srgb, var(--accent) 7%, var(--matcha-panel));
  }

  :global(html[data-theme='light']) .g1-feedback-correct {
    color: var(--success);
    background: color-mix(in srgb, var(--success) 9%, var(--matcha-panel));
  }

  :global(html[data-theme='light']) .g1-feedback-wrong {
    color: var(--danger);
    background: color-mix(in srgb, var(--accent-2) 11%, var(--matcha-panel));
  }

  :global(html[data-theme='light']) .g1-feedback-wrong del {
    text-decoration-color: var(--accent-2);
  }

  :global(html[data-theme='light']) .g1-feedback-wrong strong::before {
    color: var(--danger);
  }

  :global(html[data-theme='light']) .g1-missing-form {
    background: color-mix(in srgb, var(--matcha-field) 45%, transparent);
  }

  :global(html[data-theme='light']) .g1-shortcut-action.finish-warn {
    border-color: var(--accent-2);
    color: var(--danger);
    background: color-mix(in srgb, var(--accent-2) 9%, transparent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent-2) 8%, transparent);
  }

  :global(html[data-theme='light']) .g1-shortcut-action .kbd-chip-armed {
    border-color: var(--accent-2);
    color: var(--danger);
  }

  /* Ink Saffron · Moon tables. Structure, row heights and keyboard flow stay
     untouched; this replaces the old blue-black instrument skin. */
  :global(html[data-theme='dark']) :is(
    .language-card,
    .stair-step,
    .stair-level,
    .stair-tense-row button,
    .custom-route,
    .length-card,
    .support-row button,
    .setup-launch-row
  ) {
    border-radius: 0 12px 0 12px;
  }

  :global(html[data-theme='dark']) .step-number,
  :global(html[data-theme='dark']) .language-code {
    border-radius: 0 9px 0 9px;
    box-shadow: inset 0 -2px 0 color-mix(in srgb, var(--accent-2) 52%, transparent);
  }

  :global(html[data-theme='dark']) .stair-on .stair-level {
    box-shadow: inset 0 -2px 0 color-mix(in srgb, var(--accent-2) 52%, transparent);
  }

  :global(html[data-theme='dark']) .setup-launch-row {
    background: linear-gradient(90deg, color-mix(in srgb, var(--accent-2) 8%, var(--ink-panel)), color-mix(in srgb, var(--accent) 7%, var(--ink-panel)));
  }

  :global(html[data-theme='dark']) .g1-session-frame {
    border-color: color-mix(in srgb, var(--accent) 46%, transparent);
    border-radius: 0 20px 0 20px;
    color: var(--text);
    background:
      linear-gradient(90deg, var(--accent-2) 0 3px, transparent 3px),
      linear-gradient(rgba(240, 231, 216, 0.022) 1px, transparent 1px),
      linear-gradient(90deg, rgba(240, 231, 216, 0.022) 1px, transparent 1px),
      linear-gradient(145deg, var(--ink-raised), var(--ink-panel));
    background-size: auto, 24px 24px, 24px 24px, auto;
    box-shadow: 0 28px 58px -38px rgba(0, 0, 0, 0.92);
  }

  :global(html[data-theme='dark']) .g1-utility-line,
  :global(html[data-theme='dark']) .g1-column-head small,
  :global(html[data-theme='dark']) .g1-hero > span,
  :global(html[data-theme='dark']) .g1-hero > em,
  :global(html[data-theme='dark']) .u1-form-notice small,
  :global(html[data-theme='dark']) .c1-form-key > small,
  :global(html[data-theme='dark']) .g1-quick-shot-note p,
  :global(html[data-theme='dark']) .g1-linked-form .g1-linked-empty,
  :global(html[data-theme='dark']) .g1-linked-form em,
  :global(html[data-theme='dark']) .g1-missing-form,
  :global(html[data-theme='dark']) .g1-feedback-wrong del {
    color: var(--muted);
  }

  :global(html[data-theme='dark']) .g1-strip-name,
  :global(html[data-theme='dark']) .g1-hero > em b,
  :global(html[data-theme='dark']) .g1-hero-count,
  :global(html[data-theme='dark']) .g1-hero-tense,
  :global(html[data-theme='dark']) .g1-hero-review {
    color: var(--accent) !important;
    text-shadow: none;
  }

  :global(html[data-theme='dark']) .g1-seg {
    border-color: color-mix(in srgb, var(--ink-ivory) 13%, transparent);
    border-radius: 0 7px 0 7px;
    color: var(--muted);
    background: color-mix(in srgb, var(--ink-field) 58%, transparent);
  }

  :global(html[data-theme='dark']) .g1-seg-done {
    border-color: color-mix(in srgb, var(--success) 62%, transparent);
    color: var(--success);
    background: color-mix(in srgb, var(--success) 9%, var(--ink-panel));
    box-shadow: none;
  }

  :global(html[data-theme='dark']) .g1-seg-active {
    border-color: transparent;
    color: var(--accent);
    background: none;
    box-shadow: none;
    text-shadow: none;
  }

  :global(html[data-theme='dark']) .g1-hero {
    border-color: color-mix(in srgb, var(--accent) 24%, transparent);
    border-radius: 0 15px 0 15px;
    background:
      linear-gradient(rgba(240, 231, 216, 0.018) 1px, transparent 1px),
      linear-gradient(90deg, rgba(240, 231, 216, 0.018) 1px, transparent 1px),
      color-mix(in srgb, var(--ink-field) 72%, var(--ink-panel));
    background-size: 24px 24px;
  }

  :global(html[data-theme='dark']) .g1-hero > strong {
    color: var(--text);
    font-family: var(--display);
    letter-spacing: -0.045em;
  }

  :global(html[data-theme='dark']) .g1-utility-line b,
  :global(html[data-theme='dark']) .g1-column-head strong,
  :global(html[data-theme='dark']) .g1-column-row label strong,
  :global(html[data-theme='dark']) .u1-form-notice strong,
  :global(html[data-theme='dark']) .c1-form-key strong,
  :global(html[data-theme='dark']) .g1-linked-form strong,
  :global(html[data-theme='dark']) .g1-locked-guide strong,
  :global(html[data-theme='dark']) .g1-inline-feedback strong,
  :global(html[data-theme='dark']) .g1-quick-shot-note {
    color: var(--text);
  }

  :global(html[data-theme='dark']) .g1-utility-line i,
  :global(html[data-theme='dark']) .g1-column-rail {
    background: color-mix(in srgb, var(--accent) 17%, transparent);
  }

  :global(html[data-theme='dark']) .g1-active-column {
    border-color: color-mix(in srgb, var(--accent) 29%, transparent);
    border-radius: 0 14px 0 14px;
    background: color-mix(in srgb, var(--ink-field) 48%, transparent);
  }

  :global(html[data-theme='dark']) .g1-column-review {
    border-color: var(--accent);
    box-shadow: inset 0 -2px 0 var(--accent-2);
  }

  :global(html[data-theme='dark']) .g1-column-head {
    border-bottom-color: color-mix(in srgb, var(--accent) 18%, transparent);
    background: color-mix(in srgb, var(--accent) 4%, var(--ink-panel));
  }

  :global(html[data-theme='dark']) .u1-form-notice {
    border-color: color-mix(in srgb, var(--accent) 37%, transparent);
    border-radius: 0 9px 0 9px;
    background: color-mix(in srgb, var(--accent) 6%, var(--ink-panel));
  }

  :global(html[data-theme='dark']) .u1-form-notice > span,
  :global(html[data-theme='dark']) .u1-form-notice em,
  :global(html[data-theme='dark']) .g1-row-guide .g1-row-marker,
  :global(html[data-theme='dark']) .g1-linked-guide,
  :global(html[data-theme='dark']) .g1-locked-guide > span,
  :global(html[data-theme='dark']) .g1-locked-guide > small {
    color: var(--accent);
  }

  :global(html[data-theme='dark']) .c1-form-key > span {
    background: color-mix(in srgb, var(--group-color) 6%, var(--ink-panel));
  }

  :global(html[data-theme='dark']) .g1-column-row {
    border-color: color-mix(in srgb, var(--ink-ivory) 10%, transparent);
    color: var(--text);
    background: color-mix(in srgb, var(--ink-field) 58%, transparent);
  }

  :global(html[data-theme='dark']) .g1-row-active {
    border-color: var(--accent);
    background: color-mix(in srgb, var(--accent) 8%, var(--ink-panel));
    box-shadow: inset 3px 0 0 var(--accent-2);
    transform: translateX(0.2rem);
  }

  :global(html[data-theme='dark']) .g1-row-clustered {
    background: color-mix(in srgb, var(--group-color) 5%, var(--ink-panel));
  }

  :global(html[data-theme='dark']) .g1-row-clustered.g1-row-active {
    background: color-mix(in srgb, var(--group-color) 9%, var(--ink-panel));
    box-shadow: inset 3px 0 0 var(--group-color);
  }

  :global(html[data-theme='dark']) .g1-row-correct {
    border-color: color-mix(in srgb, var(--success) 62%, transparent);
    background: color-mix(in srgb, var(--success) 9%, var(--ink-panel));
  }

  :global(html[data-theme='dark']) .g1-row-wrong {
    border-color: color-mix(in srgb, var(--danger) 68%, transparent);
    background: color-mix(in srgb, var(--danger) 9%, var(--ink-panel));
  }

  :global(html[data-theme='dark']) .g1-row-correct .g1-row-marker {
    border-color: var(--success);
    color: var(--success);
    background: color-mix(in srgb, var(--success) 8%, var(--ink-panel));
  }

  :global(html[data-theme='dark']) .g1-row-wrong .g1-row-marker {
    border-color: var(--danger);
    color: var(--danger);
    background: color-mix(in srgb, var(--danger) 8%, var(--ink-panel));
  }

  :global(html[data-theme='dark']) .g1-conj-input {
    border-color: color-mix(in srgb, var(--ink-ivory) 14%, transparent);
    border-radius: 0 8px 0 8px;
    color: var(--text);
    background: var(--ink-field);
  }

  :global(html[data-theme='dark']) .g1-conj-input:focus {
    border-color: var(--accent);
    box-shadow: inset 0 -2px 0 var(--accent-2);
  }

  :global(html[data-theme='dark']) .g1-quick-shot-note,
  :global(html[data-theme='dark']) .g1-linked-form,
  :global(html[data-theme='dark']) .g1-locked-guide,
  :global(html[data-theme='dark']) .g1-inline-feedback,
  :global(html[data-theme='dark']) .g1-missing-form {
    border-radius: 0 9px 0 9px;
  }

  :global(html[data-theme='dark']) .g1-quick-shot-note {
    border-color: color-mix(in srgb, var(--accent) 40%, transparent);
    background: var(--ink-panel);
    box-shadow: 0 12px 24px -18px rgba(0, 0, 0, 0.92);
  }

  :global(html[data-theme='dark']) .g1-linked-form {
    border-color: color-mix(in srgb, var(--accent) 30%, transparent);
    color: var(--accent-strong);
    background: color-mix(in srgb, var(--accent) 5%, var(--ink-field));
  }

  :global(html[data-theme='dark']) .g1-row-clustered .g1-linked-form:not(.g1-linked-guide):not(.g1-linked-correct):not(.g1-linked-wrong) {
    background: color-mix(in srgb, var(--group-color) 5%, var(--ink-field));
  }

  :global(html[data-theme='dark']) .g1-linked-guide,
  :global(html[data-theme='dark']) .g1-locked-guide {
    border-color: color-mix(in srgb, var(--accent) 38%, transparent);
    background: color-mix(in srgb, var(--accent) 7%, var(--ink-field));
  }

  :global(html[data-theme='dark']) .g1-feedback-correct {
    color: var(--success);
    background: color-mix(in srgb, var(--success) 8%, var(--ink-field));
  }

  :global(html[data-theme='dark']) .g1-feedback-wrong {
    color: var(--danger);
    background: color-mix(in srgb, var(--danger) 9%, var(--ink-field));
  }

  :global(html[data-theme='dark']) .g1-feedback-wrong del {
    text-decoration-color: var(--danger);
  }

  :global(html[data-theme='dark']) .g1-feedback-wrong strong::before {
    color: var(--danger);
  }

  :global(html[data-theme='dark']) .g1-missing-form {
    background: color-mix(in srgb, var(--ink-field) 72%, transparent);
  }

  :global(html[data-theme='dark']) .g1-shortcut-action.finish-warn {
    border-color: var(--danger);
    color: var(--danger);
    background: color-mix(in srgb, var(--danger) 8%, transparent);
    box-shadow: inset 0 -2px 0 color-mix(in srgb, var(--accent) 44%, transparent);
  }

  :global(html[data-theme='dark']) .g1-shortcut-action .kbd-chip-armed {
    border-color: var(--danger);
    color: var(--danger);
  }

  :global(html[data-theme='arcade']) .step-number,
  :global(html[data-theme='arcade']) .language-code,
  :global(html[data-theme='arcade']) .launch-summary > span,
  :global(html[data-theme='arcade']) .g1-hero > strong {
    text-shadow: 0 0 9px color-mix(in srgb, var(--accent) 65%, transparent);
  }

  /* Arcade: the active-tense marquee is this screen's Press Start 2P moment */
  :global(html[data-theme='arcade']) .g1-strip-name {
    font-family: var(--marquee);
    font-size: 0.95rem;
    line-height: 1.5;
  }

  :global(html[data-theme='arcade']) .g1-seg-active {
    font-family: var(--marquee);
    font-size: 1.6rem;
    line-height: 1.3;
  }

  /* VT323 optical compensation for the in-game mono chrome */
  :global(html[data-theme='arcade']) .g1-hero > span {
    font-size: 1.05rem;
  }

  :global(html[data-theme='arcade']) .g1-column-head span,
  :global(html[data-theme='arcade']) .g1-column-row label small,
  :global(html[data-theme='arcade']) .g1-group-badge,
  :global(html[data-theme='arcade']) .g1-linked-form small,
  :global(html[data-theme='arcade']) .g1-linked-form em,
  :global(html[data-theme='arcade']) .g1-locked-guide small,
  :global(html[data-theme='arcade']) .g1-inline-feedback small,
  :global(html[data-theme='arcade']) .u1-form-notice > span,
  :global(html[data-theme='arcade']) .u1-form-notice em,
  :global(html[data-theme='arcade']) .c1-form-key i,
  :global(html[data-theme='arcade']) .c1-form-key > small {
    font-size: 1rem;
    line-height: 1.15;
  }

  @media (max-width: 760px) {
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

  /* Full language names stop fitting two-up around here */
  @media (max-width: 430px) {
    .language-card-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 560px) {
    .table-setup-lead,
    .setup-launch-row {
      align-items: stretch;
      flex-direction: column;
    }

    .table-setup-side {
      justify-items: stretch;
    }

    .table-setup-side .section-copy {
      max-width: none;
      text-align: left;
    }

    .language-card {
      grid-template-columns: auto minmax(0, 1fr) auto;
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

    /* Fullscreen is a desktop affordance — no place for it on a phone. */
    .table-fs-toggle {
      display: none;
    }

    .u1-form-notice {
      grid-template-columns: auto minmax(0, 1fr);
    }

    .u1-form-notice em {
      grid-column: 2;
    }

    .c1-form-key > small {
      width: 100%;
      margin-left: 0;
    }

    .g1-column-row {
      grid-template-columns: auto 1fr;
    }

    .g1-column-row label strong {
      font-size: 1.08rem;
    }

    /* Compact table (per the M1-9 mobile concept): while answering, collapse the
       column to the single active pronoun so the verb hero stays on screen.
       The full grid returns automatically for the tense-review feedback. */
    .g1-hero-count,
    .g1-hero-tense {
      display: block;
    }

    /* Badges (1/N tense · N/6) now carry the context, so drop the "Current verb"
       caption that otherwise collides with the top-left tense badge. */
    .g1-hero > span:not(.g1-hero-count):not(.g1-hero-tense) {
      display: none;
    }

    .g1-hero {
      padding-top: 1.5rem;
    }

    /* Declutter the answering header: one big pixelated tense name; the tense
       and cell positions live as badges on the verb hero. Drop the segment
       strip and the ACTIVE TENSE block. */
    .g1-name-strip {
      display: none;
    }

    .g1-strip-head {
      display: flex;
      justify-content: center;
    }

    .g1-strip-name {
      font-size: 1.9rem;
      text-align: center;
    }

    .g1-active-column:not(.g1-column-review) .g1-column-head {
      display: none;
    }

    .g1-active-column:not(.g1-column-review) .g1-column-row:not(.g1-row-active) {
      display: none;
    }

    .g1-active-column:not(.g1-column-review) .g1-column-rail {
      display: none;
    }

    .g1-active-column:not(.g1-column-review) .g1-column-rows {
      padding-left: 0.65rem;
    }

    .g1-active-column:not(.g1-column-review) .g1-row-active {
      transform: none;
    }

    /* Compact tense-review feedback so it fits the half-screen above the
       keyboard: correct/given answers shrink to small check chips that wrap
       inline; only mistakes take a full-width row (crossed answer + correction). */
    .g1-column-review .g1-column-rows {
      display: flex;
      flex-wrap: wrap;
      align-items: flex-start;   /* chips size to content, no vertical stretch */
      gap: 0.35rem;
      padding: 0.5rem;
    }

    .g1-column-review .g1-column-rail {
      display: none;
    }

    .g1-column-review .g1-column-row {
      flex: 0 0 auto;
      width: auto;
      min-height: 0;
      align-items: center;
      grid-template-columns: auto auto;
      gap: 0.4rem;
      padding: 0.3rem 0.55rem;
    }

    .g1-column-review .g1-column-row label {
      flex-direction: row;
      align-items: center;
      gap: 0.3rem;
    }

    /* keep each pronoun on one line so chips never grow to 2–3 lines */
    .g1-column-review .g1-column-row label small {
      display: none;
    }

    .g1-column-review .g1-column-row label strong {
      white-space: nowrap;
    }

    .g1-column-review .g1-inline-feedback,
    .g1-column-review .g1-locked-guide,
    .g1-column-review .g1-linked-form,
    .g1-column-review .g1-missing-form {
      display: none;
    }

    .g1-column-review .g1-row-wrong {
      flex: 1 1 100%;
      grid-template-columns: auto 1fr;
    }

    .g1-column-review .g1-row-wrong .g1-inline-feedback {
      display: grid;
      grid-column: 2;
    }

    .g1-input-shell,
    .g1-locked-guide,
    .g1-linked-form,
    .g1-inline-feedback,
    .g1-missing-form {
      grid-column: 2;
    }

    .g1-inline-feedback,
    .g1-locked-guide,
    .g1-linked-form {
      grid-template-columns: auto minmax(0, 1fr);
    }

    .g1-inline-feedback > small,
    .g1-locked-guide > small,
    .g1-linked-form > em {
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

    .table-clear-card :global(.rank-actions) {
      width: 100%;
      flex-direction: column;
    }

    .table-clear-card :global(.rank-actions button) {
      width: 100%;
      justify-content: center;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .g1-production-card,
    .g1-column-review .g1-column-row,
    .g1-row-active .g1-row-marker,
    .g1-quick-shot-note,
    .table-clear-card {
      animation: none;
    }
  }
</style>
