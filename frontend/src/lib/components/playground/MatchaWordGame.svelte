<script lang="ts">
  import { onDestroy } from 'svelte';

  export let variant: 'vector' | 'bio' = 'vector';

  type Tone = 'success' | 'error';
  const waveCells = (() => {
    const output: Array<{ delay: string }> = [];
    for (let row = 0; row < 11; row += 1) {
      for (let column = 0; column < 22; column += 1) {
        const dx = column - 10.5;
        const dy = (row - 5) * 1.9;
        output.push({ delay: (Math.sqrt(dx * dx + dy * dy) * 0.032).toFixed(3) });
      }
    }
    return output;
  })();

  let answer = '';
  let tone: Tone | null = null;
  let sequence = 0;
  let message = 'Two tries available · quick-shot armed';
  let timer: ReturnType<typeof setTimeout> | null = null;

  export function pulse(nextTone: Tone): void {
    tone = nextTone;
    sequence += 1;
    message = nextTone === 'success'
      ? '✓ Correct · combo increased to ×5'
      : '× Not yet · last try · hint: s••••';
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => { tone = null; }, 1200);
  }

  function preview(nextTone: Tone): void {
    answer = nextTone === 'success' ? 'still' : 'steel';
    pulse(nextTone);
  }

  function grade(): void {
    pulse(answer.trim().toLocaleLowerCase() === 'still' ? 'success' : 'error');
  }

  onDestroy(() => {
    if (timer) clearTimeout(timer);
  });
</script>

