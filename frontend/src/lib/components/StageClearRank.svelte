<script lang="ts">
  import { onMount } from 'svelte';

  // C1-A stage clear (chosen in /playground2): a letter grade stamps in,
  // the score counts up with tabular digits, and the per-item segment bar
  // fills left to right. Shared by the Words/Verbs trainer and the tables
  // game so every mode ends on the same moment. Reduced motion renders the
  // settled state immediately.
  export let score = 0; // percent 0..100
  export let ok = 0;
  export let total = 0;
  export let bestCombo = 0;
  export let unitLabel = 'words';

  let shownScore = 0;
  let rafId = 0;

  $: grade = score >= 95 ? 'S' : score >= 85 ? 'A' : score >= 70 ? 'B' : 'C';

  function countUp(): void {
    cancelAnimationFrame(rafId);
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      shownScore = score;
      return;
    }
    shownScore = 0;
    const start = performance.now();
    const duration = 900;
    const target = score;
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      shownScore = Math.round(eased * target);
      if (t < 1) {
        rafId = requestAnimationFrame(step);
      }
    };
    rafId = requestAnimationFrame(step);
  }

  onMount(() => {
    if (total > 0) {
      countUp();
    }
    return () => cancelAnimationFrame(rafId);
  });
</script>

<div class="rank-clear">
  {#if total > 0}
    <div class="rank-head">
      <div class={`rank-stamp rank-${grade.toLowerCase()}`} role="img" aria-label={`Rank ${grade} — ${score} percent`}>
        <span class="rank-ring" aria-hidden="true"></span>
        {#if grade === 'S'}<span class="rank-ring rank-ring-2" aria-hidden="true"></span>{/if}
        <strong>{grade}</strong>
      </div>
      <div class="rank-readout">
        <span>Stage clear</span>
        <strong class="rank-count">{shownScore}%</strong>
        <small>{ok}/{total} {unitLabel} · best combo ×{bestCombo}</small>
      </div>
    </div>
    <div class="rank-bar" role="img" aria-label={`${ok} of ${total} ${unitLabel} correct`}>
      {#each Array(total) as _, i}
        <span class:rank-seg-ok={i < ok} style={`animation-delay: ${0.55 + i * 0.05}s;`}></span>
      {/each}
    </div>
  {:else}
    <h2 class="rank-title">Stage clear</h2>
    <p class="rank-fallback">Session complete — jump back in!</p>
  {/if}
  <div class="rank-actions">
    <slot />
  </div>
</div>

<style>
  .rank-clear {
    display: grid;
    gap: 1.1rem;
    justify-items: center;
  }

  .rank-head {
    display: flex;
    align-items: center;
    gap: 1.4rem;
  }

  .rank-stamp {
    position: relative;
    display: grid;
    place-items: center;
    width: 6rem;
    height: 6rem;
    border: 3px solid var(--rank-color, var(--accent));
    border-radius: 18px;
    background: color-mix(in srgb, var(--rank-color, var(--accent)) 10%, transparent);
    box-shadow: 0 0 26px color-mix(in srgb, var(--rank-color, var(--accent)) 35%, transparent);
    animation: rank-stamp-in 0.45s cubic-bezier(0.2, 1.4, 0.4, 1) both;
  }

  .rank-s,
  .rank-a {
    --rank-color: var(--xp);
  }

  :global(html[data-theme='light']) .rank-s {
    --rank-color: var(--accent-2);
    background: color-mix(in srgb, var(--matcha-panel) 40%, white);
    box-shadow: inset 0 0 0 1px color-mix(in srgb, white 72%, transparent);
  }

  :global(html[data-theme='light']) .rank-s strong {
    text-shadow: none;
  }

  .rank-b {
    --rank-color: var(--accent);
  }

  .rank-c {
    --rank-color: var(--muted);
  }

  .rank-stamp strong {
    color: var(--rank-color, var(--accent));
    font: 800 3rem/1 var(--marquee);
    text-shadow: 0 0 18px color-mix(in srgb, var(--rank-color, var(--accent)) 60%, transparent);
  }

  .rank-ring {
    position: absolute;
    inset: -3px;
    border: 3px solid var(--rank-color, var(--accent));
    border-radius: 18px;
    opacity: 0;
    animation: rank-ring 0.9s 0.3s ease-out both;
  }

  .rank-ring-2 {
    animation-delay: 0.5s;
  }

  @keyframes rank-stamp-in {
    0% { opacity: 0; transform: scale(2.1) rotate(-8deg); }
    100% { opacity: 1; transform: scale(1) rotate(0deg); }
  }

  @keyframes rank-ring {
    0% { opacity: 0.8; transform: scale(1); }
    100% { opacity: 0; transform: scale(1.55); }
  }

  .rank-readout {
    display: grid;
    gap: 0.2rem;
    justify-items: start;
    text-align: left;
  }

  .rank-readout > span {
    color: var(--muted);
    font: 700 0.8rem/1 var(--mono);
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }

  .rank-count {
    color: var(--text);
    font: 800 clamp(2.3rem, 7vw, 3.2rem)/1 var(--mono);
    font-variant-numeric: tabular-nums;
  }

  .rank-readout small {
    color: var(--muted);
    font-size: 0.88rem;
  }

  .rank-bar {
    display: flex;
    gap: 5px;
    width: min(100%, 22rem);
  }

  .rank-bar span {
    flex: 1;
    height: 0.8rem;
    border-radius: 4px;
    border: 1px solid color-mix(in srgb, var(--danger) 45%, transparent);
    background: color-mix(in srgb, var(--danger) 8%, transparent);
  }

  .rank-bar .rank-seg-ok {
    border-color: var(--success);
    background: color-mix(in srgb, var(--success) 65%, transparent);
    box-shadow: 0 0 10px color-mix(in srgb, var(--success) 35%, transparent);
    animation: rank-seg 0.3s ease-out both;
    animation-delay: inherit;
  }

  @keyframes rank-seg {
    0% { opacity: 0.2; transform: scaleY(0.4); }
    100% { opacity: 1; transform: scaleY(1); }
  }

  .rank-title {
    margin: 0;
    color: var(--text);
    font: 800 1.9rem/1.2 var(--marquee);
  }

  .rank-fallback {
    margin: 0;
    color: var(--muted);
    font-size: 1rem;
    font-weight: 600;
  }

  .rank-actions {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    justify-content: center;
    animation: rank-rise 0.4s 0.85s ease-out both;
  }

  @keyframes rank-rise {
    0% { opacity: 0; transform: translateY(0.6rem); }
    100% { opacity: 1; transform: translateY(0); }
  }

  :global(html[data-theme='dark']) .rank-s { --rank-color: var(--accent-strong); }
  :global(html[data-theme='dark']) .rank-a { --rank-color: var(--accent); }
  :global(html[data-theme='dark']) .rank-b { --rank-color: var(--accent-2); }

  :global(html[data-theme='dark']) .rank-stamp {
    border-radius: 0 18px 0 18px;
    background: color-mix(in srgb, var(--rank-color, var(--accent)) 7%, var(--ink-panel));
    box-shadow: inset 4px 0 0 var(--accent-2), 0 18px 34px -26px rgba(0, 0, 0, 0.9);
  }

  :global(html[data-theme='dark']) .rank-stamp strong {
    text-shadow: none;
  }

  :global(html[data-theme='dark']) .rank-ring {
    border-radius: 0 18px 0 18px;
  }

  :global(html[data-theme='dark']) .rank-bar span {
    border-radius: 0;
  }

  :global(html[data-theme='dark']) .rank-bar .rank-seg-ok {
    box-shadow: none;
  }

  :global(html[data-theme='arcade']) .rank-stamp strong {
    font-size: 2.2rem;
  }

  :global(html[data-theme='arcade']) .rank-count {
    font-size: clamp(2.6rem, 7vw, 3.6rem);
  }

  :global(html[data-theme='arcade']) .rank-readout > span {
    font-size: 1.05rem;
  }

  :global(html[data-theme='arcade']) .rank-readout small {
    font-size: 0.95rem;
  }

  :global(html[data-theme='arcade']) .rank-title {
    font-size: 1.5rem;
    text-shadow: 0 0 18px color-mix(in srgb, var(--accent) 100%, transparent);
  }

  @media (prefers-reduced-motion: reduce) {
    .rank-stamp,
    .rank-ring,
    .rank-bar .rank-seg-ok,
    .rank-actions {
      animation: none;
    }

    .rank-ring {
      display: none;
    }
  }

  @media (max-width: 560px) {
    .rank-head {
      flex-direction: column;
      gap: 0.8rem;
    }

    .rank-readout {
      justify-items: center;
      text-align: center;
    }
  }
</style>
