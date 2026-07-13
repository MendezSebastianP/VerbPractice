<script lang="ts">
  import { onMount, tick } from 'svelte';

  export let tenseCount: 3 | 9 = 3;
  export let index = 'M1-3';
  export let kicker = 'Three-tense run';
  export let title = 'Labeled trio';
  export let description = '';
  export let tenseLayout: 'bridge' | 'inline' = 'bridge';
  export let visualStyle: 'arcade-glass' | 'word-line' | 'pixel-cabinet' = 'arcade-glass';
  export let quickIcon: 'stair' | 'spark' | 'cartridge' = 'stair';

  const PRONOUNS = ['je', 'tu', 'il / elle / on', 'nous', 'vous', 'ils / elles'];
  const ALL_TENSES = [
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

  const EXPECTED_ANSWERS: string[][][] = [
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
    return Array.from({ length: ALL_TENSES.length }, () => Array(PRONOUNS.length).fill(''));
  }

  function createChanceGrid(): boolean[][] {
    return Array.from({ length: ALL_TENSES.length }, () => Array(PRONOUNS.length).fill(false));
  }

  let answers = createAnswerGrid();
  let quickSubmitSpent = createChanceGrid();

  let activeTenseIndex = 0;
  let activePronounIndex = 0;
  let answerInput: HTMLInputElement;
  let phonePreview: HTMLElement;
  let previewHeight = 390;
  let runComplete = false;
  let dockTimer: number | undefined;
  let quickFeedbackTimer: number | undefined;
  let enterGuardTimer: number | undefined;
  let quickFeedback = '';
  let quickExplanationOpen = false;
  let enterGuardActive = false;
  let isComposing = false;
  let autoAdvanceInFlight = false;

  $: tenses = ALL_TENSES.slice(0, tenseCount);
  $: activeTense = tenses[activeTenseIndex];
  $: currentAnswer = answers[activeTenseIndex][activePronounIndex];
  $: expectedAnswers = EXPECTED_ANSWERS[activeTenseIndex]?.[activePronounIndex] ?? [];
  $: currentQuickSubmitSpent = quickSubmitSpent[activeTenseIndex][activePronounIndex];
  $: quickSubmitReady = expectedAnswers.length > 0 && !currentQuickSubmitSpent;
  $: totalAnswered = answers
    .slice(0, tenseCount)
    .reduce((total, tenseAnswers) => total + tenseAnswers.filter((answer) => answer.trim()).length, 0);
  $: totalCells = tenseCount * PRONOUNS.length;
  $: progress = Math.max(2, (totalAnswered / totalCells) * 100);
  $: previousTense = activeTenseIndex > 0 ? tenses[activeTenseIndex - 1] : 'Start';
  $: nextTense = activeTenseIndex < tenses.length - 1 ? tenses[activeTenseIndex + 1] : 'Finish';
  $: quickIconName = quickIcon === 'stair' ? 'stair bolt' : quickIcon === 'spark' ? 'spark bolt' : 'cartridge bolt';

  function answeredInTense(index: number): number {
    return answers[index].filter((answer) => answer.trim()).length;
  }

  function isTenseComplete(index: number): boolean {
    return answeredInTense(index) === PRONOUNS.length;
  }

  function updateCurrentAnswer(value: string): void {
    const next = answers.map((tenseAnswers) => [...tenseAnswers]);
    next[activeTenseIndex][activePronounIndex] = value;
    answers = next;
    runComplete = false;
  }

  function normalizeDraft(value: string): string {
    return value
      .normalize('NFC')
      .toLocaleLowerCase('fr-FR')
      .replace(/\s+/g, ' ')
      .trimStart();
  }

  function markQuickSubmitSpent(): void {
    const next = quickSubmitSpent.map((tenseChances) => [...tenseChances]);
    next[activeTenseIndex][activePronounIndex] = true;
    quickSubmitSpent = next;
  }

  function armEnterGuard(): void {
    enterGuardActive = true;
    window.clearTimeout(enterGuardTimer);
    enterGuardTimer = window.setTimeout(() => {
      enterGuardActive = false;
    }, 600);
  }

  async function autoSubmit(value: string): Promise<void> {
    await tick();
    quickFeedback = `${value.trim()} · correct, advanced`;
    window.clearTimeout(quickFeedbackTimer);
    quickFeedbackTimer = window.setTimeout(() => {
      quickFeedback = '';
    }, 1050);
    await advance();
    autoAdvanceInFlight = false;
  }

  function processInput(value: string): void {
    quickExplanationOpen = false;
    updateCurrentAnswer(value);
    if (isComposing || autoAdvanceInFlight || currentQuickSubmitSpent || expectedAnswers.length === 0) {
      return;
    }

    const draft = normalizeDraft(value);
    if (!draft) {
      return;
    }
    const normalizedAnswers = expectedAnswers.map((answer) => normalizeDraft(answer).trimEnd());
    const submitted = draft.trimEnd();
    if (normalizedAnswers.includes(submitted)) {
      armEnterGuard();
      autoAdvanceInFlight = true;
      void autoSubmit(value);
      return;
    }
    if (!normalizedAnswers.some((answer) => answer.startsWith(draft))) {
      markQuickSubmitSpent();
    }
  }

  function handleInput(event: Event): void {
    processInput((event.currentTarget as HTMLInputElement).value);
  }

  function handleCompositionEnd(event: CompositionEvent): void {
    isComposing = false;
    processInput((event.currentTarget as HTMLInputElement).value);
  }

  async function focusAnswer(): Promise<void> {
    await tick();
    if (!answerInput) {
      return;
    }
    const alreadyFocused = document.activeElement === answerInput;
    answerInput.focus({ preventScroll: true });
    const end = answerInput.value.length;
    answerInput.setSelectionRange(end, end);
    if (!alreadyFocused && shouldDockPhonePreview()) {
      schedulePreviewDock();
    }
  }

  async function selectPronoun(index: number): Promise<void> {
    activePronounIndex = index;
    runComplete = false;
    quickExplanationOpen = false;
    await focusAnswer();
  }

  async function selectTense(index: number): Promise<void> {
    activeTenseIndex = index;
    const firstEmpty = answers[index].findIndex((answer) => !answer.trim());
    activePronounIndex = firstEmpty === -1 ? PRONOUNS.length - 1 : firstEmpty;
    runComplete = false;
    quickExplanationOpen = false;
    await focusAnswer();
  }

  async function advance(): Promise<void> {
    quickExplanationOpen = false;
    if (!currentAnswer.trim()) {
      if (activePronounIndex === 0) {
        return;
      }
      updateCurrentAnswer(answers[activeTenseIndex][activePronounIndex - 1]);
    }

    if (activePronounIndex < PRONOUNS.length - 1) {
      activePronounIndex += 1;
    } else if (activeTenseIndex < tenses.length - 1) {
      activeTenseIndex += 1;
      const firstEmpty = answers[activeTenseIndex].findIndex((answer) => !answer.trim());
      activePronounIndex = firstEmpty === -1 ? 0 : firstEmpty;
    } else {
      runComplete = true;
    }
    await focusAnswer();
  }

  async function returnToPrevious(): Promise<void> {
    quickExplanationOpen = false;
    if (activePronounIndex > 0) {
      activePronounIndex -= 1;
    } else if (activeTenseIndex > 0) {
      activeTenseIndex -= 1;
      activePronounIndex = PRONOUNS.length - 1;
    }
    runComplete = false;
    await focusAnswer();
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      event.preventDefault();
      if (enterGuardActive) {
        return;
      }
      void advance();
      return;
    }
    if (event.key === 'Backspace' && !currentAnswer) {
      event.preventDefault();
      void returnToPrevious();
    }
  }

  function reset(): void {
    answers = createAnswerGrid();
    quickSubmitSpent = createChanceGrid();
    activeTenseIndex = 0;
    activePronounIndex = 0;
    runComplete = false;
    quickFeedback = '';
    quickExplanationOpen = false;
    window.clearTimeout(enterGuardTimer);
    enterGuardActive = false;
    autoAdvanceInFlight = false;
  }

  function toggleQuickExplanation(): void {
    quickExplanationOpen = !quickExplanationOpen;
  }

  function jumpTense(direction: 1 | -1): void {
    const nextIndex = (activeTenseIndex + direction + tenses.length) % tenses.length;
    void selectTense(nextIndex);
  }

  async function toggleFullscreen(): Promise<void> {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await phonePreview.requestFullscreen();
      }
    } catch {
      // Some mobile browsers expose the button but reserve fullscreen for installed apps.
    }
  }

  function syncPreviewHeight(): void {
    const viewportHeight = window.visualViewport?.height ?? window.innerHeight;
    const mobileLayout = window.matchMedia('(max-width: 600px)').matches;
    const maximum = mobileLayout ? 370 : 390;
    const minimum = mobileLayout ? 286 : 318;
    const gutter = mobileLayout ? 8 : 18;
    previewHeight = Math.max(minimum, Math.min(maximum, viewportHeight - gutter));
  }

  function shouldDockPhonePreview(): boolean {
    return window.matchMedia('(max-width: 760px) and (hover: none) and (pointer: coarse)').matches;
  }

  function dockPreviewToViewport(): void {
    if (!shouldDockPhonePreview() || !phonePreview || document.activeElement !== answerInput) {
      return;
    }
    syncPreviewHeight();
    window.requestAnimationFrame(() => {
      if (document.activeElement !== answerInput) {
        return;
      }
      const rect = phonePreview.getBoundingClientRect();
      const targetTop = (window.visualViewport?.offsetTop ?? 0) + 4;
      const targetScroll = window.scrollY + rect.top - targetTop;
      window.scrollTo({ top: Math.max(0, targetScroll), behavior: 'auto' });
    });
  }

  function schedulePreviewDock(delay = 180): void {
    window.clearTimeout(dockTimer);
    dockTimer = window.setTimeout(dockPreviewToViewport, delay);
  }

  function handleInputFocus(): void {
    if (shouldDockPhonePreview()) {
      schedulePreviewDock(420);
    }
  }

  function handleViewportResize(): void {
    syncPreviewHeight();
    if (shouldDockPhonePreview() && document.activeElement === answerInput) {
      schedulePreviewDock(160);
    }
  }

  onMount(() => {
    syncPreviewHeight();
    const viewport = window.visualViewport;
    viewport?.addEventListener('resize', handleViewportResize);
    window.addEventListener('resize', handleViewportResize);

    return () => {
      window.clearTimeout(dockTimer);
      window.clearTimeout(quickFeedbackTimer);
      window.clearTimeout(enterGuardTimer);
      viewport?.removeEventListener('resize', handleViewportResize);
      window.removeEventListener('resize', handleViewportResize);
    };
  });
