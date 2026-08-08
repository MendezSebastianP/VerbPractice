<script lang="ts" context="module">
  /**
   * A gated step hides Next and waits for the learner to do the thing itself.
   * That is the difference between being told where a control is and having
   * used it once.
   */
  export type TourGate =
    /** Advance when this element is clicked. */
    | { kind: 'click'; selector: string; nudge: string }
    /** Advance when this key is pressed anywhere. */
    | { kind: 'key'; key: string; nudge: string }
    /**
     * Advance when the host signals it. The host owns the condition — used for
     * "they typed the right answer", "the session moved on", and similar.
     */
    | { kind: 'signal'; name: string; nudge: string };

  export interface TourStep {
    id: string;
    /**
     * CSS selector resolved inside `root` (or the document when no root is set).
     * `null` renders a centred card with no cut-out — used for welcome and
     * sign-off steps that are not about any one control.
     */
    target: string | null;
    title: string;
    body: string;
    /**
     * Extra selectors folded into the spotlight when they are on screen. For
     * panels that open next to the anchor — a language dropdown, say — so the
     * thing the learner is being told to use does not sit outside the cut-out.
     */
    extraTargets?: string[];
    /** Preferred side; the engine flips it when the popover would leave the viewport. */
    placement?: 'top' | 'bottom' | 'left' | 'right';
    /** Blocks Next until the learner performs the action. */
    gate?: TourGate;
    /** Lets clicks through the scrim so the learner can reach the target. */
    interactive?: boolean;
    /** Hides Skip on steps that are the point of the exercise. */
    noSkip?: boolean;
  }
</script>

