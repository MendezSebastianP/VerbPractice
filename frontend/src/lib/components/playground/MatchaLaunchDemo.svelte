<script lang="ts">
  import { onDestroy } from 'svelte';

  export let variant: 'vector' | 'bio' = 'vector';

  const cells = (() => {
    const output: Array<{ delay: string; color: number }> = [];
    for (let row = 0; row < 10; row += 1) {
      for (let column = 0; column < 16; column += 1) {
        const delay = variant === 'vector'
          ? column * 0.022 + Math.abs(row - 4.5) * 0.012
          : Math.sqrt((column - 7.5) ** 2 + ((row - 4.5) * 1.6) ** 2) * 0.045;
        output.push({ delay: delay.toFixed(3), color: (column + row) % 3 });
      }
    }
    return output;
  })();

  let overlay = false;
  let fading = false;
  let session = false;
  let running = false;
  let sequence = 0;
  const timers: ReturnType<typeof setTimeout>[] = [];

  function begin(): void {
    running = true;
    overlay = true;
    fading = false;
    sequence += 1;
    timers.push(setTimeout(() => {
      session = true;
      fading = true;
    }, 700));
    timers.push(setTimeout(() => {
      overlay = false;
      fading = false;
      running = false;
    }, 1300));
  }

  export function run(): void {
    if (running) return;
    if (session) {
      session = false;
      timers.push(setTimeout(begin, 100));
    } else {
      begin();
    }
  }

  onDestroy(() => timers.forEach(clearTimeout));
</script>

<div class={`launch-demo ${variant}`} aria-live="polite">
  <div class="launch-status">
    <span>{running ? 'TRANSITION RUNNING' : session ? 'SESSION READY' : 'SETUP READY'}</span>
    <i>{variant === 'vector' ? '700MS_COVER / 600MS_REVEAL' : '160 BIO-CELLS / SAME CLOCK'}</i>
  </div>

  <div class="launch-screen">
    <div class="screen-view setup-view" class:hidden={session}>
      <span class="screen-meta">DAILY STAGE · ES / EN</span>
      <strong>WORD RUSH</strong>
      <span class="route"><i>Spanish</i><b>→</b><i>English</i></span>
    </div>
    <div class="screen-view session-view" class:visible={session}>
      <span class="screen-meta">01 / 10 · ES → EN · COMBO ×0</span>
      <strong lang="es">verdad</strong>
      <span class="answer-line">type your answer</span>
    </div>

    {#key sequence}
      {#if overlay}
        <div class="launch-cells" class:fading aria-hidden="true">
          {#each cells as cell}
            <i class={`cell c${cell.color}`} style={`animation-delay:${cell.delay}s;`}></i>
          {/each}
        </div>
      {/if}
    {/key}
  </div>
</div>

<style>
  .launch-demo { display: grid; width: 100%; gap: .55rem; }
  .launch-status { display: flex; justify-content: space-between; gap: 1rem; min-height: 32px; align-items: center; font: 400 1rem/1 "VT323", monospace; }
  .launch-status i { color: color-mix(in srgb, var(--m-ink, #13281e) 62%, transparent); font-style: normal; }
  .launch-screen { position: relative; min-height: 250px; overflow: hidden; border: 2px solid var(--m-ink, #13281e); background: var(--m-panel, #f0f4ce); }
  .screen-view { position: absolute; inset: 0; display: grid; place-content: center; justify-items: center; gap: 1rem; padding: 1.25rem; transition: opacity 140ms ease-out, transform 180ms ease-out; }
  .screen-view.hidden { opacity: 0; transform: scale(.98); }
  .session-view { opacity: 0; transform: scale(1.02); }
  .session-view.visible { opacity: 1; transform: scale(1); }
  .screen-meta { font: 400 1rem/1 "VT323", monospace; letter-spacing: .04em; }
  .screen-view > strong { font: 700 clamp(2rem, 5vw, 3.8rem)/.88 "Chakra Petch", sans-serif; letter-spacing: -.06em; }
  .route { display: grid; grid-template-columns: 1fr auto 1fr; gap: .8rem; align-items: center; min-width: min(100%, 320px); }
  .route i { padding: .55rem; border: 1px solid var(--m-core, #236249); font: 600 .72rem/1 "Figtree", sans-serif; font-style: normal; text-align: center; }
  .route b { color: var(--m-spark, #ff4c91); }
  .answer-line { min-width: min(82%, 330px); padding: .6rem; border-bottom: 2px solid var(--m-core, #236249); color: color-mix(in srgb, var(--m-ink, #13281e) 56%, transparent); font: 500 .8rem/1 "Figtree", sans-serif; text-align: center; }

  .launch-cells { position: absolute; z-index: 4; inset: 0; display: grid; grid-template-columns: repeat(16, 1fr); grid-template-rows: repeat(10, 1fr); opacity: 1; transition: opacity 600ms ease-in; pointer-events: none; }
  .launch-cells.fading { opacity: 0; }
  .cell { display: block; background: var(--cell-color); animation-duration: 320ms; animation-timing-function: cubic-bezier(.2,.8,.2,1); animation-fill-mode: both; transform-origin: center; }
  .c0 { --cell-color: var(--m-core, #236249); }
  .c1 { --cell-color: var(--m-ink, #13281e); }
  .c2 { --cell-color: var(--m-spark, #ff4c91); }

  .vector .launch-screen { clip-path: polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 16px 100%, 0 calc(100% - 16px)); }
  .vector .launch-cells { gap: 0; background: transparent; }
  .vector .cell { transform-origin: left center; animation-name: vector-cover; }
  @keyframes vector-cover { from { opacity: 0; transform: scaleX(0); } to { opacity: 1; transform: scaleX(1); } }

  .bio .launch-screen { border-radius: 26px; }
  .bio .launch-cells { gap: 2px; padding: 3px; background: var(--m-field, #dce8a6); }
  .bio .cell { border-radius: 50%; animation-name: bio-cover; }
  @keyframes bio-cover { from { opacity: 0; transform: scale(.08) rotate(-20deg); } to { opacity: 1; transform: scale(1.12) rotate(0); } }

  @media (max-width: 520px) {
    .launch-status { align-items: flex-start; flex-direction: column; gap: .2rem; }
    .launch-screen { min-height: 220px; }
  }

  @media (prefers-reduced-motion: reduce) {
    .screen-view, .launch-cells { transition-duration: 1ms; }
    .cell { animation-duration: 1ms; animation-delay: 0ms !important; }
  }
</style>
