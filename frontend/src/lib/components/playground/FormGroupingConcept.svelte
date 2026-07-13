<script lang="ts">
  export let variant: 'uniform-rail' | 'uniform-bundle' | 'cluster-rows' | 'cluster-lanes';
  export let index = 'U1';
  export let kicker = '';
  export let title = '';
  export let description = '';

  const PRONOUNS = ['I', 'you', 'he / she / it', 'we', 'you (plural)', 'they'];
  const BASE_GROUP = new Set([0, 1, 3, 4, 5]);

  let firstAnswer = variant.startsWith('uniform') ? 'abolished' : 'accept';
  let secondAnswer = 'accepts';
  let firstInput: HTMLInputElement | null = null;
  let secondInput: HTMLInputElement | null = null;

  $: isUniform = variant.startsWith('uniform');

  function reset(): void {
    firstAnswer = isUniform ? 'abolished' : 'accept';
    secondAnswer = 'accepts';
    requestAnimationFrame(() => firstInput?.focus());
  }

  function moveToSecond(event: KeyboardEvent): void {
    if (event.key !== 'Enter' || isUniform) {
      return;
    }
    event.preventDefault();
    secondInput?.focus();
  }

  function returnToFirst(event: KeyboardEvent): void {
    if (event.key !== 'Backspace' || secondAnswer !== '') {
      return;
    }
    event.preventDefault();
    firstInput?.focus();
    const end = firstInput?.value.length ?? 0;
    firstInput?.setSelectionRange(end, end);
  }
</script>

