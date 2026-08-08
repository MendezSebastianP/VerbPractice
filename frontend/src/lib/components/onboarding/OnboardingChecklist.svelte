<script lang="ts" context="module">
  export interface ChecklistStep {
    id: string;
    label: string;
    hint: string;
    /** Label for the button that takes the learner to the step. */
    cta: string;
    done: boolean;
    /** Where the real app would send them; the bench only echoes it. */
    href?: string;
  }

  export type ChecklistVariant = 'card' | 'strip' | 'banner';
</script>

<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let steps: ChecklistStep[] = [];
  export let variant: ChecklistVariant = 'card';
  export let title = 'Get started';
  /** Hides the dismiss control for benches that want the card pinned. */
  export let dismissible = true;
  /** True once the learner has opted out of the guided order. */
  export let skipped = false;
  /**
   * Step that just landed, as `{ id, seq }`. Supplied by the host because
   * completions happen while this card is unmounted (mid-drill) — watching our
   * own props would miss them. A new `seq` triggers the tick-over.
   */
  export let landed: { id: string; seq: number } | null = null;

  const dispatch = createEventDispatcher<{
    action: { id: string };
    dismiss: void;
    skip: void;
    unskip: void;
  }>();

  // Two clicks to leave the guided path — the first only reveals the warning.
  let confirmingSkip = false;

  // Collapsed by default: the card follows the learner onto every screen, so it
  // has to sit quietly until it is wanted. The choice is remembered per browser.
  const COLLAPSE_KEY = 'vp-onboarding-collapsed';
  let collapsed = readCollapsed();

  function readCollapsed(): boolean {
    if (typeof window === 'undefined') return true;
    return window.localStorage.getItem(COLLAPSE_KEY) !== 'false';
  }

  function toggleCollapsed(): void {
    collapsed = !collapsed;
    window.localStorage.setItem(COLLAPSE_KEY, String(collapsed));
  }

  $: done = steps.filter((step) => step.done).length;
  $: total = steps.length;
  $: complete = total > 0 && done === total;
  $: percent = total === 0 ? 0 : Math.round((done / total) * 100);
  // The first unfinished step is the one we push; everything else stays quiet.
  $: nextStep = steps.find((step) => !step.done) ?? null;
  $: if (skipped) confirmingSkip = false;

  // --- arcade tick-over ------------------------------------------------------
  // Two sources: a `landed` seq from the host (survives the card unmounting
  // mid-drill) and a local diff, which is what the playground bench runs on.
  let seenDone = new Set(steps.filter((step) => step.done).map((step) => step.id));
  let flashing: string | null = null;
  let flashTimer = 0;
  let primed = false;
  let lastLandedSeq = 0;

  function celebrate(id: string): void {
    flashing = id;
    window.clearTimeout(flashTimer);
    flashTimer = window.setTimeout(() => (flashing = null), 1500);
    // A step landing is the one moment the learner wants the list open.
    if (collapsed) {
      collapsed = false;
      window.localStorage.setItem(COLLAPSE_KEY, 'false');
    }
  }

  $: if (landed && landed.seq !== lastLandedSeq) {
    lastLandedSeq = landed.seq;
    celebrate(landed.id);
  }

  $: {
    const nowDone = steps.filter((step) => step.done).map((step) => step.id);
    const fresh = primed ? nowDone.find((id) => !seenDone.has(id)) : undefined;
    seenDone = new Set(nowDone);
    primed = true;
    if (fresh && !landed) {
      celebrate(fresh);
    }
  }

  // Ring geometry for the card variant.
  const RADIUS = 22;
  const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
  $: dashOffset = CIRCUMFERENCE * (1 - percent / 100);

  function act(id: string): void {
    dispatch('action', { id });
  }

  function requestSkip(): void {
    if (!confirmingSkip) {
      confirmingSkip = true;
      return;
    }
    confirmingSkip = false;
    dispatch('skip');
  }
</script>

