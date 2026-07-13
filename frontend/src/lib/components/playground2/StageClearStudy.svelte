<script lang="ts">
  import { onMount } from 'svelte';

  // Study 04 — the arcade Stage Clear moment. 'current' is the production
  // screen; 'rank' adds a grade stamp + counting score; 'scoreboard' turns
  // results into a staggered high-score table. Both demos can be replayed.
  export let variant: 'current' | 'rank' | 'scoreboard';
  export let index = 'C1';
  export let kicker = '';
  export let title = '';
  export let description = '';

  const SCORE = 87;
  const TOTAL = 10;
  const OK = 9;

  let runId = 0;
  let shownScore = variant === 'rank' ? 0 : SCORE;
  let rafId = 0;
  let reduceMotion = false;

  function countUp(): void {
    cancelAnimationFrame(rafId);
    if (reduceMotion) {
      shownScore = SCORE;
      return;
    }
    shownScore = 0;
    const start = performance.now();
    const duration = 900;
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      shownScore = Math.round(eased * SCORE);
      if (t < 1) {
        rafId = requestAnimationFrame(step);
      }
    };
    rafId = requestAnimationFrame(step);
  }

  function replay(): void {
    runId += 1;
    if (variant === 'rank') {
      countUp();
    }
  }

  onMount(() => {
    reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (variant === 'rank') {
      countUp();
    }
    return () => cancelAnimationFrame(rafId);
  });
</script>

