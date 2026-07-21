<script lang="ts">
  import { fly } from 'svelte/transition';
  import { iconEmoji } from '../badges';
  import { dismissOverlay, fxQueue, missFlash } from '../fx';
  import type { FxOverlay } from '../fx';

  // Rendered as a small self-dismissing toast — never a blocking overlay.
  // No key/click handlers on purpose: a mid-typing Enter must always reach
  // the trainer, not a celebration screen.
  const TOAST_MS = 2000;

  let current: FxOverlay | null = null;
  let autoTimer: ReturnType<typeof setTimeout> | null = null;
  let lastOverlayId = 0;

  $: current = $fxQueue[0] ?? null;
  $: if (current && current.id !== lastOverlayId) {
    lastOverlayId = current.id;
    if (autoTimer) clearTimeout(autoTimer);
    const overlayId = current.id;
    autoTimer = setTimeout(() => dismissOverlay(overlayId), TOAST_MS);
  }

  function rarityClass(rarity: string): string {
    const normalized = (rarity || 'common').toLowerCase();
    return ['common', 'rare', 'epic', 'legendary'].includes(normalized)
      ? `rarity-${normalized}`
      : 'rarity-common';
  }
</script>

<!-- Arcade-only 'miss' screen flash on wrong answers -->
{#key $missFlash}
  {#if $missFlash > 0}
    <div class="miss-flash" aria-hidden="true"></div>
  {/if}
{/key}

{#if current}
  <div
    class="fx-toast-layer"
    role="status"
    aria-live="polite"
    transition:fly={{ y: -14, duration: 180 }}
  >
    {#if current.kind === 'level'}
      <div class="fx-toast level-toast">
        <span class="level-toast-burst" aria-hidden="true">✦</span>
        <div class="level-toast-copy">
          <p class="level-up-title">LEVEL UP!</p>
          <p class="level-up-number">Level {current.level}</p>
        </div>
      </div>
    {:else}
      <div class="fx-toast badge-stack">
        <p class="badge-headline">Badge unlocked</p>
        {#each current.badges as badge, i (badge.code)}
          <div class={`badge-flip-card ${rarityClass(badge.rarity)}`} style={`animation-delay: ${i * 180}ms;`}>
            <span class="badge-icon">{iconEmoji(badge.icon)}</span>
            <div class="badge-copy">
              <strong>{badge.title}</strong>
              <span>{badge.description}</span>
            </div>
            <span class="badge-rarity">{badge.rarity}</span>
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}

<style>
  .miss-flash {
    position: fixed;
    inset: 0;
    z-index: 35;
    pointer-events: none;
    background: var(--danger);
    opacity: 0;
    display: none;
  }

  :global(html[data-theme='arcade']) .miss-flash {
    display: block;
    animation: miss-blink 160ms ease-out forwards;
  }

  @keyframes miss-blink {
    0% { opacity: 0.07; }
    100% { opacity: 0; }
  }

  /* Non-blocking celebration toast: fixed near the top, ignores the pointer,
     and auto-dismisses — play (and Enter) always stays with the trainer. */
  .fx-toast-layer {
    position: fixed;
    top: 4.25rem;
    left: 0;
    right: 0;
    z-index: 50;
    display: flex;
    justify-content: center;
    pointer-events: none;
  }

  .fx-toast {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    padding: 0.7rem 1.25rem;
    border-radius: 14px;
    border: 1px solid color-mix(in srgb, var(--xp) 45%, var(--line-strong));
    background: var(--surface-strong);
    box-shadow: var(--shadow), 0 0 22px color-mix(in srgb, var(--xp) 22%, transparent);
  }

  .level-toast-burst {
    font-size: 1.5rem;
    color: var(--xp);
    animation: level-pop 500ms cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .level-toast-copy {
    display: flex;
    flex-direction: column;
    text-align: left;
  }

  .level-up-title {
    font-family: var(--marquee);
    font-weight: 800;
    font-size: 1rem;
    letter-spacing: 0.04em;
    margin: 0;
    color: var(--xp);
    text-shadow: 0 0 14px color-mix(in srgb, var(--xp) 40%, transparent);
    animation: level-pop 500ms cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  :global(html[data-theme='arcade']) .level-up-title {
    font-size: 0.85rem;
    text-shadow:
      0 0 12px color-mix(in srgb, var(--xp) 75%, transparent),
      0 0 30px color-mix(in srgb, var(--xp) 35%, transparent);
  }

  @keyframes level-pop {
    0% { transform: scale(0.4); opacity: 0; }
    70% { transform: scale(1.12); opacity: 1; }
    100% { transform: scale(1); }
  }

  .level-up-number {
    font-family: var(--display);
    font-size: 0.95rem;
    font-weight: 600;
    margin: 0;
    color: var(--text);
  }

  :global(html[data-theme='arcade']) .badge-headline {
    font-size: 1.05rem;
  }

  .badge-stack {
    flex-direction: column;
    align-items: stretch;
    gap: 0.5rem;
    max-width: 420px;
    width: min(420px, 92vw);
  }

  .badge-headline {
    font-family: var(--mono);
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    margin: 0;
    color: var(--muted);
  }

  .badge-flip-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    width: 100%;
    padding: 1rem 1.25rem;
    border-radius: 16px;
    border: 2px solid var(--line-strong);
    background: var(--surface-strong);
    box-shadow: var(--shadow);
    transform: perspective(700px) rotateY(180deg);
    opacity: 0;
    animation: badge-flip 650ms cubic-bezier(0.3, 0.9, 0.3, 1.1) forwards;
    text-align: left;
  }

  @keyframes badge-flip {
    0% { transform: perspective(700px) rotateY(180deg); opacity: 0; }
    55% { opacity: 1; }
    100% { transform: perspective(700px) rotateY(0deg); opacity: 1; }
  }

  .badge-icon {
    font-size: 1.9rem;
    flex-shrink: 0;
  }

  .badge-copy {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 0;
  }

  .badge-copy strong {
    font-family: var(--display);
    font-size: 1rem;
    color: var(--text);
  }

  .badge-copy span {
    font-size: 0.85rem;
    color: var(--muted);
  }

  .badge-rarity {
    margin-left: auto;
    font-family: var(--mono);
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    flex-shrink: 0;
  }

  .badge-flip-card.rarity-rare {
    border-color: color-mix(in srgb, var(--accent) 65%, transparent);
    box-shadow: 0 0 18px color-mix(in srgb, var(--accent) 30%, transparent);
  }

  .badge-flip-card.rarity-rare .badge-rarity {
    color: var(--accent-strong);
  }

  .badge-flip-card.rarity-epic {
    border-color: color-mix(in srgb, var(--accent-2) 70%, transparent);
    box-shadow: 0 0 22px color-mix(in srgb, var(--accent-2) 32%, transparent);
  }

  .badge-flip-card.rarity-epic .badge-rarity {
    color: var(--accent-2);
  }

  .badge-flip-card.rarity-legendary {
    border-color: color-mix(in srgb, var(--xp) 80%, transparent);
    box-shadow: 0 0 26px color-mix(in srgb, var(--xp) 40%, transparent);
  }

  .badge-flip-card.rarity-legendary .badge-rarity {
    color: var(--xp);
  }

  .badge-flip-card.rarity-common .badge-rarity {
    color: var(--muted);
  }

  :global(html[data-theme='dark']) .level-up-title {
    font-family: var(--display);
    letter-spacing: -0.02em;
    text-shadow: none;
  }

  :global(html[data-theme='dark']) .badge-flip-card {
    border-radius: 0 16px 0 16px;
    background:
      linear-gradient(90deg, var(--accent-2) 0 3px, transparent 3px),
      var(--ink-panel);
    box-shadow: var(--shadow);
  }

  :global(html[data-theme='dark']) :is(
    .badge-flip-card.rarity-rare,
    .badge-flip-card.rarity-epic,
    .badge-flip-card.rarity-legendary
  ) {
    box-shadow: var(--shadow);
  }

  @media (prefers-reduced-motion: reduce) {
    .level-up-title,
    .badge-flip-card {
      animation-duration: 1ms;
    }

    .miss-flash {
      display: none !important;
    }
  }
</style>
