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

  type Phase = 'capture' | 'reading' | 'review' | 'submitting';

  interface WordOutcome {
    word: string;
    status: 'added' | 'corrected' | 'not_found' | 'error';
    detail: string;
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
  let fileInput: HTMLInputElement | null = null;
  let previewUrl = '';
  let extractedText = '';
  let ocrConfidence: number | null = null;
  let selected = new Set<number>();
  let outcomes: WordOutcome[] = [];

  interface Token {
    raw: string;
    word: string;
  }

  // Chips derive from the *edited* text so OCR fixes flow straight into them.
  $: tokens = extractedText
    .split(/\s+/)
    .map((raw): Token => ({ raw, word: raw.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '') }))
    .filter((t) => t.word.length > 0);

  function languageName(code: string): string {
    return languages.find((l) => l.code === code)?.name ?? code;
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
  });

  async function downscale(file: File): Promise<Blob> {
    try {
      const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
      const scale = Math.min(1, MAX_UPLOAD_DIMENSION / Math.max(bitmap.width, bitmap.height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(bitmap.width * scale);
      canvas.height = Math.round(bitmap.height * scale);
      const ctx = canvas.getContext('2d');
      if (!ctx) return file;
      ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      bitmap.close();
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85));
      return blob ?? file;
    } catch {
      // Older browsers: upload the original; the server downscales too.
      return file;
    }
  }

  async function handleFile(event: Event): Promise<void> {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    if (!sourceCode) {
      notify('Pick the subtitle language first.', 'error');
      return;
    }

    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);
    phase = 'reading';
    outcomes = [];
    selected = new Set();

    try {
      const blob = await downscale(file);
      const response = await api.ocrExtract(blob, sourceCode.toLowerCase(), csrfToken);
      if (!response.text.trim()) {
        notify('No text found — try a closer, steadier shot.', 'error');
        phase = 'capture';
        return;
      }
      extractedText = response.text;
      ocrConfidence = response.mean_confidence;
      phase = 'review';
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to read the photo', 'error');
      phase = 'capture';
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

  async function submitSelected(): Promise<void> {
    if (selected.size === 0) return;
    if (!settings?.mother_tongue) {
      notify('Set your mother tongue in Settings first.', 'error');
      return;
    }
    if (!sourceCode || !targetCode || sourceCode === targetCode) {
      notify('Subtitle and translation languages must differ.', 'error');
      return;
    }

    const context = extractedText.trim().replace(/\s+/g, ' ').slice(0, CONTEXT_MAX_CHARS);
    const words = [...selected].sort((a, b) => a - b).map((i) => tokens[i]?.word ?? '').filter(Boolean);
    phase = 'submitting';
    outcomes = [];

    for (const word of words) {
      if (word.length > WORD_MAX_CHARS) {
        outcomes = [...outcomes, { word, status: 'error', detail: 'Too long for a single word.' }];
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
          outcomes = [
            ...outcomes,
            {
              word,
              status: 'not_found',
              detail: response.suggestions.length ? `Not found. Try: ${response.suggestions.join(', ')}` : 'Not found.',
            },
          ];
        } else if (response.status === 'corrected') {
          const translation = response.natives[0]?.translation ?? '';
          outcomes = [
            ...outcomes,
            { word, status: 'corrected', detail: `Saved as “${response.text}”${translation ? ` — ${translation}` : ''}` },
          ];
        } else {
          const translation = response.natives[0]?.translation ?? '';
          outcomes = [
            ...outcomes,
            { word, status: 'added', detail: translation ? `${response.text} — ${translation}` : response.text },
          ];
        }
      } catch (err) {
        outcomes = [
          ...outcomes,
          { word, status: 'error', detail: err instanceof ApiError ? err.message : 'Request failed' },
        ];
      }
    }

    const addedCount = outcomes.filter((o) => o.status === 'added' || o.status === 'corrected').length;
    const failedCount = outcomes.length - addedCount;
    if (addedCount && !failedCount) {
      notify(`Added ${addedCount} word${addedCount === 1 ? '' : 's'} to your pool.`, 'success');
    } else if (addedCount) {
      notify(`Added ${addedCount}, ${failedCount} need attention.`, 'info');
    } else {
      notify('No words were added — check the results below.', 'error');
    }
    selected = new Set();
    phase = 'review';
  }

  function reset(): void {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = '';
    extractedText = '';
    ocrConfidence = null;
    selected = new Set();
    outcomes = [];
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
          <h4>Add words from TV subtitles</h4>
          <p>
            Watching something with subtitles? <strong>Photograph the subtitle line</strong> and the server
            reads the text locally (no photo leaves your mini PC).
          </p>
          <p>
            Tap the words you don't know — the <strong>whole sentence is sent as context</strong>, which helps
            the AI pick the right meaning. Fix any misread letters in the text box first; the chips follow your edits.
          </p>
          <p>Get close, hold steady, and keep the subtitle line horizontal for the best read.</p>
        </HelpTip>
      </div>

      {#if !settings?.mother_tongue}
        <div class="feedback-banner info-banner" style="margin-top: 0.75rem;">
          Set your mother tongue on the home page first.
        </div>
      {/if}

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
              <small>subtitles</small>
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
        bind:this={fileInput}
        type="file"
        accept="image/*"
        capture="environment"
        class="visually-hidden-input"
        on:change={handleFile}
      />

      {#if phase === 'capture'}
        <div class="capture-stage">
          <button class="primary-button capture-button" type="button" on:click={() => fileInput?.click()}>
            📷 Take a photo of the subtitles
          </button>
          <p class="translate-note">The photo is read on your own server — nothing is uploaded elsewhere.</p>
        </div>
      {:else if phase === 'reading'}
        <div class="capture-stage">
          {#if previewUrl}
            <img class="photo-preview" src={previewUrl} alt="Captured subtitles" />
          {/if}
          <p class="translate-note translating">Reading subtitles…</p>
        </div>
      {:else}
        <div class="review-stage" in:fly={{ y: 20, duration: 200 }}>
          {#if previewUrl}
            <img class="photo-preview" src={previewUrl} alt="Captured subtitles" />
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
            disabled={phase === 'submitting'}
          ></textarea>

          <p class="eyebrow" style="margin-top: 0.75rem;">Tap the words you want to learn</p>
          <div class="chip-row">
            {#each tokens as token, i}
              <button
                type="button"
                class="option-chip word-chip"
                class:option-on={selected.has(i)}
                disabled={phase === 'submitting'}
                on:click={() => toggle(i)}
              >
                {token.word}
              </button>
            {/each}
          </div>

          <div class="review-actions">
            <button
              class="primary-button"
              type="button"
              disabled={selected.size === 0 || phase === 'submitting'}
              on:click={() => void submitSelected()}
            >
              {phase === 'submitting'
                ? 'Adding…'
                : `Add ${selected.size || ''} word${selected.size === 1 ? '' : 's'} with context`}
            </button>
            <button class="ghost-button" type="button" disabled={phase === 'submitting'} on:click={reset}>
              Take another photo
            </button>
          </div>
        </div>
      {/if}
    </article>

    {#if outcomes.length > 0}
      <article class="glass-panel" in:fly={{ y: 20, duration: 200 }}>
        <div class="section-head">
          <div>
            <p class="eyebrow">Results</p>
            <h3>This photo's words</h3>
          </div>
        </div>
        <ul class="outcome-list">
          {#each outcomes as outcome}
            <li class={`outcome-row outcome-${outcome.status}`}>
              <span class="outcome-icon" aria-hidden="true">
                {outcome.status === 'added' ? '✓' : outcome.status === 'corrected' ? '✎' : outcome.status === 'not_found' ? '?' : '✗'}
              </span>
              <div>
                <strong>{outcome.word}</strong>
                <p>{outcome.detail}</p>
              </div>
            </li>
          {/each}
        </ul>
        <button class="ghost-button" type="button" style="margin-top: 0.75rem;" on:click={() => navigate('/add-word')}>
          Open Add Word
        </button>
      </article>
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
    font-size: 1.05rem;
    padding: 1rem 1.5rem;
  }

  .photo-preview {
    max-width: 100%;
    max-height: 220px;
    border-radius: 12px;
    object-fit: contain;
    display: block;
    margin: 0.75rem auto 0;
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

  .chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.35rem;
  }

  .word-chip {
    font-size: 1rem;
  }

  .review-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-top: 1.25rem;
    align-items: center;
  }

  .outcome-list {
    list-style: none;
    margin: 0.5rem 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
  }

  .outcome-row {
    display: flex;
    gap: 0.6rem;
    align-items: baseline;
  }

  .outcome-row p {
    margin: 0.1rem 0 0;
    opacity: 0.85;
  }

  .outcome-icon {
    font-weight: 700;
  }

  .outcome-added .outcome-icon {
    color: var(--success, #2e9e6b);
  }

  .outcome-corrected .outcome-icon {
    color: var(--info, #3a7bd5);
  }

  .outcome-not_found .outcome-icon,
  .outcome-error .outcome-icon {
    color: var(--danger, #d5573a);
  }
</style>