{#if variant === 'card'}
  <section class="ob-card" aria-labelledby="ob-card-title">
    <header class="ob-card-head">
      <div class="ob-ring" role="img" aria-label={`${done} of ${total} steps complete`}>
        <svg viewBox="0 0 52 52" aria-hidden="true">
          <circle class="ring-track" cx="26" cy="26" r={RADIUS} />
          <circle
            class="ring-fill"
            cx="26"
            cy="26"
            r={RADIUS}
            stroke-dasharray={CIRCUMFERENCE}
            stroke-dashoffset={dashOffset}
          />
        </svg>
        <span class="ring-label">{done}<small>/{total}</small></span>
      </div>

      <div class="ob-card-copy">
        <h3 id="ob-card-title">{complete ? 'You are all set.' : title}</h3>
        <p>
          {#if complete}
            Every starter step is done. This card disappears for good.
          {:else if skipped}
            Everything is unlocked. The list stays as a suggested order.
          {:else if collapsed}
            Next: <strong class="head-next">{nextStep?.label}</strong>
          {:else}
            <!-- Stays generic: the active row already carries the specific hint. -->
            {done === 0 ? `${total} short steps` : `${total - done} left`} — each one opens the next.
          {/if}
        </p>
      </div>

      <button
        class="ob-collapse"
        class:is-collapsed={collapsed}
        type="button"
        aria-expanded={!collapsed}
        aria-controls="ob-card-body"
        aria-label={collapsed ? 'Expand the tutorial checklist' : 'Collapse the tutorial checklist'}
        on:click={toggleCollapsed}
      >
        <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M4 6.2 8 10l4-3.8" />
        </svg>
      </button>

      {#if dismissible}
        <button class="ob-dismiss" type="button" aria-label="Dismiss checklist" on:click={() => dispatch('dismiss')}>
          ×
        </button>
      {/if}
    </header>

    <div id="ob-card-body" hidden={collapsed}>
    <ol class="ob-list">
      {#each steps as step (step.id)}
        {@const isNext = !complete && nextStep?.id === step.id}
        <li
          class="ob-item"
          class:item-done={step.done}
          class:item-next={isNext}
          class:item-landed={flashing === step.id}
        >
          <span class="ob-mark" aria-hidden="true">
            {#if step.done}
              <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 8.4l3.2 3.2L13 5" />
              </svg>
            {/if}
          </span>

          <span class="ob-text">
            <strong>{step.label}</strong>
            {#if isNext}<small>{step.hint}</small>{/if}
          </span>

          {#if step.done}
            <span class="ob-status" class:status-landed={flashing === step.id}>
              {flashing === step.id ? 'Cleared!' : 'Done'}
            </span>
          {:else if isNext || skipped}
            <button class="ob-cta" class:cta-quiet={skipped && !isNext} type="button" on:click={() => act(step.id)}>
              {step.cta}
            </button>
          {:else}
            <span class="ob-status ob-locked">
              <svg viewBox="0 0 16 16" width="10" height="10" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <rect x="3.2" y="7" width="9.6" height="6.4" rx="1.6" />
                <path d="M5.6 7V5.2a2.4 2.4 0 0 1 4.8 0V7" />
              </svg>
              Locked
            </span>
          {/if}
        </li>
      {/each}
    </ol>

    {#if !complete}
      <footer class="ob-foot">
        {#if skipped}
          <span class="foot-note">Guided order turned off — every drill is open.</span>
          <button class="ob-link" type="button" on:click={() => dispatch('unskip')}>Turn it back on</button>
        {:else if confirmingSkip}
          <span class="foot-note foot-warn">
            This opens every drill at once, including ones that assume earlier practice.
          </span>
          <button class="ob-link" type="button" on:click={() => (confirmingSkip = false)}>Cancel</button>
          <button class="ob-cta cta-quiet" type="button" on:click={requestSkip}>Unlock everything</button>
        {:else}
          <button class="ob-link foot-skip" type="button" on:click={requestSkip}>Skip the tutorial →</button>
        {/if}
      </footer>
    {/if}
    </div>
  </section>
{:else if variant === 'strip'}
  <section class="ob-strip" aria-label={`${title}: ${done} of ${total} complete`}>
    <div class="strip-meter">
      <span class="strip-count">{done}/{total}</span>
      <span class="strip-track" aria-hidden="true">
        <span class="strip-fill" style={`width: ${percent}%;`}></span>
      </span>
    </div>

    <p class="strip-copy">
      {#if complete}
        <strong>Setup complete.</strong> Nothing left to do here.
      {:else}
        <strong>Next:</strong> {nextStep?.label}
        <small>{nextStep?.hint}</small>
      {/if}
    </p>

    {#if !complete && nextStep}
      <button class="ob-cta" type="button" on:click={() => act(nextStep.id)}>{nextStep.cta}</button>
    {/if}

    {#if dismissible}
      <button class="ob-dismiss" type="button" aria-label="Dismiss checklist" on:click={() => dispatch('dismiss')}>×</button>
    {/if}
  </section>
{:else}
  <section class="ob-banner" aria-label={`${title}: ${done} of ${total} complete`}>
    <span class="banner-dots" aria-hidden="true">
      {#each steps as step (step.id)}
        <span class="banner-dot" class:dot-done={step.done}></span>
      {/each}
    </span>

    <p class="banner-copy">
      {#if complete}
        Setup complete — nice work.
      {:else}
        <strong>{done} of {total} done.</strong> {nextStep?.label}
      {/if}
    </p>

    {#if !complete && nextStep}
      <button class="ob-link" type="button" on:click={() => act(nextStep.id)}>{nextStep.cta} →</button>
    {/if}

    {#if dismissible}
      <button class="ob-dismiss" type="button" aria-label="Dismiss checklist" on:click={() => dispatch('dismiss')}>×</button>
    {/if}
  </section>
{/if}

<style>
  /* ---- shared controls ---- */
  .ob-cta,
  .ob-link,
  .ob-dismiss {
    font: inherit;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s, color 0.15s, transform 0.07s;
  }

  .ob-cta {
    padding: 0.4rem 0.8rem;
    border-radius: 9px;
    border: 1px solid var(--accent, #4c8);
    background: var(--accent, #4c8);
    color: var(--bg, #fff);
    font-size: 0.78rem;
    font-weight: 600;
    white-space: nowrap;
  }

  .ob-cta:hover {
    background: var(--accent-strong, var(--accent, #4c8));
  }

  .ob-link {
    padding: 0.4rem 0.55rem;
    border-radius: 9px;
    border: 1px solid transparent;
    background: transparent;
    color: var(--muted, #666);
    font-size: 0.78rem;
    white-space: nowrap;
  }

  .ob-link:hover {
    border-color: var(--line, rgba(0, 0, 0, 0.14));
    color: var(--text, #111);
  }

  .ob-cta:active,
  .ob-link:active,
  .ob-dismiss:active {
    transform: scale(0.95);
  }

  .ob-dismiss {
    flex: none;
    width: 1.7rem;
    height: 1.7rem;
    line-height: 1;
    border-radius: 999px;
    border: 1px solid transparent;
    background: transparent;
    color: var(--muted, #666);
    font-size: 1.15rem;
  }

  .ob-dismiss:hover {
    border-color: var(--line, rgba(0, 0, 0, 0.14));
    color: var(--text, #111);
  }

  /* ---- variant: card ---- */
  .ob-card {
    padding: 1.1rem 1.2rem 0.6rem;
    border-radius: 16px;
    border: 1px solid var(--line, rgba(0, 0, 0, 0.14));
    background: var(--surface, rgba(255, 255, 255, 0.7));
    box-shadow: var(--shadow, 0 18px 38px -26px rgba(0, 0, 0, 0.4));
  }

  .ob-card-head {
    display: flex;
    align-items: flex-start;
    gap: 0.9rem;
  }

  .ob-card-copy {
    flex: 1;
    min-width: 0;
  }

  .ob-card-copy h3 {
    margin: 0.1rem 0 0.2rem;
    font-size: 1.05rem;
  }

  .ob-card-copy p {
    margin: 0;
    font-size: 0.82rem;
    line-height: 1.45;
    color: var(--muted, #666);
  }

  .ob-ring {
    position: relative;
    flex: none;
    width: 52px;
    height: 52px;
  }

  .ob-ring svg {
    width: 52px;
    height: 52px;
    transform: rotate(-90deg);
  }

  .ring-track,
  .ring-fill {
    fill: none;
    stroke-width: 4;
  }

  .ring-track {
    stroke: var(--line, rgba(0, 0, 0, 0.14));
  }

  .ring-fill {
    stroke: var(--accent, #4c8);
    stroke-linecap: round;
    transition: stroke-dashoffset 0.4s ease;
  }

  .ring-label {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.88rem;
    font-weight: 700;
  }

  .ring-label small {
    font-size: 0.62rem;
    font-weight: 500;
    color: var(--muted, #666);
  }

  .ob-list {
    margin: 0.9rem 0 0;
    padding: 0;
    list-style: none;
  }

  .ob-item {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.55rem 0.15rem;
    border-top: 1px solid var(--line, rgba(0, 0, 0, 0.1));
  }

  .ob-item.item-next {
    /* Only the active step gets a tint; a fully highlighted list reads as noise. */
    margin: 0 -0.5rem;
    padding: 0.6rem 0.65rem;
    border-radius: 11px;
    border-top-color: transparent;
    background: var(--accent-soft, rgba(0, 0, 0, 0.05));
  }

  .ob-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: none;
    width: 1.25rem;
    height: 1.25rem;
    border-radius: 999px;
    border: 1.5px solid var(--line-strong, rgba(0, 0, 0, 0.24));
    color: var(--bg, #fff);
  }

  .item-done .ob-mark {
    border-color: var(--accent, #4c8);
    background: var(--accent, #4c8);
  }

  .item-next .ob-mark {
    border-color: var(--accent, #4c8);
    border-style: dashed;
  }

  .ob-text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.12rem;
  }

  .ob-text strong {
    font-size: 0.88rem;
    font-weight: 600;
  }

  .item-done .ob-text strong {
    color: var(--muted, #666);
    text-decoration: line-through;
    text-decoration-color: var(--line-strong, rgba(0, 0, 0, 0.3));
  }

  .ob-text small {
    font-size: 0.75rem;
    line-height: 1.4;
    color: var(--muted, #666);
  }

  .ob-status {
    font-size: 0.72rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--muted, #666);
  }

  .ob-locked {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    opacity: 0.75;
  }

  /* ---- collapse ---- */
  .ob-collapse {
    flex: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.8rem;
    height: 1.8rem;
    border-radius: 999px;
    border: 1px solid var(--line, rgba(0, 0, 0, 0.14));
    background: transparent;
    color: var(--muted, #666);
    cursor: pointer;
    transition: transform 0.2s ease, color 0.15s, border-color 0.15s;
  }

  .ob-collapse:hover {
    color: var(--text, #111);
    border-color: var(--line-strong, rgba(0, 0, 0, 0.24));
  }

  .ob-collapse.is-collapsed {
    transform: rotate(-90deg);
  }

  .head-next {
    color: var(--text, #111);
  }

  /* ---- arcade tick-over ----
     Fires the moment a step lands, not on the next reload: the row flashes to
     the accent, the tick pops, and the status reads "Cleared!" for a beat. */
  .item-landed {
    animation: ob-land 1.3s ease-out both;
  }

  .item-landed .ob-mark {
    animation: ob-mark-pop 0.55s cubic-bezier(0.34, 1.7, 0.5, 1) both;
  }

  .status-landed {
    color: var(--accent-strong, var(--accent, #4c8));
    font-weight: 800;
    animation: ob-blink 0.28s steps(1, end) 4;
  }

  @keyframes ob-land {
    0% {
      background: color-mix(in srgb, var(--accent, #4c8) 55%, transparent);
      box-shadow: inset 0 0 0 1px var(--accent, #4c8);
    }
    45% {
      background: color-mix(in srgb, var(--accent, #4c8) 22%, transparent);
    }
    100% {
      background: transparent;
      box-shadow: none;
    }
  }

  @keyframes ob-mark-pop {
    0% { transform: scale(0.3) rotate(-25deg); }
    60% { transform: scale(1.35) rotate(6deg); }
    100% { transform: scale(1) rotate(0); }
  }

  @keyframes ob-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.25; }
  }

  @media (prefers-reduced-motion: reduce) {
    .item-landed,
    .item-landed .ob-mark,
    .status-landed {
      animation: none;
    }
  }

  .cta-quiet {
    border-color: var(--line-strong, rgba(0, 0, 0, 0.2));
    background: transparent;
    color: var(--text, #111);
  }

  .cta-quiet:hover {
    background: var(--accent-soft, rgba(0, 0, 0, 0.06));
  }

  .ob-foot {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.45rem;
    margin: 0 -0.15rem;
    padding: 0.6rem 0.15rem 0.25rem;
    border-top: 1px solid var(--line, rgba(0, 0, 0, 0.1));
  }

  .foot-note {
    flex: 1;
    min-width: 12rem;
    font-size: 0.74rem;
    line-height: 1.4;
    color: var(--muted, #666);
  }

  .foot-warn {
    color: var(--danger, #b33);
  }

  /* The escape hatch stays available but never competes with the active step. */
  .foot-skip {
    margin-left: auto;
    font-size: 0.75rem;
  }

  /* ---- variant: strip ---- */
  .ob-strip {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    padding: 0.6rem 0.7rem 0.6rem 0.9rem;
    border-radius: 12px;
    border: 1px solid var(--line, rgba(0, 0, 0, 0.14));
    background: var(--surface, rgba(255, 255, 255, 0.7));
  }

  .strip-meter {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: none;
  }

  .strip-count {
    font-size: 0.76rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  .strip-track {
    display: block;
    width: 4.5rem;
    height: 5px;
    border-radius: 999px;
    background: var(--line, rgba(0, 0, 0, 0.14));
    overflow: hidden;
  }

  .strip-fill {
    display: block;
    height: 100%;
    border-radius: 999px;
    background: var(--accent, #4c8);
    transition: width 0.35s ease;
  }

  .strip-copy {
    flex: 1;
    min-width: 0;
    margin: 0;
    font-size: 0.82rem;
    line-height: 1.35;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .strip-copy small {
    margin-left: 0.4rem;
    font-size: 0.75rem;
    color: var(--muted, #666);
  }

  /* ---- variant: banner ---- */
  .ob-banner {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.5rem 0.6rem 0.5rem 0.85rem;
    border-radius: 999px;
    border: 1px solid var(--line, rgba(0, 0, 0, 0.14));
    background: var(--surface, rgba(255, 255, 255, 0.7));
  }

  .banner-dots {
    display: inline-flex;
    gap: 4px;
    flex: none;
  }

  .banner-dot {
    width: 6px;
    height: 6px;
    border-radius: 999px;
    background: var(--line-strong, rgba(0, 0, 0, 0.22));
  }

  .banner-dot.dot-done {
    background: var(--accent, #4c8);
  }

  .banner-copy {
    flex: 1;
    min-width: 0;
    margin: 0;
    font-size: 0.8rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--muted, #666);
  }

  .banner-copy strong {
    color: var(--text, #111);
  }

  @media (max-width: 640px) {
    .ob-strip {
      flex-wrap: wrap;
    }

    .strip-copy {
      order: 3;
      flex-basis: 100%;
      white-space: normal;
    }

    .strip-copy small {
      display: block;
      margin-left: 0;
    }
  }
</style>
