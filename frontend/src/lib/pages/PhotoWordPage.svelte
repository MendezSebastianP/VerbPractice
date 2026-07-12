<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import HelpTip from '../components/HelpTip.svelte';
  import { navigate } from '../router';
  import type { AddWordResponse, AddedWordResult, LanguageEntry, UserSettings } from '../types';

  export let csrfToken = '';
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;

  const MAX_UPLOAD_DIMENSION = 1600;
  const CONTEXT_MAX_CHARS = 512;
  const WORD_MAX_CHARS = 128;
  const MIN_CROP = 0.08;

  type Phase = 'capture' | 'crop' | 'reading' | 'review';

  interface WordCard {
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

  let loading = true;
  let error = '';
  let languages: LanguageEntry[] = [];
  let settings: UserSettings | null = null;

  let sourceCode = '';
  let targetCode = '';
  let sourceTileOpen = false;
  let targetTileOpen = false;

  let phase: Phase = 'capture';
  let submitting = false;
  let cameraInput: HTMLInputElement | null = null;
  let libraryInput: HTMLInputElement | null = null;
  let pickedFile: File | null = null;
  let previewUrl = '';
  let croppedUrl = '';
  let extractedText = '';
  let ocrConfidence: number | null = null;
  let selected = new Set<number>();
  let cards: WordCard[] = [];
  let nextCardId = 1;

  // --- crop state: fractions of the displayed image ---
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

  function languageName(code: string): string {
    return languages.find((l) => l.code.toLowerCase() === code.toLowerCase())?.name ?? code;
  }

  function isFoundResult(payload: AddWordResponse): payload is AddedWordResult {
    return payload.status !== 'not_found';
  }

  async function load(): Promise<void> {
    loading = true;
    error = '';
    try {
      const [langs, s] = await Promise.all([api.listLanguages(), api.getSettings()]);
      languages = langs.languages;
      settings = s;
      sourceCode = s.learning_language?.code ?? languages[0]?.code ?? '';
      targetCode = s.mother_tongue?.code ?? languages.find((l) => l.code !== sourceCode)?.code ?? '';
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to load';
    } finally {
      loading = false;
    }
  }

  onMount(load);
  onDestroy(() => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (croppedUrl) URL.revokeObjectURL(croppedUrl);
  });

  function handleFile(event: Event): void {
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
    phase = 'crop';
  }

  // --- crop interactions (pointer events cover mouse + touch) ---
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
    phase = 'reading';
    cards = [];
    selected = new Set();
    try {
      const blob = await cropAndScale();
      if (croppedUrl) URL.revokeObjectURL(croppedUrl);
      croppedUrl = URL.createObjectURL(blob);
      const response = await api.ocrExtract(blob, sourceCode.toLowerCase(), csrfToken);
      if (!response.text.trim()) {
        notify('No text found — try a closer shot or a tighter crop.', 'error');
        phase = 'crop';
        return;
      }
      extractedText = response.text;
      ocrConfidence = response.mean_confidence;
      phase = 'review';
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to read the photo', 'error');
      phase = 'crop';
    }
  }

  function toggle(index: number): void {
    const next = new Set(selected);
    if (next.has(index)) {
      next.delete(index);
    } else {
      next.add(index);
    }
    selected = next;
  }

  function handleTextEdited(): void {
    // Token indices shift when the text changes; a stale selection would tag the wrong words.
    if (selected.size > 0) selected = new Set();
  }

  function patchCard(id: number, patch: Partial<WordCard>): void {
    cards = cards.map((c) => (c.id === id ? { ...c, ...patch } : c));
  }

  async function submitSelected(): Promise<void> {
    if (selected.size === 0 || submitting) return;
    if (!sourceCode || !targetCode || sourceCode === targetCode) {
      notify('Text and translation languages must differ.', 'error');
      return;
    }

    const context = extractedText.trim().replace(/\s+/g, ' ').slice(0, CONTEXT_MAX_CHARS);
    const words = [...selected].sort((a, b) => a - b).map((i) => tokens[i]?.word ?? '').filter(Boolean);
    submitting = true;
    selected = new Set();

    for (const word of words) {
      const id = nextCardId++;
      cards = [...cards, { id, word, state: 'loading' }];
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

    submitting = false;
    const added = cards.filter((c) => c.state === 'done').length;
    if (added > 0) {
      notify(`${added} word${added === 1 ? '' : 's'} defined and added to your pool.`, 'success');
    }
  }

  async function undoCard(card: WordCard): Promise<void> {
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

  function reset(): void {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (croppedUrl) URL.revokeObjectURL(croppedUrl);
    previewUrl = '';
    croppedUrl = '';
    pickedFile = null;
    extractedText = '';
    ocrConfidence = null;
    selected = new Set();
    cards = [];
    phase = 'capture';
  }
</script>

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
        <HelpTip label="How Photo Word works">
          <h4>Add words from any text</h4>
          <p>
            Subtitles, a book page, a menu, a sign — <strong>photograph the text</strong> and the server
            reads it locally (no photo leaves your mini PC).
          </p>
          <p>
            Crop to the text you care about, then tap the words you don't know — the
            <strong>surrounding sentence is sent as context</strong>, which helps the AI pick the right
            meaning. Fix any misread letters in the text box first; the chips follow your edits.
          </p>
        </HelpTip>
      </div>

      <div class="toggle-group" style="margin-top: 0.5rem;">
        <span class="toggle-label">Direction</span>
        <div class="lang-direction">
          <div class="tile-wrap">
            <button
              type="button"
              class="option-chip option-on lang-tile"
              on:click={() => { sourceTileOpen = !sourceTileOpen; targetTileOpen = false; }}
            >
              {languageName(sourceCode) || '—'}
              <small>text</small>
            </button>
            {#if sourceTileOpen}
              <div class="glass-panel lang-menu">
                {#each languages as lang}
                  <button
                    class="option-chip"
                    type="button"
                    on:click={() => { sourceCode = lang.code; sourceTileOpen = false; }}
                    disabled={lang.code === targetCode}
                  >
                    {lang.name}
                  </button>
                {/each}
              </div>
            {/if}
          </div>

          <div class="tile-wrap">
            <button
              type="button"
              class="option-chip option-on lang-tile"
              on:click={() => { targetTileOpen = !targetTileOpen; sourceTileOpen = false; }}
            >
              {languageName(targetCode) || '—'}
              <small>you get</small>
            </button>
            {#if targetTileOpen}
              <div class="glass-panel lang-menu">
                {#each languages as lang}
                  <button
                    class="option-chip"
                    type="button"
                    on:click={() => { targetCode = lang.code; targetTileOpen = false; }}
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

      <input
        bind:this={cameraInput}
        type="file"
        accept="image/*"
        capture="environment"
        class="visually-hidden-input"
        on:change={handleFile}
      />
      <input
        bind:this={libraryInput}
        type="file"
        accept="image/*"
        class="visually-hidden-input"
        on:change={handleFile}
      />

      {#if phase === 'capture'}
        <div class="capture-stage">
          <button class="primary-button capture-button" type="button" on:click={() => cameraInput?.click()}>
            <svg class="button-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
            Photograph the text
          </button>
          <button class="ghost-button" type="button" on:click={() => libraryInput?.click()}>
            Choose from library
          </button>
          <p class="translate-note">The photo is read on your own server — nothing is uploaded elsewhere.</p>
        </div>
      {:else if phase === 'crop'}
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
            <button class="ghost-button" type="button" on:click={reset}>Retake</button>
          </div>
        </div>
      {:else if phase === 'reading'}
        <div class="capture-stage">
          {#if croppedUrl || previewUrl}
            <img class="photo-preview" src={croppedUrl || previewUrl} alt="Captured text" />
          {/if}
          <p class="translate-note translating">Reading the text…</p>
        </div>
      {:else}
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
            disabled={submitting}
          ></textarea>

          <p class="eyebrow" style="margin-top: 0.75rem;">Tap the words you want to learn</p>
          <p class="word-flow" role="group" aria-label="Tap words to select them">
            {#each tokens as token, i}
              <button
                type="button"
                class="flow-word"
                class:flow-on={selected.has(i)}
                disabled={submitting}
                on:click={() => toggle(i)}
              >{token.raw}</button>
            {/each}
          </p>

          <div class="review-actions">
            <button
              class="primary-button"
              type="button"
              disabled={selected.size === 0 || submitting}
              on:click={() => void submitSelected()}
            >
              {submitting
                ? 'Looking up…'
                : `Define & add ${selected.size || ''} word${selected.size === 1 ? '' : 's'}`}
            </button>
            <button class="ghost-button" type="button" disabled={submitting} on:click={reset}>
              Take another photo
            </button>
          </div>
        </div>
      {/if}
    </article>

    {#each cards as card (card.id)}
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

    {#if cards.length > 0}
      <button class="ghost-button" type="button" on:click={() => navigate('/add-word')}>
        Open Add Word
      </button>
    {/if}
  </section>
{/if}

<style>
  .visually-hidden-input {
    position: absolute;
    width: 1px;
    height: 1px;
    opacity: 0;
    pointer-events: none;
  }

  .capture-stage {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    margin-top: 1.5rem;
  }

  .capture-button {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 1.05rem;
    padding: 1rem 1.5rem;
  }

  .button-icon {
    width: 22px;
    height: 22px;
    flex-shrink: 0;
  }

  .photo-preview {
    max-width: 100%;
    max-height: 220px;
    border-radius: 12px;
    object-fit: contain;
    display: block;
    margin: 0.75rem auto 0;
  }

  /* --- crop --- */
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

  .crop-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

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

  /* --- definition cards --- */
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
</style>
