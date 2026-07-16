<script lang="ts">
  // Arcade action control from VerbPractice App.dc.html: a pixel grid tilted
  // in 3D. Cells glow as the pointer approaches; firing lights the whole grid.
  import { createEventDispatcher, onDestroy } from 'svelte';

  export let disabled = false;
  export let label = 'PLAY';
  // Render the custom play glyph before the label. Off for non-launch actions.
  export let icon = true;
  export let cols = 10;
  export let rows = 4;
  export let cell = 22;
  export let gap = 6;
  export let fontSize = 15;
  // Action buttons re-arm shortly after firing; session launches stay lit
  // (the pixel dissolve takes over the screen).
  export let resetAfterFire = false;

  const dispatch = createEventDispatcher<{ fire: void }>();

  $: cellCount = cols * rows;

  let gridEl: HTMLElement | null = null;
  let fired = false;
  let rearmTimer: ReturnType<typeof setTimeout> | null = null;

  function cellEls(): HTMLElement[] {
    return gridEl ? (Array.from(gridEl.children) as HTMLElement[]) : [];
  }

  function handleMove(event: MouseEvent): void {
    if (fired) return;
    const mx = event.clientX;
    const my = event.clientY;
    for (const c of cellEls()) {
      const r = c.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      const d = Math.sqrt((mx - cx) ** 2 + (my - cy) ** 2);
      const t = Math.max(0, 1 - d / 90);
      c.style.background = `rgba(167,139,250,${(0.12 + t * 0.88).toFixed(3)})`;
      c.style.boxShadow = t > 0.05 ? `0 0 ${Math.round(14 * t)}px rgba(167,139,250,${t.toFixed(2)})` : 'none';
    }
  }

  function handleLeave(): void {
    if (fired) return;
    for (const c of cellEls()) {
      c.style.background = 'rgba(167,139,250,0.12)';
      c.style.boxShadow = 'none';
    }
  }

  export function fire(): void {
    if (disabled || fired) return;
    fired = true;
    for (const c of cellEls()) {
      c.style.background = '#cdbcff';
      c.style.boxShadow = '0 0 16px rgba(205,188,255,.95)';
    }
    dispatch('fire');
    if (resetAfterFire) {
      if (rearmTimer) clearTimeout(rearmTimer);
      rearmTimer = setTimeout(() => reset(), 700);
    }
  }

  export function reset(): void {
    fired = false;
    handleLeave();
  }

  onDestroy(() => {
    if (rearmTimer) clearTimeout(rearmTimer);
  });
</script>

<button class="pg-wrap" class:pg-disabled={disabled} type="button" on:click={fire} {disabled} aria-label={label}>
  <span class="pg-tilt">
    <span
      class="pg-grid"
      bind:this={gridEl}
      style={`grid-template-columns: repeat(${cols}, ${cell}px); gap: ${gap}px;`}
      on:mousemove={handleMove}
      on:mouseleave={handleLeave}
      role="presentation"
    >
      {#each Array(cellCount) as _, i (i)}
        <span class="pg-cell" style={`width: ${cell}px; height: ${cell}px;`}></span>
      {/each}
    </span>
  </span>
  <span class="pg-label" style={`font-size: ${fontSize}px;`}>
    {#if icon}
      <svg class="pg-play-glyph" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l11-6.5z" /></svg>
    {/if}
    {label}
  </span>
</button>

<style>
  .pg-wrap {
    position: relative;
    display: inline-block;
    cursor: pointer;
    background: transparent;
    border: 0;
    padding: 0;
  }

  .pg-disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .pg-tilt {
    display: block;
    transform: perspective(420px) rotateX(30deg);
  }

  .pg-grid {
    display: grid;
  }

  .pg-cell {
    border-radius: 3px;
    background: rgba(167, 139, 250, 0.12);
    border: 1px solid rgba(167, 139, 250, 0.22);
  }

  .pg-label {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.45em;
    pointer-events: none;
    font-family: var(--display);
    color: #fff;
    text-shadow: 0 0 14px rgba(124, 58, 237, 1), 0 2px 0 rgba(0, 0, 0, 0.6);
    letter-spacing: 0.04em;
  }

  .pg-play-glyph {
    width: 0.9em;
    height: 0.9em;
    flex: 0 0 auto;
    fill: #fff;
    filter: drop-shadow(0 0 10px rgba(124, 58, 237, 0.9));
  }
</style>
