<script lang="ts">
  import { onDestroy, tick } from 'svelte';
  import PixelQuickShot from './PixelQuickShot.svelte';

  export let variant: 'centered-ledger' | 'split-workbench' | 'focus-console' = 'centered-ledger';
  export let index = 'D1';
  export let kicker = '';
  export let title = '';
  export let description = '';

  const PRONOUNS = ['je', 'tu', 'il / elle / on', 'nous', 'vous', 'ils / elles'];
  const TENSES = [
    'Présent',
    'Futur',
    'Passé composé',
    'Imparfait',
    'Conditionnel présent',
    'Impératif',
    'Subjonctif présent',
    'Passé simple',
    'Subjonctif imparfait',
  ];
  const EXPECTED: string[][][] = [
    [['vais'], ['vas'], ['va'], ['allons'], ['allez'], ['vont']],
    [['irai'], ['iras'], ['ira'], ['irons'], ['irez'], ['iront']],
    [
      ['suis allé', 'suis allée'],
      ['es allé', 'es allée'],
      ['est allé', 'est allée'],
      ['sommes allés', 'sommes allées'],
      ['êtes allé', 'êtes allée', 'êtes allés', 'êtes allées'],
      ['sont allés', 'sont allées'],
    ],
    [['allais'], ['allais'], ['allait'], ['allions'], ['alliez'], ['allaient']],
    [['irais'], ['irais'], ['irait'], ['irions'], ['iriez'], ['iraient']],
    [[], ['va'], [], ['allons'], ['allez'], []],
    [['aille'], ['ailles'], ['aille'], ['allions'], ['alliez'], ['aillent']],
    [['allai'], ['allas'], ['alla'], ['allâmes'], ['allâtes'], ['allèrent']],
    [['allasse'], ['allasses'], ['allât'], ['allassions'], ['allassiez'], ['allassent']],
  ];

  function createAnswerGrid(): string[][] {
    return TENSES.map(() => PRONOUNS.map(() => ''));
  }

  function createSpentGrid(): boolean[][] {
    return TENSES.map(() => PRONOUNS.map(() => false));
  }

  let answers = createAnswerGrid();
  let quickSpent = createSpentGrid();
  let activeTenseIndex = 0;
  let activePronounIndex = 0;
  let completedTenses = new Set<number>();
  let review = false;
  let explanationOpen = false;
  let guarding = false;
  let accepted = false;
  let isComposing = false;
  let quickAdvanceInFlight = false;
  let inputRefs: HTMLInputElement[] = [];
  let focusInput: HTMLInputElement;
  let desktopShell: HTMLElement;
  let guardTimer: number | undefined;
  let acceptedTimer: number | undefined;

  $: activeTense = TENSES[activeTenseIndex];
  $: currentAnswer = answers[activeTenseIndex][activePronounIndex];
  $: currentExpected = EXPECTED[activeTenseIndex][activePronounIndex] ?? [];
  $: quickReady = currentExpected.length > 0 && !quickSpent[activeTenseIndex][activePronounIndex];
  $: activePronouns = editablePronouns(activeTenseIndex);
  $: activePosition = Math.max(0, activePronouns.indexOf(activePronounIndex));
  $: answeredCount = answers[activeTenseIndex].filter((answer, answerIndex) => EXPECTED[activeTenseIndex][answerIndex].length > 0 && answer.trim()).length;
  $: runProgress = Math.max(1, ((activeTenseIndex * PRONOUNS.length + answeredCount) / (TENSES.length * PRONOUNS.length)) * 100);
  $: reviewScore = answers[activeTenseIndex].reduce((score, _, pronounIndex) => score + (isCorrect(pronounIndex) ? 1 : 0), 0);

  function editablePronouns(tenseIndex: number): number[] {
    return PRONOUNS.map((_, indexValue) => indexValue).filter((indexValue) => EXPECTED[tenseIndex][indexValue].length > 0);
  }

  function normalize(value: string): string {
    return value.normalize('NFC').toLocaleLowerCase('fr-FR').replace(/\s+/g, ' ').trim();
  }

  function isCorrect(pronounIndex: number): boolean {
    const answer = normalize(answers[activeTenseIndex][pronounIndex]);
    return Boolean(answer) && EXPECTED[activeTenseIndex][pronounIndex].some((expected) => normalize(expected) === answer);
  }

  function setAnswer(pronounIndex: number, value: string): void {
    const next = answers.map((tenseAnswers) => [...tenseAnswers]);
    next[activeTenseIndex][pronounIndex] = value;
    answers = next;
  }

  function markSpent(): void {
    const next = quickSpent.map((tenseSpent) => [...tenseSpent]);
    next[activeTenseIndex][activePronounIndex] = true;
    quickSpent = next;
  }

  function armGuard(): void {
    guarding = true;
    window.clearTimeout(guardTimer);
    guardTimer = window.setTimeout(() => {
      guarding = false;
    }, 600);
  }

  function registerInput(node: HTMLInputElement, pronounIndex: number): { update: (nextIndex: number) => void; destroy: () => void } {
    inputRefs[pronounIndex] = node;
    return {
      update(nextIndex: number) {
        inputRefs[nextIndex] = node;
      },
      destroy() {
        if (inputRefs[pronounIndex] === node) {
          delete inputRefs[pronounIndex];
        }
      },
    };
  }

  async function focusActive(): Promise<void> {
    await tick();
    if (review) {
      return;
    }
    const target = variant === 'focus-console' ? focusInput : inputRefs[activePronounIndex];
    target?.focus({ preventScroll: true });
    const end = target?.value.length ?? 0;
    target?.setSelectionRange(end, end);
  }

  async function selectPronoun(pronounIndex: number): Promise<void> {
    if (!activePronouns.includes(pronounIndex) || review) {
      return;
    }
    activePronounIndex = pronounIndex;
    explanationOpen = false;
    await focusActive();
  }

  async function selectTense(tenseIndex: number): Promise<void> {
    activeTenseIndex = tenseIndex;
    const editable = editablePronouns(tenseIndex);
    activePronounIndex = editable.find((indexValue) => !answers[tenseIndex][indexValue].trim()) ?? editable[0] ?? 0;
    review = false;
    explanationOpen = false;
    await focusActive();
  }

  async function advance(fromQuickShot = false): Promise<void> {
    explanationOpen = false;
    if (!fromQuickShot && !answers[activeTenseIndex][activePronounIndex].trim()) {
      const previousIndex = activePronouns[activePosition - 1];
      if (previousIndex === undefined) {
        return;
      }
      setAnswer(activePronounIndex, answers[activeTenseIndex][previousIndex]);
    }

    if (activePosition < activePronouns.length - 1) {
      activePronounIndex = activePronouns[activePosition + 1];
      await focusActive();
      return;
    }

    completedTenses = new Set([...completedTenses, activeTenseIndex]);
    review = true;
    await tick();
    desktopShell?.focus({ preventScroll: true });
  }

  async function returnToPrevious(): Promise<void> {
    if (review) {
      review = false;
      await focusActive();
      return;
    }
    const previousIndex = activePronouns[activePosition - 1];
    if (previousIndex === undefined) {
      return;
    }
    activePronounIndex = previousIndex;
    explanationOpen = false;
    await focusActive();
  }

  async function quickAdvance(): Promise<void> {
    await tick();
    accepted = true;
    window.clearTimeout(acceptedTimer);
    acceptedTimer = window.setTimeout(() => {
      accepted = false;
    }, 520);
    await advance(true);
    quickAdvanceInFlight = false;
  }

  function processInput(value: string): void {
    explanationOpen = false;
    setAnswer(activePronounIndex, value);
    if (isComposing || quickAdvanceInFlight || !quickReady) {
      return;
    }
    const draft = normalize(value);
    if (!draft) {
      return;
    }
    const expected = currentExpected.map(normalize);
    if (expected.includes(draft)) {
      armGuard();
      quickAdvanceInFlight = true;
      void quickAdvance();
      return;
    }
    if (!expected.some((answer) => answer.startsWith(draft))) {
      markSpent();
    }
  }

  function handleInput(event: Event): void {
    processInput((event.currentTarget as HTMLInputElement).value);
  }

  function handleCompositionEnd(event: CompositionEvent): void {
    isComposing = false;
    processInput((event.currentTarget as HTMLInputElement).value);
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      event.preventDefault();
      if (guarding) {
        return;
      }
      if (review) {
        void continueAfterReview();
      } else {
        void advance();
      }
      return;
    }
    if (event.key === 'Backspace' && !currentAnswer) {
      event.preventDefault();
      void returnToPrevious();
    }
  }

  function handleWindowKeydown(event: KeyboardEvent): void {
    if (document.activeElement !== desktopShell || !review || event.key !== 'Enter') {
      return;
    }
    event.preventDefault();
    void continueAfterReview();
  }

  async function continueAfterReview(): Promise<void> {
    await selectTense((activeTenseIndex + 1) % TENSES.length);
  }

  function reset(): void {
    answers = createAnswerGrid();
    quickSpent = createSpentGrid();
    activeTenseIndex = 0;
    activePronounIndex = 0;
    completedTenses = new Set();
    review = false;
    explanationOpen = false;
    guarding = false;
    accepted = false;
    quickAdvanceInFlight = false;
    window.clearTimeout(guardTimer);
    window.clearTimeout(acceptedTimer);
    void focusActive();
  }

  async function toggleFullscreen(): Promise<void> {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await desktopShell.requestFullscreen();
      }
    } catch {
      // Fullscreen can be unavailable in embedded browser previews.
    }
  }

  onDestroy(() => {
    window.clearTimeout(guardTimer);
    window.clearTimeout(acceptedTimer);
  });
