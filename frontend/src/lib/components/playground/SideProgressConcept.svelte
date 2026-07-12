<script lang="ts">
  export let variant: 'rails' | 'rungs' | 'pulse';
  export let index = 'P1';
  export let kicker = '';
  export let title = '';
  export let description = '';

  const STEPS = [1, 2, 3, 4, 5];
</script>

<article class="progress-concept" data-progress-variant={variant}>
  <header class="concept-intro">
    <span class="concept-number">{index}</span>
    <div><p>{kicker}</p><h3>{title}</h3><span>{description}</span></div>
  </header>

  <div class={`stage-shell stage-${variant}`}>
    <aside class="side-progress side-left" aria-label="Session progress: verb 2 of 5">
      {#if variant === 'rails'}
        <span class="rail-label">02</span><div class="rail-track"><i></i><b></b></div><small>05</small>
      {:else if variant === 'rungs'}
        <span class="rail-label">VERBS</span><div class="rung-stack">{#each STEPS as step}<i class:rung-done={step < 3} class:rung-active={step === 3}></i>{/each}</div><small>2 / 5</small>
      {:else}
        <span class="rail-label">02/05</span><div class="pulse-track">{#each Array(14) as _, dot}<i class:pulse-done={dot < 6} class:pulse-now={dot === 6}></i>{/each}</div><small>RUN</small>
      {/if}
    </aside>

    <div class="mini-game">
      <div class="mini-top"><span>TABLE SHORTCUTS ON</span><small>verb 2 of 5</small></div>
      <div class="mini-prompt"><span>CURRENT VERB</span><strong>aller</strong><small>Présent · 1/3</small></div>
      <div class="mini-column">
        <header><span>ACTIVE TENSE</span><strong>Présent</strong></header>
        <div class="mini-row active"><b>01</b><strong>je</strong><i>vais</i></div>
        <div class="mini-row"><b>02</b><strong>tu</strong><i></i></div>
        <div class="mini-row guide"><b>03</b><strong>il / elle / on</strong><i>va</i></div>
      </div>
      <div class="mini-shortcuts"><span>Enter · next</span><span>Esc ×2 · finish</span></div>
    </div>

    <aside class="side-progress side-right" aria-hidden="true">
      {#if variant === 'rails'}
        <span class="rail-label">02</span><div class="rail-track"><i></i><b></b></div><small>05</small>
      {:else if variant === 'rungs'}
        <span class="rail-label">VERBS</span><div class="rung-stack">{#each STEPS as step}<i class:rung-done={step < 3} class:rung-active={step === 3}></i>{/each}</div><small>2 / 5</small>
      {:else}
        <span class="rail-label">02/05</span><div class="pulse-track">{#each Array(14) as _, dot}<i class:pulse-done={dot < 6} class:pulse-now={dot === 6}></i>{/each}</div><small>RUN</small>
      {/if}
    </aside>
  </div>
</article>

<style>
  .progress-concept {
    width: min(100%, 820px);
    margin-inline: auto;
  }

  .concept-intro {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.85rem;
    align-items: start;
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

  .concept-intro p {
    margin: 0 0 0.12rem;
    color: var(--accent-strong);
    font: 750 0.5rem/1 var(--mono);
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .concept-intro h3 {
    margin: 0 0 0.25rem;
    color: var(--text);
    font: 800 clamp(1.08rem, 3vw, 1.4rem)/1.1 var(--display);
    letter-spacing: -0.035em;
  }

  .concept-intro div > span {
    color: var(--muted);
    font-size: 0.74rem;
  }

  .stage-shell {
    display: grid;
    grid-template-columns: 3.25rem minmax(0, 1fr) 3.25rem;
    min-height: 31rem;
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--accent) 38%, var(--line));
    border-radius: 24px;
    color: white;
    background:
      radial-gradient(circle at 50% 0%, color-mix(in srgb, var(--accent) 18%, transparent), transparent 33%),
      color-mix(in srgb, var(--surface-dark) 92%, black);
    box-shadow: 0 24px 52px rgba(5, 8, 20, 0.2);
  }

  .side-progress {
    position: relative;
    z-index: 2;
    display: flex;
    min-width: 0;
    flex-direction: column;
    align-items: center;
    gap: 0.55rem;
    padding: 1rem 0.45rem;
    border-color: rgba(255, 255, 255, 0.1);
    background: rgba(4, 7, 20, 0.42);
  }

  .side-left { border-right: 1px solid rgba(255, 255, 255, 0.1); }
  .side-right { border-left: 1px solid rgba(255, 255, 255, 0.1); }

  .side-progress small,
  .rail-label {
    color: rgba(255, 255, 255, 0.52);
    font: 750 0.46rem/1 var(--mono);
    letter-spacing: 0.08em;
  }

  .rail-track {
    position: relative;
    width: 0.55rem;
    flex: 1;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.045);
  }

  .rail-track i {
    position: absolute;
    right: 0;
    bottom: 0;
    left: 0;
    height: 40%;
    background: linear-gradient(0deg, var(--accent), var(--accent-2), #f6c84c);
    animation: rail-rise 800ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  .rail-track b {
    position: absolute;
    right: 50%;
    bottom: 40%;
    width: 1rem;
    height: 3px;
    border-radius: 999px;
    background: #f6c84c;
    box-shadow: 0 0 10px #f6c84c;
    transform: translate(50%, 50%);
  }

  @keyframes rail-rise { from { height: 0; } to { height: 40%; } }

  .rung-stack {
    display: flex;
    width: 100%;
    flex: 1;
    flex-direction: column-reverse;
    gap: 0.45rem;
    justify-content: center;
  }

  .rung-stack i {
    display: block;
    width: 100%;
    height: 2.6rem;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 5px;
    background: rgba(255, 255, 255, 0.035);
  }

  .rung-stack .rung-done {
    border-color: color-mix(in srgb, var(--accent-2) 48%, transparent);
    background: color-mix(in srgb, var(--accent) 42%, transparent);
  }

  .rung-stack .rung-active {
    border-color: #f6c84c;
    background: color-mix(in srgb, #f6c84c 16%, transparent);
    box-shadow: 0 0 12px color-mix(in srgb, #f6c84c 28%, transparent);
  }

  .pulse-track {
    display: flex;
    flex: 1;
    flex-direction: column-reverse;
    gap: 0.55rem;
    justify-content: center;
  }

  .pulse-track i {
    width: 0.48rem;
    height: 0.48rem;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.04);
  }

  .pulse-track .pulse-done { border-color: var(--accent-2); background: var(--accent); }
  .pulse-track .pulse-now { border-color: #f6c84c; background: #f6c84c; box-shadow: 0 0 12px #f6c84c; animation: dot-pulse 1.1s ease-in-out infinite; }
  @keyframes dot-pulse { 50% { transform: scale(1.65); } }

  .mini-game {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 0.75rem;
    padding: 1rem;
  }

  .mini-top,
  .mini-shortcuts,
  .mini-prompt,
  .mini-column header,
  .mini-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.7rem;
  }

  .mini-top { color: rgba(255, 255, 255, 0.46); font: 700 0.48rem/1 var(--mono); }

  .mini-prompt {
    min-height: 5rem;
    padding: 0.8rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 13px;
    background: rgba(8, 13, 31, 0.58);
  }

  .mini-prompt span,
  .mini-prompt small,
  .mini-column header span { color: var(--accent-2); font: 750 0.46rem/1 var(--mono); }
  .mini-prompt strong { font: 820 clamp(1.25rem, 4vw, 1.8rem)/1 var(--display); }

  .mini-column {
    display: grid;
    gap: 0.4rem;
    padding: 0.65rem;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 13px;
    background: rgba(255, 255, 255, 0.025);
  }

  .mini-column header { padding: 0.3rem 0.2rem 0.6rem; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
  .mini-column header strong { font-size: 0.72rem; }

  .mini-row {
    min-height: 3.5rem;
    padding: 0.55rem;
    border: 1px solid rgba(255, 255, 255, 0.09);
    border-radius: 7px;
    background: rgba(255, 255, 255, 0.025);
  }

  .mini-row b { color: var(--accent-2); font: 750 0.45rem/1 var(--mono); }
  .mini-row strong { flex: 1; font-size: 0.95rem; }
  .mini-row i { width: 45%; height: 2rem; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 6px; background: rgba(4, 7, 20, 0.55); font: 700 0.68rem/2rem var(--display); text-align: center; }
  .mini-row.active { border-color: var(--accent-2); background: color-mix(in srgb, var(--accent) 18%, transparent); }
  .mini-row.guide { border-color: color-mix(in srgb, #f6c84c 42%, transparent); color: #ffe39a; }
  .mini-shortcuts { margin-top: auto; color: rgba(255, 255, 255, 0.5); font: 700 0.5rem/1 var(--mono); }

  .stage-rungs { grid-template-columns: 4.4rem minmax(0, 1fr) 4.4rem; }
  .stage-pulse .side-progress { background: linear-gradient(180deg, color-mix(in srgb, var(--accent) 11%, rgba(4, 7, 20, 0.65)), rgba(4, 7, 20, 0.48)); }

  @media (max-width: 560px) {
    .stage-shell { grid-template-columns: 2.25rem minmax(0, 1fr) 2.25rem; min-height: 29rem; }
    .stage-rungs { grid-template-columns: 2.8rem minmax(0, 1fr) 2.8rem; }
    .side-progress { padding-inline: 0.3rem; }
    .rung-stack i { height: 2.15rem; }
    .mini-game { padding: 0.7rem; }
    .mini-prompt { align-items: flex-start; flex-direction: column; }
    .mini-row { display: grid; grid-template-columns: auto 1fr; }
    .mini-row i { grid-column: 2; width: 100%; }
    .mini-shortcuts { align-items: flex-start; flex-direction: column; }
  }

  @media (prefers-reduced-motion: reduce) {
    .rail-track i,
    .pulse-track .pulse-now { animation: none; }
  }
</style>