<script lang="ts">
  import { createEventDispatcher, onMount, tick } from 'svelte';

  export let steps: TourStep[] = [];
  export let open = false;
  /** 'intro' is the light first-run pass; 'feature' is the in-context one. */
  export let tone: 'intro' | 'feature' = 'feature';
  /** Scope for target lookup so several tours can coexist on one page. */
  export let root: HTMLElement | null = null;
  /** Breathing room around the cut-out, in px. */
  export let padding = 8;
  /** Label for the final button. */
  export let finishLabel = 'Got it';

  const dispatch = createEventDispatcher<{
    finish: void;
    skip: { at: number };
    step: { index: number; id: string };
    /** The step's anchor left the page — the tour has closed itself. */
    lost: { id: string; target: string };
  }>();

  interface Box {
    top: number;
    left: number;
    width: number;
    height: number;
    radius: number;
  }

  let index = 0;
  let box: Box | null = null;
  let popoverEl: HTMLElement | null = null;
  let popoverStyle = 'visibility: hidden;';
  let arrowStyle = '';
  let resolvedPlacement: 'top' | 'bottom' | 'left' | 'right' | 'center' = 'bottom';
  /** Set once the current step's gate is satisfied. */
  let gateOpen = false;
  /** Pending grace period before giving up on a missing anchor. */
  let missTimer = 0;

  $: step = steps[index] ?? null;
  $: total = steps.length;
  $: gated = Boolean(step?.gate) && !gateOpen;
  // The page always stays reachable. A modal scrim reads as a bug the moment a
  // step says "set your languages" and the dropdowns underneath do not respond —
  // and every step here either asks for an action or is safe to click past.
  $: letClicksThrough = true;

  /**
   * Called by the host when a 'signal' gate is met. Named signals keep the
   * engine ignorant of trainer internals — it only knows a step is waiting.
   */
  /**
   * Returns whether the running step was actually waiting on this signal. The
   * host uses that to decide between "the tour advances by itself" and "the
   * script needs rebuilding for a branch it did not anticipate" — doing both
   * races a restart against the advance and the tour ends up closed.
   */
  export function fireSignal(name: string): boolean {
    if (open && step?.gate?.kind === 'signal' && step.gate.name === name) {
      openGate();
      return true;
    }
    return false;
  }

  function openGate(): void {
    if (gateOpen) return;
    gateOpen = true;
    // Give the learner a beat to see the result of what they just did.
    window.setTimeout(() => {
      if (open && gateOpen) next();
    }, 620);
  }

  function onGateClick(event: MouseEvent): void {
    const gate = step?.gate;
    if (!open || !gated || gate?.kind !== 'click') return;
    const target = event.target as HTMLElement | null;
    if (target?.closest(gate.selector)) {
      openGate();
    }
  }

  function onGateKey(event: KeyboardEvent): void {
    const gate = step?.gate;
    if (!open || !gated || gate?.kind !== 'key') return;
    if (event.key === gate.key) {
      openGate();
    }
  }

  function reduceMotion(): boolean {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function findTarget(): HTMLElement | null {
    if (!step || !step.target) return null;
    const scope: ParentNode = root ?? document;
    return scope.querySelector<HTMLElement>(step.target);
  }

  function centreCard(): void {
    box = null;
    resolvedPlacement = 'center';
    popoverStyle = 'top: 50%; left: 50%; transform: translate(-50%, -50%);';
    arrowStyle = 'display: none;';
  }

  function measure(): void {
    if (step && step.target === null) {
      centreCard();
      return;
    }

    const el = findTarget();
    if (!el) {
      // The anchor left the page — the learner navigated, or a drill replaced
      // the setup screen. Bow out rather than hovering over nothing: a stranded
      // popover pointing at a control that no longer exists is worse than no
      // tour at all.
      //
      // Grace period first: a keyed block re-rendering removes and re-adds its
      // node within a frame, and closing on that would kill the tour every time
      // the trainer swapped prompts.
      if (missTimer) return;
      missTimer = window.setTimeout(() => {
        missTimer = 0;
        if (!open) return;
        if (findTarget()) {
          measure();
          return;
        }
        const lost = step;
        close();
        if (lost) {
          // Reported as a skip so the host records the tour as seen; without
          // that the "not seen yet" check re-opens it and the pair loops.
          dispatch('lost', { id: lost.id, target: lost.target ?? '' });
          dispatch('skip', { at: index });
        }
      }, 320);
      return;
    }

    if (missTimer) {
      window.clearTimeout(missTimer);
      missTimer = 0;
    }

    const rect = el.getBoundingClientRect();
    const computed = window.getComputedStyle(el);
    const radius = parseFloat(computed.borderTopLeftRadius) || 0;

    // Grow the cut-out over any companion panel that is currently open, so an
    // expanded dropdown is lit rather than left in the dark below the ring.
    let top = rect.top;
    let left = rect.left;
    let right = rect.right;
    let bottom = rect.bottom;
    const scope: ParentNode = root ?? document;
    for (const selector of step?.extraTargets ?? []) {
      for (const extra of Array.from(scope.querySelectorAll<HTMLElement>(selector))) {
        const r = extra.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        top = Math.min(top, r.top);
        left = Math.min(left, r.left);
        right = Math.max(right, r.right);
        bottom = Math.max(bottom, r.bottom);
      }
    }

    box = {
      top: top - padding,
      left: left - padding,
      width: right - left + padding * 2,
      height: bottom - top + padding * 2,
      radius: radius + padding / 2,
    };

    positionPopover(box);
  }

  function positionPopover(anchor: Box): void {
    if (!popoverEl) {
      return;
    }

    const gap = 12;
    const margin = 12;
    // Extra headroom so a tall card never slides under the fixed nav bar. It has
    // to be the same number the clamp below uses: measuring "does it fit above?"
    // against 12px and then clamping to 76px pushed the card back down over the
    // very control it was pointing at.
    const topMargin = 76;
    const pop = popoverEl.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    const room = {
      bottom: vh - (anchor.top + anchor.height) - gap - margin,
      top: anchor.top - gap - topMargin,
      right: vw - (anchor.left + anchor.width) - gap - margin,
      left: anchor.left - gap - margin,
    };
    const needed = { bottom: pop.height, top: pop.height, right: pop.width, left: pop.width };

    const preferred = step?.placement ?? 'bottom';
    const opposite = { bottom: 'top', top: 'bottom', left: 'right', right: 'left' } as const;
    const order: Array<'top' | 'bottom' | 'left' | 'right'> = [
      preferred,
      opposite[preferred],
      'bottom',
      'top',
      'right',
      'left',
    ];

    const fitting = order.find((side) => room[side] >= needed[side]);
    // Nothing fits on a small screen: fall back to whichever side has the most
    // room so the card still lands beside the anchor rather than on top of it.
    resolvedPlacement =
      fitting
      ?? (Object.keys(room) as Array<'top' | 'bottom' | 'left' | 'right'>).reduce((best, side) =>
        room[side] - needed[side] > room[best] - needed[best] ? side : best,
      );

    let top = 0;
    let left = 0;

    if (resolvedPlacement === 'bottom' || resolvedPlacement === 'top') {
      left = anchor.left + anchor.width / 2 - pop.width / 2;
      top = resolvedPlacement === 'bottom' ? anchor.top + anchor.height + gap : anchor.top - gap - pop.height;
    } else {
      top = anchor.top + anchor.height / 2 - pop.height / 2;
      left = resolvedPlacement === 'right' ? anchor.left + anchor.width + gap : anchor.left - gap - pop.width;
    }

    const clampedLeft = Math.max(margin, Math.min(left, vw - pop.width - margin));
    const clampedTop = Math.max(topMargin, Math.min(top, vh - pop.height - margin));
    popoverStyle = `top: ${clampedTop}px; left: ${clampedLeft}px;`;

    // Point the arrow back at the anchor centre after clamping moved the card.
    const anchorCx = anchor.left + anchor.width / 2;
    const anchorCy = anchor.top + anchor.height / 2;
    if (resolvedPlacement === 'bottom' || resolvedPlacement === 'top') {
      const x = Math.max(16, Math.min(anchorCx - clampedLeft, pop.width - 16));
      arrowStyle = `left: ${x}px;`;
    } else {
      const y = Math.max(16, Math.min(anchorCy - clampedTop, pop.height - 16));
      arrowStyle = `top: ${y}px;`;
    }
  }

  async function goTo(next: number): Promise<void> {
    index = Math.max(0, Math.min(next, total - 1));
    gateOpen = false;
    popoverStyle = 'visibility: hidden;';
    await tick();

    const el = findTarget();
    if (el) {
      el.scrollIntoView({
        behavior: reduceMotion() ? 'auto' : 'smooth',
        block: 'center',
        inline: 'nearest',
      });
      // Let the smooth scroll settle, or the cut-out lands where the target was.
      await new Promise((resolve) => window.setTimeout(resolve, reduceMotion() ? 0 : 320));
    }

    measure();
    await tick();

    if (step?.gate) {
      // A gated step is waiting for the learner to act on the page, so the
      // popover must not take focus — otherwise their Enter lands on the tour
      // card instead of the trainer, and the gate can never open. Put the caret
      // in the target field when there is one; the aria-live nudge still
      // announces what to do.
      const el = findTarget();
      const field =
        el && (el.matches('input, textarea') ? el : el.querySelector('input, textarea'));
      (field as HTMLElement | null)?.focus({ preventScroll: true });
    } else {
      popoverEl?.focus({ preventScroll: true });
    }

    if (step) {
      dispatch('step', { index, id: step.id });
    }
  }

  function next(): void {
    if (index >= total - 1) {
      finish();
      return;
    }
    void goTo(index + 1);
  }

  function prev(): void {
    if (index === 0) return;
    void goTo(index - 1);
  }

  function finish(): void {
    open = false;
    dispatch('finish');
  }

  function skip(): void {
    const at = index;
    open = false;
    dispatch('skip', { at });
  }

  export function start(): void {
    if (!steps.length) return;
    // Hide before opening. Without this the card paints one frame at the
    // previous run's coordinates — a flash of the old position carrying the new
    // step's text, right as a prompt changes.
    popoverStyle = 'visibility: hidden;';
    box = null;
    gateOpen = false;
    open = true;
    index = 0;
    void goTo(0);
  }

  /** Shut the tour down without firing finish/skip — used when the host takes over. */
  export function close(): void {
    open = false;
    gateOpen = false;
    if (missTimer) {
      window.clearTimeout(missTimer);
      missTimer = 0;
    }
    box = null;
    popoverStyle = 'visibility: hidden;';
  }

  function onKeydown(event: KeyboardEvent): void {
    if (!open) return;
    onGateKey(event);
    if (event.key === 'Escape') {
      if (step?.noSkip) return;
      event.preventDefault();
      skip();
      return;
    }
    // While a gate is open the keyboard belongs to the trainer underneath —
    // stealing Enter here would submit nothing and eat the learner's answer.
    if (gated) return;
    if (event.key === 'ArrowRight' || event.key === 'Enter') {
      event.preventDefault();
      next();
      return;
    }
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      prev();
    }
  }

  function reflow(): void {
    if (open) measure();
  }

  let mutationFrame = 0;

  onMount(() => {
    // Layout shifts (fonts, responsive reflow) move the anchor after the first
    // measurement, so keep the cut-out attached to it.
    const resize = new ResizeObserver(() => reflow());
    resize.observe(document.body);

    // A dropdown opening is absolutely positioned, so it changes no layout the
    // ResizeObserver can see. Watch the tree instead, coalesced to one frame.
    const mutations = new MutationObserver(() => {
      if (!open || mutationFrame) return;
      mutationFrame = window.requestAnimationFrame(() => {
        mutationFrame = 0;
        reflow();
      });
    });
    mutations.observe(document.body, { childList: true, subtree: true });

    return () => {
      resize.disconnect();
      mutations.disconnect();
      if (mutationFrame) window.cancelAnimationFrame(mutationFrame);
    };
  });

  $: if (open && steps.length && index >= steps.length) {
    index = steps.length - 1;
  }
