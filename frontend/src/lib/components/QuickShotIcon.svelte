<script lang="ts">
  export let ready = true;
  export let guarding = false;
  export let accepted = false;
  export let explanationOpen = false;
  export let controls = '';
  export let onToggle: () => void = () => {};

  $: spent = !ready;
</script>

<button
  class:accepted
  class:guarding
  class:spent
  class="quick-shot-icon"
  type="button"
  aria-label={ready ? 'Quick-shot is armed. Open explanation.' : 'Quick-shot is spent. Open explanation.'}
  aria-expanded={explanationOpen}
  aria-controls={controls || undefined}
  on:click={onToggle}
  on:pointerdown|preventDefault
>
  <svg viewBox="0 0 32 32" shape-rendering="crispEdges" aria-hidden="true">
    <path class="pixel-frame" d="M6 3h20v3h3v20h-3v3H6v-3H3V6h3zM8 8v16h16V8z"></path>
    <g class="bolt-core">
      <rect x="18" y="7" width="6" height="3"></rect>
      <rect x="15" y="10" width="6" height="3"></rect>
      <rect x="12" y="13" width="6" height="3"></rect>
      <rect x="9" y="16" width="12" height="3"></rect>
      <rect x="15" y="19" width="6" height="3"></rect>
      <rect x="12" y="22" width="6" height="3"></rect>
      <rect x="9" y="25" width="6" height="2"></rect>
    </g>
    <rect class="charge-pip pip-one" x="5" y="14" width="2" height="4"></rect>
    <rect class="charge-pip pip-two" x="25" y="14" width="2" height="4"></rect>
  </svg>
  <span aria-hidden="true"></span>
</button>

<style>
  .quick-shot-icon {
    position: relative;
    display: grid;
    width: 36px;
    height: 36px;
    flex: 0 0 36px;
    padding: 0;
    place-items: center;
    border: 1px solid color-mix(in srgb, var(--accent-2) 70%, transparent);
    border-radius: 6px;
    color: var(--accent-2);
    background: color-mix(in srgb, var(--accent-soft) 130%, var(--surface-dark));
    box-shadow:
      0 0 0 3px color-mix(in srgb, var(--accent) 8%, transparent),
      0 0 16px color-mix(in srgb, var(--accent-2) 20%, transparent);
    image-rendering: pixelated;
    animation: shot-breathe 1.8s steps(2, end) infinite;
  }

  .quick-shot-icon svg {
    width: 28px;
    height: 28px;
    fill: none;
    image-rendering: pixelated;
  }

  .pixel-frame {
    fill: currentColor;
    opacity: 0.16;
  }

  .bolt-core,
  .charge-pip {
    fill: currentColor;
  }

  .bolt-core {
    animation: cartridge-charge 1.4s steps(3, end) infinite;
  }

  .charge-pip {
    animation: charge-pip 1.4s steps(2, end) infinite;
  }

  .quick-shot-icon > span {
    position: absolute;
    top: 3px;
    right: 3px;
    width: 4px;
    height: 4px;
    background: white;
    box-shadow: 0 0 7px 2px var(--accent-2);
  }

  .quick-shot-icon.spent {
    border-color: color-mix(in srgb, var(--muted) 36%, transparent);
    color: color-mix(in srgb, var(--muted) 58%, var(--surface-dark));
    background: color-mix(in srgb, var(--surface-dark) 90%, black);
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.025);
    animation: none;
  }

  .quick-shot-icon.spent .bolt-core,
  .quick-shot-icon.spent .charge-pip {
    animation: none;
  }

  .quick-shot-icon.spent .charge-pip {
    opacity: 0;
  }

  .quick-shot-icon.spent > span {
    background: color-mix(in srgb, var(--muted) 45%, var(--surface-dark));
    box-shadow: none;
  }

  .quick-shot-icon.accepted {
    animation: shot-accepted 480ms steps(3, end) both;
  }

  .quick-shot-icon.guarding::before {
    position: absolute;
    border: 1px solid color-mix(in srgb, var(--success) 72%, transparent);
    border-radius: 8px;
    content: '';
    inset: -4px;
    pointer-events: none;
    animation: guard-window 600ms ease-out both;
  }

  @keyframes shot-breathe {
    50% {
      box-shadow:
        0 0 0 4px color-mix(in srgb, var(--accent) 11%, transparent),
        0 0 22px color-mix(in srgb, var(--accent-2) 34%, transparent);
    }
  }

  @keyframes cartridge-charge {
    0%, 32% { opacity: 0.58; }
    33%, 66% { opacity: 0.8; }
    67%, 100% { opacity: 1; }
  }

  @keyframes charge-pip {
    0%, 42% { opacity: 0.25; }
    43%, 100% { opacity: 1; }
  }

  @keyframes shot-accepted {
    42% {
      color: white;
      transform: scale(1.16);
      box-shadow: 0 0 28px color-mix(in srgb, var(--success) 65%, transparent);
    }
  }

  @keyframes guard-window {
    from { opacity: 0.9; transform: scale(0.92); }
    to { opacity: 0; transform: scale(1.28); }
  }

  @media (prefers-reduced-motion: reduce) {
    .quick-shot-icon,
    .bolt-core,
    .charge-pip,
    .quick-shot-icon.guarding::before {
      animation: none;
    }
  }
</style>
