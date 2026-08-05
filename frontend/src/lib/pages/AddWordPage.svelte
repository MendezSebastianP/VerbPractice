<script lang="ts">
  import { onMount, onDestroy, tick } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import DirectionPicker from '../components/DirectionPicker.svelte';
  import HelpTip from '../components/HelpTip.svelte';
  import PlayClear from '../components/PlayClear.svelte';
  import PlayGrid from '../components/PlayGrid.svelte';
  import PlaySaffronRelay from '../components/PlaySaffronRelay.svelte';
  import type {
    AddWordResponse,
    AddedWordNotFound,
    AddedWordResult,
    LanguageEntry,
    OcrWordResult,
    ThemeName,
    UserWordEntry,
    WordHistoryEntry,
  } from '../types';

  export let csrfToken = '';
  export let theme: ThemeName = 'light';
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;

  let translateRelayRef: PlaySaffronRelay | null = null;
  let translateClearRef: PlayClear | null = null;
  let translateGridRef: PlayGrid | null = null;
  let wordInput: HTMLInputElement | null = null;

  let loading = true;
  let error = '';
  let languages: LanguageEntry[] = [];

  let inputText = '';
  let contextHint = '';
  let questionHint = '';
  let adding = false;
  let entryBusy = false;

  // Source → output language pair (any combination). Equal codes request a
  // monolingual definition; different codes also produce a translation.
  let sourceCode = '';
  let targetCode = '';
  let directionRef: DirectionPicker | null = null;

  // Keyboard shortcuts mirror the Words trainer.
  const LANG_KEY: Record<string, string> = { e: 'EN', s: 'ES', r: 'RU', f: 'FR' };
  // One concept ("house") per language powers a clear, pair-specific example line.
  const EXAMPLE_WORD: Record<string, string> = { EN: 'house', ES: 'casa', FR: 'maison', RU: 'дом' };

  let result: AddedWordResult | null = null;
  let notFound: AddedWordNotFound | null = null;
  let expanding = false;
  let selectingSenseId: number | null = null;
  let reportTarget: { entry_type: 'lexical' | 'native'; entry_id: number } | null = null;
  let reportReason = '';

  let history: WordHistoryEntry[] = [];
  let expandedHistoryId: number | null = null;
  let historyOpen = false;

  // My words drawer
  let manageOpen = false;
  let manageLearning = '';
  let manageMother = '';
  let manageEntries: UserWordEntry[] = [];
  let manageLoading = false;
  let manageLoadedPair = '';

  // Offline add drawer
  let offlineOpen = false;
  let offlineLearning = '';
  let offlineNative = '';
  let offlineLearningLang = '';
  let offlineMotherLang = '';
  let offlineSaving = false;

  // --- Photo capture. Photograph text → local server OCR → select words on
  // the photo itself. Adjacent selections form one compound word; the nearby
  // text rides along only as translation context. ---
  const MAX_UPLOAD_DIMENSION = 1600;
  const CONTEXT_MAX_CHARS = 512;
  const CONTEXT_WINDOW_WORDS = 15;
  const WORD_MAX_CHARS = 128;
  const MIN_CROP = 0.08;

  type PhotoPhase = 'idle' | 'crop' | 'reading' | 'review';

  interface PhotoCard {
    id: number;
    word: string;
    state: 'loading' | 'done' | 'not_found' | 'error' | 'removed';
    result?: AddedWordResult;
    detail?: string;
    undoing?: boolean;
    selectingSenseId?: number | null;
  }

  interface Token {
    raw: string;
    word: string;
  }

  interface SelectionPreview {
    key: string;
    indices: number[];
    value: string;
  }

  let photoPhase: PhotoPhase = 'idle';
  let photoSubmitting = false;
  let cameraInput: HTMLInputElement | null = null;
  let libraryInput: HTMLInputElement | null = null;
  let pickedFile: File | null = null;
  let previewUrl = '';
  let croppedUrl = '';
  let ocrConfidence: number | null = null;
  let ocrWords: OcrWordResult[] = [];
  let selectedTokens = new Set<number>();
  let selectionDrafts: Record<string, string> = {};
  let photoCards: PhotoCard[] = [];
  let nextCardId = 1;

  // crop state: fractions of the displayed image
  let cropStage: HTMLDivElement | null = null;
  let crop = { x: 0.03, y: 0.03, w: 0.94, h: 0.94 };
  let dragging: {
    mode: string;
    startX: number;
    startY: number;
    rect: typeof crop;
    bounds: DOMRect;
  } | null = null;

  $: tokens = ocrWords.map((word): Token => ({ raw: word.text, word: word.text }));

  $: managePair = manageLearning && manageMother
    ? `${manageLearning.toLowerCase()}_${manageMother.toLowerCase()}`
    : '';
  $: if (manageOpen && managePair && managePair !== manageLoadedPair && !manageLoading) {
    void loadManage();
  }

  $: sameLanguageLookup = Boolean(sourceCode && sourceCode === targetCode);
  $: exampleLine =
    sourceCode && targetCode && EXAMPLE_WORD[sourceCode] && EXAMPLE_WORD[targetCode]
      ? sameLanguageLookup
        ? `Type “${EXAMPLE_WORD[sourceCode]}” and get its definition in ${languageName(targetCode)}.`
        : `Type “${EXAMPLE_WORD[sourceCode]}” and get “${EXAMPLE_WORD[targetCode]}” with a ${languageName(targetCode)} definition.`
      : '';
  $: detectedMismatch =
    !!result &&
    !!result.detected_input_language &&
    result.detected_input_language.toUpperCase() !== result.learning_language_code.toUpperCase() &&
    result.detected_input_language.toUpperCase() !== result.mother_tongue_code.toUpperCase();
  $: entryBusy = adding || photoSubmitting || expanding || selectingSenseId !== null;

  function isFoundResult(payload: AddWordResponse): payload is AddedWordResult {
    return payload.status !== 'not_found';
  }

  function escapeHtml(value: string): string {
    return value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function renderInlineMarkdown(value: string): string {
    return escapeHtml(value.trim())
      .replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>')
      .replace(/__([^_]+?)__/g, '<strong>$1</strong>');
  }

  function renderMoreInfoMarkdown(value: string): string {
    const blocks: string[] = [];
    let paragraph: string[] = [];
    let listItems: string[] = [];

    const flushParagraph = () => {
      if (!paragraph.length) return;
      blocks.push(`<p>${paragraph.join(' ')}</p>`);
      paragraph = [];
    };

    const flushList = () => {
      if (!listItems.length) return;
      blocks.push(`<ul>${listItems.join('')}</ul>`);
      listItems = [];
    };

    for (const rawLine of value.replace(/\r\n/g, '\n').split('\n')) {
      const line = rawLine.trim();
      if (!line) {
        flushParagraph();
        flushList();
        continue;
      }

      const bullet = line.match(/^[-*]\s+(.+)$/);
      if (bullet) {
        flushParagraph();
        listItems.push(`<li>${renderInlineMarkdown(bullet[1])}</li>`);
        continue;
      }

      flushList();
      paragraph.push(renderInlineMarkdown(line));
    }

    flushParagraph();
    flushList();
    return blocks.join('');
  }

  async function load(): Promise<void> {
    loading = true;
    error = '';
    try {
      const [langs, s, hist] = await Promise.all([
        api.listLanguages(),
        api.getSettings(),
        api.wordHistory(20).catch(() => ({ entries: [] as WordHistoryEntry[] })),
      ]);
      languages = langs.languages;
      // Default direction: the pair of the most recent translation, since people
      // usually keep translating between the same two languages. Fall back to the
      // settings prefs, then to the first two available languages.
      const last = hist.entries[0];
      if (last?.learning_language_code && last?.mother_tongue_code) {
        sourceCode = last.learning_language_code.toUpperCase();
        targetCode = last.mother_tongue_code.toUpperCase();
      } else {
        sourceCode = s.learning_language?.code ?? languages[0]?.code ?? '';
        targetCode = s.mother_tongue?.code ?? languages.find((l) => l.code !== sourceCode)?.code ?? '';
      }
      history = hist.entries;
      manageLearning = s.learning_language?.code ?? '';
      manageMother = s.mother_tongue?.code ?? '';
      offlineLearningLang = s.learning_language?.code ?? '';
      offlineMotherLang = s.mother_tongue?.code ?? '';
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to load';
    } finally {
      loading = false;
    }
  }

  // Route Enter/submit through the themed control so its fire visuals play;
  // the control dispatches `fire` back into addWord().
  function fireTranslate(): void {
    if (entryTransitionBusy() || !inputText.trim()) {
      return;
    }
    if (theme === 'arcade') {
      translateGridRef?.fire();
    } else if (theme === 'light') {
      translateClearRef?.fire();
    } else {
      translateRelayRef?.fire();
    }
  }

  async function addWord(textOverride?: string): Promise<void> {
    const text = (textOverride ?? inputText).trim();
    if (!text || entryTransitionBusy()) {
      return;
    }
    if (!sourceCode || !targetCode) {
      notify('Pick both languages.', 'error');
      return;
    }
    adding = true;
    result = null;
    notFound = null;
    try {
      const response = await api.addWord({
        input_text: text,
        context: contextHint.trim() || undefined,
        question: questionHint.trim() || undefined,
        context_source: 'manual',
        learning_lang_code: sourceCode,
        mother_lang_code: targetCode,
        csrf_token: csrfToken,
      });
      if (isFoundResult(response)) {
        result = response;
        inputText = '';
        contextHint = '';
        questionHint = '';
        if (response.status === 'corrected') {
          notify(`Corrected "${response.original_input}" → "${response.text}".`, 'info');
        } else {
          notify(`Added "${response.text}".`, 'success');
        }
        try {
          const hist = await api.wordHistory(20);
          history = hist.entries;
        } catch {
          // non-fatal
        }
      } else {
        notFound = response;
        inputText = text;
      }
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to add word', 'error');
    } finally {
      adding = false;
    }
  }

  async function expand(): Promise<void> {
    if (!result) {
      return;
    }
    const activeResult = result;
    expanding = true;
    try {
      const { extended_content } = await api.expandWord(activeResult.word_id, csrfToken);
      if (result?.lookup_id !== activeResult.lookup_id) {
        return;
      }
      result = { ...result, lexical: { ...result.lexical, extended_content } };
      notify('Added more info.', 'success');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to expand', 'error');
    } finally {
      expanding = false;
    }
  }

  async function chooseResultSense(senseId: number): Promise<void> {
    if (!result || result.selected_sense_id === senseId || selectingSenseId !== null) {
      return;
    }
    const activeResult = result;
    selectingSenseId = senseId;
    try {
      const update = await api.selectWordSense(activeResult.lookup_id, senseId, csrfToken);
      if (result?.lookup_id !== activeResult.lookup_id) {
        return;
      }
      result = { ...result, ...update };
      const hist = await api.wordHistory(20);
      history = hist.entries;
      notify('Meaning updated for your lookup.', 'success');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to change meaning', 'error');
    } finally {
      selectingSenseId = null;
    }
  }

  async function submitReport(): Promise<void> {
    if (!result || !reportTarget) {
      return;
    }
    try {
      await api.reportTranslation(result.word_id, {
        entry_type: reportTarget.entry_type,
        entry_id: reportTarget.entry_id,
        reason: reportReason.trim() || undefined,
        csrf_token: csrfToken,
      });
      reportTarget = null;
      reportReason = '';
      notify('Thanks — queued for review.', 'success');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to submit report', 'error');
    }
  }

  function resetForAnother(): void {
    result = null;
    notFound = null;
    reportTarget = null;
    reportReason = '';
    inputText = '';
    contextHint = '';
    questionHint = '';
  }

  function entryTransitionBusy(): boolean {
    return entryBusy;
  }

  async function startWordSearch(): Promise<void> {
    if (entryTransitionBusy()) {
      return;
    }
    resetForAnother();
    resetPhoto();
    photoCards = [];
    nextCardId = 1;
    await tick();
    wordInput?.focus();
  }

  function startPhotoCapture(): void {
    if (entryTransitionBusy()) {
      return;
    }
    cameraInput?.click();
  }

  function reportResult(): void {
    if (!result || !result.reportable) {
      return;
    }
    const primaryNative = result.natives[0];
    reportTarget = primaryNative?.id != null
      ? { entry_type: 'native', entry_id: primaryNative.id }
      : result.lexical.id != null
        ? { entry_type: 'lexical', entry_id: result.lexical.id }
        : null;
  }

  async function loadManage(): Promise<void> {
    if (!managePair) return;
    manageLoading = true;
    try {
      const data = await api.listUserWords(managePair);
      manageEntries = data.entries;
      manageLoadedPair = managePair;
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to load words', 'error');
      manageEntries = [];
    } finally {
      manageLoading = false;
    }
  }

  async function removeWord(entry: UserWordEntry): Promise<void> {
    if (!managePair) return;
    if (!confirm(`Remove "${entry.text}" from this pair?`)) return;
    try {
      await api.deleteUserWord(entry.word_id, managePair, csrfToken);
      manageEntries = manageEntries.filter((e) => e.word_id !== entry.word_id);
      history = history.filter((h) => !(h.word_id === entry.word_id && h.language_pair === managePair));
      notify(`Removed "${entry.text}".`, 'success');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to remove', 'error');
    }
  }

  async function submitOfflineAdd(): Promise<void> {
    const lt = offlineLearning.trim();
    const nt = offlineNative.trim();
    if (!lt || !nt || !offlineLearningLang || !offlineMotherLang) return;
    if (offlineLearningLang === offlineMotherLang) {
      notify('Pick two different languages.', 'error');
      return;
    }
    offlineSaving = true;
    try {
      const res = await api.addWordOffline({
        learning_text: lt,
        native_text: nt,
        learning_lang_code: offlineLearningLang,
        mother_lang_code: offlineMotherLang,
        csrf_token: csrfToken,
      });
      notify(
        res.force_unlocked
          ? `Added "${lt}" → "${nt}" (unlocked now).`
          : `Added "${lt}" → "${nt}" (queued).`,
        'success',
      );
      offlineLearning = '';
      offlineNative = '';
      try {
        const hist = await api.wordHistory(20);
        history = hist.entries;
      } catch {
        // non-fatal
      }
      if (manageOpen && manageLoadedPair === res.language_pair) {
        void loadManage();
      }
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to add', 'error');
    } finally {
      offlineSaving = false;
    }
  }

  function trySuggestion(s: string): void {
    inputText = s;
    void addWord(s);
  }

  function languageName(code: string): string {
    return languages.find((l) => l.code === code.toUpperCase())?.name ?? code;
  }

  function swapDetected(): void {
    if (!result || !result.detected_input_language) {
      return;
    }
    const newSource = result.detected_input_language.toUpperCase();
    if (newSource === targetCode.toUpperCase()) {
      notify('That matches your target language — pick a different one.', 'error');
      return;
    }
    sourceCode = newSource;
    void addWord(result.original_input || result.text);
  }

  function swapLangs(): void {
    const t = sourceCode;
    sourceCode = targetCode;
    targetCode = t;
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (loading || entryTransitionBusy()) {
      return;
    }

    // Ctrl+Space swaps source/target — works even while typing, like the trainer.
    if (event.code === 'Space' && event.ctrlKey && !event.altKey && !event.metaKey) {
      event.preventDefault();
      swapLangs();
      directionRef?.popSwap();
      return;
    }

    // Letter shortcuts only when not typing in a field.
    const active = document.activeElement as HTMLElement | null;
    const isTyping =
      active?.tagName === 'INPUT' ||
      active?.tagName === 'TEXTAREA' ||
      active?.tagName === 'SELECT' ||
      active?.isContentEditable;
    if (isTyping || event.ctrlKey || event.metaKey || event.altKey) {
      return;
    }

    // E/S/R/F set the source language; add Shift for the output language.
    // Add Word intentionally permits the same language on both sides.
    const code = LANG_KEY[event.key.toLowerCase()];
    if (code) {
      event.preventDefault();
      if (event.shiftKey) {
        targetCode = code;
      } else {
        sourceCode = code;
      }
    }
  }

  // --- photo flow handlers ---
  function handlePhotoFile(event: Event): void {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    if (!sourceCode) {
      notify('Pick the text language first.', 'error');
      return;
    }
    const replacingPhoto = photoPhase !== 'idle';
    result = null;
    notFound = null;
    reportTarget = null;
    reportReason = '';
    inputText = '';
    if (replacingPhoto) {
      contextHint = '';
      questionHint = '';
    }
    photoCards = [];
    nextCardId = 1;
    pickedFile = file;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (croppedUrl) URL.revokeObjectURL(croppedUrl);
    previewUrl = URL.createObjectURL(file);
    croppedUrl = '';
    ocrConfidence = null;
    ocrWords = [];
    selectedTokens = new Set();
    selectionDrafts = {};
    crop = { x: 0, y: 0, w: 1, h: 1 };
    // The happy path goes straight from capture to selectable word boxes.
    // Cropping remains available after recognition, or automatically on a miss.
    void readText();
  }

  // crop interactions (pointer events cover mouse + touch)
  function clamp(value: number, min: number, max: number): number {
    return Math.min(Math.max(value, min), max);
  }

  function cropPointerDown(mode: string, event: PointerEvent): void {
    if (!cropStage) return;
    event.preventDefault();
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
    dragging = {
      mode,
      startX: event.clientX,
      startY: event.clientY,
      rect: { ...crop },
      bounds: cropStage.getBoundingClientRect(),
    };
  }

  function cropPointerMove(event: PointerEvent): void {
    if (!dragging) return;
    const { mode, rect, bounds } = dragging;
    const dx = (event.clientX - dragging.startX) / bounds.width;
    const dy = (event.clientY - dragging.startY) / bounds.height;
    const right = rect.x + rect.w;
    const bottom = rect.y + rect.h;

    if (mode === 'move') {
      crop = {
        ...rect,
        x: clamp(rect.x + dx, 0, 1 - rect.w),
        y: clamp(rect.y + dy, 0, 1 - rect.h),
      };
      return;
    }

    let { x, y } = rect;
    let w = rect.w;
    let h = rect.h;
    if (mode.includes('w')) {
      x = clamp(rect.x + dx, 0, right - MIN_CROP);
      w = right - x;
    }
    if (mode.includes('e')) {
      w = clamp(rect.w + dx, MIN_CROP, 1 - rect.x);
    }
    if (mode.includes('n')) {
      y = clamp(rect.y + dy, 0, bottom - MIN_CROP);
      h = bottom - y;
    }
    if (mode.includes('s')) {
      h = clamp(rect.h + dy, MIN_CROP, 1 - rect.y);
    }
    crop = { x, y, w, h };
  }

  function cropPointerUp(): void {
    dragging = null;
  }

  async function cropAndScale(): Promise<Blob> {
    if (!pickedFile) throw new Error('No photo selected');
    try {
      const bitmap = await createImageBitmap(pickedFile, { imageOrientation: 'from-image' });
      const sx = Math.round(crop.x * bitmap.width);
      const sy = Math.round(crop.y * bitmap.height);
      const sw = Math.max(1, Math.round(crop.w * bitmap.width));
      const sh = Math.max(1, Math.round(crop.h * bitmap.height));
      const scale = Math.min(1, MAX_UPLOAD_DIMENSION / Math.max(sw, sh));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(sw * scale));
      canvas.height = Math.max(1, Math.round(sh * scale));
      const ctx = canvas.getContext('2d');
      if (!ctx) return pickedFile;
      ctx.drawImage(bitmap, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
      bitmap.close();
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85));
      return blob ?? pickedFile;
    } catch {
      // Older browsers: upload the original; the server downscales too.
      return pickedFile;
    }
  }

  async function readText(): Promise<void> {
    photoPhase = 'reading';
    selectedTokens = new Set();
    selectionDrafts = {};
    try {
      const blob = await cropAndScale();
      if (croppedUrl) URL.revokeObjectURL(croppedUrl);
      croppedUrl = URL.createObjectURL(blob);
      const response = await api.ocrExtract(blob, sourceCode.toLowerCase(), csrfToken);
      if (!response.text.trim()) {
        notify('No text found — try a closer shot or a tighter crop.', 'error');
        photoPhase = 'crop';
        return;
      }
      if (!response.words.length) {
        notify('No selectable words found — try a closer shot or a tighter crop.', 'error');
        photoPhase = 'crop';
        return;
      }
      ocrConfidence = response.mean_confidence;
      ocrWords = response.words;
      photoPhase = 'review';
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to read the photo', 'error');
      photoPhase = 'crop';
    }
  }

  function toggleToken(index: number): void {
    const next = new Set(selectedTokens);
    if (next.has(index)) {
      next.delete(index);
    } else {
      next.add(index);
    }
    const activeKeys = new Set(groupSelection(next).map(selectionKey));
    selectionDrafts = Object.fromEntries(
      Object.entries(selectionDrafts).filter(([key]) => activeKeys.has(key)),
    );
    selectedTokens = next;
  }

  function updateSelectionDraft(key: string, event: Event): void {
    selectionDrafts = {
      ...selectionDrafts,
      [key]: (event.currentTarget as HTMLInputElement).value,
    };
  }

  function openCrop(): void {
    selectedTokens = new Set();
    selectionDrafts = {};
    photoPhase = 'crop';
  }

  function cancelCrop(): void {
    if (ocrWords.length > 0) {
      photoPhase = 'review';
      return;
    }
    resetPhoto();
  }

  function wordBoxStyle(word: OcrWordResult): string {
    // Give the OCR bounds a small optical cushion without allowing the box to
    // escape the photograph.
    const padX = Math.min(0.004, word.box.width * 0.08);
    const padY = Math.min(0.006, word.box.height * 0.12);
    const left = clamp(word.box.x - padX, 0, 1);
    const top = clamp(word.box.y - padY, 0, 1);
    const width = clamp(word.box.width + padX * 2, 0, 1 - left);
    const height = clamp(word.box.height + padY * 2, 0, 1 - top);
    return `left:${left * 100}%;top:${top * 100}%;width:${width * 100}%;height:${height * 100}%;`;
  }

  function patchCard(id: number, patch: Partial<PhotoCard>): void {
    photoCards = photoCards.map((c) => (c.id === id ? { ...c, ...patch } : c));
  }

  // Consecutive selected tokens form one compound word, so tapping
  // "salle", "de", "bain" looks up "salle de bain" as a single entry.
  function groupSelection(selection: Set<number>): number[][] {
    const groups: number[][] = [];
    for (const i of [...selection].sort((a, b) => a - b)) {
      const last = groups[groups.length - 1];
      if (last && i === last[last.length - 1] + 1) {
        last.push(i);
      } else {
        groups.push([i]);
      }
    }
    return groups;
  }

  function selectionKey(group: number[]): string {
    return group.join(':');
  }

  function detectedSelectionText(group: number[]): string {
    return group.map((index) => tokens[index]?.word ?? '').filter(Boolean).join(' ');
  }

  function photoContextFor(group: number[], userContext: string): string {
    const start = Math.max(0, group[0] - CONTEXT_WINDOW_WORDS);
    const end = Math.min(tokens.length - 1, group[group.length - 1] + CONTEXT_WINDOW_WORDS);
    const nearbyText = tokens
      .slice(start, end + 1)
      .map((token) => token.raw)
      .join(' ')
      .trim();
    const personalContext = userContext.trim();

    if (!personalContext) {
      return nearbyText.slice(0, CONTEXT_MAX_CHARS);
    }
    if (!nearbyText) {
      return personalContext.slice(0, CONTEXT_MAX_CHARS);
    }

    // Keep the learner's note intact and use the remaining budget for the
    // nearby OCR text. The API accepts one context field capped at 512 chars.
    const separator = '\nYour context: ';
    const personalSlice = personalContext.slice(0, CONTEXT_MAX_CHARS);
    const nearbyBudget = CONTEXT_MAX_CHARS - separator.length - personalSlice.length;
    if (nearbyBudget <= 0) {
      return personalSlice;
    }
    return `${nearbyText.slice(0, nearbyBudget)}${separator}${personalSlice}`;
  }

  $: selectedGroups = groupSelection(selectedTokens);
  $: selectionPreviews = selectedGroups.map((indices): SelectionPreview => {
    const key = selectionKey(indices);
    return {
      key,
      indices,
      value: selectionDrafts[key] ?? detectedSelectionText(indices),
    };
  });
  $: selectionPreviewInvalid = selectionPreviews.some((preview) => !preview.value.trim());
  $: selectedEntryLabel = selectedGroups.length === 0
    ? 'No words selected'
    : selectedGroups.length === 1
      ? selectedGroups[0].length === 1
        ? '1 word selected'
        : '1 compound word selected'
      : `${selectedGroups.length} word entries selected`;

  async function submitSelected(): Promise<void> {
    if (selectedTokens.size === 0 || photoSubmitting) return;
    if (selectionPreviewInvalid) {
      notify('Each selected word needs text.', 'error');
      return;
    }
    if (!sourceCode || !targetCode) {
      notify('Pick both languages.', 'error');
      return;
    }

    const batchSourceCode = sourceCode;
    const batchTargetCode = targetCode;
    const batchQuestion = questionHint.trim();
    const userPhotoContext = contextHint.trim();
    // Only the words around the selection ride along as automatic context.
    // A learner-written note is appended within the same API character budget.
    const lookups = selectionPreviews.map((preview) => {
      const group = preview.indices;
      return {
        word: preview.value.trim(),
        context: photoContextFor(group, userPhotoContext),
      };
    }).filter((l) => l.word.length > 0);
    photoSubmitting = true;
    selectedTokens = new Set();
    selectionDrafts = {};
    let addedThisBatch = 0;

    for (const { word, context } of lookups) {
      const id = nextCardId++;
      photoCards = [...photoCards, { id, word, state: 'loading' }];
      if (word.length > WORD_MAX_CHARS) {
        patchCard(id, { state: 'error', detail: 'Too long for a single entry.' });
        continue;
      }
      try {
        const response = await api.addWord({
          input_text: word,
          context,
          question: batchQuestion || undefined,
          context_source: 'photo',
          learning_lang_code: batchSourceCode,
          mother_lang_code: batchTargetCode,
          csrf_token: csrfToken,
        });
        if (!isFoundResult(response)) {
          patchCard(id, {
            state: 'not_found',
            detail: response.suggestions.length
              ? `Not found. Try: ${response.suggestions.join(', ')}`
              : 'Not found.',
          });
        } else {
          patchCard(id, { state: 'done', result: response });
          addedThisBatch += 1;
        }
      } catch (err) {
        patchCard(id, {
          state: 'error',
          detail: err instanceof ApiError ? err.message : 'Request failed',
        });
      }
    }

    photoSubmitting = false;
    if (addedThisBatch > 0) {
      notify(`${addedThisBatch} ${addedThisBatch === 1 ? 'entry' : 'entries'} defined and added to your pool.`, 'success');
      questionHint = '';
      try {
        const hist = await api.wordHistory(20);
        history = hist.entries;
      } catch {
        // non-fatal
      }
    }
  }

  async function undoCard(card: PhotoCard): Promise<void> {
    if (!card.result || card.undoing) return;
    patchCard(card.id, { undoing: true });
    try {
      const pair = `${card.result.learning_language_code}_${card.result.mother_tongue_code}`.toLowerCase();
      await api.deleteUserWord(card.result.word_id, pair, csrfToken);
      patchCard(card.id, { state: 'removed', undoing: false });
    } catch (err) {
      patchCard(card.id, { undoing: false });
      notify(err instanceof ApiError ? err.message : 'Could not remove the word', 'error');
    }
  }

  async function chooseCardSense(card: PhotoCard, senseId: number): Promise<void> {
    if (
      !card.result ||
      card.result.selected_sense_id === senseId ||
      card.selectingSenseId != null
    ) {
      return;
    }
    patchCard(card.id, { selectingSenseId: senseId });
    try {
      const update = await api.selectWordSense(card.result.lookup_id, senseId, csrfToken);
      patchCard(card.id, {
        result: { ...card.result, ...update },
        selectingSenseId: null,
      });
      const hist = await api.wordHistory(20);
      history = hist.entries;
      notify('Meaning updated for your lookup.', 'success');
    } catch (err) {
      patchCard(card.id, { selectingSenseId: null });
      notify(err instanceof ApiError ? err.message : 'Unable to change meaning', 'error');
    }
  }

  function resetPhoto(): void {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (croppedUrl) URL.revokeObjectURL(croppedUrl);
    previewUrl = '';
    croppedUrl = '';
    pickedFile = null;
    ocrConfidence = null;
    ocrWords = [];
    selectedTokens = new Set();
    selectionDrafts = {};
    photoPhase = 'idle';
  }

  onMount(load);
  onDestroy(() => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (croppedUrl) URL.revokeObjectURL(croppedUrl);
  });
