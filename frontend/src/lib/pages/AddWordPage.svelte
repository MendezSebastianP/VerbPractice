<script lang="ts">
  import { onMount } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import HelpTip from '../components/HelpTip.svelte';
  import { navigate } from '../router';
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
  let sourceTileOpen = false;
  let targetTileOpen = false;

  // Keyboard shortcuts mirror the Words trainer (no on-screen badges here).
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

  onMount(load);
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
        </HelpTip>
      </div>

      {#if !settings?.mother_tongue}
        <div class="feedback-banner info-banner" style="margin-top: 0.75rem;">
          Set your mother tongue on the home page first.
        </div>
      {/if}

      <form class="answer-form" on:submit|preventDefault={fireTranslate} style="margin-top: 0.5rem;">
        <div class="toggle-group">
          <span class="toggle-label">Direction</span>
          <div class="lang-direction">
            <div class="tile-wrap">
              <button
                type="button"
                class="option-chip option-on lang-tile"
                on:click={() => { sourceTileOpen = !sourceTileOpen; targetTileOpen = false; }}
              >
                {languageName(sourceCode) || '—'}
                <small>you type</small>
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

            <button
              type="button"
              class="ghost-button swap-btn"
              aria-label="Swap languages"
              title="Swap"
              on:click={swapLangs}
            >
              ⇄
            </button>

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
          {#if exampleLine}
            <p class="example-line">{exampleLine}</p>
          {/if}
        </div>

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
      </form>

      <button
        class="ghost-button"
        type="button"
        style="margin-top: 0.75rem;"
        on:click={() => navigate('/photo-word')}
      >
        📷 From a photo of subtitles
      </button>
    </article>

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

  .lang-direction {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-top: 0.4rem;
  }

  .tile-wrap {
    position: relative;
    flex: 1;
  }

  .lang-tile {
    width: 100%;
    padding: 0.85rem 1rem;
    font-size: 1.1rem;
  }

  .lang-tile small {
    display: block;
    opacity: 0.6;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 0.15rem;
  }

  .swap-btn {
    padding: 0.5rem 0.75rem;
    font-size: 1.25rem;
    flex-shrink: 0;
  }

  .lang-menu {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 10;
    padding: 0.5rem;
    margin-top: 0.25rem;
  }

  .lang-menu .option-chip {
    display: block;
    width: 100%;
    margin: 0.15rem 0;
    text-align: left;
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
