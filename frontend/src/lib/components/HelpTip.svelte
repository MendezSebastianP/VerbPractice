<script lang="ts">
  export let label = 'How this works';
  export let align: 'left' | 'right' = 'right';

  let open = false;
  let wrapEl: HTMLElement | null = null;

  function toggle(): void {
    open = !open;
  }

  function onWindowClick(event: MouseEvent): void {
    if (open && wrapEl && !wrapEl.contains(event.target as Node)) {
      open = false;
    }
  }

  function onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape' && open) {
      open = false;
    }
  }
</script>

<svelte:window on:click={onWindowClick} on:keydown={onKeydown} />

<span class="help-wrap" bind:this={wrapEl}>
  <button
    type="button"
    class="help-button"
    class:help-on={open}
    aria-label={label}
    aria-expanded={open}
    title={label}
    on:click|stopPropagation={toggle}
  >
    <!-- Hand-built question mark: ring + curved hook + dot -->
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9.25"></circle>
      <path d="M9.1 9.2a2.95 2.95 0 0 1 5.45 1.1c0 1.95-2.55 2.35-2.55 3.95"></path>
      <path d="M12 17.1v.02"></path>
    </svg>
  </button>

  {#if open}
    <div class="help-pop glass-panel" class:pop-left={align === 'left'} role="dialog" aria-label={label}>
      <slot />
    </div>
  {/if}
</span>

<style>
  .help-wrap {
    position: relative;
    display: inline-flex;
  }

  .help-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    padding: 0;
    border-radius: 999px;
    border: 1px solid var(--line);
    background: color-mix(in srgb, var(--surface-strong) 84%, transparent);
    color: var(--muted);
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s, background 0.15s, transform 0.07s;
  }

  .help-button:hover,
  .help-button.help-on {
    color: var(--accent-strong, var(--accent));
    border-color: var(--accent, currentColor);
  }

  .help-button:active {
    transform: scale(0.92);
  }

  .help-pop {
    position: absolute;
    top: calc(100% + 0.5rem);
    right: 0;
    z-index: 40;
    width: min(22rem, 80vw);
    padding: 0.9rem 1rem;
    text-align: left;
    font-size: 0.85rem;
    line-height: 1.5;
    box-shadow: 0 14px 40px rgba(0, 0, 0, 0.25);
  }

  .help-pop.pop-left {
    right: auto;
    left: 0;
  }

  .help-pop :global(h4) {
    margin: 0 0 0.4rem;
    font-size: 0.95rem;
  }

  .help-pop :global(p) {
    margin: 0 0 0.55rem;
  }

  .help-pop :global(p:last-child) {
    margin-bottom: 0;
  }

  .help-pop :global(ul) {
    margin: 0.2rem 0 0.55rem;
    padding-left: 1.1rem;
  }

  .help-pop :global(li) {
    margin-bottom: 0.25rem;
  }

  .help-pop :global(kbd) {
    font-family: var(--mono, monospace);
    font-size: 0.72rem;
    padding: 0.05rem 0.3rem;
    border: 1px solid var(--line);
    border-radius: 4px;
    background: color-mix(in srgb, var(--surface-strong) 70%, transparent);
    white-space: nowrap;
  }
</style>
