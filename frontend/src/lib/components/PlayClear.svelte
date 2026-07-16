<script lang="ts">
  import { createEventDispatcher, onDestroy } from 'svelte';

  export let disabled = false;
  export let label = 'PLAY';
  export let icon = true;
  export let cols = 10;
  export let rows = 4;
  export let cell = 22;
  export let gap = 6;
  export let fontSize = 15;
  export let resetAfterFire = false;

  const dispatch = createEventDispatcher<{ fire: void }>();

  let gridEl: HTMLElement | null = null;
  let fired = false;
  let rearmTimer: ReturnType<typeof setTimeout> | null = null;

  $: cellCount = cols * rows;
  $: controlWidth = cols * cell + Math.max(0, cols - 1) * gap;
  $: controlHeight = rows * cell + Math.max(0, rows - 1) * gap;

  function cells(): HTMLElement[] {
    return gridEl ? Array.from(gridEl.children) as HTMLElement[] : [];
  }

  function resetCells(): void {
    for (const item of cells()) {
      item.style.removeProperty('--cell-opacity');
      item.style.removeProperty('--cell-scale');
      item.style.removeProperty('--fire-delay');
    }
  }

  function handleMove(event: MouseEvent): void {
    if (fired) return;
    const reach = Math.max(64, cell * 4.2);
    for (const item of cells()) {
      const rect = item.getBoundingClientRect();
      const dx = event.clientX - (rect.left + rect.width / 2);
      const dy = event.clientY - (rect.top + rect.height / 2);
      const heat = Math.max(0, 1 - Math.sqrt(dx * dx + dy * dy) / reach);
      item.style.setProperty('--cell-opacity', (0.18 + heat * 0.82).toFixed(3));
      item.style.setProperty('--cell-scale', (0.72 + heat * 0.28).toFixed(3));
    }
  }

  function handleLeave(): void {
    if (!fired) resetCells();
  }

  export function fire(): void {
    if (disabled || fired) return;
    fired = true;
    for (const [index, item] of cells().entries()) {
      const row = Math.floor(index / cols);
      const column = index % cols;
      const delay = column * 0.022 + row * 0.014;
      item.style.setProperty('--fire-delay', `${delay.toFixed(3)}s`);
    }
    dispatch('fire');
    if (resetAfterFire) {
      if (rearmTimer) clearTimeout(rearmTimer);
      rearmTimer = setTimeout(reset, 700);
    }
  }

  export function reset(): void {
    fired = false;
    resetCells();
  }

  onDestroy(() => {
    if (rearmTimer) clearTimeout(rearmTimer);
  });
</script>

<button
  class="clear-play"
  class:fired
  type="button"
  {disabled}
  aria-label={label}
  style={`width:${controlWidth}px;height:${controlHeight}px;`}
  on:click={fire}
  on:mousemove={handleMove}
  on:mouseleave={handleLeave}
>
  <span
    class="cell-grid"
    bind:this={gridEl}
    style={`grid-template-columns:repeat(${cols},${cell}px);gap:${gap}px;`}
    aria-hidden="true"
  >
    {#each Array(cellCount) as _, index (index)}
      <span class="cell" style={`width:${cell}px;height:${cell}px;`}></span>
    {/each}
  </span>
  <span class="play-label" style={`font-size:${fontSize}px;`}>
    {#if icon}
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l11-6.5z" /></svg>
    {/if}
    <b>{label}</b>
    {#if cell >= 20 && rows >= 4}
      <i>RUN_01</i>
    {/if}
  </span>
</button>

<style>
  .clear-play {
    position: relative;
    display: inline-block;
    max-width: 100%;
    padding: 0;
    overflow: hidden;
    border: 0;
    color: var(--text);
    background: transparent;
    cursor: pointer;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
  }

  .clear-play:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .clear-play:focus-visible {
    outline: 4px solid var(--accent-2);
    outline-offset: 4px;
  }

  .cell-grid {
    position: absolute;
    inset: 0;
    display: grid;
  }

  .cell {
    --cell-opacity: 0.18;
    --cell-scale: 0.72;
    --fire-delay: 0s;
    display: block;
    box-sizing: border-box;
    opacity: var(--cell-opacity);
    border: 1px solid var(--accent);
    background: var(--accent);
    clip-path: polygon(0 0, 82% 0, 100% 25%, 100% 100%, 18% 100%, 0 75%);
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
    gap: 0.45em;
    background: linear-gradient(90deg, transparent 8%, color-mix(in srgb, var(--surface-strong) 92%, transparent) 31% 69%, transparent 92%);
    pointer-events: none;
  }

  .play-label svg {
    width: 0.92em;
    height: 0.92em;
    flex: 0 0 auto;
    fill: var(--accent-2);
  }

  .play-label b {
    font-family: var(--display);
    font-weight: 750;
    letter-spacing: 0.14em;
  }

  .play-label i {
    position: absolute;
    right: 10px;
    bottom: 8px;
    color: var(--accent-strong);
    font: 400 0.9rem/1 var(--mono);
    font-style: normal;
  }

  .fired .cell {
    animation: clear-vector-fire 380ms cubic-bezier(0.2, 0.8, 0.2, 1) var(--fire-delay) both;
  }

  @keyframes clear-vector-fire {
    0% { opacity: 0.18; transform: scale(0.72) skewX(0); }
    45% { opacity: 1; transform: scale(1) skewX(-10deg); }
    100% { opacity: 0.28; transform: scale(0.84) skewX(0); }
  }

  .clear-play:active:not(:disabled) .play-label {
    transform: scale(0.97);
  }

  @media (prefers-reduced-motion: reduce) {
    .cell { transition: none; }
    .fired .cell { animation-duration: 1ms; animation-delay: 0ms; }
  }
</style>