</script>

<svelte:window on:keydown={onKeydown} on:resize={reflow} on:scroll={reflow} />
<svelte:document on:click={onGateClick} />

{#if open && step}
  <div class={`tour-layer tone-${tone}`} class:layer-passthrough={letClicksThrough}>
    {#if box}
      <!-- One element: a huge spread box-shadow paints the scrim everywhere
           except the rounded cut-out. -->
      <div
        class="tour-cutout"
        class:no-motion={reduceMotion()}
        style={`top: ${box.top}px; left: ${box.left}px; width: ${box.width}px; height: ${box.height}px; border-radius: ${box.radius}px;`}
        aria-hidden="true"
      ></div>
    {:else}
      <div class="tour-scrim" aria-hidden="true"></div>
    {/if}

    <div
      bind:this={popoverEl}
      class={`tour-pop place-${resolvedPlacement}`}
      style={popoverStyle}
      role="dialog"
      aria-modal="true"
      aria-labelledby="tour-title"
      aria-describedby="tour-body"
      tabindex="-1"
    >
      {#if resolvedPlacement !== 'center'}
        <span class="tour-arrow" style={arrowStyle} aria-hidden="true"></span>
      {/if}

      {#if total > 1}
        <p class="tour-count" aria-live="polite">Step {index + 1} of {total}</p>
      {/if}
      <h3 id="tour-title">{step.title}</h3>
      <p id="tour-body" class="tour-body">{step.body}</p>

      {#if step.gate}
        <p class="tour-nudge" class:nudge-done={gateOpen} aria-live="polite">
          {#if gateOpen}
            <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M3 8.4l3.2 3.2L13 5" />
            </svg>
            Nice.
          {:else}
            <span class="nudge-pip" aria-hidden="true"></span>
            {step.gate.nudge}
          {/if}
        </p>
      {/if}

      <div class="tour-actions">
        {#if total > 1}
          <div class="tour-dots" aria-hidden="true">
            {#each steps as entry, dotIndex (entry.id)}
              <span class="tour-dot" class:dot-on={dotIndex === index} class:dot-done={dotIndex < index}></span>
            {/each}
          </div>
        {:else}
          <span></span>
        {/if}

        <div class="tour-move">
          {#if index > 0 && !step.gate}
            <button class="tour-ghost" type="button" on:click={prev}>Back</button>
          {:else if total > 1 && !step.noSkip}
            <button class="tour-ghost" type="button" on:click={skip}>Skip</button>
          {/if}
          {#if !gated}
            <button class="tour-next" type="button" on:click={next}>
              {index >= total - 1 ? finishLabel : 'Next'}
            </button>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .tour-layer {
    position: fixed;
    inset: 0;
    z-index: 120;
    /* The layer never eats clicks; only the popover and scrim do. */
    pointer-events: none;
  }

  .tour-scrim {
    position: absolute;
    inset: 0;
    background: rgba(8, 10, 14, 0.62);
    pointer-events: auto;
  }

  .tour-cutout {
    position: absolute;
    box-shadow: 0 0 0 9999px rgba(8, 10, 14, 0.62);
    border: 2px solid var(--accent, #4c8);
    pointer-events: auto;
    transition: top 0.24s ease, left 0.24s ease, width 0.24s ease, height 0.24s ease;
  }

  /* Gated steps need the learner to actually reach the control, so the scrim
     stops swallowing clicks and the cut-out ring pulses to say "here". */
  .layer-passthrough .tour-cutout,
  .layer-passthrough .tour-scrim {
    pointer-events: none;
  }

  .layer-passthrough .tour-cutout {
    animation: tour-ring 1.5s ease-in-out infinite;
  }

  @keyframes tour-ring {
    0%, 100% {
      border-color: var(--accent, #4c8);
    }
    50% {
      border-color: color-mix(in srgb, var(--accent, #4c8) 35%, transparent);
    }
  }

  /* The intro pass stays deliberately lighter than the in-feature one. */
  .tone-intro .tour-cutout {
    box-shadow: 0 0 0 9999px rgba(8, 10, 14, 0.48);
  }

  .tone-intro .tour-scrim {
    background: rgba(8, 10, 14, 0.48);
  }

  .tour-cutout.no-motion {
    transition: none;
  }

  .tour-pop {
    position: absolute;
    width: min(21rem, calc(100vw - 2rem));
    padding: 1rem 1.1rem 0.85rem;
    border-radius: 14px;
    border: 1px solid var(--line-strong, rgba(0, 0, 0, 0.2));
    background: var(--surface-strong, #fff);
    color: var(--text, #111);
    box-shadow: 0 24px 70px -24px rgba(0, 0, 0, 0.6);
    pointer-events: auto;
    text-align: left;
  }

  .tour-pop.place-center {
    width: min(24rem, calc(100vw - 2rem));
    text-align: center;
  }

  .place-center .tour-actions {
    justify-content: center;
  }

  .tour-pop:focus-visible {
    outline: 2px solid var(--accent, #4c8);
    outline-offset: 3px;
  }

  .tour-arrow {
    position: absolute;
    width: 12px;
    height: 12px;
    background: inherit;
    border: 1px solid var(--line-strong, rgba(0, 0, 0, 0.2));
    transform: rotate(45deg);
  }

  .place-bottom .tour-arrow {
    top: -7px;
    margin-left: -6px;
    border-right: 0;
    border-bottom: 0;
  }

  .place-top .tour-arrow {
    bottom: -7px;
    margin-left: -6px;
    border-left: 0;
    border-top: 0;
  }

  .place-right .tour-arrow {
    left: -7px;
    margin-top: -6px;
    border-right: 0;
    border-top: 0;
  }

  .place-left .tour-arrow {
    right: -7px;
    margin-top: -6px;
    border-left: 0;
    border-bottom: 0;
  }

  .tour-count {
    margin: 0 0 0.3rem;
    font-size: 0.68rem;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--muted, #666);
  }

  .tour-pop h3 {
    margin: 0 0 0.35rem;
    font-size: 1.02rem;
    line-height: 1.25;
  }

  .tour-body {
    margin: 0 0 0.8rem;
    font-size: 0.86rem;
    line-height: 1.5;
    color: var(--muted, #555);
  }



  .tour-nudge {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin: 0 0 0.75rem;
    padding: 0.42rem 0.6rem;
    border-radius: 9px;
    background: var(--accent-soft, rgba(0, 0, 0, 0.06));
    color: var(--accent-strong, var(--accent, #4c8));
    font-size: 0.79rem;
    font-weight: 600;
    line-height: 1.4;
  }

  .nudge-pip {
    flex: none;
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: currentColor;
    animation: tour-pip 1.1s ease-in-out infinite;
  }

  .nudge-done {
    background: color-mix(in srgb, var(--success, #4c8) 16%, transparent);
    color: var(--success, #4c8);
  }

  @keyframes tour-pip {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.35; transform: scale(0.75); }
  }

  .tour-dots {
    display: flex;
    gap: 5px;
  }

  .tour-dot {
    width: 6px;
    height: 6px;
    border-radius: 999px;
    background: var(--line-strong, rgba(0, 0, 0, 0.2));
    transition: width 0.2s ease, background 0.2s ease;
  }

  .tour-dot.dot-done {
    background: color-mix(in srgb, var(--accent, #4c8) 55%, transparent);
  }

  .tour-dot.dot-on {
    width: 18px;
    background: var(--accent, #4c8);
  }

  .tour-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .tour-move {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .tour-ghost,
  .tour-next {
    border-radius: 9px;
    font: inherit;
    font-size: 0.8rem;
    cursor: pointer;
    padding: 0.42rem 0.75rem;
    transition: background 0.15s, border-color 0.15s, transform 0.07s;
  }

  .tour-ghost {
    border: 1px solid transparent;
    background: transparent;
    color: var(--muted, #666);
  }

  .tour-ghost:hover {
    border-color: var(--line, rgba(0, 0, 0, 0.15));
    color: var(--text, #111);
  }

  .tour-next {
    border: 1px solid var(--accent, #4c8);
    background: var(--accent, #4c8);
    color: var(--bg, #fff);
    font-weight: 600;
  }

  .tour-next:hover {
    background: var(--accent-strong, var(--accent, #4c8));
  }

  .tour-next:active,
  .tour-ghost:active {
    transform: scale(0.96);
  }

  @media (prefers-reduced-motion: reduce) {
    .tour-cutout,
    .tour-dot {
      transition: none;
    }

    .layer-passthrough .tour-cutout,
    .nudge-pip {
      animation: none;
    }
  }
</style>
