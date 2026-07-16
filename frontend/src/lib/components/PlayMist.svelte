<script lang="ts">
  // Mist-wipe action pill from Clean Mode.dc.html: a frosted canvas covers the
  // button; moving the pointer wipes it, the mist slowly regrows, and firing
  // releases falling droplets that streak the frost before the action runs.
  import { createEventDispatcher, onDestroy, onMount } from 'svelte';

  export let theme: 'light' | 'dark' | 'arcade' = 'light';
  export let disabled = false;
  export let label = 'PLAY';
  // Render the custom play glyph before the label. Off for non-launch actions.
  export let icon = true;
  export let width = 340;
  export let height = 84;
  export let fontSize = 18;
  // Session launches keep the frost wiped (the screen swaps away); action
  // buttons (Home play, Add Word translate) re-arm once the droplets settle.
  export let resetAfterFire = false;

  const dispatch = createEventDispatcher<{ fire: void }>();

  const FROST: Record<string, { top: string; bottom: string; regrow: string }> = {
    light: { top: 'rgba(246,251,254,.94)', bottom: 'rgba(212,235,250,.9)', regrow: 'rgba(228,242,251,0.007)' },
    dark: { top: 'rgba(230,165,40,.16)', bottom: 'rgba(11,9,6,.28)', regrow: 'rgba(230,165,40,0.002)' },
  };

  let canvasEl: HTMLCanvasElement | null = null;
  let ctx: CanvasRenderingContext2D | null = null;
  let raf = 0;
  let drops: Array<{ x: number; y: number; v: number; r: number }> = [];
  let fired = false;

  $: palette = FROST[theme] ?? FROST.light;

  function paintFrost(): void {
    if (!ctx) return;
    ctx.globalCompositeOperation = 'source-over';
    const g = ctx.createLinearGradient(0, 0, 0, height);
    g.addColorStop(0, palette.top);
    g.addColorStop(1, palette.bottom);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, width, height);
  }

  function eraseAt(x: number, y: number, r: number, a: number): void {
    if (!ctx) return;
    ctx.globalCompositeOperation = 'destination-out';
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, `rgba(0,0,0,${a})`);
    g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 7);
    ctx.fill();
  }

  function step(): void {
    if (ctx) {
      if (drops.length) {
        drops = drops.filter((d) => {
          d.y += d.v;
          d.v += 0.45;
          eraseAt(d.x, d.y, d.r, 0.8);
          return d.y < height + 16;
        });
        if (!drops.length && resetAfterFire) {
          fired = false;
        }
      } else if (!fired) {
        ctx.globalCompositeOperation = 'source-over';
        ctx.fillStyle = palette.regrow;
        ctx.fillRect(0, 0, width, height);
      }
    }
    raf = requestAnimationFrame(step);
  }

  function handleMove(event: MouseEvent): void {
    if (!canvasEl || !ctx) return;
    const rect = canvasEl.getBoundingClientRect();
    const scaleX = rect.width ? width / rect.width : 1;
    const scaleY = rect.height ? height / rect.height : 1;
    eraseAt((event.clientX - rect.left) * scaleX, (event.clientY - rect.top) * scaleY, 30, 0.55);
  }

  export function fire(): void {
    if (disabled || fired) return;
    fired = true;
    drops = Array.from({ length: 16 }, () => ({
      x: 12 + Math.random() * (width - 24),
      y: Math.random() * 18,
      v: 1 + Math.random() * 2.2,
      r: 6 + Math.random() * 6,
    }));
    dispatch('fire');
  }

  export function reset(): void {
    fired = false;
    drops = [];
    paintFrost();
  }

  // Repaint when the theme flips so the frost tint matches the new surface.
  $: if (ctx && palette) paintFrost();

  onMount(() => {
    if (!canvasEl) return;
    canvasEl.width = width * 2;
    canvasEl.height = height * 2;
    ctx = canvasEl.getContext('2d');
    ctx?.scale(2, 2);
    paintFrost();
    raf = requestAnimationFrame(step);
  });

  onDestroy(() => cancelAnimationFrame(raf));
</script>

<div
  class="mist-wrap"
  class:mist-disabled={disabled}
  style={`width: ${width}px; height: ${height}px;`}
  on:mousemove={handleMove}
  role="presentation"
>
  <button class="mist-button" type="button" on:click={fire} {disabled} aria-label={label}>
    <canvas bind:this={canvasEl} class="mist-canvas" style={`width: ${width}px; height: ${height}px;`} aria-hidden="true"></canvas>
    <span class="mist-label" style={`font-size: ${fontSize}px;`}>
      {#if icon}
        <svg class="play-glyph" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l11-6.5z" /></svg>
      {/if}
      {label}
    </span>
  </button>
</div>

<style>
  .mist-wrap {
    position: relative;
    max-width: 100%;
  }

  .mist-disabled {
    opacity: 0.55;
  }

  .mist-button {
    position: absolute;
    inset: 0;
    cursor: pointer;
    border-radius: 999px;
    background: color-mix(in srgb, var(--surface) 92%, transparent);
    backdrop-filter: blur(14px);
    border: 1px solid var(--line-strong);
    box-shadow: var(--shadow);
    display: grid;
    place-items: center;
  }

  .mist-button:disabled {
    cursor: not-allowed;
  }

  .mist-button:active:not(:disabled) {
    transform: scale(0.98);
  }

  .mist-label {
    position: relative;
    z-index: 2;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5em;
    font-family: var(--display);
    font-weight: 800;
    letter-spacing: 5px;
    color: var(--text);
    white-space: nowrap;
  }

  .play-glyph {
    width: 0.85em;
    height: 0.85em;
    flex: 0 0 auto;
    fill: var(--accent-strong, currentColor);
    /* offset the trailing letter-spacing so the glyph+label read as centered */
    margin-left: 5px;
    filter: drop-shadow(0 1px 2px color-mix(in srgb, var(--accent) 40%, transparent));
  }

  .mist-canvas {
    position: absolute;
    z-index: 1;
    inset: 0;
    max-width: 100%;
    border-radius: 999px;
    pointer-events: none;
  }

  :global(html[data-theme='dark']) .mist-button {
    border-color: color-mix(in srgb, var(--accent) 42%, transparent);
    border-radius: 0 14px 0 14px;
    background:
      linear-gradient(90deg, var(--accent-2) 0 3px, transparent 3px),
      var(--accent);
    box-shadow: inset 0 -2px 0 color-mix(in srgb, var(--accent) 28%, transparent), var(--shadow);
  }

  :global(html[data-theme='dark']) .mist-label {
    color: var(--ink-field);
    font-weight: 700;
    letter-spacing: 0.12em;
  }

  :global(html[data-theme='dark']) .play-glyph {
    fill: var(--ink-field);
    filter: none;
  }

  :global(html[data-theme='dark']) .mist-canvas {
    border-radius: 0 14px 0 14px;
    opacity: 0.52;
  }
</style>