<article class={`form-concept variant-${variant}`}>
  <header class="concept-intro">
    <span class="concept-number">{index}</span>
    <div>
      <p class="eyebrow">{kicker}</p>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  </header>

  <div class="group-stage">
    <header class="stage-head">
      <div>
        <span>ENGLISH / {isUniform ? 'PAST' : 'PRESENT'}</span>
        <strong>{isUniform ? 'abolish' : 'accept'}</strong>
      </div>
      <div class="form-count">
        <strong>{isUniform ? 1 : 2}</strong>
        <span>DISTINCT {isUniform ? 'FORM' : 'FORMS'}</span>
      </div>
      <button type="button" on:click={reset}>Reset demo</button>
    </header>

    {#if variant === 'uniform-rail'}
      <div class="uniform-callout"><span>TYPE ONCE</span><strong>One answer powers the entire column.</strong><small>No guide is revealed; the first row remains the graded representative.</small></div>
      <div class="rail-table">
        {#each PRONOUNS as pronoun, pronounIndex}
          <div class:rail-master={pronounIndex === 0} class:rail-linked={pronounIndex > 0} class="rail-row">
            <span class="row-number">{String(pronounIndex + 1).padStart(2, '0')}</span>
            <strong>{pronoun}</strong>
            {#if pronounIndex === 0}
              <div class="demo-input-wrap">
                <input bind:this={firstInput} bind:value={firstAnswer} aria-label="Conjugation shared by every pronoun" />
                <kbd>Enter</kbd>
              </div>
            {:else}
              <div class="same-cell"><span>=</span><strong>{firstAnswer || 'Same answer'}</strong><small>same as I</small></div>
            {/if}
          </div>
        {/each}
        <span class="rail-line" aria-hidden="true"></span>
      </div>
    {:else if variant === 'uniform-bundle'}
      <div class="bundle-stage">
        <div class="pronoun-bundle" aria-label="All pronouns share one form">
          {#each PRONOUNS as pronoun, pronounIndex}
            <span style={`--chip-index: ${pronounIndex}`}><i aria-hidden="true"></i>{pronoun}</span>
          {/each}
        </div>
        <div class="answer-core">
          <span class="core-orbit" aria-hidden="true"></span>
          <small>ONE SHARED FORM</small>
          <input bind:this={firstInput} bind:value={firstAnswer} aria-label="One answer for all six pronouns" />
          <div><kbd>Enter</kbd><span>checks all six slots</span></div>
        </div>
        <div class="bundle-result"><span>6 pronouns</span><i aria-hidden="true">x</i><strong>1 answer</strong><em>scored once</em></div>
      </div>
    {:else if variant === 'cluster-rows'}
      <div class="cluster-key">
        <span class="group-a"><i>A</i> I / you / we / you / they</span>
        <span class="group-b"><i>B</i> he / she / it</span>
        <small>Two colors, two editable representatives</small>
      </div>
      <div class="cluster-table">
        {#each PRONOUNS as pronoun, pronounIndex}
          {@const baseForm = BASE_GROUP.has(pronounIndex)}
          {@const representative = pronounIndex === 0 || pronounIndex === 2}
          <div class:group-a={baseForm} class:group-b={!baseForm} class:cluster-master={representative} class="cluster-row">
            <span class="group-node">{baseForm ? 'A' : 'B'}</span>
            <strong>{pronoun}</strong>
            {#if pronounIndex === 0}
              <input bind:this={firstInput} bind:value={firstAnswer} on:keydown={moveToSecond} aria-label="Form for I, you, we, and they" />
            {:else if pronounIndex === 2}
              <input bind:this={secondInput} bind:value={secondAnswer} on:keydown={returnToFirst} aria-label="Form for he, she, and it" />
            {:else}
              <div class="cluster-linked"><span>=</span><strong>{baseForm ? firstAnswer || 'Group A' : secondAnswer || 'Group B'}</strong><small>linked to {baseForm ? 'I' : 'he / she / it'}</small></div>
            {/if}
            <em>{representative ? 'TYPE' : 'SAME'}</em>
          </div>
        {/each}
      </div>
      <div class="cluster-footer"><kbd>Enter</kbd><span>A to B</span><kbd>Backspace</kbd><span>return when empty</span></div>
    {:else}
      <div class="lane-flow">
        <section class="form-lane lane-a">
          <header><span>FORM A</span><strong>5 pronouns</strong></header>
          <div class="lane-pronouns">
            {#each PRONOUNS.filter((_, indexValue) => BASE_GROUP.has(indexValue)) as pronoun}<span>{pronoun}</span>{/each}
          </div>
          <label><span>Write their shared form</span><input bind:this={firstInput} bind:value={firstAnswer} on:keydown={moveToSecond} /></label>
          <footer><i aria-hidden="true">1</i><span>one graded answer</span></footer>
        </section>
        <div class="lane-bridge"><span>Enter</span><i aria-hidden="true">-></i><small>next distinct form</small></div>
        <section class="form-lane lane-b">
          <header><span>FORM B</span><strong>1 pronoun group</strong></header>
          <div class="lane-pronouns"><span>he / she / it</span></div>
          <label><span>Write this distinct form</span><input bind:this={secondInput} bind:value={secondAnswer} on:keydown={returnToFirst} /></label>
          <footer><i aria-hidden="true">2</i><span>second graded answer</span></footer>
        </section>
      </div>
      <div class="lane-summary"><strong>{firstAnswer || '...'} / {secondAnswer || '...'}</strong><span>Two forms complete all six pronoun rows.</span></div>
    {/if}
  </div>
</article>

<style>
  .form-concept {
    display: grid;
    gap: 1rem;
  }

  .concept-intro {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.9rem;
    width: min(100%, 760px);
    margin-inline: auto;
  }

  .concept-number {
    display: grid;
    width: 2.8rem;
    height: 2.8rem;
    place-items: center;
    border: 1px solid var(--line-strong);
    border-radius: 13px;
    color: var(--accent-strong);
    background: var(--accent-soft);
    font: 800 0.68rem/1 var(--mono);
  }

  .concept-intro h3 {
    margin: 0.2rem 0 0.25rem;
    color: var(--text);
    font: 800 1.1rem/1.1 var(--display);
    letter-spacing: -0.03em;
  }

  .concept-intro p:last-child {
    margin: 0;
    color: var(--muted);
    font-size: 0.7rem;
  }

  .group-stage {
    width: min(100%, 820px);
    margin-inline: auto;
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--accent) 36%, var(--line));
    border-radius: 24px;
    color: #f8f7ff;
    background:
      radial-gradient(circle at 92% 0%, color-mix(in srgb, var(--accent) 20%, transparent), transparent 29%),
      linear-gradient(145deg, #10152b, #080b19 66%);
    box-shadow: 0 24px 65px rgba(5, 8, 20, 0.22);
  }

  .stage-head {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 1rem;
    align-items: center;
    padding: 0.9rem 1rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(255, 255, 255, 0.025);
  }

  .stage-head > div:first-child {
    display: grid;
    gap: 0.15rem;
  }

  .stage-head > div:first-child span,
  .form-count span {
    color: #81dfff;
    font: 800 0.48rem/1 var(--mono);
    letter-spacing: 0.11em;
  }

  .stage-head > div:first-child strong {
    font: 820 clamp(1.25rem, 4vw, 1.75rem)/1 var(--display);
  }

  .form-count {
    display: grid;
    grid-template-columns: auto auto;
    gap: 0.35rem;
    align-items: center;
  }

  .form-count strong {
    color: #f8cc63;
    font: 850 1.3rem/1 var(--display);
  }

  .stage-head button {
    padding: 0.42rem 0.58rem;
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 8px;
    color: rgba(255, 255, 255, 0.68);
    background: rgba(255, 255, 255, 0.04);
    font: 700 0.5rem/1 var(--mono);
  }

  input {
    width: 100%;
    min-width: 0;
    padding: 0.66rem 0.72rem;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 8px;
    outline: none;
    color: white;
    background: rgba(3, 6, 18, 0.72);
    font: 720 0.94rem/1 var(--display);
  }

  input:focus {
    border-color: #60d8ff;
    box-shadow: 0 0 0 3px rgba(96, 216, 255, 0.1), inset 0 -2px #60d8ff;
  }

  kbd {
    padding: 0.18rem 0.3rem;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 5px;
    color: rgba(255, 255, 255, 0.68);
    background: rgba(255, 255, 255, 0.055);
    font: 760 0.44rem/1 var(--mono);
    white-space: nowrap;
  }

  .uniform-callout {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.15rem 0.65rem;
    margin: 0.8rem 0.8rem 0;
    padding: 0.65rem 0.75rem;
    border: 1px solid rgba(248, 204, 99, 0.28);
    border-radius: 10px;
    background: rgba(248, 204, 99, 0.07);
  }

  .uniform-callout > span {
    grid-row: 1 / 3;
    align-self: center;
    color: #f8cc63;
    font: 850 0.48rem/1 var(--mono);
  }

  .uniform-callout strong { font-size: 0.72rem; }
  .uniform-callout small { color: rgba(255, 255, 255, 0.5); font-size: 0.54rem; }

  .rail-table {
    position: relative;
    display: grid;
    gap: 0.34rem;
    padding: 0.8rem 0.8rem 0.8rem 1.25rem;
  }

  .rail-line {
    position: absolute;
    top: 1.55rem;
    bottom: 1.55rem;
    left: 0.86rem;
    width: 2px;
    background: linear-gradient(#60d8ff, rgba(96, 216, 255, 0.16));
  }

  .rail-row {
    z-index: 1;
    display: grid;
    grid-template-columns: 1.4rem 8.5rem minmax(0, 1fr);
    gap: 0.55rem;
    align-items: center;
    min-height: 3.35rem;
    padding: 0.48rem 0.6rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.025);
  }

  .rail-master {
    border-color: rgba(96, 216, 255, 0.58);
    background: rgba(96, 216, 255, 0.08);
    transform: translateX(0.15rem);
  }

  .rail-linked { border-style: dashed; }
  .row-number { color: #60d8ff; font: 750 0.46rem/1 var(--mono); }
  .rail-row > strong { font-size: 0.86rem; }

  .demo-input-wrap { position: relative; min-width: 0; }
  .demo-input-wrap kbd { position: absolute; right: 0.4rem; top: 50%; transform: translateY(-50%); }
  .demo-input-wrap input { padding-right: 3.2rem; }

  .same-cell,
  .cluster-linked {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 0.5rem;
    align-items: center;
    min-width: 0;
    color: #8ee4ff;
  }

  .same-cell > span,
  .cluster-linked > span {
    display: grid;
    width: 1.35rem;
    height: 1.35rem;
    place-items: center;
    border: 1px solid currentColor;
    border-radius: 50%;
    font: 800 0.55rem/1 var(--mono);
  }

  .same-cell strong,
  .cluster-linked strong { min-width: 0; color: white; font-size: 0.82rem; overflow-wrap: anywhere; }
  .same-cell small,
  .cluster-linked small { color: rgba(255, 255, 255, 0.42); font: 700 0.45rem/1 var(--mono); text-transform: uppercase; }

  .bundle-stage {
    position: relative;
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(13rem, 0.85fr);
    gap: 1rem;
    align-items: center;
    min-height: 22rem;
    padding: 1.15rem;
  }

  .pronoun-bundle {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.65rem;
  }

  .pronoun-bundle > span {
    position: relative;
    display: flex;
    gap: 0.5rem;
    align-items: center;
    min-height: 3rem;
    padding: 0.6rem;
    border: 1px solid rgba(96, 216, 255, 0.2);
    border-radius: 999px;
    color: rgba(255, 255, 255, 0.76);
    background: rgba(96, 216, 255, 0.045);
    font-size: 0.72rem;
  }

  .pronoun-bundle i {
    width: 0.6rem;
    height: 0.6rem;
    border: 2px solid #60d8ff;
    border-radius: 50%;
    box-shadow: 0 0 10px rgba(96, 216, 255, 0.4);
  }

  .answer-core {
    position: relative;
    z-index: 1;
    display: grid;
    gap: 0.65rem;
    padding: 1.2rem;
    border: 1px solid rgba(248, 204, 99, 0.48);
    border-radius: 22px;
    background: linear-gradient(145deg, rgba(248, 204, 99, 0.12), rgba(5, 8, 22, 0.92));
    box-shadow: 0 0 0 8px rgba(248, 204, 99, 0.035);
  }

  .answer-core > small { color: #f8cc63; font: 820 0.5rem/1 var(--mono); letter-spacing: 0.1em; }
  .answer-core > div { display: flex; gap: 0.5rem; align-items: center; }
  .answer-core > div span { color: rgba(255, 255, 255, 0.5); font-size: 0.54rem; }
  .core-orbit { position: absolute; inset: -0.55rem; z-index: -1; border: 1px dashed rgba(248, 204, 99, 0.22); border-radius: 26px; }

  .bundle-result {
    grid-column: 1 / -1;
    display: flex;
    gap: 0.55rem;
    justify-content: center;
    align-items: baseline;
    color: rgba(255, 255, 255, 0.56);
    font: 700 0.58rem/1 var(--mono);
  }

  .bundle-result i { color: #60d8ff; font-style: normal; }
  .bundle-result strong { color: white; }
  .bundle-result em { color: #f8cc63; font-style: normal; }

  .cluster-key {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    align-items: center;
    padding: 0.75rem 0.8rem;
  }

  .cluster-key > span {
    display: inline-flex;
    gap: 0.4rem;
    align-items: center;
    padding: 0.35rem 0.5rem;
    border: 1px solid currentColor;
    border-radius: 999px;
    font-size: 0.55rem;
  }

  .cluster-key i,
  .group-node {
    display: grid;
    place-items: center;
    font: 850 0.5rem/1 var(--mono);
    font-style: normal;
  }

  .cluster-key small { margin-left: auto; color: rgba(255, 255, 255, 0.44); font-size: 0.52rem; }
  .group-a { color: #76ddff; }
  .group-b { color: #f8cc63; }

  .cluster-table {
    display: grid;
    gap: 0.34rem;
    padding: 0 0.8rem 0.8rem;
  }

  .cluster-row {
    display: grid;
    grid-template-columns: 1.6rem 9rem minmax(0, 1fr) 2.8rem;
    gap: 0.6rem;
    align-items: center;
    min-height: 3.3rem;
    padding: 0.48rem 0.6rem;
    border: 1px solid color-mix(in srgb, currentColor 26%, transparent);
    border-left-width: 3px;
    border-radius: 8px;
    background: color-mix(in srgb, currentColor 5%, transparent);
  }

  .cluster-master { background: color-mix(in srgb, currentColor 9%, transparent); }
  .cluster-row > strong { color: white; font-size: 0.82rem; }
  .group-node { width: 1.45rem; height: 1.45rem; border: 1px solid currentColor; border-radius: 6px; }
  .cluster-row > em { color: currentColor; font: 800 0.43rem/1 var(--mono); font-style: normal; text-align: right; }

  .cluster-linked { color: currentColor; }

  .cluster-footer {
    display: flex;
    gap: 0.4rem;
    justify-content: flex-end;
    align-items: center;
    padding: 0 0.8rem 0.8rem;
    color: rgba(255, 255, 255, 0.48);
    font: 700 0.48rem/1 var(--mono);
  }

  .cluster-footer kbd:nth-of-type(2) { margin-left: 0.45rem; }

  .lane-flow {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 0.75rem;
    align-items: stretch;
    padding: 1rem;
  }

  .form-lane {
    display: grid;
    grid-template-rows: auto 1fr auto auto;
    gap: 0.85rem;
    min-width: 0;
    padding: 1rem;
    border: 1px solid currentColor;
    border-radius: 18px;
    background: color-mix(in srgb, currentColor 7%, rgba(4, 7, 19, 0.78));
  }

  .lane-a { color: #76ddff; }
  .lane-b { color: #f8cc63; }

  .form-lane header,
  .form-lane footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
  }

  .form-lane header span { font: 850 0.55rem/1 var(--mono); letter-spacing: 0.1em; }
  .form-lane header strong { color: rgba(255, 255, 255, 0.58); font-size: 0.58rem; }
  .lane-pronouns { display: flex; flex-wrap: wrap; gap: 0.4rem; align-content: start; }
  .lane-pronouns span { padding: 0.38rem 0.48rem; border: 1px solid color-mix(in srgb, currentColor 38%, transparent); border-radius: 7px; color: white; background: color-mix(in srgb, currentColor 8%, transparent); font-size: 0.62rem; }
  .form-lane label { display: grid; gap: 0.35rem; }
  .form-lane label > span { color: rgba(255, 255, 255, 0.5); font-size: 0.54rem; }
  .form-lane footer { justify-content: flex-start; color: rgba(255, 255, 255, 0.5); font: 700 0.48rem/1 var(--mono); }
  .form-lane footer i { display: grid; width: 1.25rem; height: 1.25rem; place-items: center; border-radius: 50%; color: #080b19; background: currentColor; font-style: normal; }

  .lane-bridge {
    display: grid;
    place-content: center;
    justify-items: center;
    gap: 0.25rem;
    color: #9be8ff;
  }

  .lane-bridge span { padding: 0.25rem 0.35rem; border: 1px solid rgba(155, 232, 255, 0.3); border-radius: 5px; font: 750 0.45rem/1 var(--mono); }
  .lane-bridge i { font: 850 1rem/1 var(--mono); font-style: normal; }
  .lane-bridge small { max-width: 4rem; color: rgba(255, 255, 255, 0.42); font-size: 0.45rem; text-align: center; }

  .lane-summary {
    display: flex;
    gap: 0.65rem;
    justify-content: center;
    align-items: center;
    padding: 0 1rem 1rem;
  }

  .lane-summary strong { color: white; font: 780 0.72rem/1 var(--display); }
  .lane-summary span { color: rgba(255, 255, 255, 0.5); font-size: 0.54rem; }

  :global(html[data-theme='arcade']) .stage-head > div:first-child strong,
  :global(html[data-theme='arcade']) .concept-intro h3 {
    line-height: 1.45;
    letter-spacing: 0;
  }

  @media (max-width: 620px) {
    .stage-head { grid-template-columns: 1fr auto; }
    .stage-head button { grid-column: 1 / -1; width: 100%; }
    .rail-row { grid-template-columns: 1.25rem minmax(0, 1fr); }
    .rail-row > .demo-input-wrap,
    .rail-row > .same-cell { grid-column: 2; }
    .bundle-stage { grid-template-columns: 1fr; min-height: 0; }
    .bundle-result { grid-column: 1; flex-wrap: wrap; }
    .cluster-row { grid-template-columns: 1.5rem minmax(0, 1fr) auto; }
    .cluster-row > input,
    .cluster-row > .cluster-linked { grid-column: 2 / -1; }
    .cluster-row > em { grid-column: 3; grid-row: 1; }
    .cluster-key small { width: 100%; margin-left: 0; }
    .lane-flow { grid-template-columns: 1fr; }
    .lane-bridge { grid-template-columns: auto auto auto; }
    .lane-bridge i { transform: rotate(90deg); }
    .lane-bridge small { max-width: none; }
    .lane-summary { align-items: flex-start; flex-direction: column; }
  }

  @media (max-width: 420px) {
    .pronoun-bundle { grid-template-columns: 1fr; }
    .form-count { display: none; }
  }
</style>
