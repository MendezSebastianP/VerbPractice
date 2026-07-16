<script lang="ts">
  import { createEventDispatcher, onDestroy } from 'svelte';

  export let disabled = false;
  export let label = 'PLAY';
  export let icon = true;
  export let width = 274;
  export let height = 106;
  export let fontSize = 15;
  export let resetAfterFire = false;

  const columns = 6;
  const count = 12;
  const dispatch = createEventDispatcher<{ fire: void }>();

  let gridEl: HTMLElement | null = null;
  let fired = false;
  let timer: ReturnType<typeof setTimeout> | null = null;

  $: compact = height < 80;

  function cells(): HTMLElement[] {
    return gridEl ? Array.from(gridEl.children) as HTMLElement[] : [];
  }

  function resetCells(): void {
    for (const cell of cells()) {
      cell.style.removeProperty('--cell-opacity');
      cell.style.removeProperty('--cell-scale');
      cell.style.removeProperty('--fire-delay');
    }
  }

  function handlePointerMove(event: PointerEvent): void {
    if (fired) return;
    const items = cells();
    const reach = Math.max(62, height * 1.35);
    for (const cell of items) {
      const rect = cell.getBoundingClientRect();
      const dx = event.clientX - (rect.left + rect.width / 2);
      const dy = event.clientY - (rect.top + rect.height / 2);
      const heat = Math.max(0, 1 - Math.sqrt(dx * dx + dy * dy) / reach);
      cell.style.setProperty('--cell-opacity', (0.2 + heat * 0.8).toFixed(3));
      cell.style.setProperty('--cell-scale', (0.7 + heat * 0.3).toFixed(3));
    }
  }

  function handlePointerLeave(): void {
    if (!fired) resetCells();
  }

  export function fire(): void {
    if (disabled || fired) return;
    fired = true;
    for (const [index, cell] of cells().entries()) {
      const row = Math.floor(index / columns);
      const column = index % columns;
      cell.style.setProperty('--fire-delay', `${(column * 0.05 + row * 0.025).toFixed(3)}s`);
    }
    dispatch('fire');
    if (resetAfterFire) timer = setTimeout(reset, 900);
  }

  export function reset(): void {
    if (timer) clearTimeout(timer);
    timer = null;
    fired = false;
    resetCells();
  }

  onDestroy(() => {
    if (timer) clearTimeout(timer);
  });
</script>

<button
  class="saffron-relay"
  class:compact
  class:fired
  type="button"
  {disabled}
  aria-label={label}
  style={`width:${width}px;height:${height}px;`}
  on:click={fire}
  on:pointermove={handlePointerMove}
  on:pointerleave={handlePointerLeave}
  on:pointercancel={handlePointerLeave}
>
  <span class="relay-grid" bind:this={gridEl} aria-hidden="true">
    {#each Array(count) as _, index (index)}
      <i class="relay-cell" style={`--i:${index}`}></i>
    {/each}
  </span>

  <span class="relay-label" style={`font-size:${fontSize}px;`}>
    {#if icon}<b aria-hidden="true">▶</b>{/if}
    <span>{label}</span>
  </span>
  <small aria-hidden="true">12 / READY</small>
</button>

<style>
  .saffron-relay {
    position: relative;
    display: block;
    max-width: 100%;
    overflow: hidden;
    padding: 0;
    border: 1px solid color-mix(in srgb, var(--accent) 58%, transparent);
    border-radius: 0 16px 0 16px;
    color: var(--text);
    background: var(--ink-panel, var(--surface));
    box-shadow: inset 4px 0 var(--accent-2), inset 0 -2px color-mix(in srgb, var(--accent) 24%, transparent), var(--shadow);
    cursor: pointer;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
  }

  .saffron-relay:disabled { opacity: .46; cursor: not-allowed; }
  .saffron-relay:focus-visible { outline: 3px solid var(--accent); outline-offset: 4px; }
  .saffron-relay:active:not(:disabled) { transform: scale(.98); }

  .relay-grid {
    position: absolute;
    inset: 9px;
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    grid-template-rows: repeat(2, minmax(0, 1fr));
    gap: 4px;
  }

  .relay-cell {
    --cell-opacity: .2;
    --cell-scale: .7;
    --fire-delay: 0s;
    display: block;
    min-width: 0;
    min-height: 0;
    opacity: var(--cell-opacity);
    transform: scale(var(--cell-scale));
    background: var(--accent);
    transition: opacity 100ms ease-out, transform 100ms ease-out;
  }

  .relay-label {
    position: absolute;
    z-index: 2;
    left: 50%;
    top: 50%;
    display: flex;
    min-width: 45%;
    min-height: 44%;
    align-items: center;
    justify-content: center;
    gap: .62em;
    padding: .38em .9em;
    transform: translate(-50%, -50%);
    color: var(--text);
    background: color-mix(in srgb, var(--ink-field, #0b0906) 90%, transparent);
    font-family: var(--display);
    font-weight: 750;
    letter-spacing: .15em;
    white-space: nowrap;
    pointer-events: none;
  }

  .relay-label b { color: var(--accent); font-size: .68em; }
  .saffron-relay small { position: absolute; z-index: 3; right: 8px; bottom: 5px; color: var(--muted); font: 500 .46rem/1 var(--mono); letter-spacing: .08em; }

  .compact .relay-grid { inset: 6px; gap: 3px; }
  .compact .relay-label { min-width: 48%; min-height: 46%; padding: .3em .72em; }
  .compact small { display: none; }

  .fired .relay-cell { animation: relay-fire 560ms cubic-bezier(.2,.8,.2,1) var(--fire-delay) both; }
  .fired .relay-label { animation: relay-copy 860ms cubic-bezier(.2,.8,.2,1) 140ms both; }

  @keyframes relay-fire {
    0% { opacity: .18; transform: scale(.7); }
    45% { opacity: 1; transform: scale(1); background: var(--accent-strong); }
    100% { opacity: .3; transform: scale(.82); background: var(--accent); }
  }

  @keyframes relay-copy {
    0%, 100% { color: var(--text); background: color-mix(in srgb, var(--ink-field, #0b0906) 90%, transparent); }
    35%, 58% { color: var(--ink-field, #0b0906); background: var(--accent-strong); letter-spacing: .22em; }
  }

  @media (prefers-reduced-motion: reduce) {
    .relay-cell { transition: none; }
    .fired .relay-cell, .fired .relay-label { animation-duration: 1ms; animation-delay: 0ms; }
  }
</style>
