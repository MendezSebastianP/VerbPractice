<script lang="ts">
  import { onMount } from 'svelte';
  import DesktopTableConcept from '../components/playground/DesktopTableConcept.svelte';
  import { navigate } from '../router';

  let previewTheme: 'light' | 'dark' | 'arcade' = 'arcade';

  function setTheme(next: 'light' | 'dark' | 'arcade'): void {
    previewTheme = next;
    document.documentElement.setAttribute('data-theme', next);
  }

  onMount(() => {
    const active = document.documentElement.getAttribute('data-theme');
    previewTheme = active === 'light' || active === 'dark' || active === 'arcade' ? active : 'arcade';
  });
</script>

<section class="desktop-bench-shell">
  <header class="glass-panel strong-panel desktop-bench-header">
    <div>
      <p class="eyebrow">Playground · Desktop table workshop</p>
      <h1>V1 grows into desktop.</h1>
      <p class="section-copy">
        The chosen V1 arcade-glass frame and P3 cartridge bolt are locked. These three live desktop options preserve
        the real table flow while testing how much information should remain visible around the active answer.
      </p>
    </div>
    <div class="bench-actions">
      <div class="theme-row" role="group" aria-label="Preview theme">
        <button class:theme-on={previewTheme === 'light'} type="button" on:click={() => setTheme('light')}>Light</button>
        <button class:theme-on={previewTheme === 'dark'} type="button" on:click={() => setTheme('dark')}>Dark</button>
        <button class:theme-on={previewTheme === 'arcade'} type="button" on:click={() => setTheme('arcade')}>Arcade</button>
      </div>
      <nav class="jump-row" aria-label="Jump to a prototype">
        <a href="#centered-ledger">D1 · Ledger</a>
        <a href="#split-workbench">D2 · Split</a>
        <a href="#focus-console">D3 · Focus</a>
      </nav>
      <button class="text-switch" type="button" on:click={() => navigate('/training/verbs')}>Open working Verb Lab →</button>
    </div>
  </header>

  <section class="constraint-deck" aria-label="Prototype rules">
    <div><span>V1</span><strong>Frame locked</strong><small>Violet glass, warm-yellow focus, restrained grid atmosphere</small></div>
    <div><span>P3</span><strong>Icon locked</strong><small>Pixel cartridge shows armed, spent, accepted, and guard states</small></div>
    <div><span>G1</span><strong>Rules preserved</strong><small>One tense, top to bottom, feedback in place, then continue</small></div>
    <div><span>KB</span><strong>Keyboard first</strong><small>Enter, Backspace, Esc, F11, and empty-answer repeat remain visible</small></div>
  </section>

  <div class="comparison-heading">
    <span>ONE BEHAVIOR · THREE DESKTOP INFORMATION MODELS</span>
    <h2>How much of the table should stay visible while you answer?</h2>
    <p>
      Type <strong>vais</strong> in any first field to test quick-shot and its 600ms Enter guard. Complete a tense to see
      the selected in-place feedback behavior; each prototype is independent and resettable.
    </p>
  </div>

  <section class="desktop-concept-stack" aria-label="Desktop verb table layout comparison">
    <div id="centered-ledger">
      <DesktopTableConcept
        variant="centered-ledger"
        index="D1"
        kicker="Evolution · all rows visible"
        title="Centered Ledger"
        description="The safest evolution of G1: a stronger V1 hero, one centered answer column, P3 on the active row, and feedback replacing each input in place."
      />
    </div>
    <div id="split-workbench">
      <DesktopTableConcept
        variant="split-workbench"
        index="D2"
        kicker="Workbench · context beside answers"
        title="Split Workbench"
        description="The verb, tense, equation, and pronoun progress stay anchored on the left while a denser answer ledger owns the right side."
      />
    </div>
    <div id="focus-console">
      <DesktopTableConcept
        variant="focus-console"
        index="D3"
        kicker="Focus · one expanded answer"
        title="Focus Console"
        description="The active prompt receives the desktop stage while a left status rail keeps every pronoun visible; completion unfolds into a compact feedback board."
      />
    </div>
  </section>

  <article class="glass-panel decision-note">
    <div>
      <span>LOCKED IN ALL THREE DESKTOP OPTIONS</span>
      <h2>V1 palette, P3 signal, and the complete keyboard contract.</h2>
    </div>
    <p>
      The alternatives change information density, not learning rules. Nine tenses remain selectable, progress stays on
      both sides, long labels truncate safely, and the desktop prototypes never run phone viewport centering.
    </p>
  </article>
</section>

