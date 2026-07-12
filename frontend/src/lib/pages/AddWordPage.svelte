<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import DirectionPicker from '../components/DirectionPicker.svelte';
  import HelpTip from '../components/HelpTip.svelte';
  import PlayGrid from '../components/PlayGrid.svelte';
  import PlayMist from '../components/PlayMist.svelte';
  import type {
    AddWordResponse,
    AddedWordNotFound,
    AddedWordResult,
    LanguageEntry,
    ThemeName,
    UserSettings,
    UserWordEntry,
    WordHistoryEntry,
  } from '../types';

  export let csrfToken = '';
  export let theme: ThemeName = 'light';
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;

  let translateMistRef: PlayMist | null = null;
  let translateGridRef: PlayGrid | null = null;

  let loading = true;
  let error = '';
  let languages: LanguageEntry[] = [];
  let settings: UserSettings | null = null;

  let inputText = '';
  let contextHint = '';
  let adding = false;

  // Source → target language pair (any combination). Source = the language you
  // type the word in; target = the language you want the translation in.
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

  // --- Photo capture (Playground Experiment 05, option A: photo row under the
  // input). Photograph text → crop → server OCR → tap the words to add; the
  // surrounding sentence rides along as context. ---
  const MAX_UPLOAD_DIMENSION = 1600;
  const CONTEXT_MAX_CHARS = 512;
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
  }

  interface Token {
    raw: string;
    word: string;
  }

  let photoPhase: PhotoPhase = 'idle';
  let photoSubmitting = false;
  let cameraInput: HTMLInputElement | null = null;
  let libraryInput: HTMLInputElement | null = null;
  let pickedFile: File | null = null;
  let previewUrl = '';
  let croppedUrl = '';
  let extractedText = '';
  let ocrConfidence: number | null = null;
  let selectedTokens = new Set<number>();
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

  // Chips derive from the *edited* text so OCR fixes flow straight into them.
  $: tokens = extractedText
    .split(/\s+/)
    .map((raw): Token => ({ raw, word: raw.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '') }))
    .filter((t) => t.word.length > 0);

  $: managePair = manageLearning && manageMother
    ? `${manageLearning.toLowerCase()}_${manageMother.toLowerCase()}`
    : '';
  $: if (manageOpen && managePair && managePair !== manageLoadedPair && !manageLoading) {
    void loadManage();
  }

  $: exampleLine =
    sourceCode && targetCode && EXAMPLE_WORD[sourceCode] && EXAMPLE_WORD[targetCode]
      ? `Type “${EXAMPLE_WORD[sourceCode]}” and you’ll get “${EXAMPLE_WORD[targetCode]}”.`
      : '';
  $: detectedMismatch =
    !!result &&
    !!result.detected_input_language &&
    result.detected_input_language.toUpperCase() !== result.learning_language_code.toUpperCase() &&
    result.detected_input_language.toUpperCase() !== result.mother_tongue_code.toUpperCase();

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
      settings = s;
      // Default: from learning language → native (mother tongue), with a graceful
      // fallback to the first two available languages if prefs are unset.
      sourceCode = s.learning_language?.code ?? languages[0]?.code ?? '';
      targetCode = s.mother_tongue?.code ?? languages.find((l) => l.code !== sourceCode)?.code ?? '';
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
    if (adding || !inputText.trim()) {
      return;
    }
    if (theme === 'arcade') {
      translateGridRef?.fire();
    } else {
      translateMistRef?.fire();
    }
  }

  async function addWord(textOverride?: string): Promise<void> {
    const text = (textOverride ?? inputText).trim();
    if (!text) {
      return;
    }
    if (!settings?.mother_tongue) {
      notify('Set your mother tongue in Settings first.', 'error');
      return;
    }
    if (!sourceCode || !targetCode) {
      notify('Pick both languages.', 'error');
      return;
    }
    if (sourceCode === targetCode) {
      notify('Source and target languages must differ.', 'error');
      return;
    }
    adding = true;
    result = null;
    notFound = null;
    try {
      const response = await api.addWord({
        input_text: text,
        context: contextHint.trim() || undefined,
        learning_lang_code: sourceCode,
        mother_lang_code: targetCode,
        csrf_token: csrfToken,
      });
      if (isFoundResult(response)) {
        result = response;
        inputText = '';
        contextHint = '';
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
    expanding = true;
    try {
      const { extended_content } = await api.expandWord(result.word_id, csrfToken);
      result = { ...result, lexical: { ...result.lexical, extended_content } };
      notify('Added more info.', 'success');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to expand', 'error');
    } finally {
      expanding = false;
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
  }

  function reportResult(): void {
    if (!result) {
      return;
    }
    const primaryNative = result.natives[0];
    reportTarget = primaryNative
      ? { entry_type: 'native', entry_id: primaryNative.id }
      : { entry_type: 'lexical', entry_id: result.lexical.id };
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
    if (loading || adding) {
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

    // E/S/R/F set the source language; add Shift for the target (auto-swap on clash).
    const code = LANG_KEY[event.key.toLowerCase()];
    if (code) {
      event.preventDefault();
      if (event.shiftKey) {
        if (code === sourceCode) sourceCode = targetCode;
        targetCode = code;
      } else {
        if (code === targetCode) targetCode = sourceCode;
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
    pickedFile = file;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);
    crop = { x: 0.03, y: 0.03, w: 0.94, h: 0.94 };
    photoPhase = 'crop';
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
      extractedText = response.text;
      ocrConfidence = response.mean_confidence;
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
    selectedTokens = next;
  }

  function handleTextEdited(): void {
    // Token indices shift when the text changes; a stale selection would tag the wrong words.
    if (selectedTokens.size > 0) selectedTokens = new Set();
  }

  function patchCard(id: number, patch: Partial<PhotoCard>): void {
    photoCards = photoCards.map((c) => (c.id === id ? { ...c, ...patch } : c));
  }

  async function submitSelected(): Promise<void> {
    if (selectedTokens.size === 0 || photoSubmitting) return;
    if (!sourceCode || !targetCode || sourceCode === targetCode) {
      notify('Text and translation languages must differ.', 'error');
      return;
    }

    const context = extractedText.trim().replace(/\s+/g, ' ').slice(0, CONTEXT_MAX_CHARS);
    const words = [...selectedTokens].sort((a, b) => a - b).map((i) => tokens[i]?.word ?? '').filter(Boolean);
    photoSubmitting = true;
    selectedTokens = new Set();

    for (const word of words) {
      const id = nextCardId++;
      photoCards = [...photoCards, { id, word, state: 'loading' }];
      if (word.length > WORD_MAX_CHARS) {
        patchCard(id, { state: 'error', detail: 'Too long for a single word.' });
        continue;
      }
      try {
        const response = await api.addWord({
          input_text: word,
          context,
          learning_lang_code: sourceCode,
          mother_lang_code: targetCode,
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
        }
      } catch (err) {
        patchCard(id, {
          state: 'error',
          detail: err instanceof ApiError ? err.message : 'Request failed',
        });
      }
    }

    photoSubmitting = false;
    const added = photoCards.filter((c) => c.state === 'done').length;
    if (added > 0) {
      notify(`${added} word${added === 1 ? '' : 's'} defined and added to your pool.`, 'success');
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

  function resetPhoto(): void {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (croppedUrl) URL.revokeObjectURL(croppedUrl);
    previewUrl = '';
    croppedUrl = '';
    pickedFile = null;
    extractedText = '';
    ocrConfidence = null;
    selectedTokens = new Set();
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
            You can translate <strong>any combination</strong> of your languages. Use the <strong>⇄</strong>
            button to flip the direction. You may type in either language; if the AI detects you typed in the
            target language it offers to switch.
          </p>
          <p>Keyboard shortcuts:</p>
          <ul>
            <li><kbd>E</kbd>/<kbd>S</kbd>/<kbd>R</kbd>/<kbd>F</kbd> — source language</li>
            <li><kbd>Shift</kbd> + those — target language</li>
            <li><kbd>Ctrl</kbd>+<kbd>Space</kbd> — swap direction</li>
          </ul>
          <p>
            <strong>Optional context</strong> sharpens ambiguous words. Use the drawers below to review history,
            manage saved words, or add a pair manually without the AI.
          </p>
          <p>
            <strong>Take a photo</strong> reads printed text on your own server (nothing leaves it): crop to the
            text, tap the words you don't know, and the surrounding sentence is sent as context so the AI picks
            the right meaning. Fix any misread letters first — the word chips follow your edits.
          </p>
        </HelpTip>
      </div>

      {#if !settings?.mother_tongue}
        <div class="feedback-banner info-banner" style="margin-top: 0.75rem;">
          Set your mother tongue on the home page first.
        </div>
      {/if}

      <form class="answer-form" on:submit|preventDefault={fireTranslate} style="margin-top: 0.5rem;">
        <div class="toggle-group">
          <DirectionPicker
            bind:this={directionRef}
            bind:sourceCode
            bind:targetCode
            {languages}
            sourceLabel="You type"
            targetLabel="You get"
          />
          {#if exampleLine}
            <p class="example-line">{exampleLine}</p>
          {/if}
        </div>

        {#if photoPhase === 'idle'}
          <div class="question-stage" style="margin-top: 1.25rem;">
            <p class="eyebrow">Word or short phrase</p>
            <input
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
            <button class="photo-main-btn" type="button" on:click={() => cameraInput?.click()}>
              <svg class="photo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                <circle cx="12" cy="13" r="4" />
              </svg>
              Take a photo
            </button>
            <button class="photo-side-btn" type="button" title="Choose from library" aria-label="Choose from library" on:click={() => libraryInput?.click()}>
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
              placeholder="e.g. 'in academic writing' or 'bank — riverside, not financial'"
              disabled={adding}
            />
          </div>

          <div class="translate-play" style="margin-top: 1.25rem;">
            {#if theme === 'arcade'}
              <PlayGrid
                bind:this={translateGridRef}
                label="TRANSLATE"
                rows={3}
                cell={18}
                gap={5}
                fontSize={11}
                resetAfterFire
                disabled={adding || !inputText.trim() || !sourceCode || !targetCode || sourceCode === targetCode}
                on:fire={() => void addWord()}
              />
            {:else}
              <PlayMist
                bind:this={translateMistRef}
                {theme}
                label="⌕ TRANSLATE"
                width={300}
                height={64}
                fontSize={14}
                resetAfterFire
                disabled={adding || !inputText.trim() || !sourceCode || !targetCode || sourceCode === targetCode}
                on:fire={() => void addWord()}
              />
            {/if}
          </div>
          <p class="translate-note" class:translating={adding}>
            {adding ? 'Translating…' : 'AI looks it up, translates, and queues it for practice'}
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
              Read the text
            </button>
            <button class="ghost-button" type="button" on:click={resetPhoto}>Cancel</button>
          </div>
        </div>
      {:else if photoPhase === 'reading'}
        <div class="reading-stage">
          {#if croppedUrl || previewUrl}
            <img class="photo-preview" src={croppedUrl || previewUrl} alt="Captured text" />
          {/if}
          <p class="translate-note translating">Reading the text…</p>
        </div>
      {:else if photoPhase === 'review'}
        <div class="review-stage" in:fly={{ y: 20, duration: 200 }}>
          {#if croppedUrl || previewUrl}
            <img class="photo-preview" src={croppedUrl || previewUrl} alt="Captured text" />
          {/if}

          {#if ocrConfidence !== null && ocrConfidence < 60}
            <div class="feedback-banner info-banner">
              Low OCR confidence — double-check the text below before adding words.
            </div>
          {/if}

          <p class="eyebrow" style="margin-top: 0.75rem;">Extracted text (editable)</p>
          <textarea
            class="answer-input ocr-textarea"
            rows="3"
            bind:value={extractedText}
            on:input={handleTextEdited}
            disabled={photoSubmitting}
          ></textarea>

          <p class="eyebrow" style="margin-top: 0.75rem;">Tap the words you want to learn</p>
          <p class="word-flow" role="group" aria-label="Tap words to select them">
            {#each tokens as token, i}
              <button
                type="button"
                class="flow-word"
                class:flow-on={selectedTokens.has(i)}
                disabled={photoSubmitting}
                on:click={() => toggleToken(i)}
              >{token.raw}</button>
            {/each}
          </p>

          <div class="review-actions">
            <button
              class="primary-button"
              type="button"
              disabled={selectedTokens.size === 0 || photoSubmitting}
              on:click={() => void submitSelected()}
            >
              {photoSubmitting
                ? 'Looking up…'
                : `Define & add ${selectedTokens.size || ''} word${selectedTokens.size === 1 ? '' : 's'}`}
            </button>
            <button class="ghost-button" type="button" disabled={photoSubmitting} on:click={resetPhoto}>
              Done — back to typing
            </button>
          </div>
        </div>
      {/if}
    </article>

    {#each photoCards as card (card.id)}
      <article class="glass-panel word-card" in:fly={{ y: 20, duration: 200 }}>
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
                {languageName(card.result.learning_language_code)} → {languageName(card.result.mother_tongue_code)}
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

            <div>
              <p class="eyebrow">Definition</p>
              <p class="card-detail">{card.result.lexical.definition}</p>
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
                <div class="tag-row">
                  {#each card.result.lexical.synonyms as syn}
                    <span class="mini-tag" title={syn.gloss || ''}>{syn.text}</span>
                  {/each}
                </div>
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

    {#if notFound}
      <article class="glass-panel" in:fly={{ y: 20, duration: 200 }}>
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
          <button class="ghost-button" type="button" on:click={resetForAnother}>Start over</button>
        </div>
      </article>
    {/if}

    {#if result}
      <article class="glass-panel" in:fly={{ y: 20, duration: 200 }}>
        <div class="section-head">
          <div>
            <p class="eyebrow">
              {result.learning_language_code} → {result.mother_tongue_code}
              {#if result.status === 'corrected'}· corrected{/if}
              {#if result.status === 'ambiguous'}· multiple senses{/if}
            </p>
            <h2>{result.text}</h2>
          </div>
          {#if result.force_unlocked}
            <span class="pill-chip reward-pill">unlocked now</span>
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
            <button class="ghost-button" type="button" on:click={swapDetected} style="margin-left: 0.5rem;">
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

          <div>
            <p class="eyebrow">Definition</p>
            <p>{result.lexical.definition}</p>
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
              <div class="tag-row">
                {#each result.lexical.synonyms as syn}
                  <span class="mini-tag" title={syn.gloss || ''}>{syn.text}</span>
                {/each}
              </div>
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
              <p class="eyebrow">More info</p>
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
            disabled={expanding || !!result.lexical.extended_content}
            title={result.lexical.extended_content ? 'Already expanded' : ''}
          >
            {expanding ? 'Loading…' : 'More info'}
          </button>
          <button
            class="ghost-button"
            type="button"
            on:click={reportResult}
          >
            Report
          </button>
          <button class="ghost-button" type="button" on:click={resetForAnother}>
            Add another
          </button>
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
                  <p class="history-def">{entry.lexical.definition}</p>
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
                      <div class="tag-row">
                        {#each entry.lexical.synonyms as syn}
                          <span class="mini-tag" title={syn.gloss || ''}>{syn.text}</span>
                        {/each}
                      </div>
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
              <p class="eyebrow">Learning</p>
              <select class="answer-input" bind:value={manageLearning}>
                {#each languages as lang}
                  <option value={lang.code} disabled={lang.code === manageMother}>{lang.name}</option>
                {/each}
              </select>
            </div>
            <div>
              <p class="eyebrow">Mother</p>
              <select class="answer-input" bind:value={manageMother}>
                {#each languages as lang}
                  <option value={lang.code} disabled={lang.code === manageLearning}>{lang.name}</option>
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
                  <div class="word-cell word-cell-arrow" aria-hidden="true">→</div>
                  <div class="word-cell word-cell-target">{entry.translation ?? '—'}</div>
                  <div class="word-cell word-cell-meta">
                    {#if entry.in_progress}
                      <span class="mini-tag" title={entry.unlocked ? 'In active rotation' : 'Locked'}>{entry.unlocked ? 'active' : 'locked'}</span>
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

  @media (hover: hover) {
    .photo-main-btn:hover {
      border-color: var(--accent);
      box-shadow: 0 4px 14px -6px color-mix(in srgb, var(--accent) 45%, transparent);
    }

    .photo-side-btn:hover {
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

  .ocr-textarea {
    width: 100%;
    resize: vertical;
    font-size: 1.05rem;
    line-height: 1.4;
  }

  /* Ink-underline word selection (Playground experiment 03, option B). */
  .word-flow {
    margin: 0.35rem 0 0;
    padding: 0.85rem 1rem;
    border: 1px dashed var(--line);
    border-radius: 12px;
    background: color-mix(in srgb, var(--surface-strong) 55%, transparent);
    display: flex;
    flex-wrap: wrap;
    row-gap: 0.5rem;
    column-gap: 0;
    line-height: 1.5;
  }

  .flow-word {
    position: relative;
    border: none;
    background: transparent;
    color: var(--text);
    font: inherit;
    font-size: 1.08rem;
    padding: 0.18rem 0.3rem;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
    user-select: none;
    -webkit-user-select: none;
    transition: color 0.2s;
  }

  .flow-word::after {
    content: '';
    position: absolute;
    left: 0.25rem;
    right: 0.25rem;
    bottom: 0.05rem;
    height: 2.5px;
    border-radius: 2px;
    background: var(--accent);
    box-shadow: 0 0 8px color-mix(in srgb, var(--accent) 60%, transparent);
    transform: scaleX(0);
    transform-origin: left center;
    transition: transform 0.3s cubic-bezier(0.3, 1, 0.4, 1);
  }

  .flow-word.flow-on {
    color: var(--accent-strong);
  }

  .flow-word.flow-on::after {
    transform: scaleX(1);
  }

  .flow-word:disabled {
    cursor: default;
    opacity: 0.6;
  }

  .review-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-top: 1.25rem;
    align-items: center;
    justify-content: center;
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