<div class={`word-demo ${variant}`}>
  <div class="demo-toolbar">
    <span>LIVE ANSWER TEST</span>
    <div role="group" aria-label={`${variant} answer animation previews`}>
      <button type="button" on:click={() => preview('success')}>Preview right</button>
      <button type="button" on:click={() => preview('error')}>Preview wrong</button>
    </div>
  </div>

  <article class:error={tone === 'error'} class:success={tone === 'success'} class="word-card">
    <span class="rail left" aria-hidden="true"><i></i></span>
    <span class="rail right" aria-hidden="true"><i></i></span>

    {#key sequence}
      {#if tone}
        <div class={`answer-wave ${tone}`} aria-hidden="true">
          {#each waveCells as cell}
            <i class="wave-cell" style={`animation-delay:${cell.delay}s;`}></i>
          {/each}
        </div>
      {/if}
    {/key}

    <div class="game-inner">
      <header class="game-meta">
        <span>03 / 10</span><span>ES → EN</span><span>COMBO ×4</span>
      </header>

      <div class="prompt-wrap">
        <small>TRANSLATE THIS WORD</small>
        <strong lang="es">todavía</strong>
        <i>{variant === 'vector' ? 'TARGET_03' : 'SEED_03'}</i>
      </div>

      <form on:submit|preventDefault={grade}>
        <label for={`matcha-answer-${variant}`}>Your English answer</label>
        <div class="answer-shell">
          <input
            id={`matcha-answer-${variant}`}
            bind:value={answer}
            autocomplete="off"
            autocapitalize="off"
            spellcheck="false"
            placeholder="type your answer…"
          />
          <button type="submit" aria-label="Check answer">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h13M13 6l6 6-6 6" /></svg>
          </button>
          {#if tone}
            <span class="answer-mark" aria-hidden="true">{tone === 'success' ? '✓' : '×'}</span>
          {/if}
        </div>
        <p class:success-copy={tone === 'success'} class:error-copy={tone === 'error'} role="status" aria-live="polite">{message}</p>
      </form>

      <footer class="game-actions">
        <button type="button"><kbd>F2</kbd> Hint</button>
        <button type="button"><kbd>Alt+Enter</kbd> Skip</button>
        <button type="button"><kbd>Esc ×2</kbd> Finish</button>
      </footer>
    </div>
  </article>
</div>

<style>
  .word-demo { display: grid; gap: .6rem; }
  .demo-toolbar { display: flex; min-height: 44px; justify-content: space-between; gap: 1rem; align-items: center; font: 400 1rem/1 "VT323", monospace; }
  .demo-toolbar > div { display: flex; gap: .45rem; }
  .demo-toolbar button { min-height: 44px; padding: .55rem .75rem; border: 1px solid var(--m-ink, #13281e); color: var(--m-ink, #13281e); background: var(--m-panel, #f0f4ce); font: 650 .7rem/1 "Figtree", sans-serif; cursor: pointer; touch-action: manipulation; }
  .demo-toolbar button:hover { color: var(--m-panel, #f0f4ce); background: var(--m-core, #236249); }
  .demo-toolbar button:focus-visible { outline: 3px solid var(--m-spark, #ff4c91); outline-offset: 2px; }

  .word-card { position: relative; min-height: 470px; overflow: hidden; border: 2px solid var(--m-ink, #13281e); color: var(--m-ink, #13281e); background: var(--m-panel, #f0f4ce); }
  .game-inner { position: relative; z-index: 2; display: grid; min-height: 470px; align-content: center; padding: clamp(1.2rem, 4vw, 2.5rem); }
  .game-meta { display: flex; justify-content: space-between; gap: .8rem; font: 400 1rem/1 "VT323", monospace; }
  .prompt-wrap { position: relative; display: grid; justify-items: center; margin: 3rem 0 2.3rem; }
  .prompt-wrap small { font: 600 .64rem/1 "Chakra Petch", sans-serif; letter-spacing: .12em; }
  .prompt-wrap strong { margin-top: .55rem; font: 700 clamp(2.8rem, 7vw, 5rem)/.9 "Chakra Petch", sans-serif; letter-spacing: -.065em; }
  .prompt-wrap > i { position: absolute; right: 0; bottom: .3rem; color: color-mix(in srgb, var(--m-core, #236249) 56%, transparent); font: 400 1rem/1 "VT323", monospace; font-style: normal; }
  form { width: min(100%, 460px); margin-inline: auto; }
  form > label { display: block; margin-bottom: .35rem; font: 600 .65rem/1 "Chakra Petch", sans-serif; }
  .answer-shell { position: relative; display: grid; grid-template-columns: minmax(0, 1fr) 48px; align-items: stretch; }
  input { width: 100%; min-width: 0; min-height: 52px; box-sizing: border-box; padding: .75rem 3rem .75rem .8rem; border: 0; border-bottom: 2px solid var(--m-core, #236249); border-radius: 0; outline: 0; color: var(--m-ink, #13281e); background: color-mix(in srgb, var(--m-field, #dce8a6) 50%, transparent); font: 600 1.1rem/1 "Figtree", sans-serif; text-align: center; }
  input:focus { box-shadow: inset 0 -4px 0 color-mix(in srgb, var(--m-spark, #ff4c91) 65%, transparent); }
  .answer-shell > button { display: grid; width: 48px; min-height: 48px; place-items: center; border: 0; color: var(--m-panel, #f0f4ce); background: var(--m-ink, #13281e); cursor: pointer; }
  .answer-shell > button:hover { background: var(--m-core, #236249); }
  .answer-shell > button:focus-visible { outline: 3px solid var(--m-spark, #ff4c91); outline-offset: 2px; }
  .answer-shell svg { width: 20px; fill: none; stroke: currentColor; stroke-width: 2; }
  .answer-mark { position: absolute; right: 57px; top: 50%; display: grid; width: 26px; height: 26px; margin-top: -13px; place-items: center; border: 2px solid currentColor; border-radius: 50%; font: 700 .85rem/1 "Chakra Petch", sans-serif; animation: mark-in 260ms cubic-bezier(.18,.86,.28,1.2) both; }
  @keyframes mark-in { from { opacity: 0; transform: scale(.2) rotate(-18deg); } to { opacity: 1; transform: scale(1) rotate(0); } }
  form > p { min-height: 22px; margin: .65rem 0 0; font: 600 .78rem/1.4 "Figtree", sans-serif; text-align: center; }
  .success-copy { color: var(--m-core, #236249); }
  .error-copy { color: color-mix(in srgb, var(--m-spark, #ff4c91) 62%, var(--m-ink, #13281e)); }
  .game-actions { display: flex; justify-content: center; gap: .6rem; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid color-mix(in srgb, var(--m-ink, #13281e) 30%, transparent); }
  .game-actions button { min-height: 44px; padding: .4rem .6rem; border: 0; color: color-mix(in srgb, var(--m-ink, #13281e) 72%, transparent); background: transparent; font: 600 .68rem/1 "Figtree", sans-serif; cursor: pointer; }
  kbd { padding: .22rem .35rem; border: 1px solid currentColor; font: 400 .9rem/1 "VT323", monospace; }

  .rail { position: absolute; z-index: 3; top: 12px; bottom: 12px; width: 5px; background: color-mix(in srgb, var(--m-core, #236249) 16%, transparent); }
  .rail.left { left: 9px; }
  .rail.right { right: 9px; }
  .rail i { position: absolute; right: 0; bottom: 0; left: 0; height: 43%; background: var(--m-core, #236249); }

  .answer-wave { position: absolute; z-index: 1; inset: 0; display: grid; grid-template-columns: repeat(22, 1fr); grid-template-rows: repeat(11, 1fr); gap: 2px; padding: 3px; pointer-events: none; mask-image: radial-gradient(ellipse 95% 95% at 50% 50%, rgba(0,0,0,.06),rgba(0,0,0,.22) 55%,#000 97%); }
  .wave-cell { display: block; background: var(--wave-color); transform-origin: center; animation-duration: 450ms; animation-timing-function: ease-out; animation-fill-mode: both; }
  .answer-wave.success { --wave-color: var(--m-core, #236249); }
  .answer-wave.error { --wave-color: var(--m-spark, #ff4c91); }

  .vector .word-card { clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 18px 100%, 0 calc(100% - 18px)); }
  .vector .wave-cell { clip-path: polygon(0 0, 78% 0, 100% 25%, 100% 100%, 22% 100%, 0 75%); animation-name: vector-wave; }
  @keyframes vector-wave { 0%,100% { opacity: 0; transform: scaleX(.25); } 42% { opacity: .66; transform: scaleX(1); } }
  .vector.error .prompt-wrap strong { animation: vector-jolt 420ms ease-out both; }
  @keyframes vector-jolt { 0%,100% { transform: translateX(0); } 24% { transform: translateX(-8px) skewX(-7deg); } 52% { transform: translateX(7px) skewX(5deg); } 74% { transform: translateX(-3px); } }

  .bio .word-card { border-radius: 28px; }
  .bio .rail { width: 7px; border-radius: 999px; }
  .bio .rail i { border-radius: 999px; }
  .bio .wave-cell { border-radius: 50%; animation-name: bio-wave; }
  @keyframes bio-wave { 0%,100% { opacity: 0; transform: scale(.08); } 42% { opacity: .62; transform: scale(.8); } }
  .bio.error .prompt-wrap strong { animation: bio-wobble 460ms cubic-bezier(.2,.8,.2,1) both; }
  @keyframes bio-wobble { 0%,100% { transform: rotate(0) scale(1); } 30% { transform: rotate(-2deg) scale(.97); } 62% { transform: rotate(2deg) scale(1.02); } }

  @media (max-width: 520px) {
    .demo-toolbar { align-items: stretch; flex-direction: column; }
    .demo-toolbar > div { display: grid; grid-template-columns: 1fr 1fr; }
    .word-card, .game-inner { min-height: 430px; }
    .game-inner { padding: 1.2rem; }
    .game-actions { justify-content: flex-start; overflow-x: auto; }
    .game-actions button { flex: 0 0 auto; }
  }

  @media (prefers-reduced-motion: reduce) {
    .wave-cell, .answer-mark, .vector.error .prompt-wrap strong, .bio.error .prompt-wrap strong { animation-duration: 1ms; animation-delay: 0ms !important; }
  }
</style>