<style>
  .desktop-bench-shell {
    display: flex;
    width: min(100%, 1320px);
    margin-inline: auto;
    flex-direction: column;
    gap: clamp(1.4rem, 3vw, 2.6rem);
  }

  .desktop-bench-header {
    display: grid;
    grid-template-columns: minmax(0, 1.25fr) minmax(17rem, 0.75fr);
    gap: clamp(1.2rem, 4vw, 3.5rem);
    align-items: end;
    overflow: hidden;
    padding: clamp(1.25rem, 4vw, 2.4rem);
    background:
      radial-gradient(circle at 88% 15%, color-mix(in srgb, var(--accent) 22%, transparent), transparent 32%),
      linear-gradient(145deg, color-mix(in srgb, var(--surface-strong) 94%, transparent), var(--surface));
  }

  .desktop-bench-header h1 {
    max-width: 15ch;
    margin: 0.35rem 0 0.7rem;
    color: var(--text);
    font: 820 clamp(2.25rem, 5vw, 4.7rem)/0.95 var(--display);
    letter-spacing: -0.065em;
  }

  .desktop-bench-header .section-copy {
    max-width: 46rem;
    margin: 0;
  }

  .bench-actions {
    display: grid;
    justify-items: end;
    gap: 0.8rem;
  }

  .theme-row {
    display: flex;
    padding: 0.26rem;
    border: 1px solid var(--line);
    border-radius: 12px;
    background: color-mix(in srgb, var(--surface-strong) 78%, transparent);
  }

  .theme-row button {
    min-height: 36px;
    padding: 0.52rem 0.72rem;
    border: 0;
    border-radius: 8px;
    color: var(--muted);
    background: transparent;
    font-size: 0.74rem;
    font-weight: 760;
  }

  .theme-row .theme-on {
    color: var(--accent-strong);
    background: var(--accent-soft);
    box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--accent) 40%, transparent);
  }

  .jump-row {
    display: flex;
    gap: 0.5rem;
  }

  .jump-row a {
    display: grid;
    min-height: 38px;
    padding: 0.55rem 0.75rem;
    place-items: center;
    border: 1px solid var(--line-strong);
    border-radius: 10px;
    color: var(--text);
    background: color-mix(in srgb, var(--surface-strong) 82%, transparent);
    font-size: 0.7rem;
    font-weight: 760;
    text-decoration: none;
  }

  .constraint-deck {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    overflow: hidden;
    border: 1px solid var(--line);
    border-radius: 20px;
    background: color-mix(in srgb, var(--surface-strong) 72%, transparent);
  }

  .constraint-deck > div {
    display: grid;
    min-width: 0;
    grid-template-columns: auto 1fr;
    gap: 0.2rem 0.65rem;
    align-items: center;
    padding: 1rem;
  }

  .constraint-deck > div + div {
    border-left: 1px solid var(--line);
  }

  .constraint-deck span {
    display: grid;
    width: 2rem;
    height: 2rem;
    grid-row: 1 / 3;
    place-items: center;
    border: 1px solid var(--line-strong);
    border-radius: 9px;
    color: var(--accent-strong);
    font: 800 0.62rem/1 var(--mono);
  }

  .constraint-deck strong {
    color: var(--text);
    font-size: 0.85rem;
  }

  .constraint-deck small {
    color: var(--muted);
    font-size: 0.68rem;
    line-height: 1.35;
  }

  .comparison-heading {
    display: grid;
    max-width: 64rem;
    gap: 0.3rem;
  }

  .comparison-heading > span,
  .decision-note span {
    color: var(--accent-strong);
    font: 800 0.62rem/1 var(--mono);
    letter-spacing: 0.12em;
  }

  .comparison-heading h2,
  .decision-note h2 {
    margin: 0;
    color: var(--text);
    font: 800 clamp(1.35rem, 3vw, 2.25rem)/1.08 var(--display);
    letter-spacing: -0.04em;
  }

  .comparison-heading p {
    margin: 0.2rem 0 0;
    color: var(--muted);
    font-size: 0.88rem;
    line-height: 1.55;
  }

  .desktop-concept-stack {
    display: grid;
    grid-template-columns: 1fr;
    gap: clamp(3rem, 7vw, 5.5rem);
    align-items: start;
  }

  .desktop-concept-stack > div {
    min-width: 0;
    scroll-margin-top: 1rem;
  }

  .decision-note {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(18rem, 0.75fr);
    gap: 2rem;
    align-items: center;
    padding: clamp(1.2rem, 3vw, 2rem);
  }

  .decision-note div {
    display: grid;
    gap: 0.35rem;
  }

  .decision-note p {
    margin: 0;
    color: var(--muted);
    font-size: 0.84rem;
    line-height: 1.65;
  }

  @media (max-width: 820px) {
    .desktop-bench-header,
    .decision-note {
      grid-template-columns: 1fr;
    }

    .bench-actions {
      justify-items: start;
    }

    .constraint-deck {
      grid-template-columns: repeat(2, 1fr);
    }

    .constraint-deck > div:nth-child(3) {
      border-left: 0;
      border-top: 1px solid var(--line);
    }

    .constraint-deck > div:nth-child(4) {
      border-top: 1px solid var(--line);
    }
  }

  @media (max-width: 520px) {
    .desktop-bench-shell {
      gap: 1.6rem;
    }

    .desktop-bench-header {
      padding: 1.15rem;
    }

    .desktop-bench-header h1 {
      font-size: 2.35rem;
    }

    .constraint-deck {
      grid-template-columns: 1fr 1fr;
    }

    .constraint-deck > div {
      grid-template-columns: 1fr;
      align-content: start;
      padding: 0.8rem;
    }

    .constraint-deck span {
      width: 1.7rem;
      height: 1.7rem;
      grid-row: auto;
    }

    .constraint-deck > div:nth-child(odd) {
      border-left: 0;
    }

    .constraint-deck strong {
      font-size: 0.75rem;
    }

    .constraint-deck small {
      font-size: 0.62rem;
    }

    .comparison-heading h2 {
      font-size: 1.55rem;
    }

    .comparison-heading p {
      font-size: 0.78rem;
    }
  }
</style>
