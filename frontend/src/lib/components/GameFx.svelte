<script lang="ts">
  import { fade } from 'svelte/transition';
  import { iconEmoji } from '../badges';
  import { dismissOverlay, fxQueue, missFlash } from '../fx';
  import type { FxOverlay } from '../fx';

  interface Particle {
    dx: number;
    dy: number;
    delay: number;
    size: number;
    color: string;
  }

  const PARTICLE_COLORS = ['var(--xp)', 'var(--accent)', 'var(--accent-2)', 'var(--success)'];

  function makeParticles(count: number): Particle[] {
    return Array.from({ length: count }, (_, i) => {
      const angle = (Math.PI * 2 * i) / count + Math.random() * 0.6;
      const distance = 90 + Math.random() * 140;
      return {
        dx: Math.cos(angle) * distance,
        dy: Math.sin(angle) * distance,
        delay: Math.random() * 180,
        size: 5 + Math.random() * 7,
        color: PARTICLE_COLORS[i % PARTICLE_COLORS.length],
      };
    });
  }

  let current: FxOverlay | null = null;
  let particles: Particle[] = [];
  let autoTimer: ReturnType<typeof setTimeout> | null = null;
  let lastOverlayId = 0;

  $: current = $fxQueue[0] ?? null;
  $: if (current && current.id !== lastOverlayId) {
    lastOverlayId = current.id;
    particles = current.kind === 'level' ? makeParticles(26) : [];
    if (autoTimer) clearTimeout(autoTimer);
    const overlayId = current.id;
    autoTimer = setTimeout(() => dismissOverlay(overlayId), current.kind === 'level' ? 2600 : 8000);
  }

  function dismissCurrent(): void {
    if (!current) return;
    if (autoTimer) {
      clearTimeout(autoTimer);
      autoTimer = null;
    }
    dismissOverlay(current.id);
  }

  function handleKeydown(event: KeyboardEvent): void {
    if (current && (event.key === 'Escape' || event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      dismissCurrent();
    }
  }

  // Tap anywhere to continue — the overlay covers the screen, so a window
  // listener keeps the element itself non-interactive for assistive tech.
  function handleWindowClick(): void {
    if (current) {
      dismissCurrent();
    }
  }

  function rarityClass(rarity: string): string {
    const normalized = (rarity || 'common').toLowerCase();
    return ['common', 'rare', 'epic', 'legendary'].includes(normalized)
      ? `rarity-${normalized}`
      : 'rarity-common';
  }
</script>

<svelte:window on:keydown={handleKeydown} on:click={handleWindowClick} />

<!-- Arcade-only 'miss' screen flash on wrong answers -->
{#key $missFlash}
  {#if $missFlash > 0}
    <div class="miss-flash" aria-hidden="true"></div>
  {/if}
{/key}

{#if current}
  <div
    class="fx-overlay"
    role="status"
    aria-live="polite"
    transition:fade={{ duration: 150 }}
  >
    {#if current.kind === 'level'}
      <div class="fx-center">
        {#each particles as particle, i (i)}
          <span
            class="fx-particle"
            style={`--dx: ${particle.dx}px; --dy: ${particle.dy}px; width: ${particle.size}px; height: ${particle.size}px; background: ${particle.color}; animation-delay: ${particle.delay}ms;`}
          ></span>
        {/each}
        <p class="level-up-title">LEVEL UP!</p>
        <p class="level-up-number">Level {current.level}</p>
        <p class="fx-dismiss-hint">Tap to continue</p>
      </div>
    {:else}
      <div class="fx-center badge-stack">
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
        <p class="fx-dismiss-hint">Tap to continue</p>
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

  .fx-overlay {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: flex;
    align-items: center;
    justify-content: center;
    background: color-mix(in srgb, var(--bg) 55%, transparent);
    backdrop-filter: blur(4px);
    cursor: pointer;
  }

  .fx-center {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    text-align: center;
    padding: 2rem;
  }

  .fx-particle {
    position: absolute;
    left: 50%;
    top: 45%;
    border-radius: 999px;
    opacity: 0;
    animation: particle-burst 950ms cubic-bezier(0.2, 0.7, 0.3, 1) forwards;
  }

  @keyframes particle-burst {
    0% { opacity: 1; transform: translate(0, 0) scale(1); }
    100% { opacity: 0; transform: translate(var(--dx), var(--dy)) scale(0); }
  }

  .level-up-title {
    font-family: var(--display);
    font-weight: 800;
    font-size: clamp(1.8rem, 5vw, 3rem);
    letter-spacing: 0.04em;
    margin: 0;
    color: var(--xp);
    text-shadow: 0 0 24px color-mix(in srgb, var(--xp) 45%, transparent);
    animation: level-pop 500ms cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  :global(html[data-theme='arcade']) .level-up-title {
    font-size: clamp(1.2rem, 4vw, 2rem);
    text-shadow:
      0 0 18px color-mix(in srgb, var(--xp) 75%, transparent),
      0 0 48px color-mix(in srgb, var(--xp) 35%, transparent);
  }

  @keyframes level-pop {
    0% { transform: scale(0.4); opacity: 0; }
    70% { transform: scale(1.12); opacity: 1; }
    100% { transform: scale(1); }
  }

  .level-up-number {
    font-family: var(--display);
    font-size: 1.25rem;
    font-weight: 600;
    margin: 0;
    color: var(--text);
  }

  .fx-dismiss-hint {
    margin: 0.5rem 0 0;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-family: var(--mono);
    color: var(--muted);
  }

  .badge-stack {
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

  @media (prefers-reduced-motion: reduce) {
    .level-up-title,
    .badge-flip-card {
      animation-duration: 1ms;
    }

    .fx-particle,
    .miss-flash {
      display: none !important;
    }
  }
</style>
