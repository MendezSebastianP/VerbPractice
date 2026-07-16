<script lang="ts">
  import { createEventDispatcher, onDestroy } from 'svelte';

  export let variant: 'vector' | 'bio' = 'vector';
  export let disabled = false;
  export let label = 'PLAY';

  const cols = 10;
  const rows = 4;
  const cell = 22;
  const gap = 6;
  const count = cols * rows;
  const dispatch = createEventDispatcher<{ fire: void }>();

  let gridEl: HTMLElement | null = null;
  let fired = false;
  let timer: ReturnType<typeof setTimeout> | null = null;

  function cellEls(): HTMLElement[] {
    return gridEl ? Array.from(gridEl.children) as HTMLElement[] : [];
  }

  function resetCells(): void {
    for (const item of cellEls()) {
      item.style.removeProperty('--cell-opacity');
      item.style.removeProperty('--cell-scale');
      item.style.removeProperty('--fire-delay');
    }
  }

  function handleMove(event: MouseEvent): void {
    if (fired) return;
    const items = cellEls();
    const rects = items.map((item) => item.getBoundingClientRect());
    const reach = variant === 'vector' ? 92 : 108;
    const heat = rects.map((rect) => {
      const dx = event.clientX - (rect.left + rect.width / 2);
      const dy = event.clientY - (rect.top + rect.height / 2);
      return Math.max(0, 1 - Math.sqrt(dx * dx + dy * dy) / reach);
    });

    for (const [index, item] of items.entries()) {
      item.style.setProperty('--cell-opacity', (0.18 + heat[index] * 0.82).toFixed(3));
      item.style.setProperty('--cell-scale', (0.72 + heat[index] * 0.28).toFixed(3));
    }
  }

  function handleLeave(): void {
    if (!fired) resetCells();
  }

  export function fire(): void {
    if (disabled || fired) return;
    fired = true;
    for (const [index, item] of cellEls().entries()) {
      const row = Math.floor(index / cols);
      const column = index % cols;
      const delay = variant === 'vector'
        ? (column * 0.022 + row * 0.014)
        : (Math.sqrt((column - 4.5) ** 2 + ((row - 1.5) * 1.65) ** 2) * 0.035);
      item.style.setProperty('--fire-delay', `${delay.toFixed(3)}s`);
    }
    dispatch('fire');
    timer = setTimeout(reset, 700);
  }

  export function reset(): void {
    fired = false;
    resetCells();
  }

  onDestroy(() => {
    if (timer) clearTimeout(timer);
  });
</script>

<button
  class={`matcha-play ${variant}`}
  class:fired
  type="button"
  {disabled}
  aria-label={`${label} · ${variant === 'vector' ? 'Vector Grid' : 'Bio Pulse'} alternative`}
  on:click={fire}
  on:mousemove={handleMove}
  on:mouseleave={handleLeave}
>
  <span class="cell-grid" bind:this={gridEl} aria-hidden="true">
    {#each Array(count) as _, index (index)}
      <span class="cell"></span>
    {/each}
  </span>
  <span class="play-label">
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l11-6.5z" /></svg>
    <b>{label}</b>
    <i>{variant === 'vector' ? 'RUN_01' : 'GROW_01'}</i>
  </span>
</button>

<style>
  .matcha-play {
    position: relative;
    display: block;
    width: 274px;
    height: 106px;
    max-width: 100%;
    padding: 0;
    overflow: hidden;
    border: 0;
    color: var(--m-ink, #13281e);
    background: transparent;
    cursor: pointer;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
  }

  .matcha-play:disabled { opacity: .45; cursor: not-allowed; }
  .matcha-play:focus-visible { outline: 4px solid var(--m-spark, #ff4c91); outline-offset: 4px; }
  .cell-grid { position: absolute; inset: 0; display: grid; grid-template-columns: repeat(10, 22px); gap: 6px; }

  .cell {
    --cell-opacity: .18;
    --cell-scale: .72;
    --fire-delay: 0s;
    display: block;
    width: 22px;
    height: 22px;
    box-sizing: border-box;
    opacity: var(--cell-opacity);
    transform: scale(var(--cell-scale));
    transform-origin: center;
    transition: opacity 110ms ease-out, transform 110ms ease-out;
  }

  .play-label {
    position: absolute;
    z-index: 2;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: .45rem;
    pointer-events: none;
  }

  .play-label svg { width: 15px; height: 15px; fill: var(--m-spark, #ff4c91); }
  .play-label b { font: 700 1rem/1 "Chakra Petch", sans-serif; letter-spacing: .14em; }
  .play-label i { position: absolute; right: 10px; bottom: 8px; font: 400 .9rem/1 "VT323", monospace; font-style: normal; }

  .vector .cell {
    border: 1px solid var(--m-core, #236249);
    background: var(--m-core, #236249);
    clip-path: polygon(0 0, 82% 0, 100% 25%, 100% 100%, 18% 100%, 0 75%);
  }

  .vector .play-label { background: linear-gradient(90deg, transparent 10%, color-mix(in srgb, var(--m-panel, #f0f4ce) 88%, transparent) 30% 70%, transparent 90%); }
  .vector.fired .cell { animation: vector-fire 380ms cubic-bezier(.2,.8,.2,1) var(--fire-delay) both; }

  @keyframes vector-fire {
    0% { opacity: .18; transform: scale(.72) skewX(0); }
    45% { opacity: 1; transform: scale(1) skewX(-10deg); }
    100% { opacity: .28; transform: scale(.84) skewX(0); }
  }

  .bio::before {
    content: '';
    position: absolute;
    inset: 0;
    border: 2px solid var(--m-core, #236249);
    border-radius: 53px;
    background: color-mix(in srgb, var(--m-panel, #f0f4ce) 78%, transparent);
  }

  .bio .cell {
    border: 1px solid var(--m-core, #236249);
    border-radius: 50%;
    background: var(--m-spark, #ff4c91);
  }

  .bio .play-label b { padding: .62rem 1rem; border-radius: 999px; color: var(--m-panel, #f0f4ce); background: var(--m-ink, #13281e); }
  .bio.fired .cell { animation: bio-fire 430ms cubic-bezier(.18,.86,.28,1.2) var(--fire-delay) both; }
  .bio.fired::before { animation: bio-shell 480ms cubic-bezier(.2,.8,.2,1) both; }

  @keyframes bio-fire {
    0% { opacity: .12; transform: scale(.3); }
    52% { opacity: 1; transform: scale(1); }
    100% { opacity: .24; transform: scale(.62); }
  }

  @keyframes bio-shell {
    0%, 100% { transform: scale(1); }
    45% { transform: scale(.96); }
  }

  .matcha-play:active:not(:disabled) .play-label { transform: scale(.97); }

  @media (prefers-reduced-motion: reduce) {
    .cell { transition: none; }
    .vector.fired .cell, .bio.fired .cell, .bio.fired::before { animation-duration: 1ms; animation-delay: 0ms; }
  }
</style>