</script>

<svelte:window on:keydown={handleKeydown} />

{#if loading}
  <section class="dashboard-grid loading-grid">
    <div class="glass-panel skeleton-card tall-skeleton"></div>
  </section>
{:else if error}
  <section class="glass-panel">
    <div class="feedback-banner error-banner">{error}</div>
  </section>
{:else}
  <section class="narrow-stack" in:fade={{ duration: 180 }}>
    <article class="glass-panel strong-panel trainer-card">
      <div class="card-help-row">
        <HelpTip label="How Add Word works">
          <h4>Add a word to your pool</h4>
          <p>
            Pick a <strong>direction</strong>, type a word in the source language, and the AI finds its
            canonical form, writes a definition, and generates 1–3 translations.
          </p>
          <p>
            The word is saved to your <strong>pool of words</strong>. By default it lands in your
            <strong>priority queue</strong> and unlocks gradually as you practice. In <strong>Settings</strong>
            you can switch this — turn on <em>“Force-add new words directly to the active pool”</em> to make new
            words available for practice right away.
          </p>
          <p>
            You can use <strong>any combination</strong> of your languages, including the same one twice for
            a definition-only lookup. Use the <strong>⇄</strong> button to flip a bilingual direction.
          </p>
          <div class="keyboard-shortcut-help">
            <p>Keyboard shortcuts:</p>
            <ul>
              <li><kbd>E</kbd>/<kbd>S</kbd>/<kbd>R</kbd>/<kbd>F</kbd> — source language</li>
              <li><kbd>Shift</kbd> + those — target language</li>
              <li><kbd>Ctrl</kbd>+<kbd>Space</kbd> — swap direction</li>
            </ul>
          </div>
          <p>
            <strong>Optional context</strong> sharpens ambiguous words. Use the drawers below to review history,
            manage saved words, or add a pair manually without the AI.
          </p>
          <p>
            <strong>You get</strong> also controls the definition language. Choose the same language for
            <strong>You type</strong> and <strong>You get</strong> for a monolingual definition—an immersion
            exercise recommended for advanced learners.
          </p>
          <p>
            <strong>Take a photo</strong> reads printed text on your own server (nothing leaves it), then places
            selectable boxes directly over the words. Tap one word, or tap neighbouring words to translate one
            compound word. Nearby text is used only as context so the AI picks the right meaning. If recognition
            misses a letter, correct the editable selection preview before translating.
          </p>
        </HelpTip>
      </div>

      <form class="answer-form" on:submit|preventDefault={fireTranslate} style="margin-top: 0.5rem;">
        <div class="toggle-group">
          <DirectionPicker
            bind:this={directionRef}
            bind:sourceCode
            bind:targetCode
            {languages}
            sourceLabel="You type"
            targetLabel="You get"
            disabled={entryBusy}
            allowSameLanguage
          />
          {#if exampleLine}
            <p class="example-line">{exampleLine}</p>
          {/if}
        </div>

        {#if photoPhase === 'idle'}
          <div class="question-stage" style="margin-top: 1.25rem;">
            <p class="eyebrow">Word or compound word</p>
            <input
              bind:this={wordInput}
              class="answer-input"
              bind:value={inputText}
              type="text"
              placeholder="e.g. ephemeral"
              disabled={adding}
              style="font-size: 1.1rem;"
            />
          </div>

          <!-- Photo row (Experiment 05, option A): camera opens on the first tap -->
          <div class="photo-row">
            <button class="photo-main-btn" type="button" disabled={entryBusy} on:click={startPhotoCapture}>
              <svg class="photo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                <circle cx="12" cy="13" r="4" />
              </svg>
              Take a photo
            </button>
            <button class="photo-side-btn" type="button" disabled={entryBusy} title="Choose from library" aria-label="Choose from library" on:click={() => libraryInput?.click()}>
              <svg class="photo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <path d="m21 15-5-5L5 21" />
              </svg>
            </button>
          </div>

          <div style="margin-top: 0.75rem;">
            <p class="eyebrow">Optional context</p>
            <input
              class="answer-input"
              bind:value={contextHint}
              type="text"
              maxlength={CONTEXT_MAX_CHARS}
              placeholder="e.g. 'in academic writing' or 'bank — riverside, not financial'"
              disabled={adding}
            />
          </div>

          <div style="margin-top: 0.75rem;">
            <p class="eyebrow">Optional question</p>
            <input
              class="answer-input"
              bind:value={questionHint}
              type="text"
              maxlength={CONTEXT_MAX_CHARS}
              placeholder="e.g. Why does this word have this meaning here?"
              disabled={adding}
            />
          </div>

          <div class="translate-play" style="margin-top: 1.25rem;">
            {#if theme === 'arcade'}
              <PlayGrid
                bind:this={translateGridRef}
                label={sameLanguageLookup ? 'DEFINE' : 'TRANSLATE'}
                rows={3}
                cell={18}
                gap={5}
                fontSize={11}
                resetAfterFire
                disabled={entryBusy || !inputText.trim() || !sourceCode || !targetCode}
                on:fire={() => void addWord()}
              />
            {:else if theme === 'light'}
              <PlayClear
                bind:this={translateClearRef}
                label={sameLanguageLookup ? 'DEFINE' : 'TRANSLATE'}
                rows={3}
                cell={18}
                gap={5}
                fontSize={11}
                resetAfterFire
                disabled={entryBusy || !inputText.trim() || !sourceCode || !targetCode}
                on:fire={() => void addWord()}
              />
            {:else}
              <PlaySaffronRelay
                bind:this={translateRelayRef}
                label={sameLanguageLookup ? '⌕ DEFINE' : '⌕ TRANSLATE'}
                icon={false}
                width={225}
                height={64}
                fontSize={11}
                resetAfterFire
                disabled={entryBusy || !inputText.trim() || !sourceCode || !targetCode}
                on:fire={() => void addWord()}
              />
            {/if}
          </div>
          <p class="translate-note" class:translating={adding}>
            {adding
              ? sameLanguageLookup ? 'Defining…' : 'Translating…'
              : sameLanguageLookup
                ? `AI defines it in ${languageName(targetCode)} and saves it to My Words`
                : `AI translates it, writes a ${languageName(targetCode)} definition, and queues it for practice`}
          </p>
        {/if}
      </form>

      <input
        bind:this={cameraInput}
        type="file"
        accept="image/*"
        capture="environment"
        class="visually-hidden-input"
        on:change={handlePhotoFile}
      />
      <input
        bind:this={libraryInput}
        type="file"
        accept="image/*"
        class="visually-hidden-input"
        on:change={handlePhotoFile}
      />

      {#if photoPhase === 'crop'}
        <div class="crop-wrap" in:fade={{ duration: 150 }}>
          <p class="eyebrow" style="margin-top: 0.75rem;">Crop to the text</p>
          <div class="crop-stage" bind:this={cropStage}>
            <img src={previewUrl} alt="To crop" draggable="false" />
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div
              class="crop-box"
              style={`left:${crop.x * 100}%; top:${crop.y * 100}%; width:${crop.w * 100}%; height:${crop.h * 100}%;`}
              on:pointerdown={(e) => cropPointerDown('move', e)}
              on:pointermove={cropPointerMove}
              on:pointerup={cropPointerUp}
              on:pointercancel={cropPointerUp}
            >
              {#each ['nw', 'ne', 'sw', 'se'] as corner}
                <button
                  type="button"
                  class={`crop-handle crop-${corner}`}
                  aria-label={`Resize crop (${corner})`}
                  on:pointerdown|stopPropagation={(e) => cropPointerDown(corner, e)}
                  on:pointermove={cropPointerMove}
                  on:pointerup={cropPointerUp}
                  on:pointercancel={cropPointerUp}
                ></button>
              {/each}
            </div>
          </div>
          <div class="review-actions">
            <button class="primary-button" type="button" on:click={() => void readText()}>
              Scan this area
            </button>
            <button class="ghost-button" type="button" on:click={cancelCrop}>Cancel</button>
          </div>
        </div>
      {:else if photoPhase === 'reading'}
        <div class="reading-stage">
          {#if croppedUrl || previewUrl}
            <div class="reading-photo">
              <img class="photo-preview" src={croppedUrl || previewUrl} alt="Captured text" />
              <span class="photo-scan-line" aria-hidden="true"></span>
            </div>
          {/if}
          <p class="translate-note translating">Reading the text…</p>
        </div>
      {:else if photoPhase === 'review'}
        <div class="review-stage" in:fly={{ y: 20, duration: 200 }}>
          <div class="photo-review-heading">
            <div>
              <p class="eyebrow">Select from the photo</p>
              <p class="photo-instruction">Tap a word. Select neighbours for one compound word.</p>
            </div>
            {#if ocrWords.length > 0}
              <span class="detected-count">{ocrWords.length} detected</span>
            {/if}
          </div>

          {#if croppedUrl || previewUrl}
            <div class="photo-word-stage" class:photo-busy={photoSubmitting}>
              <img class="photo-select-image" src={croppedUrl || previewUrl} alt="Captured text with selectable words" />
              {#if ocrWords.length > 0}
                <div class="word-box-layer" role="group" aria-label="Detected words on the photo">
                  {#each ocrWords as word, i}
                    <button
                      type="button"
                      class="photo-word-box"
                      class:photo-word-box-on={selectedTokens.has(i)}
                      class:photo-word-box-uncertain={word.confidence < 60}
                      style={wordBoxStyle(word)}
                      aria-label={`${selectedTokens.has(i) ? 'Deselect' : 'Select'} ${word.text}${word.confidence < 60 ? ', recognition uncertain' : ''}`}
                      aria-pressed={selectedTokens.has(i)}
                      title={word.text}
                      disabled={photoSubmitting}
                      on:click={() => toggleToken(i)}
                    ></button>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}

          {#if ocrConfidence !== null && ocrConfidence < 60}
            <div class="feedback-banner info-banner">
              Some text was hard to read. Check dashed selections in the editable preview before translating.
            </div>
          {/if}

          <div class="photo-tool-row">
            <button class="photo-tool-button" type="button" disabled={photoSubmitting} on:click={openCrop}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <path d="M6 2v14a2 2 0 0 0 2 2h14M2 6h14a2 2 0 0 1 2 2v14" />
              </svg>
              Crop & rescan
            </button>
            <button class="photo-tool-button" type="button" disabled={photoSubmitting} on:click={startPhotoCapture}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                <circle cx="12" cy="13" r="4" />
              </svg>
              New photo
            </button>
            <button class="photo-tool-button photo-tool-search" type="button" disabled={photoSubmitting} on:click={() => void startWordSearch()}>
              Search a word
            </button>
          </div>

          {#if selectionPreviews.length > 0}
            <div class="selection-preview-panel" in:fade={{ duration: 140 }}>
              <div class="selection-preview-heading">
                <p class="eyebrow">Selected word preview</p>
                <span>Editable</span>
              </div>
              <div class="selection-preview-list">
                {#each selectionPreviews as preview, i (preview.key)}
                  <label class="selection-preview-row">
                    <span>
                      {preview.indices.length > 1
                        ? 'Compound word'
                        : selectionPreviews.length > 1
                          ? `Word ${i + 1}`
                          : 'Selected word'}
                    </span>
                    <input
                      class="selection-preview-input"
                      type="text"
                      dir="auto"
                      value={preview.value}
                      maxlength={WORD_MAX_CHARS}
                      autocomplete="off"
                      spellcheck="true"
                      disabled={photoSubmitting}
                      aria-label={`Edit ${preview.indices.length > 1 ? 'compound word' : `selected word ${i + 1}`}`}
                      on:input={(event) => updateSelectionDraft(preview.key, event)}
                    />
                  </label>
                {/each}
              </div>
              <p class="selection-preview-note">
                This exact text will be {sameLanguageLookup ? 'defined' : 'translated'}.
                Nearby text is used separately as context and is not shown here.
              </p>
            </div>
          {/if}

          <div style="margin-top: 0.75rem;">
            <p class="eyebrow">Optional context</p>
            <input
              class="answer-input"
              bind:value={contextHint}
              type="text"
              maxlength={CONTEXT_MAX_CHARS}
              placeholder="e.g. a legal term, or the name of the object in the photo"
              disabled={photoSubmitting}
            />
            <p class="photo-context-note">Your note is combined with the nearby photographed text.</p>
          </div>

          <div style="margin-top: 0.75rem;">
            <p class="eyebrow">Optional question about the selected word</p>
            <input
              class="answer-input"
              bind:value={questionHint}
              type="text"
              maxlength={CONTEXT_MAX_CHARS}
              placeholder="The photographed text stays context; write your question here."
              disabled={photoSubmitting}
            />
          </div>

          <div class="photo-commit-bar">
            <div class="selection-summary" aria-live="polite">
              <strong>{selectedEntryLabel}</strong>
              <span>{selectedTokens.size > 0 ? 'Edit the preview if OCR missed a letter.' : 'Choose directly on the photo.'}</span>
            </div>
            <button
              class="primary-button photo-translate-button"
              type="button"
              disabled={selectedTokens.size === 0 || selectionPreviewInvalid || photoSubmitting}
              on:click={() => void submitSelected()}
            >
              {photoSubmitting
                ? sameLanguageLookup ? 'Defining…' : 'Translating…'
                : sameLanguageLookup ? 'Define & add' : 'Translate & add'}
            </button>
          </div>
        </div>
      {/if}
    </article>

    {#each photoCards as card (card.id)}
      <article
        class="glass-panel word-card"
        aria-live="polite"
        in:fly={{ y: 20, duration: 200 }}
      >
        {#if card.state === 'loading'}
          <div class="word-card-head">
            <h3>{card.word}</h3>
            <span class="translate-note translating">Looking it up…</span>
          </div>
        {:else if card.state === 'removed'}
          <div class="word-card-head removed-row">
            <h3 class="removed-word">{card.word}</h3>
            <span class="translate-note">Removed from your pool.</span>
          </div>
        {:else if card.state === 'not_found' || card.state === 'error'}
          <div class="word-card-head">
            <h3>{card.word}</h3>
            <span class="pill-chip warn-pill">{card.state === 'not_found' ? 'not found' : 'error'}</span>
          </div>
          <p class="card-detail">{card.detail}</p>
        {:else if card.result}
          <div class="word-card-head">
            <div>
              <p class="eyebrow">
                {card.result.lookup_mode === 'definition'
                  ? `${languageName(card.result.definition_language_code)} definition`
                  : `${languageName(card.result.learning_language_code)} → ${languageName(card.result.mother_tongue_code)}`}
              </p>
              <h3>{card.result.text}</h3>
            </div>
            <button
              class="ghost-button undo-button"
              type="button"
              disabled={card.undoing}
              on:click={() => void undoCard(card)}
            >
              {card.undoing ? 'Removing…' : 'Undo'}
            </button>
          </div>

          {#if card.result.status === 'corrected'}
            <div class="feedback-banner info-banner" style="margin-top: 0.4rem;">
              Read as <strong>“{card.result.original_input}”</strong> → saved as <strong>“{card.result.text}”</strong>.
            </div>
          {/if}

          <div class="list-stack" style="margin-top: 0.6rem;">
            {#if card.result.natives.length}
              <div class="lead-translation">
                <p class="eyebrow">Translation</p>
                <strong>{card.result.natives[0].translation}</strong>
                {#if card.result.natives[0].note}
                  <p class="card-detail">{card.result.natives[0].note}</p>
                {/if}
              </div>
            {/if}

            {#if card.result.sense_candidates.length > 1}
              <div>
                <p class="eyebrow">
                  Meaning suggested from the photo context · {languageName(card.result.definition_language_code)}
                </p>
                <div class="list-stack">
                  {#each card.result.sense_candidates as candidate}
                    <button
                      class="ghost-button"
                      type="button"
                      disabled={card.selectingSenseId != null || candidate.id === card.result.selected_sense_id}
                      on:click={() => void chooseCardSense(card, candidate.id)}
                    >
                      {#if candidate.part_of_speech}
                        <span>{candidate.part_of_speech}: </span>
                      {/if}
                      <span
                        lang={card.result.definition_language_code.toLowerCase()}
                        dir="auto"
                      >
                        {candidate.definition}
                      </span>
                      <span>
                        {candidate.id === card.selectingSenseId
                          ? ' — updating…'
                          : candidate.id === card.result.selected_sense_id ? ' — selected' : ''}
                      </span>
                    </button>
                  {/each}
                </div>
              </div>
            {/if}

            {#if card.result.question_answer}
              <div class="feedback-banner info-banner">
                <p class="eyebrow">Answer to your question</p>
                <p class="card-detail">{card.result.question_answer}</p>
              </div>
            {/if}

            <div>
              <p class="eyebrow">
                Definition · {languageName(card.result.definition_language_code)}
              </p>
              <p
                class="card-detail"
                lang={card.result.definition_language_code.toLowerCase()}
                dir="auto"
              >
                {card.result.display_definition.text}
              </p>
            </div>

            {#if card.result.natives.length > 1}
              <div>
                <p class="eyebrow">Other senses</p>
                {#each card.result.natives.slice(1) as native}
                  <p class="card-detail">
                    <strong>{native.translation}</strong>{#if native.note} — <em>{native.note}</em>{/if}
                  </p>
                {/each}
              </div>
            {/if}

            {#if card.result.general_note}
              <p class="card-detail"><em>{card.result.general_note}</em></p>
            {/if}

            {#if card.result.lexical.synonyms?.length}
              <div>
                <p class="eyebrow">Synonyms</p>
                <table class="syn-table">
                  <thead>
                    <tr>
                      <th>{languageName(card.result.mother_tongue_code)}</th>
                      <th>{languageName(card.result.learning_language_code)}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each card.result.lexical.synonyms as syn}
                      <tr>
                        <td>{syn.gloss || '—'}</td>
                        <td>{syn.text}</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {/if}

            {#if card.result.lexical.examples?.length}
              <div>
                <p class="eyebrow">Examples</p>
                <ul class="example-list">
                  {#each card.result.lexical.examples as ex}
                    <li>{ex}</li>
                  {/each}
                </ul>
              </div>
            {/if}
          </div>
        {/if}
      </article>
    {/each}

    {#if photoPhase === 'review' && photoCards.length > 0 && !photoSubmitting}
      <article class="glass-panel next-entry-card" in:fade={{ duration: 150 }}>
        <div>
          <p class="eyebrow">Keep adding</p>
          <strong>Use this photo again, search normally, or take a fresh photo.</strong>
        </div>
        <div class="next-entry-actions">
          <button class="secondary-button" type="button" disabled={entryBusy} on:click={() => void startWordSearch()}>
            Search a word
          </button>
          <button class="ghost-button" type="button" disabled={entryBusy} on:click={startPhotoCapture}>
            Take another photo
          </button>
        </div>
      </article>
    {/if}

    {#if notFound}
      <article
        class="glass-panel"
        aria-live="polite"
        in:fly={{ y: 20, duration: 200 }}
      >
        <div class="section-head">
          <div>
            <p class="eyebrow">Not found</p>
            <h2>"{notFound.original_input}"</h2>
          </div>
          <span class="pill-chip">{notFound.learning_language_code}</span>
        </div>
        <p class="section-copy">
          We couldn't find that word in <strong>{languageName(notFound.learning_language_code)}</strong>. Check the
          spelling, or pick one of the suggestions below.
        </p>

        {#if notFound.suggestions.length}
          <p class="eyebrow" style="margin-top: 0.75rem;">Did you mean?</p>
          <div class="tag-row">
            {#each notFound.suggestions as s}
              <button class="option-chip" type="button" on:click={() => trySuggestion(s)}>
                {s}
              </button>
            {/each}
          </div>
        {/if}

        <div class="trainer-actions" style="margin-top: 1rem;">
          <button class="ghost-button" type="button" on:click={() => void startWordSearch()}>Search another word</button>
          <button class="ghost-button" type="button" on:click={startPhotoCapture}>Take a photo</button>
        </div>
      </article>
    {/if}

    {#if result}
      <article class="glass-panel" in:fly={{ y: 20, duration: 200 }}>
        <div class="section-head">
          <div>
            <p class="eyebrow">
              {result.lookup_mode === 'definition'
                ? `${languageName(result.definition_language_code)} definition`
                : `${result.learning_language_code} → ${result.mother_tongue_code}`}
              {#if result.status === 'corrected'}· corrected{/if}
              {#if result.status === 'ambiguous'}· multiple senses{/if}
            </p>
            <h2>{result.text}</h2>
          </div>
          {#if result.force_unlocked}
            <span class="pill-chip reward-pill">unlocked now</span>
          {:else if !result.practice_eligible}
            <span class="pill-chip">saved definition</span>
          {:else}
            <span class="pill-chip">queued</span>
          {/if}
        </div>

        {#if result.status === 'corrected'}
          <div class="feedback-banner info-banner" style="margin-top: 0.5rem;">
            We corrected <strong>"{result.original_input}"</strong> → <strong>"{result.text}"</strong>.
          </div>
        {/if}

        {#if detectedMismatch}
          <div class="feedback-banner info-banner" style="margin-top: 0.5rem;">
            That looked like <strong>{languageName(result.detected_input_language ?? '')}</strong>. Want to switch the
            target language and try again?
            <button class="ghost-button" type="button" disabled={entryBusy} on:click={swapDetected} style="margin-left: 0.5rem;">
              Switch target → {languageName(result.detected_input_language ?? '')}
            </button>
          </div>
        {/if}

        <div class="list-stack" style="margin-top: 0.5rem;">
          {#if result.natives.length}
            <div class="closest-translation">
              <p class="eyebrow">(Closest) Translation</p>
              <strong>{result.natives[0].translation}</strong>
              {#if result.natives[0].note}
                <p>{result.natives[0].note}</p>
              {/if}
            </div>
          {/if}

          {#if result.sense_candidates.length > 1}
            <div>
              <p class="eyebrow">
                Meaning suggested from your context · {languageName(result.definition_language_code)}
              </p>
              <p style="margin: 0 0 0.5rem; opacity: 0.75;">
                Check the selected meaning; choose another with one click if needed.
              </p>
              <div class="list-stack">
                {#each result.sense_candidates as candidate}
                  <button
                    class="ghost-button"
                    type="button"
                    disabled={selectingSenseId !== null || candidate.id === result.selected_sense_id}
                    on:click={() => void chooseResultSense(candidate.id)}
                  >
                    {#if candidate.part_of_speech}
                      <span>{candidate.part_of_speech}: </span>
                    {/if}
                    <span
                      lang={result.definition_language_code.toLowerCase()}
                      dir="auto"
                    >
                      {candidate.definition}
                    </span>
                    <span>
                      {candidate.id === selectingSenseId
                        ? ' — updating…'
                        : candidate.id === result.selected_sense_id ? ' — selected' : ''}
                    </span>
                  </button>
                {/each}
              </div>
            </div>
          {/if}

          {#if result.question_answer}
            <div class="feedback-banner info-banner">
              <p class="eyebrow">Answer to your question</p>
              <p>{result.question_answer}</p>
            </div>
          {/if}

          <div>
            <p class="eyebrow">
              Definition · {languageName(result.definition_language_code)}
            </p>
            <p
              lang={result.definition_language_code.toLowerCase()}
              dir="auto"
            >
              {result.display_definition.text}
            </p>
          </div>

          {#if result.natives.length > 1}
            <div>
              <p class="eyebrow">Other senses</p>
              <div class="list-stack">
                {#each result.natives.slice(1) as native}
                  <div class="list-row">
                    <div>
                      <strong>{native.translation}</strong>
                      {#if native.note}
                        <p style="opacity: 0.75; margin: 0.15rem 0 0;"><em>{native.note}</em></p>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}

          {#if result.general_note}
            <div>
              <p class="eyebrow">Note</p>
              <p><em>{result.general_note}</em></p>
            </div>
          {/if}

          {#if result.lexical.synonyms?.length}
            <div>
              <p class="eyebrow">Synonyms</p>
              <table class="syn-table">
                <thead>
                  <tr>
                    <th>{languageName(result.mother_tongue_code)}</th>
                    <th>{languageName(result.learning_language_code)}</th>
                  </tr>
                </thead>
                <tbody>
                  {#each result.lexical.synonyms as syn}
                    <tr>
                      <td>{syn.gloss || '—'}</td>
                      <td>{syn.text}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}

          {#if result.lexical.examples?.length}
            <div>
              <p class="eyebrow">Examples</p>
              <ul style="margin: 0; padding-left: 1.25rem;">
                {#each result.lexical.examples as ex}
                  <li style="margin-bottom: 0.25rem;">{ex}</li>
                {/each}
              </ul>
            </div>
          {/if}

          {#if result.suggested_tags?.length}
            <div>
              <p class="eyebrow">Tags</p>
              <div class="tag-row">
                {#each result.suggested_tags as t}
                  <span class="mini-tag">{t}</span>
                {/each}
              </div>
            </div>
          {/if}

          {#if result.lexical.extended_content}
            <div>
              <p class="eyebrow">
                More info · {languageName(result.learning_language_code)}
              </p>
              <div class="more-info-content">
                {@html renderMoreInfoMarkdown(result.lexical.extended_content)}
              </div>
            </div>
          {/if}
        </div>

        <div class="trainer-actions" style="margin-top: 1rem;">
          <button
            class="secondary-button"
            type="button"
            on:click={expand}
            disabled={expanding || !!result.lexical.extended_content || !result.reportable}
            title={result.lexical.extended_content ? 'Already expanded' : ''}
          >
            {expanding ? 'Loading…' : 'More info'}
          </button>
          {#if result.reportable}
            <button
              class="ghost-button"
              type="button"
              on:click={reportResult}
            >
              Report
            </button>
          {/if}
          <button class="ghost-button" type="button" disabled={entryBusy} on:click={() => void startWordSearch()}>
            Search another word
          </button>
          <button class="ghost-button" type="button" disabled={entryBusy} on:click={startPhotoCapture}>Take a photo</button>
        </div>

        {#if reportTarget}
          <div class="glass-panel" style="margin-top: 0.75rem; padding: 0.75rem;">
            <p class="eyebrow">
              Reporting the {reportTarget.entry_type === 'lexical' ? 'definition' : 'translation'}
            </p>
            <input
              class="answer-input"
              bind:value={reportReason}
              type="text"
              placeholder="Optional: what's wrong?"
            />
            <div class="hero-actions" style="margin-top: 0.5rem;">
              <button class="primary-button" type="button" on:click={submitReport}>Submit</button>
              <button
                class="ghost-button"
                type="button"
                on:click={() => {
                  reportTarget = null;
                  reportReason = '';
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        {/if}
      </article>
    {/if}

    <article class="glass-panel drawer-card">
      <details open={historyOpen} on:toggle={(e) => (historyOpen = (e.currentTarget as HTMLDetailsElement).open)}>
        <summary class="drawer-summary">
          <div>
            <p class="eyebrow">History</p>
            <span class="drawer-title">Recent searches</span>
          </div>
          <span class="pill-chip">{history.length}</span>
          <span class="drawer-caret" aria-hidden="true">{historyOpen ? '▾' : '▸'}</span>
        </summary>
        {#if history.length === 0}
          <p class="empty-copy" style="margin: 0.75rem 0 0;">Your recent searches will appear here.</p>
        {:else}
        <div class="history-list" style="margin-top: 0.75rem;">
          {#each history as entry}
            <div class="history-item" class:history-open={expandedHistoryId === entry.added_id}>
              <button
                class="history-summary"
                type="button"
                on:click={() => (expandedHistoryId = expandedHistoryId === entry.added_id ? null : entry.added_id)}
                aria-expanded={expandedHistoryId === entry.added_id}
              >
                <div class="history-summary-text">
                  <strong>{entry.text}</strong>
                  <span class="history-meta">
                    {entry.learning_language_code}→{entry.mother_tongue_code}
                    {#if entry.natives.length}· {entry.natives[0].translation}{/if}
                  </span>
                </div>
                <span class="history-caret">{expandedHistoryId === entry.added_id ? '▾' : '▸'}</span>
              </button>
              {#if expandedHistoryId === entry.added_id}
                <div class="history-body">
                  {#if entry.display_definition.text}
                    <div>
                      <p class="eyebrow">
                        Definition · {languageName(entry.definition_language_code)}
                      </p>
                      <p
                        class="history-def"
                        lang={entry.definition_language_code.toLowerCase()}
                        dir="auto"
                      >
                        {entry.display_definition.text}
                      </p>
                    </div>
                  {/if}
                  {#if entry.context}
                    <div>
                      <p class="eyebrow">Your context</p>
                      <p class="history-def">{entry.context}</p>
                    </div>
                  {/if}
                  {#if entry.question}
                    <div>
                      <p class="eyebrow">Your question</p>
                      <p class="history-def">{entry.question}</p>
                      {#if entry.question_answer}
                        <p class="history-def"><strong>Answer:</strong> {entry.question_answer}</p>
                      {/if}
                    </div>
                  {/if}
                  {#if entry.natives.length}
                    <div>
                      <p class="eyebrow">Translation{entry.natives.length > 1 ? 's' : ''}</p>
                      {#each entry.natives as n}
                        <p style="margin: 0.1rem 0;">
                          <strong>{n.translation}</strong>
                          {#if n.note}<em style="opacity: 0.7;">— {n.note}</em>{/if}
                        </p>
                      {/each}
                    </div>
                  {/if}
                  {#if entry.lexical.synonyms?.length}
                    <div>
                      <p class="eyebrow">Synonyms</p>
                      <table class="syn-table">
                        <thead>
                          <tr>
                            <th>{languageName(entry.mother_tongue_code)}</th>
                            <th>{languageName(entry.learning_language_code)}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {#each entry.lexical.synonyms as syn}
                            <tr>
                              <td>{syn.gloss || '—'}</td>
                              <td>{syn.text}</td>
                            </tr>
                          {/each}
                        </tbody>
                      </table>
                    </div>
                  {/if}
                  {#if entry.lexical.examples?.length}
                    <div>
                      <p class="eyebrow">Examples</p>
                      <ul style="margin: 0; padding-left: 1.1rem;">
                        {#each entry.lexical.examples as ex}
                          <li>{ex}</li>
                        {/each}
                      </ul>
                    </div>
                  {/if}
                  {#if entry.lexical.extended_content}
                    <div>
                      <p class="eyebrow">More info</p>
                      <div class="more-info-content compact">
                        {@html renderMoreInfoMarkdown(entry.lexical.extended_content)}
                      </div>
                    </div>
                  {/if}
                  {#if entry.tags?.length}
                    <div class="tag-row">
                      {#each entry.tags as t}<span class="mini-tag">{t}</span>{/each}
                    </div>
                  {/if}
                </div>
              {/if}
            </div>
          {/each}
        </div>
        {/if}
      </details>
    </article>

    <article class="glass-panel drawer-card">
      <details open={manageOpen} on:toggle={(e) => (manageOpen = (e.currentTarget as HTMLDetailsElement).open)}>
        <summary class="drawer-summary">
          <div>
            <p class="eyebrow">Manage</p>
            <span class="drawer-title">My words</span>
          </div>
          <span class="pill-chip muted-tag">{manageLearning || '—'}→{manageMother || '—'}</span>
          <span class="drawer-caret" aria-hidden="true">{manageOpen ? '▾' : '▸'}</span>
        </summary>
        <div style="margin-top: 0.75rem;">
          <div class="lang-pair-row">
            <div>
              <p class="eyebrow">You type</p>
              <select class="answer-input" bind:value={manageLearning}>
                {#each languages as lang}
                  <option value={lang.code}>{lang.name}</option>
                {/each}
              </select>
            </div>
            <div>
              <p class="eyebrow">You get</p>
              <select class="answer-input" bind:value={manageMother}>
                {#each languages as lang}
                  <option value={lang.code}>{lang.name}</option>
                {/each}
              </select>
            </div>
          </div>

          {#if manageLoading}
            <p class="empty-copy" style="margin-top: 0.75rem;">Loading…</p>
          {:else if !manageEntries.length}
            <p class="empty-copy" style="margin-top: 0.75rem;">No words for this pair yet.</p>
          {:else}
            <div class="word-rows">
              {#each manageEntries as entry (entry.word_id)}
                <div class="word-row">
                  <div class="word-cell word-cell-source">{entry.text}</div>
                  <div class="word-cell word-cell-arrow" aria-hidden="true">{entry.lookup_mode === 'definition' ? '≔' : '→'}</div>
                  <div class="word-cell word-cell-target">
                    {entry.lookup_mode === 'definition' ? entry.definition ?? 'Definition saved' : entry.translation ?? '—'}
                  </div>
                  <div class="word-cell word-cell-meta">
                    {#if entry.in_progress}
                      <span class="mini-tag" title={entry.unlocked ? 'In active rotation' : 'Locked'}>{entry.unlocked ? 'active' : 'locked'}</span>
                    {:else if entry.lookup_mode === 'definition'}
                      <span class="mini-tag muted-tag" title="Saved definition">saved</span>
                    {:else}
                      <span class="mini-tag muted-tag" title="Queued for unlock">queued</span>
                    {/if}
                  </div>
                  <button
                    class="trash-button"
                    type="button"
                    on:click={() => removeWord(entry)}
                    title="Remove from this pair"
                    aria-label="Remove"
                  >
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M4 7h16"></path>
                      <path d="M10 4h4a1 1 0 0 1 1 1v2H9V5a1 1 0 0 1 1-1Z"></path>
                      <path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12"></path>
                      <path d="M10 11v6M14 11v6"></path>
                    </svg>
                  </button>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </details>
    </article>

    <article class="glass-panel drawer-card">
      <details open={offlineOpen} on:toggle={(e) => (offlineOpen = (e.currentTarget as HTMLDetailsElement).open)}>
        <summary class="drawer-summary">
          <div>
            <p class="eyebrow">Manual</p>
            <span class="drawer-title">Add word offline</span>
          </div>
          <span class="pill-chip muted-tag">no AI</span>
          <span class="drawer-caret" aria-hidden="true">{offlineOpen ? '▾' : '▸'}</span>
        </summary>
        <form class="offline-form" on:submit|preventDefault={submitOfflineAdd} style="margin-top: 0.75rem;">
          <div class="lang-pair-row">
            <div>
              <p class="eyebrow">Learning</p>
              <select class="answer-input" bind:value={offlineLearningLang} disabled={offlineSaving}>
                {#each languages as lang}
                  <option value={lang.code} disabled={lang.code === offlineMotherLang}>{lang.name}</option>
                {/each}
              </select>
            </div>
            <div>
              <p class="eyebrow">Mother</p>
              <select class="answer-input" bind:value={offlineMotherLang} disabled={offlineSaving}>
                {#each languages as lang}
                  <option value={lang.code} disabled={lang.code === offlineLearningLang}>{lang.name}</option>
                {/each}
              </select>
            </div>
          </div>
          <div class="lang-pair-row" style="margin-top: 0.6rem;">
            <div>
              <p class="eyebrow">{offlineLearningLang || 'Word'}</p>
              <input class="answer-input" bind:value={offlineLearning} placeholder="word" disabled={offlineSaving} />
            </div>
            <div>
              <p class="eyebrow">{offlineMotherLang || 'Translation'}</p>
              <input class="answer-input" bind:value={offlineNative} placeholder="translation" disabled={offlineSaving} />
            </div>
          </div>
          <button
            class="secondary-button"
            type="submit"
            disabled={offlineSaving || !offlineLearning.trim() || !offlineNative.trim() || !offlineLearningLang || !offlineMotherLang || offlineLearningLang === offlineMotherLang}
            style="margin-top: 0.75rem;"
          >
            {offlineSaving ? 'Adding…' : 'Add to queue'}
          </button>
        </form>
      </details>
    </article>
  </section>
{/if}

<style>
  /* Synonyms as a two-column table: target language | source language. */
  .syn-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 0.35rem;
    font-size: 0.95rem;
  }

  .syn-table th {
    text-align: left;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--muted);
    padding: 0.3rem 0.6rem;
    border-bottom: 1px solid var(--line);
  }

  .syn-table td {
    padding: 0.35rem 0.6rem;
    border-bottom: 1px solid color-mix(in srgb, var(--line) 55%, transparent);
  }

  .syn-table tr:last-child td {
    border-bottom: none;
  }

  .card-help-row {
    display: flex;
    justify-content: flex-end;
  }

  .visually-hidden-input {
    position: absolute;
    width: 1px;
    height: 1px;
    opacity: 0;
    pointer-events: none;
  }

  /* Photo row (Experiment 05, option A): camera + library side by side */
  .photo-row {
    display: flex;
    gap: 0.5rem;
    align-items: stretch;
    margin-top: 0.6rem;
  }

  .photo-icon {
    width: 19px;
    height: 19px;
    flex-shrink: 0;
  }

  .photo-main-btn {
    flex: 1;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    border: 1px solid color-mix(in srgb, var(--accent) 45%, transparent);
    border-radius: 12px;
    padding: 0.65rem 0.9rem;
    background: color-mix(in srgb, var(--accent-soft) 140%, transparent);
    color: var(--text);
    font-weight: 600;
    font-size: 0.95rem;
    cursor: pointer;
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .photo-side-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 0.65rem 0.8rem;
    background: color-mix(in srgb, var(--surface-strong) 85%, transparent);
    color: var(--muted);
    cursor: pointer;
    transition: color 0.2s, border-color 0.2s;
  }

  .photo-main-btn:disabled,
  .photo-side-btn:disabled {
    opacity: 0.55;
    cursor: default;
  }

  @media (hover: hover) {
    .photo-main-btn:not(:disabled):hover {
      border-color: var(--accent);
      box-shadow: 0 4px 14px -6px color-mix(in srgb, var(--accent) 45%, transparent);
    }

    .photo-side-btn:not(:disabled):hover {
      color: var(--text);
      border-color: color-mix(in srgb, var(--accent) 45%, transparent);
    }
  }

  .photo-preview {
    max-width: 100%;
    max-height: 220px;
    border-radius: 12px;
    object-fit: contain;
    display: block;
    margin: 0.75rem auto 0;
  }

  .reading-stage {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    margin-top: 1rem;
  }

  .reading-photo {
    position: relative;
    max-width: 100%;
    overflow: hidden;
    border-radius: 12px;
  }

  .reading-photo .photo-preview {
    margin: 0;
  }

  .photo-scan-line {
    position: absolute;
    z-index: 1;
    inset-inline: 4%;
    top: 0;
    height: 2px;
    border-radius: 999px;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.92) 24%, var(--accent) 50%, rgba(255, 255, 255, 0.92) 76%, transparent);
    box-shadow: 0 0 18px 3px color-mix(in srgb, var(--accent) 62%, transparent);
    animation: photo-scan 1.45s cubic-bezier(0.45, 0, 0.55, 1) infinite alternate;
  }

  @keyframes photo-scan {
    from { top: 4%; }
    to { top: 96%; }
  }

  /* --- crop --- */
  .crop-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .crop-stage {
    position: relative;
    display: inline-block;
    max-width: 100%;
    margin-top: 0.5rem;
    border-radius: 12px;
    overflow: hidden;
    line-height: 0;
    touch-action: none;
  }

  .crop-stage img {
    display: block;
    max-width: 100%;
    max-height: 55vh;
    user-select: none;
    -webkit-user-select: none;
  }

  .crop-box {
    position: absolute;
    border: 2px solid var(--accent);
    border-radius: 6px;
    box-shadow: 0 0 0 9999px rgba(8, 8, 14, 0.55);
    cursor: move;
    touch-action: none;
  }

  .crop-handle {
    position: absolute;
    width: 28px;
    height: 28px;
    padding: 0;
    background: transparent;
    border: none;
    cursor: pointer;
    touch-action: none;
  }

  .crop-handle::after {
    content: '';
    position: absolute;
    inset: 4px;
    border: 3px solid var(--accent);
    background: color-mix(in srgb, var(--surface-strong) 85%, transparent);
    border-radius: 6px;
  }

  .crop-nw { left: -14px; top: -14px; cursor: nwse-resize; }
  .crop-ne { right: -14px; top: -14px; cursor: nesw-resize; }
  .crop-sw { left: -14px; bottom: -14px; cursor: nesw-resize; }
  .crop-se { right: -14px; bottom: -14px; cursor: nwse-resize; }

  .review-stage {
    margin-top: 1rem;
  }

  .photo-review-heading {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.65rem;
  }

  .photo-review-heading .eyebrow,
  .photo-instruction {
    margin: 0;
  }

  .photo-instruction {
    margin-top: 0.18rem;
    color: var(--muted);
    font-size: 0.9rem;
    line-height: 1.35;
  }

  .detected-count {
    flex: 0 0 auto;
    border: 1px solid color-mix(in srgb, var(--line) 78%, transparent);
    border-radius: 999px;
    padding: 0.22rem 0.52rem;
    background: color-mix(in srgb, var(--surface-strong) 72%, transparent);
    color: var(--muted);
    font-size: 0.72rem;
    font-weight: 650;
    letter-spacing: 0.025em;
  }

  .photo-word-stage {
    position: relative;
    width: 100%;
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--line-strong) 72%, transparent);
    border-radius: 16px;
    background: #08111f;
    box-shadow:
      0 20px 44px -30px rgba(3, 9, 18, 0.88),
      inset 0 1px 0 rgba(255, 255, 255, 0.12);
    line-height: 0;
    isolation: isolate;
    touch-action: pan-x pan-y pinch-zoom;
  }

  .photo-select-image {
    display: block;
    width: 100%;
    height: auto;
    user-select: none;
    -webkit-user-select: none;
  }

  .word-box-layer {
    position: absolute;
    z-index: 2;
    inset: 0;
    pointer-events: none;
    transition: opacity 160ms ease;
  }

  .photo-busy .word-box-layer {
    opacity: 0.48;
  }

  .photo-word-box {
    position: absolute;
    z-index: 1;
    min-width: 2px;
    min-height: 2px;
    margin: 0;
    padding: 0;
    border: 1px solid rgba(255, 255, 255, 0.82);
    border-radius: 5px;
    background: rgba(8, 17, 31, 0.035);
    box-shadow:
      0 0 0 1px rgba(5, 12, 24, 0.38),
      inset 0 1px 0 rgba(255, 255, 255, 0.2);
    cursor: pointer;
    pointer-events: auto;
    -webkit-tap-highlight-color: transparent;
    transform: scale(1);
    transition:
      transform 150ms cubic-bezier(0.2, 0.8, 0.2, 1),
      border-color 150ms ease,
      background 150ms ease,
      box-shadow 150ms ease;
  }

  .photo-word-box::after {
    content: '';
    position: absolute;
    inset: 1px 2px auto;
    height: 1px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.38);
    opacity: 0;
    transition: opacity 150ms ease;
  }

  .photo-word-box-on {
    z-index: 3;
    border-color: color-mix(in srgb, var(--accent) 80%, white);
    background:
      linear-gradient(135deg, rgba(255, 255, 255, 0.24), color-mix(in srgb, var(--accent) 25%, rgba(255, 255, 255, 0.08)));
    box-shadow:
      0 0 0 1px color-mix(in srgb, var(--accent) 56%, rgba(255, 255, 255, 0.35)),
      0 5px 16px -7px color-mix(in srgb, var(--accent) 86%, transparent),
      inset 0 1px 0 rgba(255, 255, 255, 0.72);
    -webkit-backdrop-filter: saturate(145%) contrast(108%);
    backdrop-filter: saturate(145%) contrast(108%);
    transform: scale(1.045);
  }

  .photo-word-box-on::after {
    opacity: 1;
  }

  .photo-word-box-uncertain:not(.photo-word-box-on) {
    border-color: #f5a524;
    border-style: dashed;
  }

  .photo-word-box:focus-visible {
    z-index: 4;
    outline: 3px solid color-mix(in srgb, var(--accent) 78%, white);
    outline-offset: 2px;
  }

  @media (hover: hover) {
    .photo-word-box:not(:disabled):hover {
      z-index: 3;
      border-color: color-mix(in srgb, var(--accent) 64%, white);
      background: rgba(255, 255, 255, 0.14);
      transform: scale(1.035);
    }
  }

  .photo-tool-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.3rem;
    margin-top: 0.45rem;
  }

  .photo-tool-button {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border: 0;
    border-radius: 8px;
    padding: 0.4rem 0.52rem;
    background: transparent;
    color: var(--muted);
    font: inherit;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    transition: color 140ms ease, background 140ms ease;
  }

  .photo-tool-button svg {
    width: 15px;
    height: 15px;
  }

  .photo-tool-button:last-child {
    margin-left: auto;
  }

  .photo-tool-button:hover {
    color: var(--text);
    background: color-mix(in srgb, var(--surface-strong) 72%, transparent);
  }

  .photo-tool-button:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
  }

  .photo-tool-button:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .selection-preview-panel {
    margin-top: 0.55rem;
    padding: 0.75rem 0.8rem;
    border: 1px solid color-mix(in srgb, var(--line) 72%, transparent);
    border-radius: 12px;
    background:
      linear-gradient(90deg, color-mix(in srgb, var(--accent) 72%, transparent) 0 2px, transparent 2px),
      color-mix(in srgb, var(--surface-strong) 62%, transparent);
  }

  .selection-preview-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .selection-preview-heading .eyebrow {
    margin: 0;
  }

  .selection-preview-heading > span {
    border-radius: 999px;
    padding: 0.14rem 0.45rem;
    background: color-mix(in srgb, var(--accent-soft) 78%, transparent);
    color: var(--accent-strong);
    font-size: 0.67rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .selection-preview-list {
    display: grid;
    gap: 0.5rem;
    margin-top: 0.55rem;
  }

  .selection-preview-row {
    display: grid;
    grid-template-columns: minmax(6.8rem, 0.38fr) minmax(0, 1fr);
    align-items: center;
    gap: 0.65rem;
  }

  .selection-preview-row > span {
    color: var(--muted);
    font-size: 0.76rem;
    font-weight: 650;
  }

  .selection-preview-input {
    min-width: 0;
    width: 100%;
    border: 1px solid color-mix(in srgb, var(--line-strong) 82%, transparent);
    border-radius: 9px;
    padding: 0.52rem 0.65rem;
    background: color-mix(in srgb, var(--surface) 84%, transparent);
    color: var(--text);
    font: inherit;
    font-size: 0.96rem;
    font-weight: 650;
    line-height: 1.2;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.12);
    transition: border-color 140ms ease, box-shadow 140ms ease;
  }

  .selection-preview-input:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow:
      0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent),
      inset 0 1px 0 rgba(255, 255, 255, 0.16);
  }

  .selection-preview-input:disabled {
    opacity: 0.64;
  }

  .selection-preview-note {
    margin: 0.5rem 0 0;
    color: var(--muted);
    font-size: 0.72rem;
    line-height: 1.35;
  }

  .photo-context-note {
    margin: 0.32rem 0 0;
    color: var(--muted);
    font-size: 0.72rem;
    line-height: 1.35;
  }

  .photo-commit-bar {
    position: sticky;
    z-index: 6;
    bottom: 0.75rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-top: 0.8rem;
    padding: 0.65rem 0.7rem 0.65rem 0.85rem;
    border: 1px solid color-mix(in srgb, var(--line-strong) 72%, transparent);
    border-radius: 14px;
    background: color-mix(in srgb, var(--surface-strong) 82%, transparent);
    box-shadow:
      0 14px 30px -20px rgba(3, 9, 18, 0.72),
      inset 0 1px 0 rgba(255, 255, 255, 0.16);
    -webkit-backdrop-filter: blur(18px) saturate(145%);
    backdrop-filter: blur(18px) saturate(145%);
  }

  .selection-summary {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.08rem;
    line-height: 1.25;
  }

  .selection-summary strong {
    color: var(--text);
    font-size: 0.87rem;
  }

  .selection-summary span {
    color: var(--muted);
    font-size: 0.72rem;
  }

  .photo-translate-button {
    flex: 0 0 auto;
    min-width: 9.5rem;
    margin: 0;
  }

  @media (max-width: 560px) {
    .photo-review-heading {
      gap: 0.55rem;
    }

    .detected-count {
      font-size: 0.66rem;
    }

    .photo-commit-bar {
      position: static;
      align-items: stretch;
      flex-direction: column;
      gap: 0.55rem;
      padding: 0.7rem;
    }

    .photo-translate-button {
      width: 100%;
    }

    .selection-preview-row {
      grid-template-columns: 1fr;
      gap: 0.25rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .photo-scan-line {
      top: 50%;
      animation: none;
    }

    .word-box-layer,
    .photo-word-box,
    .photo-word-box::after {
      transition: none;
    }
  }

  .review-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-top: 1.25rem;
    align-items: center;
    justify-content: center;
  }

  .next-entry-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    border-color: color-mix(in srgb, var(--accent) 28%, var(--line));
  }

  .next-entry-card .eyebrow {
    margin: 0 0 0.2rem;
  }

  .next-entry-card strong {
    color: var(--text);
    font-size: 0.92rem;
  }

  .next-entry-actions {
    display: flex;
    flex: 0 0 auto;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  @media (max-width: 620px) {
    .next-entry-card,
    .next-entry-actions {
      align-items: stretch;
      flex-direction: column;
    }
  }

  /* --- photo definition cards --- */
  .word-card-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .word-card-head h3 {
    margin: 0.1rem 0 0;
    font-family: var(--display);
    font-size: 1.3rem;
  }

  .undo-button {
    flex-shrink: 0;
  }

  .card-detail {
    margin: 0.15rem 0 0;
    opacity: 0.88;
    line-height: 1.45;
  }

  .lead-translation strong {
    font-size: 1.15rem;
  }

  .removed-word {
    text-decoration: line-through;
    opacity: 0.6;
  }

  .removed-row {
    align-items: baseline;
  }

  .warn-pill {
    color: var(--danger, #d5573a);
    border-color: color-mix(in srgb, var(--danger, #d5573a) 45%, transparent);
  }

  .example-list {
    margin: 0.25rem 0 0;
    padding-left: 1.25rem;
  }

  .example-list li {
    margin-bottom: 0.25rem;
  }

  .translate-play {
    display: flex;
    justify-content: center;
  }

  .translate-note {
    text-align: center;
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--muted);
    margin: 0.6rem 0 0;
    min-height: 1.1rem;
  }

  .translate-note.translating {
    color: var(--accent-strong);
    animation: translate-pulse 1.2s ease-in-out infinite;
  }

  @keyframes translate-pulse {
    0%, 100% { opacity: 0.55; }
    50% { opacity: 1; }
  }

  .example-line {
    margin: 0.6rem 0 0;
    font-size: 0.88rem;
    color: var(--muted);
  }

  .closest-translation {
    border: 1px solid color-mix(in srgb, var(--accent) 36%, transparent);
    border-radius: 1.25rem;
    padding: 1.15rem;
    background: linear-gradient(
      135deg,
      color-mix(in srgb, var(--accent-soft) 210%, transparent),
      color-mix(in srgb, var(--accent-2) 12%, transparent)
    );
  }

  .closest-translation strong {
    display: block;
    margin-top: 0.35rem;
    font-size: clamp(1.55rem, 6vw, 2.35rem);
    line-height: 1.08;
    color: var(--text);
  }

  .closest-translation p:last-child {
    margin: 0.65rem 0 0;
    color: var(--muted);
  }

  .more-info-content {
    display: flex;
    flex-direction: column;
    gap: 0.7rem;
    line-height: 1.65;
  }
  .more-info-content.compact {
    gap: 0.45rem;
    line-height: 1.55;
  }
  .more-info-content :global(p) {
    margin: 0;
  }
  .more-info-content :global(ul) {
    margin: 0;
    padding-left: 1.2rem;
  }
  .more-info-content :global(li) {
    margin: 0.2rem 0;
  }
  .more-info-content :global(strong) {
    color: var(--text);
    font-weight: 700;
  }

  .history-list {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }
  .history-item {
    border-radius: 0.75rem;
    transition: background 120ms ease;
  }
  .history-item:hover {
    background: var(--accent-soft);
  }
  .history-summary {
    width: 100%;
    background: transparent;
    border: 0;
    padding: 0.55rem 0.6rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    cursor: pointer;
    font: inherit;
    color: inherit;
    text-align: left;
  }
  .history-summary-text {
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }
  .history-meta {
    font-size: 0.8rem;
    opacity: 0.7;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .history-caret {
    opacity: 0.55;
    flex-shrink: 0;
  }
  .history-body {
    padding: 0.25rem 0.7rem 0.85rem;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
    font-size: 0.9rem;
  }
  .history-def {
    margin: 0;
  }

  .drawer-card {
    padding: 0.85rem 1rem;
  }
  .drawer-card details > summary {
    list-style: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }
  .drawer-card details > summary::-webkit-details-marker { display: none; }
  .drawer-title {
    font-size: 1.05rem;
    font-weight: 600;
  }
  .drawer-summary p.eyebrow {
    margin: 0 0 0.1rem;
  }

  .drawer-caret {
    color: var(--muted);
    flex-shrink: 0;
  }

  .lang-pair-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
  }

  .word-rows {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    margin-top: 0.6rem;
    max-height: 22rem;
    overflow-y: auto;
  }
  .word-row {
    display: grid;
    grid-template-columns: 1fr auto 1fr auto auto;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.5rem;
    border-radius: 0.5rem;
    font-size: 0.9rem;
  }
  .word-row:hover {
    background: var(--accent-soft);
  }
  .word-cell {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .word-cell-source {
    font-weight: 600;
  }
  .word-cell-arrow {
    opacity: 0.45;
    flex-shrink: 0;
  }
  .word-cell-target {
    opacity: 0.85;
  }
  .word-cell-meta {
    flex-shrink: 0;
  }
  .trash-button {
    background: transparent;
    border: 0;
    padding: 0.25rem;
    cursor: pointer;
    color: inherit;
    opacity: 0.5;
    display: inline-flex;
    border-radius: 0.4rem;
    transition: opacity 120ms ease, color 120ms ease, background 120ms ease;
  }
  .trash-button:hover {
    opacity: 1;
    color: var(--danger, #c44);
    background: color-mix(in srgb, var(--danger, #c44) 12%, transparent);
  }
</style>
