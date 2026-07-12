<script lang="ts">
  import { tick } from 'svelte';
  import HelpTip from '../HelpTip.svelte';

  export let variant: 'signal' | 'runway' | 'ledger';
  export let index = 'G1';
  export let kicker = '';
  export let title = '';
  export let description = '';

  type FillDifficulty = 'hard' | 'medium' | 'easy';

  const VERB = 'aller';
  const VERB_GLOSS = 'to go';
  const TENSES = ['Présent', 'Imparfait', 'Futur'];
  const PRONOUNS = ['je', 'tu', 'il / elle / on', 'nous', 'vous', 'ils / elles'];
  const FORMS = [
    ['vais', 'vas', 'va', 'allons', 'allez', 'vont'],
    ['allais', 'allais', 'allait', 'allions', 'alliez', 'allaient'],
    ['irai', 'iras', 'ira', 'irons', 'irez', 'iront'],
  ];
  const TOTAL_CELLS = TENSES.length * PRONOUNS.length;
  const DIFFICULTIES: Array<{ value: FillDifficulty; label: string; note: string }> = [
    { value: 'hard', label: 'Hard', note: '0 guides' },
    { value: 'medium', label: 'Medium', note: '1 / tense' },
    { value: 'easy', label: 'Easy', note: '≈ 70%' },
  ];
  const INITIAL_GUIDE_ORDERS: Record<typeof variant, number[][]> = {
    signal: [[3, 1, 5, 2, 4, 0], [2, 5, 1, 4, 3, 0], [4, 1, 5, 2, 3, 0]],
    runway: [[4, 2, 5, 1, 3, 0], [1, 4, 2, 5, 3, 0], [3, 5, 1, 4, 2, 0]],
    ledger: [[2, 5, 3, 1, 4, 0], [4, 1, 5, 2, 3, 0], [1, 3, 5, 2, 4, 0]],
  };

  let gameFrame: HTMLElement | null = null;
  let difficulty: FillDifficulty = 'medium';
  let guideOrders = INITIAL_GUIDE_ORDERS[variant].map((order) => [...order]);
  let cursor = 0;
  let answers = buildDemoAnswers(buildPrefilledCells(difficulty, guideOrders));
  let submitted = false;
  let finishedEarly = false;
  let finishArmed = false;
  let isFullscreen = false;
  let specialInfoOpen = false;
  let reviewTenseIndex: number | null = null;
  let reviewedTenses = new Set<number>();
  let finishTimer: ReturnType<typeof setTimeout> | null = null;

  $: prefilledCells = buildPrefilledCells(difficulty, guideOrders);
  $: editableOrder = Array.from({ length: TOTAL_CELLS }, (_, cell) => cell).filter((cell) => !prefilledCells.has(cell));
  $: cursorPosition = Math.max(0, editableOrder.indexOf(cursor));
  $: guideCounts = TENSES.map((_, tenseIndex) => Array.from(prefilledCells).filter((cell) => Math.floor(cell / PRONOUNS.length) === tenseIndex).length);
  $: completedTenses = TENSES.map((_, tenseIndex) => reviewedTenses.has(tenseIndex));
  $: activeTenseIndex = reviewTenseIndex ?? Math.floor(cursor / PRONOUNS.length);
  $: activePronounIndex = cursor % PRONOUNS.length;
  $: activeTense = TENSES[activeTenseIndex];
  $: activePronoun = PRONOUNS[activePronounIndex];
  $: promptPronoun = activePronoun.charAt(0).toUpperCase() + activePronoun.slice(1);
  $: progress = editableOrder.length ? ((cursorPosition + 1) / editableOrder.length) * 100 : 100;
  $: nextCell = cursorPosition < editableOrder.length - 1 ? editableOrder[cursorPosition + 1] : null;
  $: nextTenseIndex = nextCell === null ? null : Math.floor(nextCell / PRONOUNS.length);
  $: nextPronounIndex = nextCell === null ? null : nextCell % PRONOUNS.length;
  $: reviewCells = reviewTenseIndex === null ? [] : editableCellsForTense(reviewTenseIndex);
  $: wrongReviewCells = reviewCells.filter((cell) => answers[cell].trim().toLocaleLowerCase() !== expectedForm(cell).toLocaleLowerCase());
  $: reviewCorrectCount = reviewCells.length - wrongReviewCells.length;
  $: revealedReviewCells = new Set(reviewTenseIndex === null ? [] : reviewCells);

  function cellIndex(tenseIndex: number, pronounIndex: number): number {
    return tenseIndex * PRONOUNS.length + pronounIndex;
  }

  function inputId(indexValue: number): string {
    return `pg-${variant}-final-${indexValue}`;
  }

  function guideCountForDifficulty(targetDifficulty: FillDifficulty): number {
    if (targetDifficulty === 'hard') {
      return 0;
    }
    if (targetDifficulty === 'medium') {
      return 1;
    }
    return Math.min(PRONOUNS.length - 1, Math.floor(PRONOUNS.length * 0.7));
  }

  function buildPrefilledCells(targetDifficulty: FillDifficulty, orders: number[][]): Set<number> {
    const prefilled = new Set<number>();
    const guideCount = guideCountForDifficulty(targetDifficulty);
    for (let tenseIndex = 0; tenseIndex < TENSES.length; tenseIndex++) {
      for (const pronounIndex of orders[tenseIndex].slice(0, guideCount)) {
        prefilled.add(cellIndex(tenseIndex, pronounIndex));
      }
    }
    return prefilled;
  }

  function editableCellsForTense(tenseIndex: number): number[] {
    return editableOrder.filter((cell) => Math.floor(cell / PRONOUNS.length) === tenseIndex);
  }

  function demoWrongForm(indexValue: number): string {
    const tenseIndex = Math.floor(indexValue / PRONOUNS.length);
    const expected = expectedForm(indexValue);
    return FORMS[tenseIndex].find((form) => form !== expected) ?? `${expected}?`;
  }

  function buildDemoAnswers(prefilled: Set<number>): string[] {
    const demoAnswers = Array<string>(TOTAL_CELLS).fill('');
    for (let tenseIndex = 0; tenseIndex < TENSES.length; tenseIndex++) {
      const cells = Array.from({ length: PRONOUNS.length }, (_, pronounIndex) => cellIndex(tenseIndex, pronounIndex)).filter((cell) => !prefilled.has(cell));
      const randomizedCells = [...cells].sort(() => Math.random() - 0.5);
      const correctTarget = cells.length > 1 ? Math.max(1, Math.min(cells.length - 1, Math.round(cells.length * 0.55))) : Math.random() > 0.5 ? 1 : 0;
      const correctCells = new Set(randomizedCells.slice(0, correctTarget));
      for (const cell of cells) {
        demoAnswers[cell] = correctCells.has(cell) ? expectedForm(cell) : demoWrongForm(cell);
      }
    }
    return demoAnswers;
  }

  function shuffledPronouns(): number[] {
    const values = Array.from({ length: PRONOUNS.length }, (_, indexValue) => indexValue);
    for (let indexValue = values.length - 1; indexValue > 0; indexValue--) {
      const swapIndex = Math.floor(Math.random() * (indexValue + 1));
      [values[indexValue], values[swapIndex]] = [values[swapIndex], values[indexValue]];
    }
    return values;
  }

  async function resetInteraction(): Promise<void> {
    submitted = false;
    finishedEarly = false;
    finishArmed = false;
    reviewTenseIndex = null;
    reviewedTenses = new Set<number>();
    if (finishTimer) {
      clearTimeout(finishTimer);
      finishTimer = null;
    }
    await tick();
    answers = buildDemoAnswers(prefilledCells);
    cursor = editableOrder[0] ?? 0;
    await tick();
    (document.getElementById(inputId(cursor)) as HTMLInputElement | null)?.focus();
  }

  function chooseDifficulty(next: FillDifficulty): void {
    difficulty = next;
    void resetInteraction();
  }

  function reshuffleGuides(): void {
    guideOrders = TENSES.map(() => shuffledPronouns());
    void resetInteraction();
  }

  function randomizeDemoAnswers(): void {
    void resetInteraction();
  }

  function setAnswer(indexValue: number, value: string): void {
    answers[indexValue] = value;
    answers = [...answers];
  }

  async function focusCursor(indexValue: number): Promise<void> {
    if (!editableOrder.includes(indexValue)) {
      return;
    }
    cursor = indexValue;
    await tick();
    (document.getElementById(inputId(cursor)) as HTMLInputElement | null)?.focus();
  }

  async function advance(indexValue: number): Promise<void> {
    if (submitted || finishedEarly) {
      return;
    }
    const tenseIndex = Math.floor(indexValue / PRONOUNS.length);
    const tenseCells = editableCellsForTense(tenseIndex);
    const tensePosition = tenseCells.indexOf(indexValue);
    if (tensePosition < 0) {
      return;
    }
    cursor = indexValue;
    if (tensePosition === tenseCells.length - 1) {
      reviewTenseIndex = tenseIndex;
      await tick();
      gameFrame?.focus({ preventScroll: true });
      return;
    }
    await focusCursor(tenseCells[tensePosition + 1]);
  }

  async function handleEnter(event: KeyboardEvent, indexValue: number): Promise<void> {
    if (event.key !== 'Enter') {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    await advance(indexValue);
  }

  function expectedForm(indexValue: number): string {
    return FORMS[Math.floor(indexValue / PRONOUNS.length)][indexValue % PRONOUNS.length];
  }

  function isCorrect(indexValue: number): boolean {
    return answers[indexValue].trim().toLocaleLowerCase() === expectedForm(indexValue).toLocaleLowerCase();
  }

  function isLastEditableInTense(indexValue: number): boolean {
    const tenseCells = editableCellsForTense(Math.floor(indexValue / PRONOUNS.length));
    return tenseCells[tenseCells.length - 1] === indexValue;
  }

  function scoreForTense(tenseIndex: number): number {
    return editableCellsForTense(tenseIndex).filter((cell) => isCorrect(cell)).length;
  }

  async function completeTenseReview(): Promise<void> {
    if (reviewTenseIndex === null) {
      return;
    }
    const completedIndex = reviewTenseIndex;
    reviewedTenses = new Set([...reviewedTenses, completedIndex]);
    const nextTenseCell = editableOrder.find((cell) => Math.floor(cell / PRONOUNS.length) > completedIndex);
    reviewTenseIndex = null;
    if (nextTenseCell === undefined) {
      submitted = true;
      await tick();
      gameFrame?.focus({ preventScroll: true });
      return;
    }
    await focusCursor(nextTenseCell);
  }

  async function advanceReview(): Promise<void> {
    if (reviewTenseIndex === null) {
      return;
    }
    await completeTenseReview();
  }

  async function toggleFullscreen(): Promise<void> {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await gameFrame?.requestFullscreen();
      }
    } catch {
      // Fullscreen can be denied by the browser; the drill remains usable.
    }
  }

  function armFinish(): void {
    if (finishArmed) {
      finishArmed = false;
      finishedEarly = true;
      if (finishTimer) {
        clearTimeout(finishTimer);
        finishTimer = null;
      }
      return;
    }
    finishArmed = true;
    if (finishTimer) {
      clearTimeout(finishTimer);
    }
    finishTimer = setTimeout(() => {
      finishArmed = false;
      finishTimer = null;
    }, 750);
  }

  async function resumeInteraction(): Promise<void> {
    finishedEarly = false;
    await tick();
    if (reviewTenseIndex !== null) {
      gameFrame?.focus({ preventScroll: true });
      return;
    }
    await focusCursor(cursor);
  }

  function handleGameShortcut(event: KeyboardEvent): void {
    if (submitted || finishedEarly) {
      return;
    }
    if (reviewTenseIndex !== null && event.key === 'Enter') {
      event.preventDefault();
      void advanceReview();
      return;
    }
    const escapeFinish = !isFullscreen && event.key === 'Escape' && !event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey;
    const fullscreenFinish = isFullscreen && event.code === 'Space' && event.ctrlKey && !event.altKey && !event.metaKey;
    if (escapeFinish || fullscreenFinish) {
      event.preventDefault();
      armFinish();
    }
  }

  function gameShortcutRegion(node: HTMLElement): { destroy: () => void } {
    const keyListener = (event: KeyboardEvent) => handleGameShortcut(event);
    const fullscreenListener = () => (isFullscreen = document.fullscreenElement === node);
    node.addEventListener('keydown', keyListener);
    document.addEventListener('fullscreenchange', fullscreenListener);
    return {
      destroy: () => {
        node.removeEventListener('keydown', keyListener);
        document.removeEventListener('fullscreenchange', fullscreenListener);
      },
    };
  }