</script>

<svelte:window on:keydown={handleWindowKeydown} />

<article class={`desktop-concept variant-${variant}`}>
  <header class="concept-intro">
    <span>{index}</span>
    <div>
      <p>{kicker}</p>
      <h2>{title}</h2>
      <small>{description}</small>
    </div>
  </header>

  <section class="desktop-shell" bind:this={desktopShell} tabindex="-1" aria-label={`${title} interactive prototype`}>
    <i class="side-progress side-progress-left" aria-hidden="true"><span style={`height: ${runProgress}%`}></span></i>
    <i class="side-progress side-progress-right" aria-hidden="true"><span style={`height: ${runProgress}%`}></span></i>

    <header class="game-topbar">
      <div class="game-brand"><span>VERB LAB</span><strong>Table run</strong></div>
      <div class="verb-progress"><span><b>1</b> / 3 VERBS</span><i><s style={`width: ${runProgress}%`}></s></i></div>
      <div class="top-shortcuts"><span><kbd>Enter</kbd> next</span><span><kbd>Backspace</kbd> back</span><span><kbd>Esc ×2</kbd> finish</span></div>
      <button class="fullscreen-button" type="button" aria-label="Toggle prototype fullscreen" on:click={toggleFullscreen}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 4H4v4M16 4h4v4M20 16v4h-4M4 16v4h4"></path></svg><kbd>F11</kbd>
      </button>
    </header>

    <nav class="tense-deck" aria-label="Tenses in this desktop run">
      {#each TENSES as tense, tenseIndex}
        <button
          class:active={tenseIndex === activeTenseIndex}
          class:complete={completedTenses.has(tenseIndex)}
          type="button"
          title={tense}
          aria-current={tenseIndex === activeTenseIndex ? 'step' : undefined}
          on:click={() => selectTense(tenseIndex)}
        ><span>{tenseIndex + 1}</span><strong>{tense}</strong></button>
      {/each}
    </nav>

    {#if variant === 'centered-ledger'}
      <div class="ledger-layout">
        <header class="wide-hero">
          <div><span>CURRENT VERB</span><strong>aller</strong></div>
          <div><small>{activeTense}</small><strong><b>{PRONOUNS[activePronounIndex]}</b> + aller</strong></div>
          <div><span>{review ? 'TENSE RESULT' : 'ACTIVE ANSWER'}</span><strong>{review ? `${reviewScore}/${activePronouns.length}` : `${activePosition + 1}/${activePronouns.length}`}</strong></div>
        </header>

        <section class:reviewing={review} class="answer-ledger">
          <div class="ledger-head"><div><span>{review ? 'TENSE FEEDBACK' : 'FILL TOP TO BOTTOM'}</span><strong>{activeTense}</strong></div><small>{review ? 'All feedback shown in place' : `${activePronouns.length} answers · last Enter checks`}</small></div>
          <div class="answer-rows">
            {#each PRONOUNS as pronoun, pronounIndex}
              {@const missing = EXPECTED[activeTenseIndex][pronounIndex].length === 0}
              <div class:active={!review && pronounIndex === activePronounIndex} class:filled={Boolean(answers[activeTenseIndex][pronounIndex].trim())} class:missing class:correct={review && isCorrect(pronounIndex)} class:wrong={review && !missing && !isCorrect(pronounIndex)} class="answer-row">
                <span class="row-marker">{missing ? '–' : review ? isCorrect(pronounIndex) ? '✓' : '×' : pronounIndex === activePronounIndex ? '▶' : answers[activeTenseIndex][pronounIndex] ? '✓' : '·'}</span>
                <label for={`${index}-ledger-${pronounIndex}`}><small>{String(pronounIndex + 1).padStart(2, '0')}</small><strong>{pronoun}</strong></label>
                {#if missing}
                  <div class="missing-form">Not used in this tense</div>
                {:else if review}
                  <div class="row-feedback">{#if isCorrect(pronounIndex)}<strong>{answers[activeTenseIndex][pronounIndex]}</strong><small>RIGHT</small>{:else}<del>{answers[activeTenseIndex][pronounIndex] || 'No answer'}</del><strong>{EXPECTED[activeTenseIndex][pronounIndex][0]}</strong><small>CORRECT</small>{/if}</div>
                {:else}
                  <input id={`${index}-ledger-${pronounIndex}`} use:registerInput={pronounIndex} value={answers[activeTenseIndex][pronounIndex]} tabindex={pronounIndex === activePronounIndex ? 0 : -1} on:focus={() => selectPronoun(pronounIndex)} on:input={handleInput} on:compositionstart={() => (isComposing = true)} on:compositionend={handleCompositionEnd} on:keydown={handleKeydown} autocomplete="off" autocapitalize="off" spellcheck="false" />
                  <div class="row-shot">{#if pronounIndex === activePronounIndex}<PixelQuickShot ready={quickReady} {guarding} {accepted} {explanationOpen} onToggle={() => (explanationOpen = !explanationOpen)} />{/if}</div>
                {/if}
              </div>
            {/each}
          </div>
        </section>
      </div>
    {:else if variant === 'split-workbench'}
      <div class="split-layout">
        <aside class="context-console">
          <span>ACTIVE TENSE</span>
          <strong class="context-tense">{activeTense}</strong>
          <div class="context-verb"><small>CURRENT VERB</small><strong>aller</strong></div>
          <div class="context-equation"><b>{PRONOUNS[activePronounIndex]}</b><span>+</span><strong>aller</strong></div>
          <nav aria-label="Pronoun progress">
            {#each PRONOUNS as pronoun, pronounIndex}
              <button class:active={!review && pronounIndex === activePronounIndex} class:filled={Boolean(answers[activeTenseIndex][pronounIndex])} class:missing={EXPECTED[activeTenseIndex][pronounIndex].length === 0} type="button" on:click={() => selectPronoun(pronounIndex)}><span>{pronounIndex + 1}</span><strong>{pronoun}</strong><small>{EXPECTED[activeTenseIndex][pronounIndex].length === 0 ? 'unused' : answers[activeTenseIndex][pronounIndex] ? 'filled' : 'waiting'}</small></button>
            {/each}
          </nav>
        </aside>

        <section class:reviewing={review} class="split-column">
          <header><div><span>{review ? 'FEEDBACK' : 'ANSWER COLUMN'}</span><strong>{activeTense}</strong></div><small>{review ? `${reviewScore}/${activePronouns.length} correct` : `${activePosition + 1} of ${activePronouns.length}`}</small></header>
          <div class="answer-rows compact-rows">
            {#each PRONOUNS as pronoun, pronounIndex}
              {@const missing = EXPECTED[activeTenseIndex][pronounIndex].length === 0}
              <div class:active={!review && pronounIndex === activePronounIndex} class:filled={Boolean(answers[activeTenseIndex][pronounIndex].trim())} class:missing class:correct={review && isCorrect(pronounIndex)} class:wrong={review && !missing && !isCorrect(pronounIndex)} class="answer-row">
                <span class="row-marker">{missing ? '–' : review ? isCorrect(pronounIndex) ? '✓' : '×' : pronounIndex === activePronounIndex ? '▶' : answers[activeTenseIndex][pronounIndex] ? '✓' : '·'}</span>
                <label for={`${index}-split-${pronounIndex}`}><small>{String(pronounIndex + 1).padStart(2, '0')}</small><strong>{pronoun}</strong></label>
                {#if missing}<div class="missing-form">Not used</div>{:else if review}<div class="row-feedback">{#if isCorrect(pronounIndex)}<strong>{answers[activeTenseIndex][pronounIndex]}</strong><small>RIGHT</small>{:else}<del>{answers[activeTenseIndex][pronounIndex] || 'No answer'}</del><strong>{EXPECTED[activeTenseIndex][pronounIndex][0]}</strong><small>CORRECT</small>{/if}</div>{:else}<input id={`${index}-split-${pronounIndex}`} use:registerInput={pronounIndex} value={answers[activeTenseIndex][pronounIndex]} tabindex={pronounIndex === activePronounIndex ? 0 : -1} on:focus={() => selectPronoun(pronounIndex)} on:input={handleInput} on:compositionstart={() => (isComposing = true)} on:compositionend={handleCompositionEnd} on:keydown={handleKeydown} autocomplete="off" autocapitalize="off" spellcheck="false" /><div class="row-shot">{#if pronounIndex === activePronounIndex}<PixelQuickShot ready={quickReady} {guarding} {accepted} {explanationOpen} onToggle={() => (explanationOpen = !explanationOpen)} />{/if}</div>{/if}
              </div>
            {/each}
          </div>
        </section>
      </div>
    {:else}
      <div class="focus-layout">
        <aside class="focus-pronouns">
          <span>PRONOUN RUN</span>
          {#each PRONOUNS as pronoun, pronounIndex}
            <button class:active={!review && pronounIndex === activePronounIndex} class:filled={Boolean(answers[activeTenseIndex][pronounIndex])} class:missing={EXPECTED[activeTenseIndex][pronounIndex].length === 0} type="button" on:click={() => selectPronoun(pronounIndex)}><i>{pronounIndex + 1}</i><strong>{pronoun}</strong><small>{EXPECTED[activeTenseIndex][pronounIndex].length === 0 ? 'unused' : answers[activeTenseIndex][pronounIndex] || 'waiting'}</small></button>
          {/each}
        </aside>

        <section class:reviewing={review} class="focus-stage">
          {#if review}
            <header class="review-title"><span>{activeTense} COMPLETE</span><strong>{reviewScore}/{activePronouns.length} correct</strong><small>Enter opens the next tense</small></header>
            <div class="review-grid">
              {#each PRONOUNS as pronoun, pronounIndex}
                {#if EXPECTED[activeTenseIndex][pronounIndex].length > 0}<div class:correct={isCorrect(pronounIndex)}><span>{pronoun}</span>{#if isCorrect(pronounIndex)}<strong>{answers[activeTenseIndex][pronounIndex]}</strong><i>✓</i>{:else}<del>{answers[activeTenseIndex][pronounIndex] || 'No answer'}</del><strong>{EXPECTED[activeTenseIndex][pronounIndex][0]}</strong><i>×</i>{/if}</div>{/if}
              {/each}
            </div>
          {:else}
            <header><span>{activeTense}</span><small>ANSWER {activePosition + 1} / {activePronouns.length}</small></header>
            <div class="focus-equation"><b>{PRONOUNS[activePronounIndex]}</b><span>+</span><strong>aller</strong></div>
            <div class="focus-input-line">
              <input bind:this={focusInput} value={currentAnswer} on:input={handleInput} on:compositionstart={() => (isComposing = true)} on:compositionend={handleCompositionEnd} on:keydown={handleKeydown} autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Type the form" />
              <button type="button" aria-label="Next answer" on:click={() => advance()}><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 10 4 4 4-4"></path></svg></button>
            </div>
            <div class="focus-shot"><PixelQuickShot ready={quickReady} {guarding} {accepted} {explanationOpen} onToggle={() => (explanationOpen = !explanationOpen)} /></div>
          {/if}
        </section>

        <aside class="run-console">
          <span>RUN MAP</span>
          <strong>{answeredCount}/{activePronouns.length}</strong>
          <small>forms filled in {activeTense}</small>
          <div>{#each activePronouns as pronounIndex}<i class:filled={Boolean(answers[activeTenseIndex][pronounIndex])} class:active={!review && pronounIndex === activePronounIndex}></i>{/each}</div>
          <button type="button" on:click={reset}>Reset prototype <kbd>R</kbd></button>
        </aside>
      </div>
    {/if}

    <footer class="game-footer">
      <span>{review ? 'All feedback is visible · Enter continues' : 'Enter moves down · empty Enter repeats · Backspace returns when empty'}</span>
      <div>{#if review}<button type="button" on:click={continueAfterReview}>Next tense <kbd>Enter</kbd></button>{:else}<button type="button" on:click={() => advance()}>Check / next <kbd>Enter</kbd></button>{/if}<button type="button" on:click={reset}>Reset demo</button></div>
    </footer>
  </section>
</article>

<style>
  .desktop-concept {
    display: grid;
    min-width: 0;
    gap: 1rem;
  }

  .concept-intro {
    display: grid;
    width: min(100%, 1120px);
    grid-template-columns: auto 1fr;
    gap: 0.9rem;
    margin-inline: auto;
  }

  .concept-intro > span {
    display: grid;
    min-width: 3.4rem;
    height: 2.5rem;
    padding-inline: 0.55rem;
    place-items: center;
    border: 1px solid color-mix(in srgb, var(--accent) 55%, var(--line));
    border-radius: 10px;
    color: var(--accent-strong);
    background: var(--accent-soft);
    font: 850 0.82rem/1 var(--mono);
  }

  .concept-intro p {
    margin: 0 0 0.25rem;
    color: var(--accent-strong);
    font: 800 0.84rem/1 var(--mono);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .concept-intro h2 {
    margin: 0;
    color: var(--text);
    font: 820 clamp(1.35rem, 3vw, 1.9rem)/1.05 var(--display);
    letter-spacing: -0.04em;
  }

  .concept-intro small {
    display: block;
    max-width: 58rem;
    margin-top: 0.4rem;
    color: var(--muted);
    font-size: 0.78rem;
    line-height: 1.5;
  }

  .desktop-shell {
    --ink: color-mix(in srgb, var(--surface-dark) 94%, #05010d);
    position: relative;
    width: min(100%, 1180px);
    margin-inline: auto;
    overflow: visible;
    border: 4px solid color-mix(in srgb, var(--accent) 43%, #160b25);
    border-radius: 26px;
    color: white;
    background:
      radial-gradient(circle at 87% 2%, color-mix(in srgb, var(--accent) 18%, transparent), transparent 29%),
      linear-gradient(color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px),
      linear-gradient(90deg, color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px),
      var(--ink);
    background-size: auto, 24px 24px, 24px 24px, auto;
    box-shadow: 0 26px 65px rgba(5, 1, 13, 0.42), 0 0 28px color-mix(in srgb, var(--accent) 12%, transparent), inset 0 0 0 1px color-mix(in srgb, var(--accent) 16%, transparent);
  }

  .desktop-shell:fullscreen {
    width: 100vw;
    min-height: 100vh;
    border-radius: 0;
  }

  .desktop-shell:focus {
    outline: none;
  }

  .side-progress {
    position: absolute;
    z-index: 3;
    top: 5rem;
    bottom: 4.5rem;
    width: 4px;
    overflow: hidden;
    border-radius: 99px;
    background: color-mix(in srgb, var(--accent) 18%, transparent);
  }

  .side-progress-left { left: 9px; }
  .side-progress-right { right: 9px; }

  .side-progress span {
    position: absolute;
    right: 0;
    bottom: 0;
    left: 0;
    border-radius: inherit;
    background: linear-gradient(var(--accent-2), var(--accent));
    box-shadow: 0 0 12px color-mix(in srgb, var(--accent) 55%, transparent);
    transition: height 180ms ease;
  }

  .game-topbar {
    display: grid;
    min-height: 66px;
    grid-template-columns: auto minmax(12rem, 1fr) auto auto;
    gap: 1.2rem;
    align-items: center;
    margin-inline: 1.5rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid color-mix(in srgb, var(--accent) 25%, transparent);
  }

  .game-brand {
    display: grid;
    gap: 0.1rem;
  }

  .game-brand span,
  .wide-hero span,
  .ledger-head span,
  .context-console > span,
  .split-column header span,
  .focus-pronouns > span,
  .run-console > span,
  .focus-stage > header > span,
  .review-title > span {
    color: var(--accent-strong);
    font: 800 0.9rem/1 var(--mono);
    letter-spacing: 0.09em;
  }

  .game-brand strong { font-size: 1rem; }

  .verb-progress {
    display: grid;
    min-width: 0;
    gap: 0.32rem;
  }

  .verb-progress > span {
    justify-self: end;
    color: color-mix(in srgb, white 52%, var(--muted));
    font: 750 0.82rem/1 var(--mono);
  }

  .verb-progress b { color: white; }
  .verb-progress i { display: block; height: 4px; overflow: hidden; border-radius: 99px; background: color-mix(in srgb, var(--accent) 16%, var(--ink)); }
  .verb-progress s { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--accent), var(--accent-2)); text-decoration: none; transition: width 180ms ease; }

  .top-shortcuts {
    display: flex;
    gap: 0.75rem;
    color: color-mix(in srgb, white 50%, var(--muted));
    font-size: 0.68rem;
  }

  kbd {
    padding: 0.2rem 0.34rem;
    border: 1px solid color-mix(in srgb, var(--accent) 36%, transparent);
    border-radius: 5px;
    color: var(--accent-strong);
    background: color-mix(in srgb, var(--accent-soft) 65%, transparent);
    font: 760 0.78rem/1 var(--mono);
    white-space: nowrap;
  }

  .fullscreen-button {
    display: flex;
    gap: 0.4rem;
    align-items: center;
    min-height: 38px;
    padding: 0.42rem 0.5rem;
    border: 1px solid color-mix(in srgb, var(--accent) 34%, transparent);
    border-radius: 8px;
    color: white;
    background: color-mix(in srgb, var(--accent-soft) 35%, transparent);
  }

  .fullscreen-button svg { width: 16px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.8; }

  .tense-deck {
    display: grid;
    grid-template-columns: repeat(9, minmax(0, 1fr));
    gap: 0.4rem;
    margin: 0.65rem 1.5rem 0;
  }

  .tense-deck button {
    display: grid;
    min-width: 0;
    min-height: 48px;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 0.35rem;
    align-items: center;
    padding: 0.42rem 0.5rem;
    border: 1px solid color-mix(in srgb, var(--accent) 22%, transparent);
    border-radius: 6px;
    color: color-mix(in srgb, white 45%, var(--muted));
    background: color-mix(in srgb, var(--accent-soft) 22%, transparent);
    text-align: left;
  }

  .tense-deck span { color: var(--accent-strong); font: 800 0.78rem/1 var(--mono); }
  .tense-deck strong { min-width: 0; font-size: 0.64rem; line-height: 1.12; white-space: normal; }
  .tense-deck button.active { border-color: var(--accent-2); color: #211800; background: var(--accent-2); box-shadow: inset 0 -3px 0 color-mix(in srgb, black 42%, var(--accent-2)), 0 0 16px color-mix(in srgb, var(--accent-2) 25%, transparent); }
  .tense-deck button.active span { color: #211800; }
  .tense-deck button.complete:not(.active) { border-color: color-mix(in srgb, var(--success) 48%, transparent); color: var(--success); }

  .ledger-layout { display: grid; gap: 0.75rem; padding: 0.8rem 1.6rem 1rem; }
  .wide-hero { display: grid; grid-template-columns: minmax(9rem, 0.7fr) minmax(18rem, 1.6fr) minmax(8rem, 0.7fr); gap: 1rem; align-items: center; padding: 0.85rem 1rem; border: 1px solid color-mix(in srgb, var(--accent) 28%, transparent); border-radius: 14px; background: color-mix(in srgb, var(--accent-soft) 28%, transparent); }
  .wide-hero > div { display: grid; gap: 0.18rem; }
  .wide-hero > div:nth-child(2) { justify-items: center; text-align: center; }
  .wide-hero > div:last-child { justify-items: end; text-align: right; }
  .wide-hero > div:first-child > strong { font-size: clamp(1.65rem, 3vw, 2.3rem); overflow-wrap: anywhere; }
  .wide-hero small { color: var(--accent-2); font-size: 0.85rem; font-weight: 760; }
  .wide-hero > div:nth-child(2) > strong { font-size: clamp(1.4rem, 2.5vw, 2rem); }
  .wide-hero b { color: var(--accent-2); }
  .wide-hero > div:last-child > strong { color: var(--accent-2); font: 800 1.2rem/1 var(--mono); }

  .answer-ledger { width: min(100%, 820px); margin-inline: auto; overflow: visible; border: 1px solid color-mix(in srgb, var(--accent) 28%, transparent); border-radius: 14px; background: color-mix(in srgb, var(--surface-dark) 72%, transparent); }
  .ledger-head,
  .split-column > header { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 0.7rem 0.8rem; border-bottom: 1px solid color-mix(in srgb, var(--accent) 22%, transparent); }
  .ledger-head > div,
  .split-column > header > div { display: grid; gap: 0.15rem; }
  .ledger-head strong,
  .split-column > header strong { font-size: 0.92rem; }
  .ledger-head > small,
  .split-column > header > small { color: color-mix(in srgb, white 52%, var(--muted)); font-size: 0.7rem; }

  .answer-rows { display: grid; gap: 0.38rem; padding: 0.65rem; }
  .answer-row { position: relative; display: grid; min-height: 54px; grid-template-columns: 1.5rem 9.5rem minmax(0, 1fr) 42px; gap: 0.65rem; align-items: center; padding: 0.5rem 0.65rem; border: 1px solid color-mix(in srgb, white 9%, transparent); border-radius: 6px; background: color-mix(in srgb, white 2.5%, transparent); transition: 150ms ease; }
  .answer-row.active { border-color: var(--accent-2); background: color-mix(in srgb, var(--accent) 15%, transparent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 8%, transparent); transform: translateX(0.2rem); }
  .answer-row.filled:not(.active) { border-color: color-mix(in srgb, var(--success) 28%, transparent); }
  .answer-row.correct { border-color: color-mix(in srgb, var(--success) 56%, transparent); background: color-mix(in srgb, var(--success) 9%, transparent); }
  .answer-row.wrong { border-color: color-mix(in srgb, var(--danger) 58%, transparent); background: color-mix(in srgb, var(--danger) 9%, transparent); }
  .answer-row.missing { opacity: 0.58; }
  .row-marker { color: var(--accent-2); font: 800 0.85rem/1 var(--mono); text-align: center; }
  .correct .row-marker { color: var(--success); }
  .wrong .row-marker { color: var(--danger); }
  .answer-row label { display: grid; grid-template-columns: 1.6rem 1fr; gap: 0.35rem; align-items: center; }
  .answer-row label small { color: var(--accent-strong); font: 780 0.8rem/1 var(--mono); }
  .answer-row label strong { font-size: 0.95rem; }
  .answer-row input { width: 100%; min-width: 0; height: 38px; padding: 0 0.75rem; border: 1px solid color-mix(in srgb, var(--accent) 28%, transparent); border-radius: 6px; outline: 0; color: white; background: color-mix(in srgb, var(--surface-dark) 88%, black); font: 720 0.95rem/1 var(--ui); }
  .answer-row input:focus { border-color: var(--accent-2); box-shadow: inset 0 -2px 0 var(--accent-2); }
  .row-shot { display: grid; min-height: 38px; place-items: center; }
  .missing-form { color: color-mix(in srgb, white 45%, var(--muted)); font-size: 0.74rem; }
  .row-feedback { display: flex; min-width: 0; gap: 0.55rem; align-items: center; }
  .row-feedback strong { color: var(--success); overflow-wrap: anywhere; }
  .row-feedback del { color: var(--danger); }
  .row-feedback small { margin-left: auto; color: var(--accent-strong); font: 780 0.78rem/1 var(--mono); }

  .split-layout { display: grid; grid-template-columns: minmax(17rem, 0.72fr) minmax(30rem, 1.28fr); gap: 0.8rem; min-height: 485px; padding: 0.8rem 1.6rem 1rem; }
  .context-console,
  .split-column,
  .focus-pronouns,
  .focus-stage,
  .run-console { border: 1px solid color-mix(in srgb, var(--accent) 28%, transparent); border-radius: 14px; background: color-mix(in srgb, var(--surface-dark) 72%, transparent); }
  .context-console { display: grid; align-content: start; gap: 0.75rem; padding: 1rem; }
  .context-tense { overflow-wrap: anywhere; color: var(--accent-2); font: 400 clamp(0.88rem, 1.5vw, 1.15rem)/1.55 var(--marquee); text-shadow: 2px 2px 0 color-mix(in srgb, var(--accent) 50%, transparent); }
  .context-verb { display: grid; gap: 0.1rem; padding: 0.7rem 0; border-block: 1px solid color-mix(in srgb, var(--accent) 18%, transparent); }
  .context-verb small { color: color-mix(in srgb, white 48%, var(--muted)); font: 760 0.78rem/1 var(--mono); }
  .context-verb strong { font-size: clamp(2rem, 4vw, 3.2rem); overflow-wrap: anywhere; }
  .context-equation { display: flex; flex-wrap: wrap; gap: 0.55rem; align-items: baseline; font-size: 1.4rem; font-weight: 800; }
  .context-equation b { color: var(--accent-2); }
  .context-equation span { color: color-mix(in srgb, white 32%, var(--muted)); }
  .context-console nav { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.38rem; }
  .context-console nav button { display: grid; min-width: 0; grid-template-columns: auto 1fr; gap: 0.05rem 0.4rem; align-items: center; padding: 0.5rem; border: 1px solid color-mix(in srgb, var(--accent) 20%, transparent); border-radius: 6px; color: color-mix(in srgb, white 52%, var(--muted)); background: transparent; text-align: left; }
  .context-console nav span { grid-row: 1 / 3; color: var(--accent-strong); font: 800 0.8rem/1 var(--mono); }
  .context-console nav strong { overflow: hidden; color: white; font-size: 0.72rem; text-overflow: ellipsis; white-space: nowrap; }
  .context-console nav small { font-size: 0.58rem; }
  .context-console nav button.active { border-color: var(--accent-2); background: color-mix(in srgb, var(--accent) 14%, transparent); }
  .context-console nav button.filled { color: var(--success); }
  .context-console nav button.missing { opacity: 0.42; }
  .split-column { overflow: visible; }
  .compact-rows .answer-row { min-height: 55px; grid-template-columns: 1.4rem 8.5rem minmax(0, 1fr) 42px; }

  .focus-layout { display: grid; grid-template-columns: minmax(13rem, 0.62fr) minmax(27rem, 1.5fr) minmax(11rem, 0.5fr); gap: 0.8rem; min-height: 460px; padding: 0.8rem 1.6rem 1rem; }
  .focus-pronouns { display: grid; align-content: start; gap: 0.4rem; padding: 0.9rem; }
  .focus-pronouns > span { margin-bottom: 0.25rem; }
  .focus-pronouns button { display: grid; min-width: 0; min-height: 52px; grid-template-columns: 1.6rem 1fr; gap: 0.08rem 0.45rem; align-items: center; padding: 0.5rem; border: 1px solid color-mix(in srgb, var(--accent) 20%, transparent); border-radius: 6px; color: color-mix(in srgb, white 55%, var(--muted)); background: transparent; text-align: left; }
  .focus-pronouns i { display: grid; width: 1.5rem; height: 1.5rem; grid-row: 1 / 3; place-items: center; border: 1px solid currentColor; border-radius: 4px; font: 800 0.8rem/1 var(--mono); font-style: normal; }
  .focus-pronouns strong { overflow: hidden; color: white; font-size: 0.78rem; text-overflow: ellipsis; white-space: nowrap; }
  .focus-pronouns small { overflow: hidden; font-size: 0.62rem; text-overflow: ellipsis; white-space: nowrap; }
  .focus-pronouns button.active { border-color: var(--accent-2); color: var(--accent-2); background: color-mix(in srgb, var(--accent) 15%, transparent); transform: translateX(0.2rem); }
  .focus-pronouns button.filled:not(.active) { color: var(--success); }
  .focus-pronouns button.missing { opacity: 0.42; }
  .focus-stage { position: relative; display: grid; min-width: 0; align-content: center; gap: 1rem; padding: clamp(1.2rem, 4vw, 2.4rem); background: radial-gradient(circle at 50% 48%, color-mix(in srgb, var(--accent) 15%, transparent), transparent 46%), color-mix(in srgb, var(--surface-dark) 72%, transparent); }
  .focus-stage > header { display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; }
  .focus-stage > header > span { color: var(--accent-2); font-family: var(--marquee); font-size: clamp(0.85rem, 1.6vw, 1.15rem); line-height: 1.5; }
  .focus-stage > header > small { color: color-mix(in srgb, white 48%, var(--muted)); font: 760 0.8rem/1 var(--mono); }
  .focus-equation { display: flex; min-width: 0; gap: 0.65rem; align-items: baseline; justify-content: center; font-size: clamp(2rem, 4vw, 3.3rem); font-weight: 820; letter-spacing: -0.05em; }
  .focus-equation b { max-width: 48%; overflow: hidden; color: var(--accent-2); text-overflow: ellipsis; white-space: nowrap; }
  .focus-equation span { color: color-mix(in srgb, white 30%, var(--muted)); font-size: 0.65em; }
  .focus-input-line { display: grid; grid-template-columns: minmax(0, 1fr) 52px; overflow: hidden; border: 2px solid color-mix(in srgb, var(--accent) 58%, transparent); border-radius: 8px; background: color-mix(in srgb, var(--surface-dark) 90%, black); box-shadow: 4px 4px 0 color-mix(in srgb, var(--accent) 16%, transparent); }
  .focus-input-line:focus-within { border-color: var(--accent-2); box-shadow: 4px 4px 0 color-mix(in srgb, var(--accent-2) 24%, transparent); }
  .focus-input-line input { min-width: 0; height: 58px; padding: 0 1rem; border: 0; outline: 0; color: white; background: transparent; font: 720 1.2rem/1 var(--ui); text-align: center; }
  .focus-input-line button { display: grid; place-items: center; border: 0; color: #211800; background: var(--accent-2); }
  .focus-input-line svg { width: 19px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 2; }
  .focus-shot { display: grid; min-height: 38px; justify-content: end; }
  .run-console { display: grid; align-content: center; justify-items: center; gap: 0.55rem; padding: 1rem; text-align: center; }
  .run-console > strong { color: var(--accent-2); font: 800 clamp(2rem, 4vw, 3.2rem)/1 var(--mono); }
  .run-console > small { color: color-mix(in srgb, white 48%, var(--muted)); font-size: 0.7rem; line-height: 1.35; }
  .run-console > div { display: flex; gap: 0.32rem; }
  .run-console i { width: 9px; height: 9px; border: 1px solid color-mix(in srgb, var(--accent) 32%, transparent); background: transparent; }
  .run-console i.filled { border-color: var(--success); background: var(--success); }
  .run-console i.active { border-color: var(--accent-2); background: var(--accent-2); box-shadow: 0 0 8px color-mix(in srgb, var(--accent-2) 45%, transparent); }
  .run-console button { margin-top: 0.7rem; padding: 0.55rem 0.65rem; border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent); border-radius: 7px; color: white; background: color-mix(in srgb, var(--accent-soft) 45%, transparent); font-size: 0.68rem; }
  .review-title { display: grid !important; justify-items: center; text-align: center; }
  .review-title strong { color: var(--accent-2); font-size: 1.5rem; }
  .review-title small { color: color-mix(in srgb, white 48%, var(--muted)); }
  .review-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.5rem; }
  .review-grid > div { display: grid; min-width: 0; grid-template-columns: 1fr auto; gap: 0.15rem 0.5rem; padding: 0.65rem; border: 1px solid color-mix(in srgb, var(--danger) 50%, transparent); border-radius: 6px; background: color-mix(in srgb, var(--danger) 8%, transparent); }
  .review-grid > div.correct { border-color: color-mix(in srgb, var(--success) 50%, transparent); background: color-mix(in srgb, var(--success) 8%, transparent); }
  .review-grid span { color: color-mix(in srgb, white 55%, var(--muted)); font-size: 0.68rem; }
  .review-grid strong { overflow-wrap: anywhere; }
  .review-grid del { color: var(--danger); font-size: 0.72rem; }
  .review-grid i { grid-column: 2; grid-row: 1 / 3; align-self: center; color: var(--danger); font-style: normal; }
  .review-grid .correct i { color: var(--success); }

  .game-footer { display: flex; min-height: 58px; gap: 1rem; align-items: center; justify-content: space-between; margin-inline: 1.5rem; padding: 0.65rem 0 0.8rem; border-top: 1px solid color-mix(in srgb, var(--accent) 22%, transparent); }
  .game-footer > span { color: color-mix(in srgb, white 50%, var(--muted)); font-size: 0.7rem; }
  .game-footer > div { display: flex; gap: 0.5rem; }
  .game-footer button { display: flex; gap: 0.5rem; align-items: center; min-height: 38px; padding: 0.5rem 0.7rem; border: 1px solid color-mix(in srgb, var(--accent) 34%, transparent); border-radius: 7px; color: white; background: color-mix(in srgb, var(--accent-soft) 55%, transparent); font-size: 0.7rem; font-weight: 720; }
  .game-footer button:first-child { border-color: color-mix(in srgb, var(--accent-2) 55%, transparent); }

  button { cursor: pointer; touch-action: manipulation; }
  button:focus-visible,
  input:focus-visible { outline: 2px solid var(--accent-2); outline-offset: 2px; }

  @media (max-width: 980px) {
    .top-shortcuts { display: none; }
    .split-layout,
    .focus-layout { grid-template-columns: 1fr; }
    .context-console nav { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .focus-pronouns { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .focus-pronouns > span { grid-column: 1 / -1; }
    .run-console { display: none; }
  }

  @media (max-width: 760px) {
    .game-topbar { grid-template-columns: auto 1fr auto; margin-inline: 1rem; }
    .fullscreen-button kbd { display: none; }
    .tense-deck { grid-template-columns: repeat(9, minmax(2.6rem, 1fr)); margin-inline: 1rem; overflow-x: auto; }
    .tense-deck strong { display: none; }
    .ledger-layout,
    .split-layout,
    .focus-layout { padding-inline: 1rem; }
    .wide-hero { grid-template-columns: 1fr 1fr; }
    .wide-hero > div:nth-child(2) { grid-column: 1 / -1; grid-row: 1; }
    .answer-row,
    .compact-rows .answer-row { grid-template-columns: 1.3rem minmax(7rem, 0.75fr) minmax(0, 1fr) 40px; }
    .game-footer { align-items: stretch; flex-direction: column; margin-inline: 1rem; }
  }
</style>