<article class="clear-study" data-variant={variant}>
  <header class="concept-intro" class:intro-current={variant === 'current'}>
    <span class="concept-number">{index}</span>
    <div><p>{kicker}</p><h3>{title}</h3><span>{description}</span></div>
  </header>

  <div class="stage" class:stage-current={variant === 'current'}>
    {#if variant !== 'current'}
      <button type="button" class="replay-demo" on:click={replay}>↻ Replay demo</button>
    {/if}

    {#if variant === 'current'}
      <!-- ======= CURRENT PRODUCTION SCREEN ======= -->
      <div class="cur-clear">
        <h4 class="cur-title">STAGE CLEAR ★</h4>
        <p class="cur-score">Score 87% · 9/10 verbs · Best combo ×9</p>
        <p class="cur-gg">GG, VERBSMITH</p>
        <div class="cur-dots" aria-hidden="true">
          {#each Array(TOTAL) as _, i}
            <span class:cur-dot-ok={i < OK}></span>
          {/each}
        </div>
        <div class="cur-actions">
          <button type="button" class="cur-primary">▶ Replay <kbd>Enter</kbd></button>
          <button type="button" class="cur-secondary">Menu <kbd>Esc</kbd></button>
        </div>
      </div>
    {:else if variant === 'rank'}
      <!-- ======= OPTION A — rank stamp + counting score ======= -->
      {#key runId}
        <div class="rk-clear">
          <div class="rk-head">
            <div class="rk-stamp" aria-label={`Rank A, score ${SCORE} percent`}>
              <span class="rk-ring" aria-hidden="true"></span>
              <strong>A</strong>
            </div>
            <div class="rk-readout">
              <span>Stage clear</span>
              <strong class="rk-count">{shownScore}%</strong>
              <small>9/10 verbs · best combo ×9</small>
            </div>
          </div>
          <div class="rk-bar" role="img" aria-label="9 of 10 verbs correct">
            {#each Array(TOTAL) as _, i}
              <span class:rk-seg-ok={i < OK} style={`animation-delay: ${0.55 + i * 0.05}s;`}></span>
            {/each}
          </div>
          <div class="rk-actions">
            <button type="button" class="rk-primary">▶ Replay <kbd>Enter</kbd></button>
            <button type="button" class="rk-secondary">Menu <kbd>Esc</kbd></button>
          </div>
        </div>
      {/key}
    {:else}
      <!-- ======= OPTION B — high-score board ======= -->
      {#key runId}
        <div class="sb-clear">
          <div class="sb-tab"><span>RESULTS</span><i aria-hidden="true"></i><span class="sb-stage">STAGE 04 · FR</span></div>
          <div class="sb-rows">
            <div class="sb-row" style="--d: 0.1s;"><span>Score</span><i aria-hidden="true"></i><strong>870 <small>pts</small></strong></div>
            <div class="sb-row" style="--d: 0.16s;"><span>Accuracy</span><i aria-hidden="true"></i><strong>87%</strong></div>
            <div class="sb-row" style="--d: 0.22s;">
              <span>Best combo</span><i aria-hidden="true"></i>
              <strong>×9 <em class="sb-best">NEW BEST!</em></strong>
            </div>
            <div class="sb-row" style="--d: 0.28s;"><span>Verbs</span><i aria-hidden="true"></i><strong>9/10</strong></div>
          </div>
          <p class="sb-press" aria-hidden="true">PRESS ENTER TO REPLAY <b>▮</b></p>
          <div class="sb-actions">
            <button type="button" class="sb-primary">▶ Replay <kbd>Enter</kbd></button>
            <button type="button" class="sb-secondary">Menu <kbd>Esc</kbd></button>
          </div>
        </div>
      {/key}
    {/if}
  </div>

  {#if variant === 'rank'}
    <ul class="study-notes">
      <li>A letter grade (S / A / B / C) gives the run a verdict worth chasing — the stamp lands first, then the score counts up in ~0.9s with tabular digits.</li>
      <li>The dot row becomes a segment bar that fills left to right, 50ms per segment — same data, more payoff.</li>
      <li>With reduced motion enabled everything appears settled: no count-up, no stamps, same information.</li>
    </ul>
  {:else if variant === 'scoreboard'}
    <ul class="study-notes">
      <li>Results read like a cabinet high-score table: dotted leaders, tabular numerals, one row per stat sliding in at 60ms stagger.</li>
      <li>Records get celebrated in place — the NEW BEST! tag flashes on the combo row instead of a generic toast.</li>
      <li>The blinking PRESS ENTER line replaces the GG copy; buttons stay for pointer users.</li>
    </ul>
  {/if}
</article>

<style>
  .clear-study { width: min(100%, 760px); margin-inline: auto; }
  .concept-intro { display: grid; grid-template-columns: auto 1fr; gap: 0.85rem; align-items: start; margin-bottom: 0.8rem; padding-inline: 0.25rem; }
  .concept-number { display: grid; width: 2.45rem; height: 2.45rem; place-items: center; border: 1px solid var(--line-strong); border-radius: 13px; color: var(--accent-strong); background: var(--accent-soft); font: 800 0.7rem/1 var(--mono); }
  .intro-current .concept-number { color: var(--muted); background: transparent; border-style: dashed; }
  .concept-intro p { margin: 0 0 0.12rem; color: var(--accent-strong); font: 750 0.62rem/1 var(--mono); letter-spacing: 0.12em; text-transform: uppercase; }
  .intro-current p { color: var(--muted); }
  .concept-intro h3 { margin: 0 0 0.25rem; color: var(--text); font: 800 clamp(1.08rem, 3vw, 1.4rem)/1.15 var(--display); letter-spacing: -0.035em; }
  .concept-intro div > span { color: var(--muted); font-size: 0.82rem; line-height: 1.45; }

  .stage {
    position: relative;
    padding: clamp(1.1rem, 4vw, 1.8rem);
    border: 1px solid var(--line-strong);
    border-radius: 20px;
    text-align: center;
    background: color-mix(in srgb, var(--surface-strong) 92%, transparent);
    box-shadow: var(--shadow);
    overflow: hidden;
  }
  .stage-current { border-style: dashed; }

  .replay-demo {
    position: absolute;
    top: 0.7rem;
    right: 0.7rem;
    z-index: 2;
    padding: 0.35rem 0.7rem;
    border: 1px solid var(--line);
    border-radius: 999px;
    color: var(--muted);
    background: color-mix(in srgb, var(--surface-strong) 90%, transparent);
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: 160ms ease;
  }
  .replay-demo:hover { color: var(--text); border-color: color-mix(in srgb, var(--accent) 45%, var(--line)); }

  button { cursor: pointer; font-family: inherit; }
  kbd { display: inline-block; padding: 0 7px; border: 1px solid var(--line-strong); border-bottom-width: 3px; border-radius: 6px; color: var(--muted); font: 600 0.72rem/1.5 var(--mono); vertical-align: middle; }

  .study-notes { display: grid; gap: 0.3rem; margin: 0.7rem 0 0; padding-left: 1.1rem; }
  .study-notes li { color: var(--muted); font-size: 0.82rem; line-height: 1.5; }
  .study-notes li::marker { color: var(--accent-strong); }

  /* ===== CURRENT ===== */
  .cur-clear { display: grid; gap: 0.4rem; justify-items: center; }
  .cur-title { margin: 0; color: var(--text); font: 800 1.5rem/1.3 var(--display); text-shadow: 0 0 18px color-mix(in srgb, var(--accent) 100%, transparent); }
  .cur-score { margin: 0.35rem 0 0; color: var(--accent); font: 600 1.15rem/1.4 var(--mono); }
  .cur-gg { margin: 0; color: var(--muted); font: 400 1rem/1.4 var(--mono); letter-spacing: 1px; }
  .cur-dots { display: flex; justify-content: center; flex-wrap: wrap; gap: 8px; margin-top: 0.6rem; }
  .cur-dots span { width: 12px; height: 12px; border-radius: 2px; border: 2px solid color-mix(in srgb, var(--danger) 55%, transparent); }
  .cur-dots .cur-dot-ok { background: var(--accent); border-color: var(--accent); }
  .cur-actions { display: flex; justify-content: center; gap: 14px; margin-top: 1.1rem; flex-wrap: wrap; }
  .cur-primary { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1.25rem; border: 1px solid color-mix(in srgb, var(--accent) 45%, transparent); border-radius: 12px; color: var(--accent-strong); background: var(--accent-soft); font-family: var(--display); font-weight: 600; }
  .cur-secondary { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1.25rem; border: 1px solid var(--line); border-radius: 999px; color: var(--text); background: color-mix(in srgb, var(--surface-strong) 90%, transparent); font-family: var(--display); font-weight: 600; }

  /* ===== OPTION A — rank stamp ===== */
  .rk-clear { display: grid; gap: 1.1rem; justify-items: center; }
  .rk-head { display: flex; align-items: center; gap: 1.4rem; }

  .rk-stamp {
    position: relative;
    display: grid;
    place-items: center;
    width: 6rem;
    height: 6rem;
    border: 3px solid var(--xp);
    border-radius: 18px;
    background: color-mix(in srgb, var(--xp) 10%, transparent);
    box-shadow: 0 0 26px color-mix(in srgb, var(--xp) 35%, transparent);
    animation: rk-stamp-in 0.45s cubic-bezier(0.2, 1.4, 0.4, 1) both;
  }
  .rk-stamp strong { color: var(--xp); font: 800 3rem/1 var(--display); text-shadow: 0 0 18px color-mix(in srgb, var(--xp) 60%, transparent); }
  .rk-ring { position: absolute; inset: -3px; border: 3px solid var(--xp); border-radius: 18px; opacity: 0; animation: rk-ring 0.9s 0.3s ease-out both; }
  @keyframes rk-stamp-in { 0% { opacity: 0; transform: scale(2.1) rotate(-8deg); } 100% { opacity: 1; transform: scale(1) rotate(0deg); } }
  @keyframes rk-ring { 0% { opacity: 0.8; transform: scale(1); } 100% { opacity: 0; transform: scale(1.55); } }

  .rk-readout { display: grid; gap: 0.2rem; justify-items: start; text-align: left; }
  .rk-readout > span { color: var(--muted); font: 700 0.8rem/1 var(--mono); letter-spacing: 0.18em; text-transform: uppercase; }
  .rk-count { color: var(--text); font: 800 clamp(2.3rem, 7vw, 3.2rem)/1 var(--mono); font-variant-numeric: tabular-nums; }
  .rk-readout small { color: var(--muted); font-size: 0.88rem; }

  .rk-bar { display: flex; gap: 5px; width: min(100%, 22rem); }
  .rk-bar span { flex: 1; height: 0.8rem; border-radius: 4px; border: 1px solid color-mix(in srgb, var(--danger) 45%, transparent); background: color-mix(in srgb, var(--danger) 8%, transparent); }
  .rk-bar .rk-seg-ok { border-color: var(--success); background: color-mix(in srgb, var(--success) 65%, transparent); box-shadow: 0 0 10px color-mix(in srgb, var(--success) 35%, transparent); animation: rk-seg 0.3s ease-out both; animation-delay: inherit; }
  @keyframes rk-seg { 0% { opacity: 0.2; transform: scaleY(0.4); } 100% { opacity: 1; transform: scaleY(1); } }

  .rk-actions { display: flex; gap: 14px; flex-wrap: wrap; justify-content: center; animation: rk-rise 0.4s 0.85s ease-out both; }
  @keyframes rk-rise { 0% { opacity: 0; transform: translateY(0.6rem); } 100% { opacity: 1; transform: translateY(0); } }
  .rk-primary { display: inline-flex; align-items: center; gap: 0.5rem; min-height: 3rem; padding: 0.7rem 1.4rem; border: 1px solid color-mix(in srgb, var(--accent) 55%, transparent); border-radius: 12px; color: var(--accent-strong); background: var(--accent-soft); font-size: 1rem; font-weight: 700; }
  .rk-secondary { display: inline-flex; align-items: center; gap: 0.5rem; min-height: 3rem; padding: 0.7rem 1.4rem; border: 1px solid var(--line); border-radius: 12px; color: var(--text); background: color-mix(in srgb, var(--surface-strong) 90%, transparent); font-size: 1rem; font-weight: 600; }

  /* ===== OPTION B — high-score board ===== */
  .sb-clear { display: grid; gap: 1rem; justify-items: center; }
  .sb-tab { display: flex; align-items: center; gap: 0.8rem; width: min(100%, 24rem); color: var(--accent-strong); font: 700 0.82rem/1 var(--mono); letter-spacing: 0.2em; }
  .sb-tab i { flex: 1; height: 1px; background: color-mix(in srgb, var(--accent) 35%, var(--line)); }
  .sb-stage { color: var(--muted); letter-spacing: 0.12em; }

  .sb-rows { display: grid; gap: 0.5rem; width: min(100%, 24rem); }
  .sb-row {
    display: flex;
    align-items: baseline;
    gap: 0.7rem;
    padding: 0.55rem 0.2rem;
    animation: sb-slide 0.35s ease-out both;
    animation-delay: var(--d, 0s);
  }
  @keyframes sb-slide { 0% { opacity: 0; transform: translateX(-1.2rem); } 100% { opacity: 1; transform: translateX(0); } }
  .sb-row > span { color: var(--muted); font: 600 0.88rem/1 var(--mono); letter-spacing: 0.1em; text-transform: uppercase; white-space: nowrap; }
  .sb-row i { flex: 1; border-bottom: 2px dotted color-mix(in srgb, var(--muted) 45%, transparent); transform: translateY(-0.2rem); }
  .sb-row strong { display: inline-flex; align-items: baseline; gap: 0.5rem; color: var(--text); font: 700 1.3rem/1 var(--mono); font-variant-numeric: tabular-nums; }
  .sb-row strong small { color: var(--muted); font-size: 0.8rem; }
  .sb-best { padding: 0.18rem 0.45rem; border-radius: 6px; color: #191300; background: var(--xp); font: 800 0.66rem/1 var(--ui); font-style: normal; letter-spacing: 0.06em; animation: sb-best 1.2s step-end infinite; }
  @keyframes sb-best { 0%, 60% { opacity: 1; } 61%, 100% { opacity: 0.35; } }

  .sb-press { margin: 0.2rem 0 0; color: var(--accent-strong); font: 700 0.82rem/1.4 var(--mono); letter-spacing: 0.18em; }
  .sb-press b { animation: sb-cursor 1s step-end infinite; }
  @keyframes sb-cursor { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }

  .sb-actions { display: flex; gap: 14px; flex-wrap: wrap; justify-content: center; animation: sb-slide 0.35s 0.4s ease-out both; }
  .sb-primary { display: inline-flex; align-items: center; gap: 0.5rem; min-height: 3rem; padding: 0.7rem 1.4rem; border: 1px solid color-mix(in srgb, var(--accent) 55%, transparent); border-radius: 12px; color: var(--accent-strong); background: var(--accent-soft); font-size: 1rem; font-weight: 700; }
  .sb-secondary { display: inline-flex; align-items: center; gap: 0.5rem; min-height: 3rem; padding: 0.7rem 1.4rem; border: 1px solid var(--line); border-radius: 12px; color: var(--text); background: color-mix(in srgb, var(--surface-strong) 90%, transparent); font-size: 1rem; font-weight: 600; }

  @media (prefers-reduced-motion: reduce) {
    .rk-stamp, .rk-bar .rk-seg-ok, .rk-actions, .sb-row, .sb-actions { animation: none; }
    .sb-best, .sb-press b { animation: none; }
  }

  :global(html[data-theme='arcade']) .rk-count { font-size: clamp(2.6rem, 7vw, 3.6rem); }
  :global(html[data-theme='arcade']) .rk-stamp strong { font-size: 2.2rem; }

  @media (max-width: 560px) {
    .rk-head { flex-direction: column; gap: 0.8rem; }
    .rk-readout { justify-items: center; text-align: center; }
  }
</style>
