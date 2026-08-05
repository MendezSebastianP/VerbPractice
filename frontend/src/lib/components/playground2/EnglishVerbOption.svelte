<script lang="ts">
  import { onDestroy, onMount, tick } from 'svelte';

  export let variant: 'matrix' | 'guided';
  export let selectedTenses: Array<'past' | 'participle'> = ['past', 'participle'];

  type TenseKey = 'past' | 'participle';
  type VerbRow = {
    base: string;
    meaning: string;
    past: string;
    participle: string;
  };
  type PracticeCell = {
    verb: VerbRow;
    verbIndex: number;
    tense: TenseKey;
    tenseIndex: number;
    index: number;
  };

  const verbs: VerbRow[] = [
    { base: 'go', meaning: 'aller', past: 'went', participle: 'gone' },
    { base: 'take', meaning: 'prendre', past: 'took', participle: 'taken' },
    { base: 'write', meaning: 'écrire', past: 'wrote', participle: 'written' },
    { base: 'break', meaning: 'casser', past: 'broke', participle: 'broken' },
    { base: 'choose', meaning: 'choisir', past: 'chose', participle: 'chosen' },
  ];

  const initialAnswers: Record<string, string> = {
    'go:past': 'went',
    'go:participle': 'gone',
    'take:past': 'taked',
    'take:participle': 'taken',
  };

  let answers = { ...initialAnswers };
  let submitted = false;
  let desktopReview = false;
  let mobileReview = false;
  let desktopCellIndex = 0;
  let mobileCellIndex = 0;
  let desktopCheckButton: HTMLButtonElement | null = null;
  let mobileKeyboardPrimer: HTMLInputElement | null = null;
  let mobileViewportHeight = 440;
  let mobileCenterFrame: number | null = null;

  $: cells = verbs.flatMap((verb, verbIndex) =>
    selectedTenses.map((tense, tenseIndex) => ({
      verb,
      verbIndex,
      tense,
      tenseIndex,
      index: verbIndex * selectedTenses.length + tenseIndex,
    })),
  );
  $: totalAnswers = cells.length;
  $: filledAnswers = cells.filter((cell) => answerFor(cell.verb, cell.tense).trim()).length;
  $: correctAnswers = cells.filter((cell) => isCorrect(cell.verb, cell.tense)).length;
  $: remainingAnswers = Math.max(0, totalAnswers - filledAnswers);
  $: desktopCellIndex = clampIndex(desktopCellIndex);
  $: mobileCellIndex = clampIndex(mobileCellIndex);
  $: desktopCell = cells[desktopCellIndex] ?? cells[0];
  $: mobileCell = cells[mobileCellIndex] ?? cells[0];
  $: missedAnswers = cells.filter((cell) => !isCorrect(cell.verb, cell.tense));

  function clampIndex(index: number): number {
    return Math.max(0, Math.min(index, Math.max(0, cells.length - 1)));
  }

  function answerKey(verb: VerbRow, tense: TenseKey): string {
    return `${verb.base}:${tense}`;
  }

  function answerFor(verb: VerbRow, tense: TenseKey): string {
    return answers[answerKey(verb, tense)] ?? '';
  }

  function expectedFor(verb: VerbRow, tense: TenseKey): string {
    return verb[tense];
  }

  function tenseLabel(tense: TenseKey): string {
    return tense === 'past' ? 'Past' : 'Past participle';
  }

  function isCorrect(verb: VerbRow, tense: TenseKey): boolean {
    return answerFor(verb, tense).trim().toLowerCase() === expectedFor(verb, tense).toLowerCase();
  }

  function cellIndexFor(verbIndex: number, tense: TenseKey): number {
    return verbIndex * selectedTenses.length + selectedTenses.indexOf(tense);
  }

  function verbComplete(verb: VerbRow): boolean {
    return selectedTenses.every((tense) => answerFor(verb, tense).trim());
  }

  function firstEmptyCellIndex(): number {
    return cells.findIndex((cell) => !answerFor(cell.verb, cell.tense).trim());
  }

  function updateAnswer(event: Event, cell: PracticeCell): void {
    answers = {
      ...answers,
      [answerKey(cell.verb, cell.tense)]: (event.currentTarget as HTMLInputElement).value,
    };
    submitted = false;
    desktopReview = false;
    mobileReview = false;
  }

  function desktopSelector(index: number): string {
    return variant === 'matrix'
      ? `[data-matrix-index="${index}"]`
      : `[data-guided-index="${index}"]`;
  }

  function mobileSelector(index: number): string {
    return `[data-mobile-index="${index}"]`;
  }

  async function focusSelector(selector: string, mobile = false): Promise<void> {
    await tick();
    const input = document.querySelector<HTMLInputElement>(selector);
    input?.focus({ preventScroll: mobile });
    if (mobile) {
      scheduleMobileViewportCenter();
      await tick();
      const current = document.querySelector<HTMLInputElement>(selector);
      if (current && document.activeElement !== current) {
        current.focus({ preventScroll: true });
      }
      scheduleMobileViewportCenter();
    }
  }

  async function moveDesktopTo(index: number): Promise<void> {
    desktopCellIndex = clampIndex(index);
    await focusSelector(desktopSelector(desktopCellIndex));
  }

  async function moveMobileTo(index: number): Promise<void> {
    mobileCellIndex = clampIndex(index);
    await focusSelector(mobileSelector(mobileCellIndex), true);
  }

  async function handleDesktopEnter(event: KeyboardEvent, index: number): Promise<void> {
    if (event.key !== 'Enter' || event.isComposing) return;
    event.preventDefault();
    if (!(event.currentTarget as HTMLInputElement).value.trim()) return;
    if (index < cells.length - 1) {
      await moveDesktopTo(index + 1);
      return;
    }
    const firstEmpty = firstEmptyCellIndex();
    if (firstEmpty >= 0) {
      await moveDesktopTo(firstEmpty);
      return;
    }
    desktopReview = true;
    await tick();
    desktopCheckButton?.focus();
  }

  async function holdMobileKeyboard(): Promise<void> {
    await tick();
    mobileKeyboardPrimer?.focus({ preventScroll: true });
    scheduleMobileViewportCenter();
  }

  async function handleMobileEnter(event: KeyboardEvent, index: number): Promise<void> {
    if (event.key !== 'Enter' || event.isComposing) return;
    event.preventDefault();
    if (!(event.currentTarget as HTMLInputElement).value.trim()) return;
    if (index < cells.length - 1) {
      await moveMobileTo(index + 1);
      return;
    }
    const firstEmpty = firstEmptyCellIndex();
    if (firstEmpty >= 0) {
      await moveMobileTo(firstEmpty);
      return;
    }
    mobileReview = true;
    await holdMobileKeyboard();
  }

  async function handlePrimerEnter(event: KeyboardEvent): Promise<void> {
    if (event.key !== 'Enter' || event.isComposing) return;
    event.preventDefault();
    if (mobileReview) {
      await checkAll(true);
    } else if (submitted) {
      await editAnswers(true);
    }
  }

  function selectDesktopCell(index: number): void {
    desktopCellIndex = clampIndex(index);
    submitted = false;
    desktopReview = false;
  }

  async function selectMobileCell(index: number): Promise<void> {
    submitted = false;
    mobileReview = false;
    await moveMobileTo(index);
  }

  async function checkAll(keepKeyboard = false): Promise<void> {
    submitted = true;
    desktopReview = false;
    mobileReview = false;
    if (keepKeyboard) {
      await holdMobileKeyboard();
    }
  }

  async function editAnswers(keepKeyboard = false): Promise<void> {
    submitted = false;
    if (keepKeyboard) {
      await moveMobileTo(mobileCellIndex);
    }
  }

  function resetDemo(): void {
    answers = { ...initialAnswers };
    submitted = false;
    desktopReview = false;
    mobileReview = false;
    desktopCellIndex = 0;
    mobileCellIndex = 0;
  }

  function reviewMobileBatch(): void {
    mobileReview = true;
    void holdMobileKeyboard();
  }

  function updateMobileViewportHeight(): void {
    mobileViewportHeight = Math.round(window.visualViewport?.height ?? window.innerHeight);
    scheduleMobileViewportCenter();
  }

  function centerFocusedCellInViewport(): void {
    const active = document.activeElement as HTMLInputElement | null;
    if (!active?.matches('[data-mobile-index]')) return;
    const target = active.closest('.mobile-answer-row') ?? active;
    const rect = target.getBoundingClientRect();
    const viewport = window.visualViewport;
    const visibleTop = viewport?.offsetTop ?? 0;
    const visibleBottom = visibleTop + (viewport?.height ?? window.innerHeight);
    const topPadding = 38;
    const bottomPadding = 20;
    let delta = 0;
    if (rect.bottom > visibleBottom - bottomPadding) {
      delta = rect.bottom - (visibleBottom - bottomPadding);
    } else if (rect.top < visibleTop + topPadding) {
      delta = rect.top - (visibleTop + topPadding);
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

  onMount(() => {
    updateMobileViewportHeight();
    window.visualViewport?.addEventListener('resize', updateMobileViewportHeight);
  });

  onDestroy(() => {
    if (mobileCenterFrame !== null) {
      cancelAnimationFrame(mobileCenterFrame);
    }
    window.visualViewport?.removeEventListener('resize', updateMobileViewportHeight);
  });
</script>

<article class="option-demo" data-variant={variant}>
  <div class="preview-grid">
    <section class="preview-column desktop-column" aria-label={`${variant === 'matrix' ? 'Batch matrix' : 'Guided route'} desktop preview`}>
      <div class="preview-label">
        <span>DESKTOP</span>
        <strong>{variant === 'matrix' ? 'All verbs · selected forms in columns' : 'One verb · selected forms in rows'}</strong>
      </div>

      <div class="practice-card desktop-practice">
        <div class="outside-progress">
          <span>Verb progress</span>
          <strong>{Math.min(desktopCell?.verbIndex + 1 || 1, verbs.length)}/{verbs.length}</strong>
          <i><b style={`width: ${((desktopCellIndex + 1) / Math.max(1, cells.length)) * 100}%`}></b></i>
        </div>

        <div class="game-frame">
          <div class="tense-strip" aria-label={`Active form: ${desktopCell ? tenseLabel(desktopCell.tense) : ''}`}>
            {#each selectedTenses as tense}
              <span
                class:strip-active={desktopCell?.tense === tense}
                class:strip-done={Boolean(desktopCell && selectedTenses.indexOf(tense) < desktopCell.tenseIndex)}
              >
                {tenseLabel(tense)}
              </span>
            {/each}
          </div>

          {#if desktopCell}
            <div class="verb-hero">
              <span>Current verb</span>
              <strong>{desktopCell.verb.base}</strong>
              <em><b>{tenseLabel(desktopCell.tense)}</b> · {desktopCell.verb.meaning}</em>
            </div>
          {/if}

          {#if variant === 'matrix'}
            <div class="game-panel matrix-panel" class:panel-review={submitted}>
              <div class="panel-head">
                <div><span>{submitted ? 'BATCH FEEDBACK' : 'ENGLISH PRINCIPAL PARTS'}</span></div>
                <div>
                  <strong>{submitted ? `${correctAnswers}/${totalAnswers} correct` : `${filledAnswers}/${totalAnswers} filled`}</strong>
                  <small>{submitted ? 'all feedback shown together' : 'verbs down · forms across'}</small>
                </div>
              </div>
              <div class="matrix-scroll">
                <table class="verb-matrix" class:single-tense={selectedTenses.length === 1}>
                  <caption class="visually-hidden">English verbs with one answer column for each selected form</caption>
                  <colgroup>
                    <col class="verb-column" />
                    {#each selectedTenses as tense}<col class={`form-column form-column-${tense}`} />{/each}
                  </colgroup>
                  <thead>
                    <tr>
                      <th scope="col">Verb</th>
                      {#each selectedTenses as tense}<th scope="col">{tenseLabel(tense)}</th>{/each}
                    </tr>
                  </thead>
                  <tbody>
                    {#each verbs as verb, verbIndex}
                      <tr class:verb-row-active={desktopCell?.verbIndex === verbIndex && !submitted}>
                        <th scope="row" class="verb-cell">
                          <div class="verb-cell-content">
                            <small>{String(verbIndex + 1).padStart(2, '0')}</small>
                            <span><strong>{verb.base}</strong><em>{verb.meaning}</em></span>
                          </div>
                        </th>
                        {#each selectedTenses as tense}
                          {@const index = cellIndexFor(verbIndex, tense)}
                          {@const cell = cells[index]}
                          <td class:matrix-cell-active={desktopCellIndex === index && !submitted}>
                            <label
                              class="matrix-answer"
                              class:answer-correct={submitted && isCorrect(verb, tense)}
                              class:answer-wrong={submitted && !isCorrect(verb, tense)}
                            >
                              <span class="row-marker" aria-hidden="true">
                                {submitted ? isCorrect(verb, tense) ? '✓' : '×' : desktopCellIndex === index ? '▶' : answerFor(verb, tense).trim() ? '✓' : '·'}
                              </span>
                              <input
                                type="text"
                                value={answerFor(verb, tense)}
                                data-matrix-index={index}
                                inputmode="text"
                                enterkeyhint={index === cells.length - 1 ? 'done' : 'next'}
                                aria-label={`${verb.base}, ${tenseLabel(tense)}`}
                                aria-invalid={submitted && !isCorrect(verb, tense)}
                                autocomplete="off"
                                spellcheck="false"
                                on:focus={() => selectDesktopCell(index)}
                                on:input={(event) => updateAnswer(event, cell)}
                                on:keydown={(event) => void handleDesktopEnter(event, index)}
                              />
                              {#if submitted}
                                <small>{isCorrect(verb, tense) ? 'RIGHT' : `CORRECT · ${expectedFor(verb, tense)}`}</small>
                              {/if}
                            </label>
                          </td>
                        {/each}
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            </div>
          {:else if desktopCell}
            <div class="verb-route" aria-label="Verb route">
              {#each verbs as verb, verbIndex}
                <button
                  type="button"
                  class:route-active={desktopCell.verbIndex === verbIndex}
                  class:route-done={verbIndex < desktopCell.verbIndex || verbComplete(verb)}
                  on:click={() => void moveDesktopTo(verbIndex * selectedTenses.length)}
                >
                  <small>{verbIndex + 1}</small><strong>{verb.base}</strong>
                </button>
              {/each}
            </div>
            <div class="game-panel guided-panel" class:panel-review={submitted}>
              <div class="panel-head">
                <div><span>{submitted ? 'BATCH FEEDBACK' : `ACTIVE VERB ${desktopCell.verbIndex + 1}/${verbs.length}`}</span></div>
                <div>
                  <strong>{submitted ? `${correctAnswers}/${totalAnswers} correct` : `${selectedTenses.length} ${selectedTenses.length === 1 ? 'form' : 'forms'}`}</strong>
                  <small>{submitted ? 'all feedback shown together' : 'Enter moves through the route'}</small>
                </div>
              </div>
              <div class="guided-rows">
                <span class="answer-rail" aria-hidden="true"><i style={`height: ${submitted ? 100 : ((desktopCell.tenseIndex + 1) / selectedTenses.length) * 100}%`}></i></span>
                {#each selectedTenses as tense}
                  {@const index = cellIndexFor(desktopCell.verbIndex, tense)}
                  {@const cell = cells[index]}
                  <label
                    class="guided-answer"
                    class:guided-answer-active={desktopCellIndex === index && !submitted}
                    class:answer-correct={submitted && isCorrect(desktopCell.verb, tense)}
                    class:answer-wrong={submitted && !isCorrect(desktopCell.verb, tense)}
                  >
                    <span class="row-marker" aria-hidden="true">
                      {submitted ? isCorrect(desktopCell.verb, tense) ? '✓' : '×' : desktopCellIndex === index ? '▶' : answerFor(desktopCell.verb, tense).trim() ? '✓' : '·'}
                    </span>
                    <span class="answer-label"><small>FORM {selectedTenses.indexOf(tense) + 1}</small><strong>{tenseLabel(tense)}</strong></span>
                    <span class="input-shell">
                      <input
                        type="text"
                        value={answerFor(desktopCell.verb, tense)}
                        data-guided-index={index}
                        inputmode="text"
                        enterkeyhint={index === cells.length - 1 ? 'done' : 'next'}
                        aria-label={`${desktopCell.verb.base}, ${tenseLabel(tense)}`}
                        aria-invalid={submitted && !isCorrect(desktopCell.verb, tense)}
                        autocomplete="off"
                        spellcheck="false"
                        on:focus={() => selectDesktopCell(index)}
                        on:input={(event) => updateAnswer(event, cell)}
                        on:keydown={(event) => void handleDesktopEnter(event, index)}
                      />
                      {#if submitted}
                        <small>{isCorrect(desktopCell.verb, tense) ? 'RIGHT' : `CORRECT · ${expectedFor(desktopCell.verb, tense)}`}</small>
                      {/if}
                    </span>
                  </label>
                {/each}
              </div>
            </div>
          {/if}

          <div class="game-utility" aria-live="polite">
            {#if desktopReview}
              <b>Batch complete · ready to send</b><i></i><span>Nothing was graded early.</span>
            {:else if submitted}
              <b>{correctAnswers}/{totalAnswers} correct</b><i></i><span>{missedAnswers.length ? `${missedAnswers.length} to review` : 'Clean sweep'}</span>
            {:else}
              <b>{remainingAnswers} {remainingAnswers === 1 ? 'answer' : 'answers'} left</b><i></i><span>Enter moves to the next form</span>
            {/if}
          </div>

          <div class="game-actions">
            {#if submitted}
              <button class="secondary-action" type="button" on:click={() => void editAnswers()}>Edit answers</button>
              <button class="secondary-action" type="button" on:click={resetDemo}>Reset demo</button>
            {:else}
              <button
                bind:this={desktopCheckButton}
                class="primary-action"
                type="button"
                disabled={filledAnswers < totalAnswers}
                on:click={() => void checkAll()}
              >
                <span class="key-chip">Enter</span> Check all answers
              </button>
            {/if}
          </div>
        </div>
      </div>
    </section>

    <section class="preview-column mobile-column" aria-label={`${variant === 'matrix' ? 'Paired forms' : 'Single form'} mobile preview`}>
      <div class="preview-label">
        <span>MOBILE · KEYBOARD-OPEN VIEWPORT</span>
        <strong>{variant === 'matrix' ? 'One verb · selected forms stay together' : 'One verb · one form at a time'}</strong>
      </div>

      <div
        class="practice-card mobile-practice"
        style={`--mobile-visible-height: ${mobileViewportHeight}px`}
      >
        <div class="outside-progress compact-progress">
          <span>Verb {mobileCell ? mobileCell.verbIndex + 1 : 1}/{verbs.length}</span>
          <strong>{mobileCellIndex + 1}/{totalAnswers}</strong>
          <i><b style={`width: ${((mobileCellIndex + 1) / Math.max(1, cells.length)) * 100}%`}></b></i>
        </div>

        <div class="game-frame mobile-game">
          {#if mobileCell}
            <div class="mobile-context-bar">
              <span>VERB {mobileCell.verbIndex + 1}/{verbs.length}</span>
              <span>FORM {mobileCell.tenseIndex + 1}/{selectedTenses.length}</span>
              <strong>{Math.max(0, totalAnswers - mobileCellIndex - 1)} LEFT</strong>
            </div>
            <div class="mobile-tense-name">{tenseLabel(mobileCell.tense)}</div>
            <div class="verb-hero mobile-hero">
              <span>Current verb</span>
              <strong>{mobileCell.verb.base}</strong>
              <em>{mobileCell.verb.meaning}</em>
            </div>
          {/if}

          {#if mobileReview}
            <div class="mobile-state-card">
              <span>READY TO SEND</span>
              <strong>{filledAnswers}/{totalAnswers} answers saved</strong>
              <p>Press Enter once more or use the button. Feedback will appear for the complete batch.</p>
              <div class="review-dots" aria-label="Completion by verb">
                {#each verbs as verb}<i class:review-dot-done={verbComplete(verb)} title={verb.base}></i>{/each}
              </div>
              <button class="primary-action" type="button" on:click={() => void checkAll(true)}>
                <span class="key-chip">Enter</span> Check all
              </button>
              <button class="text-action" type="button" on:click={() => void editAnswers(true)}>Keep editing</button>
            </div>
          {:else if submitted}
            <div class="mobile-state-card mobile-results" role="status" aria-live="polite">
              <span>BATCH FEEDBACK</span>
              <strong>{correctAnswers}/{totalAnswers} correct</strong>
              {#if missedAnswers.length}
                <div class="mobile-mistakes">
                  {#each missedAnswers as cell}
                    <div>
                      <span><b>{cell.verb.base}</b><small>{tenseLabel(cell.tense)}</small></span>
                      <del>{answerFor(cell.verb, cell.tense) || 'No answer'}</del>
                      <strong>{expectedFor(cell.verb, cell.tense)}</strong>
                    </div>
                  {/each}
                </div>
              {:else}
                <p class="perfect-result">✓ Clean sweep</p>
              {/if}
              <button class="primary-action" type="button" on:click={() => void editAnswers(true)}>
                <span class="key-chip">Enter</span> Edit batch
              </button>
            </div>
          {:else if mobileCell}
            <div class="mobile-answer-area">
              {#if variant === 'matrix'}
                {#each selectedTenses as tense}
                  {@const index = cellIndexFor(mobileCell.verbIndex, tense)}
                  {@const cell = cells[index]}
                  <label
                    class="mobile-answer-row"
                    class:mobile-answer-active={mobileCellIndex === index}
                  >
                    <span class="row-marker" aria-hidden="true">{mobileCellIndex === index ? '▶' : answerFor(mobileCell.verb, tense).trim() ? '✓' : '·'}</span>
                    <span class="answer-label"><small>FORM {selectedTenses.indexOf(tense) + 1}</small><strong>{tenseLabel(tense)}</strong></span>
                    <input
                      type="text"
                      value={answerFor(mobileCell.verb, tense)}
                      data-mobile-index={index}
                      inputmode="text"
                      enterkeyhint={index === cells.length - 1 ? 'done' : 'next'}
                      aria-label={`${mobileCell.verb.base}, ${tenseLabel(tense)}, mobile`}
                      autocomplete="off"
                      spellcheck="false"
                      on:focus={() => (mobileCellIndex = index)}
                      on:input={(event) => updateAnswer(event, cell)}
                      on:keydown={(event) => void handleMobileEnter(event, index)}
                    />
                  </label>
                {/each}
              {:else}
                <label class="mobile-answer-row mobile-answer-active single-mobile-answer">
                  <span class="row-marker" aria-hidden="true">▶</span>
                  <span class="answer-label"><small>FORM {mobileCell.tenseIndex + 1}</small><strong>{tenseLabel(mobileCell.tense)}</strong></span>
                  <input
                    type="text"
                    value={answerFor(mobileCell.verb, mobileCell.tense)}
                    data-mobile-index={mobileCell.index}
                    inputmode="text"
                    enterkeyhint={mobileCell.index === cells.length - 1 ? 'done' : 'next'}
                    aria-label={`${mobileCell.verb.base}, ${tenseLabel(mobileCell.tense)}, mobile`}
                    autocomplete="off"
                    spellcheck="false"
                    on:input={(event) => updateAnswer(event, mobileCell)}
                    on:keydown={(event) => void handleMobileEnter(event, mobileCell.index)}
                  />
                </label>
              {/if}
            </div>

            <div class="mobile-nav">
              <button
                type="button"
                disabled={mobileCellIndex === 0}
                aria-label="Previous form"
                on:click={() => void selectMobileCell(mobileCellIndex - 1)}
              >←</button>
              {#if mobileCellIndex < cells.length - 1}
                <button
                  class="primary-action"
                  type="button"
                  disabled={!answerFor(mobileCell.verb, mobileCell.tense).trim()}
                  on:click={() => void selectMobileCell(mobileCellIndex + 1)}
                >
                  {mobileCell.tenseIndex < selectedTenses.length - 1 ? 'Next form' : 'Next verb'} →
                </button>
              {:else}
                <button
                  class="primary-action"
                  type="button"
                  disabled={!answerFor(mobileCell.verb, mobileCell.tense).trim()}
                  on:click={reviewMobileBatch}
                >Review batch →</button>
              {/if}
            </div>
          {/if}

          {#if mobileReview || submitted}
            <input
              bind:this={mobileKeyboardPrimer}
              class="keyboard-primer"
              type="text"
              inputmode="text"
              enterkeyhint={mobileReview ? 'send' : 'next'}
              aria-label={mobileReview ? 'Press Enter to check the batch' : 'Press Enter to edit the batch'}
              on:keydown={(event) => void handlePrimerEnter(event)}
            />
          {/if}
        </div>
      </div>
    </section>
  </div>
</article>

<style>
  .option-demo {
    container-type: inline-size;
  }

  button,
  input {
    font-family: var(--ui);
  }

  button:focus-visible,
  input:focus-visible {
    outline: 3px solid color-mix(in srgb, var(--accent-2) 42%, transparent);
    outline-offset: 2px;
  }

  .preview-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(270px, 0.36fr);
    gap: 1rem;
    align-items: start;
  }

  .preview-column {
    display: grid;
    min-width: 0;
    gap: 0.45rem;
  }

  .preview-label {
    display: grid;
    gap: 0.15rem;
    padding-inline: 0.2rem;
  }

  .preview-label span {
    color: var(--accent-strong);
    font: 780 0.58rem/1 var(--mono);
    letter-spacing: 0.11em;
  }

  .preview-label strong {
    color: var(--text);
    font-size: 0.76rem;
  }

  .practice-card {
    min-width: 0;
    overflow: hidden;
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 0.8rem;
    background: color-mix(in srgb, var(--surface-strong) 86%, transparent);
    box-shadow: 0 22px 52px -38px color-mix(in srgb, var(--text) 44%, transparent);
  }

  .outside-progress {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 0.35rem 0.8rem;
    align-items: center;
    margin-bottom: 0.65rem;
    color: var(--muted);
    font: 720 0.62rem/1 var(--mono);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .outside-progress strong {
    color: var(--text);
    font-variant-numeric: tabular-nums;
  }

  .outside-progress > i {
    grid-column: 1 / -1;
    height: 4px;
    overflow: hidden;
    border-radius: 999px;
    background: color-mix(in srgb, var(--line) 72%, transparent);
  }

  .outside-progress > i b {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--accent-2), var(--accent));
    transition: width 180ms ease;
  }

  .game-frame {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 0.72rem;
    padding: clamp(0.72rem, 2.2vw, 1rem);
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--accent) 38%, rgba(255, 255, 255, 0.14));
    border-radius: 22px;
    color: white;
    background:
      radial-gradient(circle at 92% 0%, color-mix(in srgb, var(--accent) 20%, transparent), transparent 31%),
      color-mix(in srgb, var(--surface-dark) 91%, black 9%);
    box-shadow: 0 24px 55px rgba(5, 8, 20, 0.2);
  }

  .tense-strip {
    display: flex;
    min-height: 2.2rem;
    gap: 0.4rem;
    align-items: center;
  }

  .tense-strip span {
    flex: 1 1 0;
    min-width: 0;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 6px;
    padding: 0.42rem 0.5rem;
    color: rgba(255, 255, 255, 0.6);
    background: rgba(255, 255, 255, 0.05);
    font-size: 0.72rem;
    font-weight: 650;
    text-align: center;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tense-strip .strip-active {
    border-color: transparent;
    padding-block: 0;
    color: #f6c84c;
    background: none;
    font: 800 clamp(1.2rem, 2.6vw, 1.65rem)/1.05 var(--display);
    text-shadow: 0 0 16px color-mix(in srgb, #f6c84c 45%, transparent);
  }

  .tense-strip .strip-done {
    border-color: #55ee9b;
    color: #78f2ad;
    background: color-mix(in srgb, #55ee9b 14%, transparent);
  }

  .verb-hero {
    position: relative;
    display: grid;
    gap: 0.25rem;
    justify-items: center;
    padding: 0.82rem 0.7rem 0.75rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 15px;
    text-align: center;
    background:
      linear-gradient(rgba(255, 255, 255, 0.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255, 255, 255, 0.025) 1px, transparent 1px),
      rgba(8, 13, 31, 0.54);
    background-size: 24px 24px;
  }

  .verb-hero > span {
    color: rgba(255, 255, 255, 0.66);
    font: 700 0.62rem/1 var(--mono);
    letter-spacing: 0.15em;
    text-transform: uppercase;
  }

  .verb-hero > strong {
    max-width: 100%;
    overflow-wrap: anywhere;
    font: 820 clamp(1.55rem, 4vw, 2.15rem)/1 var(--ui);
  }

  .verb-hero > em {
    color: rgba(255, 255, 255, 0.8);
    font-size: 0.82rem;
    font-style: normal;
  }

  .verb-hero > em b {
    color: #f6c84c;
  }

  .game-panel {
    width: 100%;
    min-width: 0;
    margin-inline: auto;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 13px;
    background: rgba(255, 255, 255, 0.025);
  }

  .panel-review {
    border-color: color-mix(in srgb, #f6c84c 48%, transparent);
    box-shadow: 0 0 0 3px color-mix(in srgb, #f6c84c 5%, transparent);
  }

  .panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.7rem;
    padding: 0.62rem 0.72rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(255, 255, 255, 0.035);
  }

  .panel-head > div {
    display: grid;
    gap: 0.1rem;
  }

  .panel-head > div:last-child {
    justify-items: end;
    text-align: right;
  }

  .panel-head span {
    color: var(--accent-2);
    font: 760 0.62rem/1.2 var(--mono);
    letter-spacing: 0.09em;
  }

  .panel-head strong {
    color: white;
    font-size: 0.78rem;
  }

  .panel-head small {
    color: rgba(255, 255, 255, 0.66);
    font-size: 0.63rem;
  }

  .matrix-scroll {
    min-width: 0;
    overflow-x: auto;
  }

  .verb-matrix {
    width: 100%;
    min-width: 33rem;
    border-collapse: collapse;
    table-layout: fixed;
  }

  .verb-column {
    width: 27%;
  }

  .single-tense .verb-column {
    width: 34%;
  }

  .verb-matrix th,
  .verb-matrix td {
    border-bottom: 1px solid rgba(255, 255, 255, 0.09);
    text-align: left;
    vertical-align: middle;
  }

  .verb-matrix tr:last-child > * {
    border-bottom: 0;
  }

  .verb-matrix tr > * + * {
    border-left: 1px solid rgba(255, 255, 255, 0.09);
  }

  .verb-matrix thead th {
    height: 2.3rem;
    padding: 0.5rem 0.58rem;
    color: rgba(255, 255, 255, 0.64);
    background: rgba(255, 255, 255, 0.04);
    font: 730 0.58rem/1 var(--mono);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .verb-cell {
    padding: 0;
    background: rgba(255, 255, 255, 0.018);
  }

  .verb-cell-content {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 0.05rem 0.42rem;
    align-content: center;
    min-height: 3.65rem;
    padding: 0.48rem 0.58rem;
  }

  .verb-cell-content > small {
    grid-row: 1 / 3;
    align-self: center;
    color: rgba(255, 255, 255, 0.42);
    font: 700 0.56rem/1 var(--mono);
  }

  .verb-cell-content > span {
    display: grid;
    min-width: 0;
    gap: 0.08rem;
  }

  .verb-cell-content strong {
    color: white;
    font-size: 0.78rem;
  }

  .verb-cell-content em {
    overflow: hidden;
    color: rgba(255, 255, 255, 0.58);
    font-size: 0.6rem;
    font-style: normal;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .verb-row-active .verb-cell {
    background: color-mix(in srgb, var(--accent) 8%, rgba(255, 255, 255, 0.018));
    box-shadow: inset 3px 0 0 var(--accent-2);
  }

  .matrix-answer {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 0.25rem 0.38rem;
    align-items: center;
    min-height: 3.65rem;
    padding: 0.42rem;
    background: rgba(255, 255, 255, 0.018);
  }

  .matrix-answer > small {
    grid-column: 2;
    color: rgba(255, 255, 255, 0.64);
    font: 750 0.5rem/1.1 var(--mono);
    letter-spacing: 0.04em;
  }

  .matrix-cell-active {
    background: color-mix(in srgb, var(--accent) 12%, rgba(255, 255, 255, 0.018));
    box-shadow: inset 0 -2px 0 var(--accent-2);
  }

  .row-marker {
    width: 1rem;
    color: var(--accent-2);
    font: 800 0.65rem/1 var(--mono);
    text-align: center;
  }

  .matrix-answer input,
  .guided-answer input,
  .mobile-answer-row input {
    box-sizing: border-box;
    width: 100%;
    min-width: 0;
    min-height: 2.55rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    outline: none;
    padding: 0.58rem 0.62rem;
    color: white;
    background: rgba(6, 8, 24, 0.72);
    font-size: 0.82rem;
    font-weight: 680;
  }

  .matrix-answer input:focus,
  .guided-answer input:focus,
  .mobile-answer-row input:focus {
    border-color: var(--accent-2);
    box-shadow: inset 0 -2px 0 var(--accent-2);
  }

  .answer-correct {
    background: color-mix(in srgb, #55ee9b 10%, rgba(255, 255, 255, 0.02));
  }

  .answer-correct .row-marker,
  .answer-correct > small,
  .answer-correct .input-shell > small {
    color: #55ee9b;
  }

  .answer-correct input {
    border-color: color-mix(in srgb, #55ee9b 58%, transparent);
  }

  .answer-wrong {
    background: color-mix(in srgb, #ff7188 10%, rgba(255, 255, 255, 0.02));
  }

  .answer-wrong .row-marker,
  .answer-wrong > small,
  .answer-wrong .input-shell > small {
    color: #ff7188;
  }

  .answer-wrong input {
    border-color: color-mix(in srgb, #ff7188 62%, transparent);
  }

  .verb-route {
    display: flex;
    gap: 0.35rem;
  }

  .verb-route button {
    display: grid;
    flex: 1 1 0;
    min-width: 0;
    min-height: 2.5rem;
    place-items: center;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 6px;
    padding: 0.32rem;
    color: rgba(255, 255, 255, 0.58);
    background: rgba(255, 255, 255, 0.04);
  }

  .verb-route button small {
    color: inherit;
    font: 700 0.48rem/1 var(--mono);
  }

  .verb-route button strong {
    max-width: 100%;
    overflow: hidden;
    font-size: 0.66rem;
    text-overflow: ellipsis;
  }

  .verb-route .route-active {
    border-color: transparent;
    color: #f6c84c;
    background: none;
    box-shadow: inset 0 -2px 0 #f6c84c;
  }

  .verb-route .route-done:not(.route-active) {
    border-color: color-mix(in srgb, #55ee9b 50%, transparent);
    color: #78f2ad;
    background: color-mix(in srgb, #55ee9b 10%, transparent);
  }

  .guided-rows {
    position: relative;
    display: grid;
    gap: 0.35rem;
    padding: 0.58rem 0.58rem 0.58rem 1rem;
  }

  .answer-rail {
    position: absolute;
    inset-block: 0.72rem;
    left: 0.48rem;
    width: 2px;
    overflow: hidden;
    background: rgba(255, 255, 255, 0.1);
  }

  .answer-rail i {
    display: block;
    width: 100%;
    background: linear-gradient(var(--accent-2), var(--accent));
  }

  .guided-answer {
    display: grid;
    grid-template-columns: auto minmax(8rem, 0.45fr) minmax(0, 1fr);
    gap: 0.62rem;
    align-items: center;
    min-height: 3.8rem;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 5px;
    padding: 0.5rem 0.58rem;
    background: rgba(255, 255, 255, 0.025);
  }

  .guided-answer-active {
    border-color: var(--accent-2);
    background: color-mix(in srgb, var(--accent) 18%, rgba(255, 255, 255, 0.025));
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 9%, transparent);
    transform: translateX(0.15rem);
  }

  .answer-label {
    display: grid;
    gap: 0.12rem;
  }

  .answer-label small {
    color: var(--accent-2);
    font: 750 0.56rem/1 var(--mono);
  }

  .answer-label strong {
    color: white;
    font-size: 0.8rem;
  }

  .input-shell {
    display: grid;
    min-width: 0;
    gap: 0.2rem;
  }

  .input-shell > small {
    color: rgba(255, 255, 255, 0.62);
    font: 750 0.52rem/1 var(--mono);
    letter-spacing: 0.04em;
  }

  .game-utility {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-wrap: wrap;
    gap: 0.55rem;
    color: rgba(255, 255, 255, 0.7);
    font-size: 0.68rem;
  }

  .game-utility b {
    color: white;
  }

  .game-utility i {
    width: 1px;
    height: 0.8rem;
    background: rgba(255, 255, 255, 0.18);
  }

  .game-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.45rem;
  }

  .primary-action,
  .secondary-action,
  .text-action,
  .mobile-nav button {
    min-height: 2.75rem;
    border-radius: 9px;
    padding: 0.52rem 0.72rem;
    font-size: 0.68rem;
    font-weight: 760;
  }

  .primary-action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.42rem;
    border: 1px solid color-mix(in srgb, var(--accent-2) 62%, transparent);
    color: white;
    background: var(--accent);
  }

  .secondary-action {
    border: 1px solid rgba(255, 255, 255, 0.16);
    color: white;
    background: rgba(255, 255, 255, 0.06);
  }

  .text-action {
    border: 0;
    color: rgba(255, 255, 255, 0.72);
    background: transparent;
  }

  button:disabled {
    cursor: default;
    opacity: 0.42;
  }

  .key-chip {
    border: 1px solid rgba(255, 255, 255, 0.26);
    border-radius: 5px;
    padding: 0.15rem 0.28rem;
    font: 750 0.52rem/1 var(--mono);
  }

  .mobile-practice {
    padding: 0.58rem;
  }

  .compact-progress {
    margin: 0 0.15rem 0.48rem;
  }

  .mobile-game {
    height: min(22rem, max(17rem, calc(var(--mobile-visible-height) - 1rem)));
    min-height: 17rem;
    gap: 0.42rem;
    padding: 0.58rem;
    border-radius: 18px;
  }

  .mobile-context-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.4rem;
    color: rgba(255, 255, 255, 0.62);
    font: 740 0.5rem/1 var(--mono);
    letter-spacing: 0.06em;
  }

  .mobile-context-bar strong {
    color: var(--accent-2);
  }

  .mobile-tense-name {
    min-width: 0;
    overflow: hidden;
    color: #f6c84c;
    font: 800 clamp(1.05rem, 5vw, 1.45rem)/1.05 var(--display);
    text-align: center;
    text-overflow: ellipsis;
    text-shadow: 0 0 14px color-mix(in srgb, #f6c84c 42%, transparent);
    white-space: nowrap;
  }

  .mobile-hero {
    gap: 0.12rem;
    padding: 0.48rem 0.55rem 0.45rem;
  }

  .mobile-hero > span {
    font-size: 0.48rem;
  }

  .mobile-hero > strong {
    font-size: clamp(1.35rem, 8vw, 1.8rem);
  }

  .mobile-hero > em {
    font-size: 0.62rem;
  }

  .mobile-answer-area {
    display: grid;
    min-height: 0;
    gap: 0.32rem;
    overflow-y: auto;
  }

  .mobile-answer-row {
    display: grid;
    grid-template-columns: auto minmax(5.6rem, 0.7fr) minmax(0, 1fr);
    gap: 0.4rem;
    align-items: center;
    min-height: 3.55rem;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 6px;
    padding: 0.4rem 0.45rem;
    background: rgba(255, 255, 255, 0.025);
  }

  .mobile-answer-active {
    border-color: var(--accent-2);
    background: color-mix(in srgb, var(--accent) 15%, rgba(255, 255, 255, 0.025));
    box-shadow: inset 3px 0 0 var(--accent-2);
  }

  .mobile-answer-row .answer-label small {
    font-size: 0.46rem;
  }

  .mobile-answer-row .answer-label strong {
    font-size: 0.64rem;
  }

  .mobile-answer-row input {
    min-height: 2.65rem;
    font-size: 0.86rem;
  }

  .single-mobile-answer {
    min-height: 4.15rem;
  }

  .mobile-nav {
    display: grid;
    grid-template-columns: 2.75rem 1fr;
    gap: 0.4rem;
    margin-top: auto;
    padding-top: 0.08rem;
  }

  .mobile-nav button {
    min-height: 2.75rem;
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: white;
    background: rgba(255, 255, 255, 0.06);
  }

  .mobile-nav .primary-action {
    background: var(--accent);
  }

  .mobile-state-card {
    display: grid;
    min-height: 0;
    gap: 0.52rem;
    overflow-y: auto;
    padding: 0.65rem;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.03);
  }

  .mobile-state-card > span {
    color: #f6c84c;
    font: 770 0.52rem/1 var(--mono);
    letter-spacing: 0.1em;
  }

  .mobile-state-card > strong {
    color: white;
    font-size: 1rem;
  }

  .mobile-state-card > p {
    margin: 0;
    color: rgba(255, 255, 255, 0.68);
    font-size: 0.63rem;
    line-height: 1.4;
  }

  .review-dots {
    display: flex;
    gap: 0.38rem;
  }

  .review-dots i {
    flex: 1 1 0;
    height: 5px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.14);
  }

  .review-dots .review-dot-done {
    background: #55ee9b;
  }

  .mobile-mistakes {
    display: grid;
    gap: 0.28rem;
  }

  .mobile-mistakes > div {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 0.8fr) minmax(0, 0.8fr);
    gap: 0.35rem;
    align-items: center;
    padding: 0.38rem 0.45rem;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 6px;
    font-size: 0.58rem;
  }

  .mobile-mistakes span {
    display: grid;
    min-width: 0;
  }

  .mobile-mistakes small {
    overflow: hidden;
    color: rgba(255, 255, 255, 0.58);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .mobile-mistakes del {
    overflow-wrap: anywhere;
    color: #ff7188;
  }

  .mobile-mistakes > div > strong {
    overflow-wrap: anywhere;
    color: #55ee9b;
  }

  .perfect-result {
    border: 1px solid color-mix(in srgb, #55ee9b 48%, transparent);
    border-radius: 8px;
    padding: 0.7rem;
    color: #55ee9b !important;
    background: color-mix(in srgb, #55ee9b 9%, transparent);
    text-align: center;
  }

  .keyboard-primer {
    position: fixed;
    width: 1px;
    height: 1px;
    opacity: 0;
    pointer-events: none;
  }

  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
    clip-path: inset(50%);
    white-space: nowrap;
  }

  :global(html[data-theme='dark']) .game-frame {
    border-color: color-mix(in srgb, var(--accent) 46%, transparent);
    border-radius: 0 20px 0 20px;
    color: var(--text);
    background:
      linear-gradient(90deg, var(--accent-2) 0 3px, transparent 3px),
      linear-gradient(rgba(240, 231, 216, 0.022) 1px, transparent 1px),
      linear-gradient(90deg, rgba(240, 231, 216, 0.022) 1px, transparent 1px),
      linear-gradient(145deg, var(--ink-raised), var(--ink-panel));
    background-size: auto, 24px 24px, 24px 24px, auto;
  }

  :global(html[data-theme='dark']) .verb-hero,
  :global(html[data-theme='dark']) .game-panel,
  :global(html[data-theme='dark']) .mobile-state-card {
    background-color: color-mix(in srgb, var(--ink-field) 58%, transparent);
  }

  :global(html[data-theme='dark']) .matrix-answer input,
  :global(html[data-theme='dark']) .guided-answer input,
  :global(html[data-theme='dark']) .mobile-answer-row input {
    color: var(--text);
    background: var(--ink-field);
  }

  :global(html[data-theme='arcade']) .tense-strip .strip-active,
  :global(html[data-theme='arcade']) .mobile-tense-name {
    font-family: var(--marquee);
    line-height: 1.4;
  }

  @container (max-width: 790px) {
    .preview-grid {
      grid-template-columns: 1fr;
    }

    .mobile-column {
      width: min(100%, 340px);
      margin-inline: auto;
    }
  }

  @container (max-width: 480px) {
    .desktop-column {
      display: none;
    }

    .mobile-column {
      width: 100%;
    }

    .practice-card {
      border-radius: 15px;
      padding: 0.45rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .outside-progress > i b {
      transition: none;
    }
  }
</style>