</script>

<article
  class={`game-preview game-${variant}`}
  data-game={variant}
  data-feedback="spotlight"
  data-cursor={cursor}
  data-tense={activeTense}
  data-pronoun={activePronoun}
  data-difficulty={difficulty}
  data-guide-count={prefilledCells.size}
  data-editable-count={editableOrder.length}
  data-submitted={submitted}
  data-finished-early={finishedEarly}
  data-review-tense={reviewTenseIndex ?? -1}
>
  <header class="concept-intro">
    <span class="concept-number">{index}</span>
    <div>
      <p class="eyebrow">{kicker}</p>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  </header>

  <div class="game-frame" bind:this={gameFrame} use:gameShortcutRegion tabindex="-1">
    <div class="game-progress" aria-hidden="true"><span style={`width: ${progress}%`}></span></div>

    <div class="game-utility-row">
      <span class="shortcut-status"><i aria-hidden="true"></i> TABLE SHORTCUTS ON</span>
      <div class="game-tools">
        <button class="game-tool-button" type="button" aria-label="Preview fullscreen" title="Preview fullscreen" on:click={() => void toggleFullscreen()}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"></path></svg>
        </button>
        <HelpTip label="Table game shortcuts">
          <h4>Fill-table shortcuts</h4>
          <p>Locked guide cells are skipped automatically; the pointer only visits answers you must supply.</p>
          <ul>
            <li><kbd>Enter</kbd> moves down to the next empty cell.</li>
            <li>The last answer opens feedback inside the same tense column.</li>
            <li>The completed tense shows every right answer and correction at once.</li>
            <li>During feedback, <kbd>Enter</kbd> opens the next tense or submits the table.</li>
            <li><kbd>Esc ×2</kbd> finishes early; fullscreen uses <kbd>Ctrl+Space ×2</kbd>.</li>
          </ul>
        </HelpTip>
      </div>
    </div>

    <div class="difficulty-demo">
      <div><span>PLAYGROUND CONTROL</span><strong>Difficulty · random demo answers loaded</strong></div>
      <div class="difficulty-demo-buttons" role="group" aria-label={`${title} difficulty preview`}>
        {#each DIFFICULTIES as item}
          <button class:difficulty-demo-on={difficulty === item.value} type="button" aria-pressed={difficulty === item.value} on:click={() => chooseDifficulty(item.value)}><strong>{item.label}</strong><small>{item.note}</small></button>
        {/each}
      </div>
      <div class="demo-tool-buttons">
        <button class="shuffle-guides" type="button" disabled={difficulty === 'hard'} aria-label="Randomize guide cells" title="Randomize guide cells" on:click={reshuffleGuides}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h3c4 0 6 10 10 10h3M17 4l3 3-3 3M4 17h3c1.7 0 3-1.7 4.2-3.7M17 14l3 3-3 3"></path></svg>
        </button>
        <button class="randomize-answers" type="button" aria-label="Load new random right and wrong answers" title="Load new random right and wrong answers" on:click={randomizeDemoAnswers}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16v16H4z"></path><circle cx="9" cy="9" r="1"></circle><circle cx="15" cy="15" r="1"></circle><circle cx="15" cy="9" r="1"></circle><circle cx="9" cy="15" r="1"></circle></svg>
        </button>
      </div>
    </div>

    <div class="tense-status-strip" aria-label="Tense completion status">
      {#each TENSES as tense, tenseIndex}
        <div class:tense-status-active={activeTenseIndex === tenseIndex && reviewTenseIndex === null} class:tense-status-review={reviewTenseIndex === tenseIndex} class:tense-status-done={completedTenses[tenseIndex]} class="tense-status-card">
          <span class="tense-status-index">0{tenseIndex + 1}</span>
          <span><strong>{tense}</strong><small>{completedTenses[tenseIndex] ? `${scoreForTense(tenseIndex)}/${editableCellsForTense(tenseIndex).length} correct` : reviewTenseIndex === tenseIndex ? 'checking in place' : activeTenseIndex === tenseIndex ? 'filling now' : 'waiting'}</small></span>
          <i aria-hidden="true">{completedTenses[tenseIndex] ? '✓' : reviewTenseIndex === tenseIndex ? '!' : activeTenseIndex === tenseIndex ? '↓' : '·'}</i>
          {#if guideCounts[tenseIndex]}<em>{guideCounts[tenseIndex]} guide{guideCounts[tenseIndex] === 1 ? '' : 's'}</em>{/if}
        </div>
      {/each}
    </div>

    <div class={`compact-prompt prompt-${variant}`}>
      <div class="verb-lockup"><span>CURRENT VERB</span><strong>{VERB}</strong><small>{VERB_GLOSS}</small></div>
      {#if reviewTenseIndex !== null}
        <div class="prompt-equation prompt-equation-review"><span>{activeTense} · feedback in place</span><strong>{reviewCorrectCount} / {reviewCells.length} correct</strong><small>Every result is shown; Enter continues to the next tense.</small></div>
        <div class="prompt-coordinate prompt-coordinate-review"><span>MODE</span><strong>REVIEW</strong><small>same column</small></div>
      {:else}
        <div class="prompt-equation"><span>{activeTense} · active answer</span><strong><em>{promptPronoun}</em> + {VERB}</strong><small>Locked guides stay visible; only cyan cells receive the pointer.</small></div>
        <div class="prompt-coordinate"><span>CELL</span><strong>{cursorPosition + 1}/{editableOrder.length}</strong><small>{activePronounIndex + 1}/6 in tense</small></div>
      {/if}
    </div>

    <div class:active-column-review={reviewTenseIndex !== null} class={`active-column column-${variant}`}>
      <div class="column-head">
        <div><span>{reviewTenseIndex !== null ? 'TENSE FEEDBACK' : 'ACTIVE TENSE'} {activeTenseIndex + 1}/{TENSES.length}</span><strong>{activeTense}</strong></div>
        <div><strong>{reviewTenseIndex !== null ? `${reviewCorrectCount}/${reviewCells.length} correct` : `${PRONOUNS.length - guideCounts[activeTenseIndex]} answers`}</strong><small>{reviewTenseIndex !== null ? 'all feedback shown' : `${guideCounts[activeTenseIndex]} locked ${guideCounts[activeTenseIndex] === 1 ? 'guide' : 'guides'}`}</small></div>
      </div>
      <div class="column-rows">
        <span class="column-rail" aria-hidden="true"><i style={`height: ${((activePronounIndex + 1) / PRONOUNS.length) * 100}%`}></i></span>
        {#each PRONOUNS as pronoun, pronounIndex}
          {@const indexValue = cellIndex(activeTenseIndex, pronounIndex)}
          {@const feedbackRevealed = revealedReviewCells.has(indexValue)}
          {@const answerCorrect = feedbackRevealed && answers[indexValue].trim().toLocaleLowerCase() === expectedForm(indexValue).toLocaleLowerCase()}
          <div
            class:column-row-active={reviewTenseIndex === null && cursor === indexValue}
            class:column-row-guide={prefilledCells.has(indexValue)}
            class:column-row-done={reviewTenseIndex === null && editableOrder.includes(indexValue) && editableOrder.indexOf(indexValue) < cursorPosition}
            class:column-row-review={reviewTenseIndex !== null && !prefilledCells.has(indexValue)}
            class:column-row-correct={answerCorrect}
            class:column-row-wrong={feedbackRevealed && !answerCorrect}
            class:column-row-pending={reviewTenseIndex !== null && !prefilledCells.has(indexValue) && !feedbackRevealed}
            class="column-row"
            style={`--row-index: ${pronounIndex}`}
          >
            <span class="row-marker" aria-hidden="true">{prefilledCells.has(indexValue) ? '◆' : feedbackRevealed ? answerCorrect ? '✓' : '×' : reviewTenseIndex !== null ? '○' : cursor === indexValue ? '▶' : editableOrder.includes(indexValue) && editableOrder.indexOf(indexValue) < cursorPosition ? '✓' : '·'}</span>
            <label for={prefilledCells.has(indexValue) || reviewTenseIndex !== null ? undefined : inputId(indexValue)}><small>{String(pronounIndex + 1).padStart(2, '0')}</small><strong>{pronoun}</strong></label>
            {#if prefilledCells.has(indexValue)}
              <div class="locked-guide">
                <span aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="6" y="10" width="12" height="9" rx="2"></rect><path d="M9 10V7a3 3 0 0 1 6 0v3"></path></svg></span>
                <strong>{expectedForm(indexValue)}</strong><small>GIVEN GUIDE</small>
              </div>
            {:else if reviewTenseIndex !== null}
              {#if feedbackRevealed}
                <div class:feedback-correct={answerCorrect} class:feedback-wrong={!answerCorrect} class="inline-feedback">
                  <span class="feedback-icon" aria-hidden="true">{answerCorrect ? '✓' : '×'}</span>
                  {#if answerCorrect}
                    <strong>{answers[indexValue]}</strong><small>RIGHT</small>
                  {:else}
                    <span class="answer-correction"><del>{answers[indexValue] || 'no answer'}</del><strong>{expectedForm(indexValue)}</strong></span><small>CORRECT</small>
                  {/if}
                </div>
              {:else}
                <div class="feedback-pending"><i aria-hidden="true"></i><span>ENTER TO CHECK</span></div>
              {/if}
            {:else}
              <input
                id={inputId(indexValue)}
                aria-label={`${VERB}, ${pronoun}, ${activeTense}`}
                value={answers[indexValue]}
                tabindex={cursor === indexValue ? 0 : -1}
                disabled={submitted || finishedEarly}
                placeholder=""
                autocomplete="off"
                autocapitalize="off"
                spellcheck="false"
                on:focus={() => (cursor = indexValue)}
                on:input={(event) => setAnswer(indexValue, (event.currentTarget as HTMLInputElement).value)}
                on:keydown={(event) => void handleEnter(event, indexValue)}
              />
            {/if}
            {#if reviewTenseIndex === null && cursor === indexValue}<span class="row-command">{isLastEditableInTense(indexValue) ? 'ENTER = CHECK TENSE' : 'ENTER = NEXT EMPTY ↓'}</span>{/if}
          </div>
        {/each}
      </div>
    </div>

    <div class="pointer-contract">
      <div><span class:pointer-beacon-review={reviewTenseIndex !== null} class="pointer-beacon" aria-hidden="true"></span><strong>{activeTense}</strong><span>{reviewTenseIndex !== null ? 'feedback' : activePronoun}</span></div>
      <p>
        {#if reviewTenseIndex !== null}
          {#if nextCell === null}
            Tense reviewed · <kbd>Enter</kbd> submits the table
          {:else}
            Tense reviewed · <kbd>Enter</kbd> opens {TENSES[nextTenseIndex || 0]}
          {/if}
        {:else if isLastEditableInTense(cursor)}
          Tense filled · <kbd>Enter</kbd> checks every answer here, before moving on
        {:else}
          <kbd>Enter</kbd> skips locked guides and moves to {PRONOUNS[nextPronounIndex || 0]}
        {/if}
      </p>
    </div>

    <div class="giveaway-guard">
      <button type="button" aria-expanded={specialInfoOpen} on:click={() => (specialInfoOpen = !specialInfoOpen)}>
        <span aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 3 5.5 5.6v5.8c0 4.2 2.7 7.5 6.5 9.6 3.8-2.1 6.5-5.4 6.5-9.6V5.6L12 3Z"></path><path d="m9 12 2 2 4-4"></path></svg></span>
        <span><strong>GIVEAWAY GUARD ACTIVE</strong><small>No special columns in this French aller demo</small></span><i>{specialInfoOpen ? '−' : '+'}</i>
      </button>
      {#if specialInfoOpen}<p><strong>When it appears:</strong> a tense whose valid forms are all identical, or that has only one valid form, receives a <em>SPECIAL · NO GUIDES</em> badge in the top tracker. The column remains playable but no answer is revealed.</p>{/if}
    </div>

    <div class="session-shortcut-dock" aria-label="Table game shortcuts">
      <div class="dock-action dock-primary">
        <span class="dock-icon" aria-hidden="true">
          {#if reviewTenseIndex !== null}<svg viewBox="0 0 24 24"><path d="m5 12 4 4L19 6"></path></svg>{:else}<svg viewBox="0 0 24 24"><path d="M12 4v15m-6-6 6 6 6-6"></path></svg>{/if}
        </span>
        <span><kbd>Enter</kbd><small>{reviewTenseIndex !== null ? nextCell === null ? 'submit reviewed table' : 'next tense · first empty' : isLastEditableInTense(cursor) ? 'check tense in place' : 'next empty · down'}</small></span>
      </div>
      <div class:finish-armed={finishArmed} class="dock-action">
        <span class="dock-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 5H5v14h3M13 8l4 4-4 4m4-4H8"></path></svg></span>
        <span><kbd>{isFullscreen ? (finishArmed ? 'Ctrl+Space ×1' : 'Ctrl+Space ×2') : (finishArmed ? 'Esc ×1' : 'Esc ×2')}</kbd><small>{finishArmed ? 'again to finish' : 'finish run'}</small></span>
      </div>
    </div>

    {#if finishedEarly}
      <div class="finish-preview-banner" role="status">
        <span aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 5H5v14h3M13 8l4 4-4 4m4-4H8"></path></svg></span>
        <div><strong>RUN FINISHED EARLY</strong><small>The inherited double-press shortcut fired. Prototype progress was not saved.</small></div>
        <button type="button" on:click={() => void resumeInteraction()}>Resume</button>
      </div>
    {/if}

    {#if submitted}
      <div class="submitted-banner" role="status">
        <span>✓</span><div><strong>TABLE REVIEWED & SUBMITTED</strong><small>Every tense was checked in place. The final review Enter submitted the table.</small></div><button type="button" on:click={() => void resetInteraction()}>Replay</button>
      </div>
    {/if}
  </div>
</article>

<style>
  .game-preview {
    width: min(100%, 760px);
    margin-inline: auto;
  }

  .concept-intro {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.85rem;
    align-items: flex-start;
    margin-bottom: 0.8rem;
    padding-inline: 0.25rem;
  }

  .concept-number {
    display: grid;
    width: 2.45rem;
    height: 2.45rem;
    place-items: center;
    border: 1px solid var(--line-strong);
    border-radius: 13px;
    color: var(--accent-strong);
    background: var(--accent-soft);
    font: 800 0.7rem/1 var(--mono);
  }

  .concept-intro h3 {
    margin: 0.15rem 0 0.25rem;
    color: var(--text);
    font: 780 clamp(1.05rem, 3vw, 1.35rem)/1.15 var(--display);
    letter-spacing: -0.03em;
  }

  .concept-intro p:last-child {
    max-width: 640px;
    margin: 0;
    color: var(--muted);
    font-size: 0.75rem;
  }

  .game-frame {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    padding: clamp(0.9rem, 3vw, 1.25rem);
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--accent) 34%, var(--line));
    border-radius: 24px;
    color: white;
    background:
      radial-gradient(circle at 88% 0%, color-mix(in srgb, var(--accent) 18%, transparent), transparent 30%),
      color-mix(in srgb, var(--surface-dark) 91%, black 9%);
    box-shadow: 0 24px 55px rgba(5, 8, 20, 0.22);
  }

  .game-frame:focus {
    outline: none;
  }

  .game-frame:fullscreen {
    width: min(820px, calc(100% - 2rem));
    max-height: calc(100vh - 2rem);
    margin: auto;
    overflow: auto;
  }

  .game-progress {
    position: absolute;
    top: 0;
    right: 0;
    left: 0;
    height: 3px;
    background: rgba(255, 255, 255, 0.08);
  }

  .game-progress span {
    display: block;
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--accent-2), #f6c84c);
    transition: width 220ms ease;
  }

  .game-utility-row,
  .game-tools,
  .shortcut-status,
  .difficulty-demo,
  .difficulty-demo-buttons,
  .column-head,
  .pointer-contract,
  .session-shortcut-dock,
  .dock-action,
  .finish-preview-banner,
  .submitted-banner {
    display: flex;
    align-items: center;
  }

  .game-utility-row,
  .column-head,
  .pointer-contract {
    justify-content: space-between;
  }

  .shortcut-status {
    gap: 0.4rem;
    color: rgba(255, 255, 255, 0.48);
    font: 700 0.48rem/1 var(--mono);
    letter-spacing: 0.1em;
  }

  .shortcut-status i {
    width: 0.42rem;
    height: 0.42rem;
    border-radius: 50%;
    background: #55ee9b;
    box-shadow: 0 0 9px #55ee9b;
  }

  .game-tools {
    gap: 0.4rem;
  }

  .game-tool-button {
    display: grid;
    width: 2rem;
    height: 2rem;
    padding: 0;
    place-items: center;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 50%;
    color: rgba(255, 255, 255, 0.66);
    background: rgba(255, 255, 255, 0.05);
  }

  .game-tool-button:hover {
    border-color: var(--accent-2);
    color: var(--accent-2);
  }

  .game-tool-button svg {
    width: 1rem;
    height: 1rem;
  }

  .game-tools :global(.help-button) {
    width: 2rem;
    height: 2rem;
    border-color: rgba(255, 255, 255, 0.18);
    color: rgba(255, 255, 255, 0.66);
    background: rgba(255, 255, 255, 0.05);
  }

  .game-tools :global(.help-pop) {
    color: var(--text);
  }

  .difficulty-demo {
    gap: 0.7rem;
    padding: 0.55rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.035);
  }

  .difficulty-demo > div:first-child {
    display: grid;
    gap: 0.08rem;
    margin-right: auto;
  }

  .difficulty-demo > div:first-child span {
    color: var(--accent-2);
    font: 700 0.43rem/1 var(--mono);
    letter-spacing: 0.1em;
  }

  .difficulty-demo > div:first-child strong {
    font-size: 0.6rem;
  }

  .difficulty-demo-buttons {
    gap: 0.25rem;
  }

  .demo-tool-buttons {
    display: flex;
    flex: 0 0 auto;
    gap: 0.3rem;
  }

  .difficulty-demo-buttons button {
    display: grid;
    gap: 0.08rem;
    min-width: 4.6rem;
    padding: 0.4rem 0.5rem;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    color: rgba(255, 255, 255, 0.58);
    background: transparent;
  }

  .difficulty-demo-buttons button.difficulty-demo-on {
    border-color: var(--accent-2);
    color: white;
    background: color-mix(in srgb, var(--accent) 24%, transparent);
  }

  .difficulty-demo-buttons strong {
    font-size: 0.55rem;
  }

  .difficulty-demo-buttons small {
    font-size: 0.43rem;
  }

  .shuffle-guides,
  .randomize-answers {
    display: grid;
    width: 2rem;
    height: 2rem;
    flex: 0 0 auto;
    padding: 0;
    place-items: center;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 8px;
    color: var(--accent-2);
    background: rgba(255, 255, 255, 0.04);
  }

  .shuffle-guides:disabled {
    opacity: 0.3;
  }

  .shuffle-guides svg,
  .randomize-answers svg {
    width: 1rem;
    height: 1rem;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.7;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .randomize-answers {
    color: #55ee9b;
  }

  .randomize-answers circle {
    fill: currentColor;
    stroke: none;
  }

  .tense-status-strip {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.4rem;
  }

  .tense-status-card {
    position: relative;
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 0.4rem;
    align-items: center;
    min-width: 0;
    padding: 0.55rem;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 11px;
    color: rgba(255, 255, 255, 0.5);
    background: rgba(255, 255, 255, 0.035);
  }

  .tense-status-card.tense-status-active {
    border-color: var(--accent-2);
    color: white;
    background: color-mix(in srgb, var(--accent) 24%, transparent);
    box-shadow: inset 0 -2px 0 var(--accent-2);
  }

  .tense-status-card.tense-status-review {
    border-color: #f6c84c;
    color: white;
    background: color-mix(in srgb, #f6c84c 13%, transparent);
    box-shadow: inset 0 -2px 0 #f6c84c, 0 0 18px color-mix(in srgb, #f6c84c 10%, transparent);
  }

  .tense-status-card.tense-status-review .tense-status-index,
  .tense-status-card.tense-status-review > i {
    color: #f6c84c;
  }

  .tense-status-card.tense-status-done {
    border-color: color-mix(in srgb, #55ee9b 45%, transparent);
    color: #55ee9b;
    background: color-mix(in srgb, #55ee9b 9%, transparent);
  }

  .tense-status-index {
    color: var(--accent-2);
    font: 700 0.45rem/1 var(--mono);
  }

  .tense-status-card > span:nth-child(2) {
    display: grid;
    min-width: 0;
    gap: 0.1rem;
  }

  .tense-status-card strong {
    overflow: hidden;
    font-size: 0.58rem;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tense-status-card small {
    font-size: 0.43rem;
  }

  .tense-status-card > i {
    font-style: normal;
    font-weight: 800;
  }

  .tense-status-card > em {
    position: absolute;
    right: 0.35rem;
    bottom: -0.32rem;
    padding: 0.12rem 0.28rem;
    border: 1px solid color-mix(in srgb, #f6c84c 48%, transparent);
    border-radius: 999px;
    color: #f6c84c;
    background: color-mix(in srgb, var(--surface-dark) 92%, black);
    font: 700 0.36rem/1 var(--mono);
    font-style: normal;
  }

  .compact-prompt {
    display: grid;
    grid-template-columns: minmax(6.5rem, 0.65fr) minmax(0, 1.8fr) auto;
    gap: 0.8rem;
    align-items: center;
    min-height: 6.4rem;
    padding: 0.8rem;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    background:
      linear-gradient(rgba(255, 255, 255, 0.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255, 255, 255, 0.025) 1px, transparent 1px),
      rgba(8, 13, 31, 0.52);
    background-size: 24px 24px;
  }

  .prompt-runway {
    border-left: 3px solid var(--accent-2);
  }

  .prompt-ledger {
    border-radius: 8px;
    background:
      repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.025), rgba(255, 255, 255, 0.025) 1px, transparent 1px, transparent 20px),
      rgba(8, 13, 31, 0.58);
  }

  .verb-lockup {
    display: grid;
    gap: 0.08rem;
  }

  .verb-lockup > span,
  .prompt-coordinate > span,
  .prompt-equation > span,
  .column-head span {
    color: var(--accent-2);
    font: 700 0.48rem/1 var(--mono);
    letter-spacing: 0.1em;
  }

  .verb-lockup > strong {
    font: 800 clamp(1.35rem, 4vw, 2rem)/1 var(--display);
  }

  .verb-lockup small,
  .prompt-coordinate small,
  .prompt-equation small,
  .column-head small {
    color: rgba(255, 255, 255, 0.5);
    font-size: 0.5rem;
  }

  .prompt-equation {
    display: grid;
    justify-items: center;
    gap: 0.25rem;
    text-align: center;
  }

  .prompt-equation > strong {
    font: 760 clamp(1.3rem, 4vw, 2rem)/1 var(--display);
    letter-spacing: -0.035em;
  }

  .prompt-equation > strong em {
    color: #f6c84c;
    font-style: normal;
  }

  .prompt-equation-review > strong {
    color: #f6c84c;
    font-family: var(--mono);
    font-size: clamp(1.05rem, 3vw, 1.55rem);
    letter-spacing: -0.04em;
  }

  .prompt-coordinate-review strong {
    color: #f6c84c;
  }

  .prompt-coordinate {
    display: grid;
    justify-items: end;
    gap: 0.13rem;
    text-align: right;
  }

  .prompt-coordinate strong {
    font: 750 0.72rem/1 var(--mono);
  }

  .active-column {
    width: min(100%, 650px);
    margin-inline: auto;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.025);
  }

  .active-column-review {
    border-color: color-mix(in srgb, #f6c84c 45%, rgba(255, 255, 255, 0.12));
    box-shadow: 0 0 0 3px color-mix(in srgb, #f6c84c 5%, transparent);
  }

  .column-head {
    gap: 1rem;
    padding: 0.7rem 0.8rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(255, 255, 255, 0.035);
  }

  .column-head > div {
    display: grid;
    gap: 0.12rem;
  }

  .column-head > div:last-child {
    justify-items: end;
    text-align: right;
  }

  .column-head strong {
    font-size: 0.68rem;
  }

  .column-rows {
    position: relative;
    display: grid;
    gap: 0.36rem;
    padding: 0.65rem 0.65rem 0.65rem 1.1rem;
  }

  .column-rail {
    position: absolute;
    top: 0.8rem;
    bottom: 0.8rem;
    left: 0.55rem;
    width: 2px;
    overflow: hidden;
    background: rgba(255, 255, 255, 0.1);
  }

  .column-rail i {
    display: block;
    width: 100%;
    background: linear-gradient(var(--accent-2), var(--accent));
    transition: height 180ms ease;
  }

  .column-row {
    position: relative;
    display: grid;
    grid-template-columns: auto 7.5rem minmax(0, 1fr);
    gap: 0.55rem;
    align-items: center;
    min-height: 3.15rem;
    padding: 0.45rem 0.55rem;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 11px;
    background: rgba(255, 255, 255, 0.025);
    transition: 160ms ease;
  }

  .column-row.column-row-active {
    border-color: var(--accent-2);
    background: color-mix(in srgb, var(--accent) 18%, rgba(255, 255, 255, 0.025));
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 9%, transparent);
  }

  .column-row.column-row-guide {
    border-color: color-mix(in srgb, #f6c84c 42%, transparent);
    background: color-mix(in srgb, #f6c84c 8%, rgba(255, 255, 255, 0.02));
  }

  .column-row.column-row-done:not(.column-row-active) {
    border-color: color-mix(in srgb, #55ee9b 25%, transparent);
  }

  .column-row.column-row-review {
    transition: border-color 180ms ease, background 180ms ease, opacity 180ms ease, transform 180ms ease;
  }

  .column-row.column-row-correct {
    border-color: color-mix(in srgb, #55ee9b 58%, transparent);
    background: color-mix(in srgb, #55ee9b 10%, rgba(255, 255, 255, 0.02));
  }

  .column-row.column-row-wrong {
    border-color: color-mix(in srgb, #ff7188 62%, transparent);
    background: color-mix(in srgb, #ff7188 10%, rgba(255, 255, 255, 0.02));
  }

  .column-row.column-row-pending {
    border-color: rgba(255, 255, 255, 0.07);
    opacity: 0.58;
  }

  .row-marker {
    width: 0.75rem;
    color: var(--accent-2);
    font: 750 0.55rem/1 var(--mono);
    text-align: center;
  }

  .column-row-guide .row-marker {
    color: #f6c84c;
  }

  .column-row-done .row-marker {
    color: #55ee9b;
  }

  .column-row-correct .row-marker {
    color: #55ee9b;
  }

  .column-row-wrong .row-marker {
    color: #ff7188;
  }

  .column-row label {
    display: grid;
    grid-template-columns: 1.5rem 1fr;
    gap: 0.35rem;
    align-items: center;
  }

  .column-row label small {
    color: var(--accent-2);
    font: 700 0.43rem/1 var(--mono);
  }

  .column-row label strong {
    color: white;
    font-size: clamp(1rem, 2.4vw, 1.16rem);
    font-weight: 800;
  }

  .column-row input {
    min-width: 0;
    width: 100%;
    padding: 0.62rem 0.7rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    outline: none;
    color: white;
    background: rgba(6, 8, 24, 0.72);
    font: 600 0.72rem/1 var(--display);
  }

  .column-row input:focus {
    border-color: var(--accent-2);
    box-shadow: inset 0 -2px 0 var(--accent-2);
  }

  .locked-guide {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 0.55rem;
    align-items: center;
    min-width: 0;
    padding: 0.58rem 0.65rem;
    border: 1px solid color-mix(in srgb, #f6c84c 38%, transparent);
    border-radius: 8px;
    color: #ffe39a;
    background: color-mix(in srgb, #f6c84c 9%, rgba(6, 8, 24, 0.75));
  }

  .locked-guide > span {
    display: grid;
    color: #f6c84c;
  }

  .locked-guide svg {
    width: 0.8rem;
    height: 0.8rem;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.7;
    stroke-linecap: round;
  }

  .locked-guide strong {
    overflow: hidden;
    font-size: 0.68rem;
    text-overflow: ellipsis;
  }

  .locked-guide small {
    color: #f6c84c;
    font: 700 0.4rem/1 var(--mono);
  }

  .inline-feedback,
  .feedback-pending {
    min-width: 0;
    min-height: 2.25rem;
    border-radius: 8px;
  }

  .inline-feedback {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 0.6rem;
    align-items: center;
    padding: 0.45rem 0.65rem;
    animation: verdict-arrive 240ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  .feedback-correct {
    color: #78f2ad;
    background: color-mix(in srgb, #55ee9b 8%, rgba(6, 8, 24, 0.65));
  }

  .feedback-wrong {
    color: #ff91a3;
    background: color-mix(in srgb, #ff7188 9%, rgba(6, 8, 24, 0.65));
  }

  .feedback-icon {
    display: grid;
    width: 1.35rem;
    height: 1.35rem;
    place-items: center;
    border: 1px solid currentColor;
    border-radius: 50%;
    font: 850 0.65rem/1 var(--mono);
  }

  .inline-feedback > strong,
  .answer-correction strong {
    overflow: hidden;
    color: white;
    font-size: clamp(0.9rem, 2.2vw, 1.05rem);
    text-overflow: ellipsis;
  }

  .inline-feedback > small {
    color: currentColor;
    font: 800 0.42rem/1 var(--mono);
    letter-spacing: 0.08em;
  }

  .answer-correction {
    display: flex;
    min-width: 0;
    gap: 0.6rem;
    align-items: baseline;
  }

  .answer-correction del {
    overflow: hidden;
    color: rgba(255, 255, 255, 0.48);
    font-size: 0.82rem;
    text-decoration-color: #ff7188;
    text-decoration-thickness: 2px;
    text-overflow: ellipsis;
  }

  .answer-correction strong::before {
    margin-right: 0.35rem;
    color: #ff91a3;
    content: '→';
  }

  .feedback-pending {
    display: flex;
    gap: 0.55rem;
    align-items: center;
    padding: 0.55rem 0.65rem;
    border: 1px dashed rgba(255, 255, 255, 0.12);
    color: rgba(255, 255, 255, 0.34);
    background: rgba(6, 8, 24, 0.4);
    font: 750 0.43rem/1 var(--mono);
    letter-spacing: 0.08em;
  }

  .feedback-pending i {
    width: 1.2rem;
    height: 0.35rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.12);
  }

  .game-preview[data-feedback='spotlight'] .inline-feedback {
    animation-delay: calc(var(--row-index) * 45ms);
  }

  @keyframes verdict-arrive {
    from {
      opacity: 0;
      transform: translateY(0.35rem) scale(0.985);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  .row-command {
    position: absolute;
    right: 0.45rem;
    bottom: -0.28rem;
    z-index: 2;
    padding: 0.12rem 0.3rem;
    border-radius: 999px;
    color: #191300;
    background: #f6c84c;
    font: 800 0.38rem/1 var(--mono);
  }

  .column-signal .column-row {
    border-radius: 5px;
  }

  .column-signal .column-row-active {
    transform: translateX(0.2rem);
  }

  .column-runway {
    border-radius: 20px;
  }

  .column-runway .column-rows {
    gap: 0.5rem;
  }

  .column-runway .column-row {
    border-radius: 14px;
  }

  .column-runway .column-row-active {
    min-height: 3.6rem;
  }

  .column-ledger {
    border-radius: 8px;
    background:
      repeating-linear-gradient(0deg, transparent, transparent 31px, rgba(255, 255, 255, 0.025) 32px),
      rgba(255, 255, 255, 0.02);
  }

  .column-ledger .column-head,
  .column-ledger .column-row {
    border-radius: 0;
  }

  .column-ledger .column-row {
    border-width: 0 0 1px;
    background: transparent;
  }

  .column-ledger .column-row-active {
    border: 1px solid var(--accent-2);
    border-left-width: 4px;
    border-radius: 6px;
  }

  .column-ledger .column-row-guide {
    border: 1px solid color-mix(in srgb, #f6c84c 38%, transparent);
    border-left-width: 4px;
    border-radius: 6px;
  }

  .pointer-contract {
    gap: 1rem;
    padding-top: 0.7rem;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.58);
    font-size: 0.58rem;
  }

  .pointer-contract > div {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .pointer-contract > div strong {
    color: white;
  }

  .pointer-contract > div > span:last-child {
    color: var(--accent-2);
  }

  .pointer-contract p {
    margin: 0;
    text-align: right;
  }

  .pointer-beacon {
    width: 0.45rem;
    height: 0.45rem;
    border-radius: 50%;
    background: var(--accent-2);
    box-shadow: 0 0 8px var(--accent-2);
  }

  .pointer-beacon-review {
    background: #f6c84c;
    box-shadow: 0 0 8px #f6c84c;
  }

  kbd {
    padding: 0.15rem 0.35rem;
    border: 1px solid rgba(255, 255, 255, 0.24);
    border-bottom-width: 2px;
    border-radius: 5px;
    color: white;
    background: rgba(255, 255, 255, 0.06);
    font: 700 0.52rem/1 var(--mono);
    white-space: nowrap;
  }

  .giveaway-guard {
    overflow: hidden;
    border: 1px solid color-mix(in srgb, #f6c84c 30%, transparent);
    border-radius: 11px;
    background: color-mix(in srgb, #f6c84c 5%, transparent);
  }

  .giveaway-guard > button {
    display: grid;
    width: 100%;
    grid-template-columns: auto 1fr auto;
    gap: 0.55rem;
    align-items: center;
    padding: 0.55rem 0.65rem;
    border: 0;
    color: white;
    text-align: left;
    background: transparent;
  }

  .giveaway-guard > button > span:first-child {
    display: grid;
    width: 1.65rem;
    height: 1.65rem;
    place-items: center;
    border-radius: 8px;
    color: #f6c84c;
    background: color-mix(in srgb, #f6c84c 13%, transparent);
  }

  .giveaway-guard svg {
    width: 0.95rem;
    height: 0.95rem;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.7;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .giveaway-guard > button > span:nth-child(2) {
    display: grid;
    gap: 0.1rem;
  }

  .giveaway-guard strong {
    color: #f6c84c;
    font: 700 0.48rem/1 var(--mono);
  }

  .giveaway-guard small,
  .giveaway-guard p {
    color: rgba(255, 255, 255, 0.54);
    font-size: 0.5rem;
  }

  .giveaway-guard > button > i {
    color: #f6c84c;
    font-style: normal;
  }

  .giveaway-guard p {
    margin: 0;
    padding: 0 0.7rem 0.65rem 2.85rem;
    line-height: 1.5;
  }

  .giveaway-guard p strong,
  .giveaway-guard p em {
    color: #ffe39a;
    font: inherit;
    font-style: normal;
    font-weight: 700;
  }

  .session-shortcut-dock {
    justify-content: flex-end;
    gap: 0.45rem;
  }

  .dock-action {
    gap: 0.5rem;
    min-width: 9.5rem;
    padding: 0.48rem 0.6rem;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    color: rgba(255, 255, 255, 0.62);
    background: rgba(255, 255, 255, 0.035);
  }

  .dock-primary {
    border-color: color-mix(in srgb, var(--accent-2) 38%, transparent);
    background: color-mix(in srgb, var(--accent) 10%, transparent);
  }

  .dock-action.finish-armed {
    border-color: #f6c84c;
    color: #f6c84c;
    background: color-mix(in srgb, #f6c84c 10%, transparent);
    box-shadow: 0 0 0 3px color-mix(in srgb, #f6c84c 8%, transparent);
  }

  .dock-icon {
    display: grid;
    width: 1.55rem;
    height: 1.55rem;
    flex: 0 0 auto;
    place-items: center;
    border-radius: 7px;
    color: var(--accent-2);
    background: color-mix(in srgb, var(--accent) 18%, transparent);
  }

  .dock-icon svg,
  .finish-preview-banner svg {
    width: 0.9rem;
    height: 0.9rem;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.8;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .dock-action > span:last-child {
    display: grid;
    gap: 0.2rem;
  }

  .dock-action small {
    font-size: 0.48rem;
  }

  .finish-preview-banner,
  .submitted-banner {
    gap: 0.65rem;
    padding: 0.7rem;
    border-radius: 12px;
  }

  .finish-preview-banner {
    border: 1px solid color-mix(in srgb, #f6c84c 55%, transparent);
    color: #f6c84c;
    background: color-mix(in srgb, #f6c84c 9%, transparent);
  }

  .submitted-banner {
    border: 1px solid color-mix(in srgb, #55ee9b 48%, transparent);
    color: #55ee9b;
    background: color-mix(in srgb, #55ee9b 10%, transparent);
  }

  .finish-preview-banner > span,
  .submitted-banner > span {
    display: grid;
    width: 1.8rem;
    height: 1.8rem;
    flex: 0 0 auto;
    place-items: center;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.08);
  }

  .finish-preview-banner > div,
  .submitted-banner > div {
    display: grid;
    flex: 1;
    gap: 0.12rem;
  }

  .finish-preview-banner strong,
  .submitted-banner strong {
    font: 750 0.56rem/1 var(--mono);
  }

  .finish-preview-banner small,
  .submitted-banner small {
    color: rgba(255, 255, 255, 0.58);
    font-size: 0.5rem;
  }

  .finish-preview-banner button,
  .submitted-banner button {
    padding: 0.45rem 0.6rem;
    border: 1px solid currentColor;
    border-radius: 8px;
    color: inherit;
    background: transparent;
    font: 700 0.5rem/1 var(--mono);
  }

  button:not(:disabled) {
    cursor: pointer;
  }

  button {
    transition: 160ms ease;
  }

  button:not(:disabled):hover {
    transform: translateY(-1px);
  }

  :global(html[data-theme='arcade']) .game-frame {
    border-radius: 8px;
  }

  :global(html[data-theme='arcade']) .verb-lockup > strong,
  :global(html[data-theme='arcade']) .prompt-equation > strong,
  :global(html[data-theme='arcade']) .concept-intro h3 {
    line-height: 1.5;
    letter-spacing: 0;
  }

  @media (max-width: 660px) {
    .difficulty-demo {
      align-items: stretch;
      flex-direction: column;
    }

    .difficulty-demo-buttons {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
    }

    .difficulty-demo-buttons button {
      min-width: 0;
    }

    .demo-tool-buttons {
      align-self: flex-end;
    }

    .compact-prompt {
      grid-template-columns: 1fr auto;
    }

    .prompt-equation {
      grid-column: 1 / -1;
      grid-row: 2;
      order: 3;
      padding-top: 0.55rem;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }

    .column-row {
      grid-template-columns: auto 6rem minmax(0, 1fr);
    }

    .pointer-contract {
      align-items: flex-start;
      flex-direction: column;
    }

    .pointer-contract p {
      text-align: left;
    }

    .session-shortcut-dock {
      align-items: stretch;
      flex-direction: column;
    }

    .dock-action {
      min-width: 0;
    }
  }

  @media (max-width: 440px) {
    .game-frame {
      border-radius: 18px;
    }

    .tense-status-strip {
      grid-template-columns: 1fr;
    }

    .tense-status-card > em {
      right: 2rem;
      bottom: 50%;
      transform: translateY(50%);
    }

    .compact-prompt {
      min-height: 0;
    }

    .column-row {
      grid-template-columns: auto 1fr;
    }

    .column-row input,
    .locked-guide {
      grid-column: 2;
    }

    .locked-guide {
      grid-template-columns: auto 1fr;
    }

    .inline-feedback,
    .feedback-pending {
      grid-column: 2;
    }

    .inline-feedback {
      grid-template-columns: auto minmax(0, 1fr);
    }

    .inline-feedback > small {
      display: none;
    }

    .answer-correction {
      align-items: flex-start;
      flex-direction: column;
      gap: 0.15rem;
    }

    .locked-guide small {
      display: none;
    }

    .row-command {
      right: 0.35rem;
    }

    .finish-preview-banner,
    .submitted-banner {
      align-items: flex-start;
      flex-wrap: wrap;
    }
  }
</style>