</script>

<article class="mobile-concept" data-tense-count={tenseCount}>
  <header class="concept-intro">
    <div class="concept-index">{index}</div>
    <div>
      <p>{kicker}</p>
      <h2>{title}</h2>
      <span>{description}</span>
    </div>
  </header>

  <div class="phone-cradle">
    <section
      class:bridge-tense={tenseLayout === 'bridge'}
      class:compact-preview={previewHeight < 380}
      class:inline-tense={tenseLayout === 'inline'}
      class:nine-tense={tenseCount === 9}
      class:style-arcade-glass={visualStyle === 'arcade-glass'}
      class:style-word-line={visualStyle === 'word-line'}
      class:style-pixel-cabinet={visualStyle === 'pixel-cabinet'}
      class="phone-preview"
      bind:this={phonePreview}
      style={`--preview-height: ${previewHeight}px`}
    >
      <div class="phone-speaker" aria-hidden="true"></div>
      <div class="game-half">
        <header class="game-topbar">
          <div class="game-identity">
            <span>VERB LAB</span>
            <strong>Table run</strong>
          </div>
          <div class="run-progress" aria-label={`${totalAnswered} of ${totalCells} answers filled`}>
            <span><b>{totalAnswered}</b> / {totalCells}</span>
            <i><s style={`width: ${progress}%`}></s></i>
          </div>
          <button class="fullscreen-button" type="button" aria-label="Toggle fullscreen" on:click={toggleFullscreen}>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M8 4H4v4M16 4h4v4M20 16v4h-4M4 16v4h4"></path>
            </svg>
          </button>
        </header>

        {#if tenseCount === 3}
          <nav class="tense-trio" aria-label="Tenses in this run">
            {#each tenses as tense, tenseIndex}
              <button
                class:active={tenseIndex === activeTenseIndex}
                class:complete={isTenseComplete(tenseIndex)}
                type="button"
                aria-current={tenseIndex === activeTenseIndex ? 'step' : undefined}
                on:click={() => selectTense(tenseIndex)}
              >
                <span>{String(tenseIndex + 1).padStart(2, '0')}</span>
                <strong>{tense}</strong>
                <small>{answeredInTense(tenseIndex)}/6</small>
              </button>
            {/each}
          </nav>
        {:else}
          <section class="tense-marquee" aria-label="Tense navigation">
            <nav class="tense-rail" aria-label="Nine tenses in this run">
              {#each tenses as tense, tenseIndex}
                <button
                  class:active={tenseIndex === activeTenseIndex}
                  class:complete={isTenseComplete(tenseIndex)}
                  type="button"
                  aria-label={`${tense}, ${answeredInTense(tenseIndex)} of 6 filled`}
                  aria-current={tenseIndex === activeTenseIndex ? 'step' : undefined}
                  on:click={() => selectTense(tenseIndex)}
                >
                  <span>{tenseIndex + 1}</span>
                </button>
              {/each}
            </nav>
            {#if tenseLayout === 'bridge'}
              <div class="marquee-copy">
                <span>{previousTense}</span>
                <div>
                  <small>TENSE {activeTenseIndex + 1} / {tenses.length}</small>
                  <strong>{activeTense}</strong>
                </div>
                <span>{nextTense}</span>
              </div>
            {/if}
          </section>
        {/if}

        <section
          class:auto-advanced={Boolean(quickFeedback)}
          class="answer-stage"
          class:complete-stage={runComplete}
        >
          {#if tenseLayout === 'inline'}
            <div class="inline-tense-cue">
              <div>
                <strong>{activeTense}</strong>
              </div>
              <span>ANSWER {activePronounIndex + 1} / 6</span>
            </div>
          {:else}
            <div class="answer-meta">
              <span>CURRENT ANSWER</span>
              <small>{activePronounIndex + 1} / 6</small>
            </div>
          {/if}
          <div class="equation">
            <span>{PRONOUNS[activePronounIndex]}</span>
            <b>+</b>
            <strong>aller</strong>
          </div>
          <label class:quick-spent={currentQuickSubmitSpent} class="answer-field">
            <span class="sr-only">Conjugation for {PRONOUNS[activePronounIndex]} in {activeTense}</span>
            <input
              bind:this={answerInput}
              type="text"
              value={currentAnswer}
              inputmode="text"
              enterkeyhint={activeTenseIndex === tenses.length - 1 && activePronounIndex === PRONOUNS.length - 1 ? 'done' : 'next'}
              autocomplete="off"
              autocapitalize="none"
              spellcheck="false"
              placeholder="Type the form"
              aria-describedby={runComplete || expectedAnswers.length === 0 ? `quick-status-${index}` : undefined}
              on:compositionend={handleCompositionEnd}
              on:compositionstart={() => (isComposing = true)}
              on:focus={handleInputFocus}
              on:input={handleInput}
              on:keydown={handleKeydown}
            />
            <button type="button" aria-label="Move to next answer" on:click={advance}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 10 4 4 4-4"></path></svg>
            </button>
          </label>
          <div class="quick-control-row">
            <button
              class:accepted={Boolean(quickFeedback)}
              class:guarding={enterGuardActive}
              class:spent={!quickSubmitReady}
              class="quick-icon-button charge"
              type="button"
              aria-controls={`quick-explanation-${index}`}
              aria-expanded={quickExplanationOpen}
              aria-label={quickSubmitReady
                ? `Instant submit is ready, shown by the ${quickIconName}. Tap for an explanation.`
                : currentQuickSubmitSpent
                  ? `Instant submit chance spent, shown by the ${quickIconName}. Tap for an explanation.`
                  : `Instant submit is unavailable for this form, shown by the ${quickIconName}. Tap for an explanation.`}
              on:click={toggleQuickExplanation}
              on:pointerdown|preventDefault
            >
              {#if quickIcon === 'stair'}
                <svg class="pixel-bolt pixel-bolt-stair" viewBox="0 0 32 32" shape-rendering="crispEdges" aria-hidden="true">
                  <path class="pixel-frame" d="M7 3h18v2h4v22h-4v2H7v-2H3V5h4z"></path>
                  <g class="icon-core">
                    <rect x="18" y="3" width="8" height="4"></rect>
                    <rect x="14" y="7" width="8" height="4"></rect>
                    <rect x="10" y="11" width="8" height="4"></rect>
                    <rect x="6" y="15" width="16" height="4"></rect>
                    <rect x="14" y="19" width="8" height="4"></rect>
                    <rect x="10" y="23" width="8" height="4"></rect>
                    <rect x="6" y="27" width="8" height="3"></rect>
                  </g>
                  <rect class="icon-particle particle-one" x="25" y="7" width="2" height="2"></rect>
                  <rect class="icon-particle particle-two" x="5" y="23" width="2" height="2"></rect>
                </svg>
              {:else if quickIcon === 'spark'}
                <svg class="pixel-bolt pixel-bolt-spark" viewBox="0 0 32 32" shape-rendering="crispEdges" aria-hidden="true">
                  <g class="icon-core">
                    <rect x="19" y="3" width="7" height="4"></rect>
                    <rect x="16" y="7" width="7" height="4"></rect>
                    <rect x="13" y="11" width="7" height="4"></rect>
                    <rect x="8" y="15" width="15" height="4"></rect>
                    <rect x="15" y="19" width="7" height="4"></rect>
                    <rect x="12" y="23" width="7" height="4"></rect>
                    <rect x="9" y="27" width="7" height="3"></rect>
                  </g>
                  <rect class="spark-pixel spark-one" x="5" y="5" width="3" height="3"></rect>
                  <rect class="spark-pixel spark-two" x="25" y="23" width="3" height="3"></rect>
                  <rect class="spark-pixel spark-three" x="4" y="27" width="2" height="2"></rect>
                </svg>
              {:else}
                <svg class="pixel-bolt pixel-bolt-cartridge" viewBox="0 0 32 32" shape-rendering="crispEdges" aria-hidden="true">
                  <path class="pixel-frame" d="M6 3h20v3h3v20h-3v3H6v-3H3V6h3zM8 8v16h16V8z"></path>
                  <g class="icon-core">
                    <rect x="18" y="7" width="6" height="3"></rect>
                    <rect x="15" y="10" width="6" height="3"></rect>
                    <rect x="12" y="13" width="6" height="3"></rect>
                    <rect x="9" y="16" width="12" height="3"></rect>
                    <rect x="15" y="19" width="6" height="3"></rect>
                    <rect x="12" y="22" width="6" height="3"></rect>
                    <rect x="9" y="25" width="6" height="2"></rect>
                  </g>
                  <rect class="charge-pip pip-one" x="5" y="14" width="2" height="4"></rect>
                  <rect class="charge-pip pip-two" x="25" y="14" width="2" height="4"></rect>
                </svg>
              {/if}
              <span class="quick-state-dot" aria-hidden="true"></span>
            </button>
            {#if quickExplanationOpen}
              <div class="quick-explanation" id={`quick-explanation-${index}`} role="note">
                {#if quickSubmitReady}
                  <span>ONE-SHOT ARMED</span>
                  <strong>A perfect first attempt advances instantly.</strong>
                  <p>The first impossible letter turns this signal off for the current cell. Then the answer waits for Enter.</p>
                {:else if currentQuickSubmitSpent}
                  <span>ONE-SHOT SPENT</span>
                  <strong>This cell now needs Enter.</strong>
                  <p>Correct the form and submit normally. The next cell receives a fresh one-shot chance.</p>
                {:else}
                  <span>SPECIAL FORM</span>
                  <strong>Instant submit is paused here.</strong>
                  <p>This tense does not use the current pronoun, so the regular Enter flow stays in control.</p>
                {/if}
              </div>
            {/if}
          </div>
          {#if runComplete || expectedAnswers.length === 0}
            <div class="answer-status" id={`quick-status-${index}`} aria-live="polite">
              {#if runComplete}
              <p class="complete-message">All {tenseCount} tenses reached. Prototype run complete.</p>
              {:else}
                <p>Special form · Enter submits this cell.</p>
              {/if}
            </div>
          {/if}
        </section>

        <nav class="pronoun-dock" aria-label="Pronouns in the active tense">
          {#each PRONOUNS as pronoun, pronounIndex}
            <button
              class:active={pronounIndex === activePronounIndex}
              class:filled={Boolean(answers[activeTenseIndex][pronounIndex].trim())}
              type="button"
              aria-label={`${pronoun}: ${answers[activeTenseIndex][pronounIndex] ? 'filled' : 'empty'}`}
              aria-current={pronounIndex === activePronounIndex ? 'step' : undefined}
              on:click={() => selectPronoun(pronounIndex)}
            >
              <span>{pronounIndex + 1}</span>
              <small>{pronoun}</small>
            </button>
          {/each}
        </nav>
      </div>
    </section>
  </div>

  <footer class="prototype-controls">
    <span>LIVE PROTOTYPE · TAP THE FIELD FOR YOUR PHONE KEYBOARD</span>
    <div>
      <button type="button" on:click={returnToPrevious}>← Previous cell</button>
      <button type="button" on:click={reset}>Reset</button>
      <button type="button" on:click={() => jumpTense(1)}>Next tense →</button>
    </div>
  </footer>
</article>

<style>
  .mobile-concept {
    display: grid;
    min-width: 0;
    gap: 1rem;
  }

  .concept-intro {
    display: grid;
    min-height: 8.2rem;
    grid-template-columns: auto 1fr;
    gap: 0.9rem;
    align-items: start;
  }

  .concept-index {
    display: grid;
    min-width: 3.4rem;
    height: 2.3rem;
    padding-inline: 0.55rem;
    place-items: center;
    border: 1px solid color-mix(in srgb, var(--accent) 55%, var(--line));
    border-radius: 10px;
    color: var(--accent-strong);
    background: var(--accent-soft);
    font: 850 0.7rem/1 var(--mono);
    letter-spacing: 0.06em;
  }

  .concept-intro p {
    margin: 0 0 0.28rem;
    color: var(--accent-strong);
    font: 800 0.64rem/1 var(--mono);
    letter-spacing: 0.09em;
    text-transform: uppercase;
  }

  .concept-intro h2 {
    margin: 0;
    color: var(--text);
    font: 820 clamp(1.2rem, 2.4vw, 1.65rem)/1.05 var(--display);
    letter-spacing: -0.035em;
  }

  .concept-intro > div:last-child > span {
    display: block;
    max-width: 42rem;
    margin-top: 0.46rem;
    color: var(--muted);
    font-size: 0.78rem;
    line-height: 1.5;
  }

  .phone-cradle {
    display: grid;
    min-width: 0;
    place-items: center;
    padding: clamp(0.5rem, 2vw, 1.1rem);
    border: 1px solid var(--line);
    border-radius: 30px;
    background:
      radial-gradient(circle at 50% 8%, color-mix(in srgb, var(--accent) 14%, transparent), transparent 36%),
      repeating-linear-gradient(135deg, transparent 0 12px, color-mix(in srgb, var(--line) 22%, transparent) 12px 13px),
      color-mix(in srgb, var(--surface-strong) 88%, var(--surface-dark));
  }

  .phone-preview {
    --cyan: var(--accent-strong);
    --yellow: var(--accent-2);
    --green: var(--success);
    --ink: color-mix(in srgb, var(--surface-dark) 92%, #05010d);
    --panel: color-mix(in srgb, var(--surface-strong) 32%, var(--ink));
    --soft-panel: color-mix(in srgb, var(--accent-soft) 72%, var(--ink));
    position: relative;
    width: min(100%, 390px);
    height: min(390px, var(--preview-height));
    min-height: 286px;
    overflow: hidden;
    scroll-margin-top: 4px;
    border: 5px solid color-mix(in srgb, var(--accent) 28%, #160b25);
    border-radius: 34px;
    color: #f7f9ff;
    background:
      linear-gradient(color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px),
      linear-gradient(90deg, color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px),
      var(--ink);
    background-size: 24px 24px;
    box-shadow:
      0 24px 60px rgba(5, 1, 13, 0.46),
      0 0 24px color-mix(in srgb, var(--accent) 10%, transparent),
      inset 0 0 0 1px color-mix(in srgb, var(--accent) 18%, transparent);
  }

  .phone-preview:fullscreen {
    width: 100vw;
    height: 100dvh;
    max-width: none;
    border: 0;
    border-radius: 0;
  }

  .phone-speaker {
    position: absolute;
    z-index: 3;
    top: 7px;
    left: 50%;
    width: 42px;
    height: 3px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.16);
    transform: translateX(-50%);
  }

  .game-half {
    display: grid;
    height: 100%;
    grid-template-rows: 52px auto minmax(0, 1fr) 48px;
    padding: 12px 12px 10px;
  }

  .game-topbar {
    display: grid;
    grid-template-columns: auto 1fr 34px;
    gap: 0.65rem;
    align-items: center;
    border-bottom: 1px solid color-mix(in srgb, var(--accent) 24%, transparent);
  }

  .game-identity {
    display: grid;
    gap: 0.12rem;
  }

  .game-identity span,
  .answer-meta span,
  .tense-marquee small {
    color: var(--cyan);
    font: 800 0.5rem/1 var(--mono);
    letter-spacing: 0.1em;
  }

  .game-identity strong {
    color: #fff;
    font-size: 0.72rem;
    line-height: 1;
  }

  .run-progress {
    display: grid;
    min-width: 0;
    gap: 0.28rem;
  }

  .run-progress > span {
    justify-self: end;
    color: #91a1b9;
    font: 750 0.57rem/1 var(--mono);
  }

  .run-progress b {
    color: #fff;
  }

  .run-progress i {
    display: block;
    height: 3px;
    overflow: hidden;
    border-radius: 999px;
    background: color-mix(in srgb, var(--accent) 17%, var(--ink));
  }

  .run-progress s {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--cyan), var(--yellow));
    box-shadow: 0 0 10px color-mix(in srgb, var(--accent) 50%, transparent);
    text-decoration: none;
    transition: width 180ms ease;
  }

  .fullscreen-button {
    display: grid;
    width: 32px;
    height: 32px;
    padding: 0;
    place-items: center;
    border: 1px solid color-mix(in srgb, var(--accent) 34%, transparent);
    border-radius: 9px;
    color: #dbe5f6;
    background: color-mix(in srgb, var(--accent-soft) 32%, transparent);
  }

  .fullscreen-button svg {
    width: 15px;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.8;
  }

  .tense-trio {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 5px;
    padding-block: 8px 6px;
  }

  .tense-trio button {
    display: grid;
    min-width: 0;
    height: 46px;
    grid-template-columns: auto 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 0 5px;
    align-items: center;
    padding: 6px 7px;
    border: 1px solid color-mix(in srgb, var(--accent) 24%, transparent);
    border-radius: 10px;
    color: #73829b;
    background: color-mix(in srgb, var(--surface-strong) 9%, var(--ink));
    text-align: left;
  }

  .tense-trio button > span {
    grid-row: 1 / 3;
    color: #60708b;
    font: 800 0.46rem/1 var(--mono);
  }

  .tense-trio strong {
    overflow: hidden;
    font-size: clamp(0.57rem, 2.4vw, 0.68rem);
    line-height: 1.05;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tense-trio small {
    color: #677892;
    font: 700 0.46rem/1 var(--mono);
  }

  .tense-trio button.active {
    border-color: var(--yellow);
    color: #fff;
    background: linear-gradient(145deg, color-mix(in srgb, var(--yellow) 16%, var(--ink)), var(--panel));
    box-shadow: inset 0 -2px 0 var(--yellow), 0 0 18px color-mix(in srgb, var(--yellow) 12%, transparent);
  }

  .tense-trio button.active > span,
  .tense-trio button.active small {
    color: var(--yellow);
  }

  .tense-trio button.complete:not(.active) {
    border-color: rgba(94, 242, 164, 0.4);
    color: var(--green);
  }

  .tense-marquee {
    display: grid;
    gap: 4px;
    padding-block: 5px 3px;
  }

  .marquee-copy {
    display: grid;
    grid-template-columns: minmax(0, 0.55fr) minmax(0, 1.9fr) minmax(0, 0.55fr);
    gap: 8px;
    align-items: center;
  }

  .marquee-copy > span {
    overflow: hidden;
    color: #60708b;
    font-size: 0.55rem;
    font-weight: 700;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .marquee-copy > span:last-child {
    text-align: right;
  }

  .marquee-copy > div {
    display: grid;
    min-width: 0;
    justify-items: center;
    gap: 2px;
  }

  .marquee-copy strong {
    width: 100%;
    overflow: hidden;
    color: var(--yellow);
    font-size: clamp(1.05rem, 4.5vw, 1.2rem);
    line-height: 1.05;
    text-align: center;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tense-rail {
    display: grid;
    grid-template-columns: repeat(9, 1fr);
    gap: 4px;
  }

  .tense-rail button {
    position: relative;
    display: grid;
    height: 18px;
    padding: 0;
    place-items: center;
    border: 0;
    border-radius: 4px;
    color: color-mix(in srgb, white 40%, var(--accent));
    background: color-mix(in srgb, var(--accent) 14%, var(--ink));
    font: 800 0.43rem/1 var(--mono);
  }

  .tense-rail button::after {
    position: absolute;
    right: 3px;
    bottom: 2px;
    left: 3px;
    height: 2px;
    border-radius: 99px;
    background: color-mix(in srgb, var(--accent) 28%, var(--ink));
    content: '';
  }

  .tense-rail button.complete {
    color: #071b17;
    background: var(--green);
  }

  .tense-rail button.complete::after {
    background: rgba(7, 27, 23, 0.35);
  }

  .tense-rail button.active {
    color: #211800;
    background: var(--yellow);
    box-shadow: 0 0 12px color-mix(in srgb, var(--yellow) 38%, transparent);
  }

  .tense-rail button.active::after {
    background: #5c4700;
  }

  .answer-stage {
    position: relative;
    display: grid;
    min-height: 0;
    align-content: center;
    gap: 6px;
    padding: 7px 8px 8px;
    border: 1px solid color-mix(in srgb, var(--accent) 28%, transparent);
    border-radius: 14px;
    background:
      linear-gradient(color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px),
      linear-gradient(90deg, color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px),
      color-mix(in srgb, var(--ink) 92%, var(--accent-soft));
    background-size: 20px 20px;
    transition: border-color 160ms ease, box-shadow 160ms ease;
  }

  .answer-stage.complete-stage {
    border-color: color-mix(in srgb, var(--green) 65%, transparent);
    box-shadow: inset 0 0 24px color-mix(in srgb, var(--green) 8%, transparent);
  }

  .answer-stage.auto-advanced {
    border-color: color-mix(in srgb, var(--green) 72%, transparent);
    box-shadow: inset 0 0 26px color-mix(in srgb, var(--green) 10%, transparent), 0 0 18px color-mix(in srgb, var(--green) 6%, transparent);
  }

  .answer-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .answer-meta small {
    color: #8493aa;
    font: 800 0.52rem/1 var(--mono);
  }

  .inline-tense-cue {
    position: relative;
    display: grid;
    min-width: 0;
    place-items: center;
  }

  .inline-tense-cue > div {
    display: grid;
    min-width: 0;
    justify-items: center;
    gap: 2px;
  }

  .inline-tense-cue strong {
    max-width: 15rem;
    overflow: hidden;
    color: var(--yellow);
    font-size: clamp(1.05rem, 4.5vw, 1.2rem);
    line-height: 1.05;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .inline-tense-cue > span {
    position: absolute;
    right: 0;
    bottom: 2px;
    color: #8493aa;
    font: 800 0.48rem/1 var(--mono);
  }

  .quick-control-row {
    position: relative;
    display: flex;
    min-height: 32px;
    justify-content: flex-end;
    padding-right: 3px;
  }

  .quick-icon-button {
    position: relative;
    display: grid;
    width: 32px;
    height: 32px;
    padding: 0;
    place-items: center;
    border: 1px solid color-mix(in srgb, var(--yellow) 68%, transparent);
    border-radius: 6px;
    color: var(--yellow);
    background: color-mix(in srgb, var(--accent-soft) 130%, var(--ink));
    box-shadow:
      0 0 0 3px color-mix(in srgb, var(--accent) 8%, transparent),
      0 0 18px color-mix(in srgb, var(--yellow) 18%, transparent),
      inset 0 0 12px color-mix(in srgb, var(--accent) 10%, transparent);
    image-rendering: pixelated;
    animation: signalBreathe 1.8s steps(2, end) infinite;
  }

  .quick-icon-button svg {
    width: 26px;
    height: 26px;
    overflow: visible;
    fill: none;
    image-rendering: pixelated;
  }

  .quick-icon-button .pixel-frame {
    fill: currentColor;
    opacity: 0.18;
  }

  .quick-icon-button .icon-core {
    fill: currentColor;
  }

  .quick-icon-button .icon-particle,
  .quick-icon-button .spark-pixel,
  .quick-icon-button .charge-pip {
    fill: color-mix(in srgb, white 45%, var(--yellow));
  }

  .quick-icon-button .quick-state-dot {
    position: absolute;
    top: 2px;
    right: 2px;
    width: 4px;
    height: 4px;
    background: white;
    box-shadow: 0 0 7px 2px var(--yellow);
  }

  .quick-icon-button:not(.spent) .pixel-bolt-stair .icon-core {
    animation: stairCharge 1.25s steps(2, end) infinite;
  }

  .quick-icon-button:not(.spent) .pixel-bolt-spark .icon-core {
    animation: sparkJolt 1.1s steps(2, end) infinite;
  }

  .quick-icon-button:not(.spent) .pixel-bolt-spark .spark-one {
    animation: sparkPixel 0.9s steps(2, end) infinite;
  }

  .quick-icon-button:not(.spent) .pixel-bolt-spark .spark-two {
    animation: sparkPixel 0.9s 0.3s steps(2, end) infinite;
  }

  .quick-icon-button:not(.spent) .pixel-bolt-spark .spark-three {
    animation: sparkPixel 0.9s 0.6s steps(2, end) infinite;
  }

  .quick-icon-button:not(.spent) .pixel-bolt-cartridge .icon-core {
    animation: cartridgeCharge 1.4s steps(3, end) infinite;
  }

  .quick-icon-button:not(.spent) .pixel-bolt-cartridge .charge-pip {
    animation: chargePip 1.4s steps(2, end) infinite;
  }

  .quick-icon-button.spent {
    border-color: color-mix(in srgb, var(--muted) 36%, transparent);
    color: color-mix(in srgb, var(--muted) 58%, var(--ink));
    background: color-mix(in srgb, var(--surface-dark) 88%, black);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.025);
    animation: none;
  }

  .quick-icon-button.spent .icon-particle,
  .quick-icon-button.spent .spark-pixel,
  .quick-icon-button.spent .charge-pip {
    opacity: 0;
    animation: none;
  }

  .quick-icon-button.spent .quick-state-dot {
    background: color-mix(in srgb, var(--muted) 45%, var(--ink));
    box-shadow: none;
  }

  .quick-icon-button.accepted {
    animation: signalAccepted 0.48s ease-out both;
  }

  .quick-icon-button.guarding::before {
    position: absolute;
    border: 1px solid color-mix(in srgb, var(--green) 72%, transparent);
    border-radius: 8px;
    content: '';
    inset: -4px;
    pointer-events: none;
    animation: guardWindow 0.6s ease-out both;
  }

  .quick-explanation {
    position: absolute;
    z-index: 6;
    right: 0;
    bottom: calc(100% + 6px);
    display: grid;
    width: min(270px, calc(100% - 6px));
    gap: 0.25rem;
    padding: 0.68rem 0.75rem;
    border: 1px solid color-mix(in srgb, var(--accent) 56%, transparent);
    border-radius: 11px;
    color: #dfe8f8;
    background: color-mix(in srgb, var(--surface-dark) 96%, black);
    box-shadow: 0 14px 35px rgba(0, 0, 0, 0.5), 0 0 20px color-mix(in srgb, var(--accent) 10%, transparent);
    animation: explanationIn 140ms ease-out both;
  }

  .quick-explanation > span {
    color: var(--cyan);
    font: 800 0.48rem/1 var(--mono);
    letter-spacing: 0.08em;
  }

  .quick-explanation > strong {
    color: #fff;
    font-size: 0.68rem;
    line-height: 1.2;
  }

  .quick-explanation > p {
    margin: 0;
    color: #91a2bc;
    font-size: 0.58rem;
    line-height: 1.35;
  }

  .equation {
    display: flex;
    min-width: 0;
    align-items: baseline;
    justify-content: center;
    gap: 0.42rem;
    color: #fff;
    font: 800 clamp(1.05rem, 5vw, 1.55rem)/1 var(--display);
    letter-spacing: -0.04em;
  }

  .equation span {
    max-width: 48%;
    overflow: hidden;
    color: var(--yellow);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .equation b {
    color: #53617a;
    font-size: 0.72em;
  }

  .answer-field {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 38px;
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--accent) 56%, transparent);
    border-radius: 10px;
    background: color-mix(in srgb, var(--surface-dark) 88%, black);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 6%, transparent);
  }

  .answer-field:focus-within {
    border-color: var(--cyan);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 14%, transparent), 0 0 22px color-mix(in srgb, var(--accent) 8%, transparent);
  }

  .answer-field.quick-spent,
  .answer-field.quick-spent:focus-within {
    border-color: color-mix(in srgb, var(--danger) 72%, white 10%);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--danger) 11%, transparent), 0 0 20px color-mix(in srgb, var(--danger) 7%, transparent);
  }

  .answer-field input {
    min-width: 0;
    height: 42px;
    padding: 0 12px;
    border: 0;
    outline: 0;
    color: #fff;
    background: transparent;
    font: 750 1rem/1 var(--ui);
    text-align: center;
  }

  .answer-field input::placeholder {
    color: #586882;
  }

  .answer-field button {
    display: grid;
    padding: 0;
    place-items: center;
    border: 0;
    border-left: 1px solid color-mix(in srgb, var(--accent) 30%, transparent);
    color: color-mix(in srgb, var(--surface-dark) 90%, black);
    background: var(--yellow);
  }

  .answer-field button svg {
    width: 17px;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 2;
  }

  .answer-status {
    display: grid;
    min-height: 0.7rem;
    place-items: center;
  }

  .answer-status p {
    margin: 0;
    color: #72829a;
    font-size: 0.54rem;
    line-height: 1.2;
    text-align: center;
  }

  .answer-status .complete-message {
    color: var(--green);
    font-weight: 750;
  }

  .pronoun-dock {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 5px;
    align-items: end;
    padding-top: 7px;
  }

  .pronoun-dock button {
    display: grid;
    min-width: 0;
    height: 36px;
    gap: 2px;
    place-items: center;
    padding: 3px 2px;
    border: 1px solid color-mix(in srgb, var(--accent) 25%, transparent);
    border-radius: 8px;
    color: #7d8ca3;
    background: color-mix(in srgb, var(--surface-strong) 9%, var(--ink));
  }

  .pronoun-dock span {
    font: 800 0.52rem/1 var(--mono);
  }

  .pronoun-dock small {
    width: 100%;
    overflow: hidden;
    font-size: 0.46rem;
    font-weight: 700;
    line-height: 1;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .pronoun-dock button.filled {
    border-color: color-mix(in srgb, var(--green) 46%, transparent);
    color: var(--green);
  }

  .pronoun-dock button.active {
    border-color: var(--yellow);
    color: #211800;
    background: var(--yellow);
    box-shadow: 0 0 14px color-mix(in srgb, var(--yellow) 22%, transparent);
  }

  /* V1 mirrors the production Verb Lab's violet glass and warm focus color. */
  .style-arcade-glass {
    border-color: color-mix(in srgb, var(--accent) 45%, #160b25);
    background:
      radial-gradient(circle at 86% 4%, color-mix(in srgb, var(--accent) 18%, transparent), transparent 34%),
      linear-gradient(color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px),
      linear-gradient(90deg, color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px),
      var(--ink);
    background-size: auto, 24px 24px, 24px 24px, auto;
  }

  .style-arcade-glass .answer-stage {
    background:
      radial-gradient(circle at 50% 36%, color-mix(in srgb, var(--accent) 12%, transparent), transparent 45%),
      linear-gradient(color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px),
      linear-gradient(90deg, color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px),
      color-mix(in srgb, var(--ink) 92%, var(--accent-soft));
    background-size: auto, 20px 20px, 20px 20px, auto;
  }

  .style-arcade-glass .inline-tense-cue strong {
    text-shadow: 0 0 14px color-mix(in srgb, var(--yellow) 35%, transparent);
  }

  /* V2 borrows the Words game's open stage and answer underline. */
  .style-word-line {
    border-width: 3px;
    border-color: color-mix(in srgb, var(--accent) 38%, var(--line));
    background:
      radial-gradient(circle at 50% 42%, color-mix(in srgb, var(--accent) 17%, transparent), transparent 48%),
      color-mix(in srgb, var(--surface-dark) 94%, black);
  }

  .style-word-line .phone-speaker {
    background: color-mix(in srgb, var(--accent) 42%, transparent);
  }

  .style-word-line .game-topbar {
    border-bottom-color: color-mix(in srgb, var(--accent) 16%, transparent);
  }

  .style-word-line .tense-rail button {
    border: 1px solid color-mix(in srgb, var(--accent) 24%, transparent);
    background: transparent;
  }

  .style-word-line .tense-rail button::after {
    right: 5px;
    bottom: 1px;
    left: 5px;
    height: 1px;
    background: color-mix(in srgb, var(--accent) 36%, transparent);
  }

  .style-word-line .tense-rail button.active {
    border-color: var(--yellow);
    color: var(--yellow);
    background: color-mix(in srgb, var(--yellow) 7%, transparent);
    box-shadow: inset 0 -2px 0 var(--yellow), 0 0 12px color-mix(in srgb, var(--yellow) 14%, transparent);
  }

  .style-word-line .answer-stage {
    border: 0;
    border-right: 2px solid color-mix(in srgb, var(--accent) 34%, transparent);
    border-left: 2px solid color-mix(in srgb, var(--accent) 34%, transparent);
    border-radius: 0;
    background: transparent;
    box-shadow: none;
  }

  .style-word-line .answer-field,
  .style-word-line .answer-field:focus-within {
    border: 0;
    border-bottom: 2px solid var(--accent);
    border-radius: 0;
    background: transparent;
    box-shadow: 0 12px 20px -16px color-mix(in srgb, var(--accent) 62%, transparent);
  }

  .style-word-line .answer-field.quick-spent,
  .style-word-line .answer-field.quick-spent:focus-within {
    border-bottom-color: var(--danger);
    box-shadow: 0 12px 20px -16px color-mix(in srgb, var(--danger) 62%, transparent);
  }

  .style-word-line .answer-field button {
    border: 0;
    color: var(--yellow);
    background: transparent;
  }

  .style-word-line .quick-icon-button {
    border-color: color-mix(in srgb, var(--accent-strong) 72%, transparent);
    color: var(--accent-strong);
    background: color-mix(in srgb, var(--accent-soft) 74%, transparent);
  }

  .style-word-line .pronoun-dock button {
    border: 0;
    border-top: 1px solid color-mix(in srgb, var(--accent) 24%, transparent);
    border-radius: 0;
    background: transparent;
  }

  .style-word-line .pronoun-dock button.active {
    border-top-color: var(--yellow);
    color: var(--yellow);
    background: color-mix(in srgb, var(--yellow) 8%, transparent);
    box-shadow: inset 0 2px 0 var(--yellow);
  }

  /* V3 uses the app's restrained pixel language: one marquee and hard edges. */
  .style-pixel-cabinet {
    border-color: color-mix(in srgb, var(--accent) 58%, #160b25);
    border-radius: 18px;
    background:
      repeating-linear-gradient(180deg, rgba(255, 255, 255, 0.018) 0 2px, rgba(0, 0, 0, 0.08) 2px 4px),
      linear-gradient(color-mix(in srgb, var(--accent) 5%, transparent) 1px, transparent 1px),
      linear-gradient(90deg, color-mix(in srgb, var(--accent) 5%, transparent) 1px, transparent 1px),
      var(--ink);
    background-size: auto, 16px 16px, 16px 16px, auto;
    box-shadow:
      6px 6px 0 color-mix(in srgb, var(--accent) 18%, #08020f),
      0 0 24px color-mix(in srgb, var(--accent) 16%, transparent),
      inset 0 0 0 1px color-mix(in srgb, var(--yellow) 16%, transparent);
  }

  .style-pixel-cabinet .phone-speaker,
  .style-pixel-cabinet .fullscreen-button,
  .style-pixel-cabinet .tense-rail button,
  .style-pixel-cabinet .answer-stage,
  .style-pixel-cabinet .answer-field,
  .style-pixel-cabinet .quick-icon-button,
  .style-pixel-cabinet .pronoun-dock button {
    border-radius: 2px;
  }

  .style-pixel-cabinet .inline-tense-cue strong {
    max-width: 18rem;
    font: 400 clamp(0.72rem, 3.2vw, 0.9rem)/1.55 var(--marquee);
    letter-spacing: -0.03em;
    text-shadow: 2px 2px 0 color-mix(in srgb, var(--accent) 62%, transparent);
  }

  .style-pixel-cabinet .game-identity span,
  .style-pixel-cabinet .run-progress > span,
  .style-pixel-cabinet .inline-tense-cue > span,
  .style-pixel-cabinet .pronoun-dock span {
    font-size: 0.75rem;
  }

  .style-pixel-cabinet .answer-stage {
    border-color: color-mix(in srgb, var(--accent) 44%, transparent);
    background: color-mix(in srgb, var(--surface-dark) 92%, black);
  }

  .style-pixel-cabinet .answer-field {
    border-width: 2px;
    border-color: color-mix(in srgb, var(--accent) 70%, transparent);
    box-shadow: 3px 3px 0 color-mix(in srgb, var(--accent) 18%, transparent);
  }

  .style-pixel-cabinet .answer-field:focus-within {
    border-color: var(--yellow);
    box-shadow: 3px 3px 0 color-mix(in srgb, var(--yellow) 28%, transparent);
  }

  .style-pixel-cabinet .tense-rail button.active,
  .style-pixel-cabinet .pronoun-dock button.active {
    box-shadow: 3px 3px 0 color-mix(in srgb, var(--yellow) 28%, transparent);
  }

  .bridge-tense .game-half {
    grid-template-rows: 52px 61px minmax(0, 1fr) 48px;
  }

  .inline-tense .game-half {
    grid-template-rows: 52px 30px minmax(0, 1fr) 48px;
  }

  .inline-tense .tense-marquee {
    align-content: center;
    padding-block: 4px;
  }

  .bridge-tense .answer-stage {
    --answer-lift: clamp(8px, calc(var(--preview-height) - 294px), 24px);
    padding-top: 5px;
    padding-bottom: 6px;
  }

  .bridge-tense .answer-stage > .answer-meta,
  .bridge-tense .answer-stage > .equation,
  .bridge-tense .answer-stage > .answer-field,
  .bridge-tense .answer-stage > .quick-control-row,
  .bridge-tense .answer-stage > .answer-status {
    transform: translateY(calc(0px - var(--answer-lift)));
  }

  .compact-preview .game-half {
    grid-template-rows: 44px auto minmax(0, 1fr) 40px;
    padding: 8px 9px 7px;
  }

  .compact-preview.bridge-tense .game-half {
    grid-template-rows: 44px 52px minmax(0, 1fr) 40px;
  }

  .compact-preview.inline-tense .game-half {
    grid-template-rows: 44px 24px minmax(0, 1fr) 40px;
  }

  .compact-preview.inline-tense .tense-marquee {
    padding-block: 3px;
  }

  .compact-preview .fullscreen-button {
    width: 29px;
    height: 29px;
  }

  .compact-preview .tense-trio {
    padding-block: 5px;
  }

  .compact-preview .tense-trio button {
    height: 40px;
  }

  .compact-preview .tense-marquee {
    gap: 3px;
    padding-block: 2px 0;
  }

  .compact-preview .answer-stage,
  .compact-preview.nine-tense .answer-stage {
    gap: 4px;
    padding: 5px 7px;
  }

  .compact-preview .equation {
    font-size: clamp(1rem, 4.7vw, 1.35rem);
  }

  .compact-preview .answer-field input {
    height: 38px;
  }

  .compact-preview .answer-status p {
    font-size: 0.5rem;
  }

  .compact-preview .quick-icon-button {
    width: 28px;
    height: 28px;
    border-radius: 9px;
  }

  .compact-preview .quick-icon-button svg {
    width: 22px;
    height: 22px;
  }

  .compact-preview .quick-control-row {
    min-height: 28px;
  }

  .compact-preview .quick-explanation {
    bottom: calc(100% + 5px);
    padding: 0.58rem 0.65rem;
  }

  .compact-preview .pronoun-dock {
    padding-top: 4px;
  }

  .compact-preview .pronoun-dock button {
    height: 31px;
  }

  .prototype-controls {
    display: grid;
    gap: 0.65rem;
    padding-inline: 0.2rem;
  }

  .prototype-controls > span {
    color: var(--muted);
    font: 750 0.58rem/1.35 var(--mono);
    letter-spacing: 0.06em;
  }

  .prototype-controls > div {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
  }

  .prototype-controls button {
    min-height: 38px;
    padding: 0.55rem 0.72rem;
    border: 1px solid var(--line-strong);
    border-radius: 10px;
    color: var(--text);
    background: color-mix(in srgb, var(--surface-strong) 88%, transparent);
    font-size: 0.7rem;
    font-weight: 760;
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    clip-path: inset(50%);
    white-space: nowrap;
  }

  button {
    cursor: pointer;
    touch-action: manipulation;
  }

  button:focus-visible,
  input:focus-visible {
    outline: 2px solid var(--cyan, var(--accent));
    outline-offset: 2px;
  }

  @keyframes signalBreathe {
    0%, 100% { box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 7%, transparent), 0 0 13px color-mix(in srgb, var(--yellow) 14%, transparent); }
    50% { box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 11%, transparent), 0 0 22px color-mix(in srgb, var(--yellow) 30%, transparent); }
  }

  @keyframes stairCharge {
    0%, 100% { opacity: 0.72; transform: translate(0, 0); }
    50% { opacity: 1; transform: translate(1px, -1px); }
  }

  @keyframes sparkJolt {
    0%, 100% { opacity: 0.72; transform: translateX(0); }
    50% { opacity: 1; transform: translateX(1px); }
  }

  @keyframes sparkPixel {
    0%, 45% { opacity: 0; }
    46%, 78% { opacity: 1; }
    79%, 100% { opacity: 0.2; }
  }

  @keyframes cartridgeCharge {
    0%, 32% { opacity: 0.58; }
    33%, 66% { opacity: 0.8; }
    67%, 100% { opacity: 1; }
  }

  @keyframes chargePip {
    0%, 42% { opacity: 0.25; }
    43%, 100% { opacity: 1; }
  }

  @keyframes signalAccepted {
    0% { transform: scale(1); }
    42% { color: #fff; transform: scale(1.2); box-shadow: 0 0 28px color-mix(in srgb, var(--green) 65%, transparent); }
    100% { transform: scale(1); }
  }

  @keyframes guardWindow {
    from { opacity: 0.9; transform: scale(0.92); }
    to { opacity: 0; transform: scale(1.28); }
  }

  @keyframes explanationIn {
    from { opacity: 0; transform: translateY(-5px) scale(0.98); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }

  @media (max-width: 520px) {
    .concept-intro {
      min-height: 0;
      padding-inline: 0.15rem;
    }

    .concept-intro > div:last-child > span {
      font-size: 0.74rem;
    }

    .phone-cradle {
      margin-inline: calc(clamp(0rem, 3vw, 0.75rem) * -1);
      padding: 0;
      border: 0;
      border-radius: 0;
      background: transparent;
    }

    .phone-preview {
      width: 100%;
      border-width: 3px;
      border-radius: 24px;
    }

    .game-half {
      padding-inline: 9px;
    }

    .tense-trio button {
      padding-inline: 5px;
    }

    .tense-trio button > span {
      display: none;
    }

    .prototype-controls > span {
      font-size: 0.52rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .run-progress s,
    .quick-icon-button,
    .quick-icon-button .icon-core,
    .quick-icon-button .icon-particle,
    .quick-icon-button .spark-pixel,
    .quick-icon-button .charge-pip,
    .quick-icon-button.guarding::before,
    .quick-explanation {
      animation: none;
    }

    .run-progress s {
      transition: none;
    }
  }
</style>
