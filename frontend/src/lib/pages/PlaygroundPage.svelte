<script lang="ts">
  import LaunchControlConcept from '../components/playground/LaunchControlConcept.svelte';
  import SideProgressConcept from '../components/playground/SideProgressConcept.svelte';
  import TableGameConcept from '../components/playground/TableGameConcept.svelte';
  import TableTransitionConcept from '../components/playground/TableTransitionConcept.svelte';
  import VerbSetupConcept from '../components/playground/VerbSetupConcept.svelte';
  import { navigate } from '../router';

  let previewTheme: 'light' | 'dark' | 'arcade' = 'light';

  function setTheme(next: 'light' | 'dark' | 'arcade'): void {
    previewTheme = next;
    document.documentElement.setAttribute('data-theme', next);
  }
</script>

<section class="pg-shell">
  <header class="glass-panel strong-panel pg-header">
    <div>
      <p class="eyebrow">Playground · Verb tables design bench</p>
      <h1>A1 and G1 are live. Three decisions remain.</h1>
      <p class="section-copy">Compare mirrored side progress, replacement launch controls, and three table-specific transitions. Every study stays isolated until you choose a production direction.</p>
    </div>
    <div class="pg-header-actions">
      <div class="pg-theme-row" role="group" aria-label="Preview theme">
        <button class:option-on={previewTheme === 'light'} class="option-chip" type="button" on:click={() => setTheme('light')}>Light</button>
        <button class:option-on={previewTheme === 'dark'} class="option-chip" type="button" on:click={() => setTheme('dark')}>Dark</button>
        <button class:option-on={previewTheme === 'arcade'} class="option-chip" type="button" on:click={() => setTheme('arcade')}>Arcade</button>
      </div>
      <button class="text-switch" type="button" on:click={() => navigate('/training/verbs')}>Open working Verb Lab →</button>
    </div>
  </header>

  <nav class="study-nav" aria-label="Playground studies">
    <a href="#setup-study"><span>01</span><strong>Chosen setup</strong><small>A1 · staircase</small></a>
    <a href="#game-study"><span>02</span><strong>Chosen game</strong><small>G1-B · final behavior</small></a>
    <a href="#progress-study"><span>03</span><strong>Side progress</strong><small>Three mirrored options</small></a>
    <a href="#launch-study"><span>04</span><strong>Launch control</strong><small>Three button options</small></a>
    <a href="#transition-study"><span>05</span><strong>Table transition</strong><small>Three animation options</small></a>
  </nav>

  <section class="study-section" id="setup-study">
    <header class="study-heading">
      <span class="study-index">01 / SETUP</span>
      <h2>A1 is the selected setup.</h2>
      <p>The explicit vertical staircase stays. Translate opens the unchanged production Verb Rush, while tables choose language, tense depth, guide difficulty, and run length.</p>
    </header>

    <div class="concept-stack">
      <VerbSetupConcept
        variant="staircase"
        index="A1"
        kicker="Original direction · refined"
        title="Climb from core to mastery"
        description="The chosen direction, now corrected with an unchanged Verb Rush handoff, visible shortcuts, fullscreen/help tools, and the same explicit cumulative steps."
      />
    </div>
  </section>

  <section class="study-section game-study" id="game-study">
    <header class="study-heading">
      <span class="study-index">02 / G1-B FINAL</span>
      <h2>All tense feedback appears at once.</h2>
      <p>G1’s large pronouns, one active column, visible guides, and top-to-bottom entry stay. The final answer grades every row in place; the following Enter opens the next tense.</p>
    </header>

    <div class="pointer-law glass-panel">
      <div class="law-head"><span>ENTER PATH</span><strong>One tense at a time</strong></div>
      <div class="law-track" aria-label="Pointer order">
        <div><span>01</span><strong>Fill Présent</strong><small>top ↓ guides skip ↓ final answer</small></div>
        <i>↪ CHECK HERE</i>
        <div><span>02</span><strong>All feedback in place</strong><small>right ✓ · wrong × · correction shown</small></div>
        <i>ENTER ↪ NEXT</i>
        <div><span>03</span><strong>Fill Imparfait</strong><small>only after Présent review is complete</small></div>
        <i class="submit-arrow">FINAL REVIEW = SUBMIT</i>
      </div>
    </div>

    <article class="giveaway-study glass-panel">
      <div class="giveaway-study-head">
        <span class="policy-shield" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path d="M12 3 5.5 5.6v5.8c0 4.2 2.7 7.5 6.5 9.6 3.8-2.1 6.5-5.4 6.5-9.6V5.6L12 3Z"></path><path d="m9 12 2 2 4-4"></path></svg>
        </span>
        <div><span>CORPUS CHECK · SPECIAL TENSE POLICY</span><h3>When one guide gives away the column</h3><p>The proposed automatic rule is visible in every prototype: exact giveaways and one-answer paradigms receive no locked guides.</p></div>
      </div>
      <div class="giveaway-cases">
        <div><span>EXACT</span><strong>English Future</strong><small>942/942 verbs · one form across all pronouns</small><em>go → will go × 6</em></div>
        <div><span>EXACT</span><strong>English Past</strong><small>936/942 verbs · six be-family exceptions</small><em>go → went × 6</em></div>
        <div><span>EXACT</span><strong>Russian быть · Present</strong><small>One form across all six rows</small><em>есть × 6</em></div>
        <div><span>ONE CELL</span><strong>French falloir</strong><small>Many tenses only have an il form</small><em>Présent → il faut</em></div>
      </div>
      <div class="giveaway-decision">
        <span>DECISION NEEDED</span><p><strong>English Present is not exact:</strong> 936/942 verbs have five base forms plus one third-person form. The current proposal allows guides there; the stricter alternative marks those near-uniform columns Special too.</p>
      </div>
    </article>

    <div class="concept-stack game-stack">
      <TableGameConcept
        variant="signal"
        index="G1"
        kicker="Selected · in-place tense feedback"
        title="See every result, then continue"
        description="The final answer grades the whole column at once. Correct forms, struck-through mistakes, and corrections stay in their rows; one Enter opens the next tense."
      />
    </div>
  </section>

  <section class="study-section decision-study" id="progress-study">
    <header class="study-heading">
      <span class="study-index">03 / SIDE PROGRESS</span>
      <h2>Progress leaves the top and frames the game.</h2>
      <p>All three options mirror the same verb progress on the left and right without competing with tense status inside G1.</p>
    </header>

    <div class="concept-stack decision-stack">
      <SideProgressConcept
        variant="rails"
        index="P1"
        kicker="Continuous signal"
        title="Twin ascent rails"
        description="A quiet continuous fill rises from the bottom on both sides. The glowing cap marks the exact session position without adding another dashboard."
      />
      <SideProgressConcept
        variant="rungs"
        index="P2"
        kicker="Verb-by-verb ladder"
        title="Mirrored checkpoint rungs"
        description="Each side contains one substantial block per verb. Completed blocks remain lit and the current checkpoint receives a warm focus signal."
      />
      <SideProgressConcept
        variant="pulse"
        index="P3"
        kicker="Arcade telemetry"
        title="Dual pulse columns"
        description="Fine-grained light nodes climb both edges. It is the least structural option and gives Arcade a lively instrument-panel rhythm."
      />
    </div>
  </section>

  <section class="study-section decision-study" id="launch-study">
    <header class="study-heading">
      <span class="study-index">04 / LAUNCH CONTROL</span>
      <h2>Three exits from setup into play.</h2>
      <p>Each option keeps the explicit setup summary but replaces the oversized current button with a more intentional final action.</p>
    </header>

    <div class="concept-stack launch-stack">
      <LaunchControlConcept
        variant="command"
        index="L1"
        kicker="Compact command deck"
        title="Summary left, launch right"
        description="The lowest-risk direction: compact, fast to scan, and visibly keyboard-ready without repeating the entire setup hierarchy."
      />
      <LaunchControlConcept
        variant="gate"
        index="L2"
        kicker="Threshold interaction"
        title="Open the training gate"
        description="A horizontal gate turns launch into a transition moment. The moving arrow and striped threshold make the action feel physical but still restrained."
      />
      <LaunchControlConcept
        variant="ticket"
        index="L3"
        kicker="Session artifact"
        title="Validate a run ticket"
        description="The setup resolves into a compact ticket with a perforated PLAY stub. It is the most distinctive option and suits the Arcade visual language strongly."
      />
    </div>
  </section>

  <section class="study-section decision-study" id="transition-study">
    <header class="study-heading">
      <span class="study-index">05 / TABLE TRANSITION</span>
      <h2>The table should assemble, not dissolve.</h2>
      <p>Each sequence turns the choices made in A1 into the structure used by G1, giving table practice its own identity instead of borrowing Words’ pixel transition.</p>
    </header>

    <div class="concept-stack transition-stack">
      <TableTransitionConcept
        variant="blueprint"
        index="T1"
        kicker="Architectural reveal"
        title="Draft the table into existence"
        description="The setup contracts into construction lines; rails and cells draw themselves before the finished active column receives a physical approval stamp. Precise, calm, and unmistakably table-specific."
      />
      <TableTransitionConcept
        variant="deal"
        index="T2"
        kicker="Tactile column motion"
        title="Deal the selected tenses"
        description="Every selected tense becomes a card, fans across the stage, then stacks into the first playable column. This makes the cumulative A1 selection feel like material entering the game."
      />
      <TableTransitionConcept
        variant="thread"
        index="T3"
        kicker="Answer-path transfer"
        title="Thread the route downward"
        description="A luminous route connects the chosen tenses and travels into G1’s top-to-bottom answer rail. It communicates the keyboard flow before the first input receives focus."
      />
    </div>
  </section>

  <footer class="pg-footer glass-panel">
    <span>DESIGN BENCH</span>
    <p>A1 and G1 are in production. P1–P3, L1–L3, and T1–T3 remain isolated visual decisions.</p>
    <a href="#setup-study">Back to setup concepts ↑</a>
  </footer>
</section>

<style>
  :global(html) {
    scroll-behavior: smooth;
  }

  .pg-shell {
    width: min(100%, 940px);
    margin-inline: auto;
    display: flex;
    flex-direction: column;
    gap: 1.35rem;
  }

  .pg-header,
  .pg-header-actions,
  .law-head,
  .pg-footer {
    display: flex;
  }

  .pg-header {
    justify-content: space-between;
    align-items: flex-start;
    gap: 1.25rem;
  }

  .pg-header h1 {
    max-width: 670px;
    margin: 0.25rem 0 0.45rem;
    color: var(--text);
    font: 800 clamp(1.55rem, 4vw, 2.45rem)/1.06 var(--display);
    letter-spacing: -0.05em;
  }

  .pg-header-actions {
    flex: 0 0 auto;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.7rem;
  }

  .pg-theme-row {
    display: flex;
    gap: 0.35rem;
  }

  .study-nav {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0.6rem;
  }

  .study-nav a {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-rows: auto auto;
    gap: 0.05rem 0.65rem;
    align-items: center;
    padding: 0.8rem;
    border: 1px solid var(--line);
    border-radius: 16px;
    color: var(--text);
    text-decoration: none;
    background: color-mix(in srgb, var(--surface-strong) 78%, transparent);
    transition: 160ms ease;
  }

  .study-nav a:hover {
    border-color: color-mix(in srgb, var(--accent) 48%, var(--line));
    background: var(--accent-soft);
    transform: translateY(-1px);
  }

  .study-nav a > span {
    grid-row: 1 / 3;
    display: grid;
    width: 2rem;
    height: 2rem;
    place-items: center;
    border-radius: 10px;
    color: var(--accent-strong);
    background: var(--accent-soft);
    font: 700 0.58rem/1 var(--mono);
  }

  .study-nav a strong {
    font-size: 0.76rem;
  }

  .study-nav a small {
    color: var(--muted);
    font-size: 0.6rem;
  }

  .study-section {
    display: flex;
    flex-direction: column;
    gap: 1.4rem;
    padding-top: 1rem;
    scroll-margin-top: 6rem;
  }

  .game-study,
  .decision-study {
    padding-top: 2rem;
    border-top: 1px solid var(--line);
  }

  .study-heading {
    width: min(100%, 720px);
    margin-inline: auto;
    text-align: center;
  }

  .study-index {
    display: inline-flex;
    padding: 0.3rem 0.55rem;
    border: 1px solid var(--line);
    border-radius: 999px;
    color: var(--accent-strong);
    background: var(--accent-soft);
    font: 700 0.58rem/1 var(--mono);
    letter-spacing: 0.12em;
  }

  .study-heading h2 {
    margin: 0.7rem 0 0.45rem;
    color: var(--text);
    font: 800 clamp(1.35rem, 4vw, 2rem)/1.08 var(--display);
    letter-spacing: -0.045em;
  }

  .study-heading p {
    margin: 0;
    color: var(--muted);
    font-size: 0.8rem;
  }

  .concept-stack {
    display: flex;
    flex-direction: column;
    gap: 2.3rem;
  }

  .game-stack {
    gap: 2.6rem;
  }

  .decision-stack {
    gap: 3rem;
  }

  .launch-stack {
    gap: 2.6rem;
  }

  .transition-stack {
    gap: 3.2rem;
  }

  .pointer-law {
    width: min(100%, 760px);
    margin-inline: auto;
    padding: 1rem;
  }

  .law-head {
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.8rem;
  }

  .law-head span,
  .pg-footer > span {
    color: var(--accent-strong);
    font: 700 0.58rem/1 var(--mono);
    letter-spacing: 0.14em;
  }

  .law-head strong {
    color: var(--text);
    font-size: 0.78rem;
  }

  .law-track {
    display: grid;
    grid-template-columns: 1fr auto 1fr auto 1fr;
    gap: 0.45rem;
    align-items: stretch;
  }

  .law-track > div {
    display: grid;
    gap: 0.12rem;
    padding: 0.65rem;
    border: 1px solid var(--line);
    border-radius: 11px;
    background: color-mix(in srgb, var(--surface-dark) 8%, transparent);
  }

  .law-track > div span {
    color: var(--accent-strong);
    font: 700 0.52rem/1 var(--mono);
  }

  .law-track > div strong {
    color: var(--text);
    font-size: 0.7rem;
  }

  .law-track > div small {
    color: var(--muted);
    font-size: 0.53rem;
  }

  .law-track > i {
    align-self: center;
    color: var(--accent-strong);
    font: 700 0.48rem/1 var(--mono);
    text-align: center;
  }

  .law-track .submit-arrow {
    grid-column: 5;
    margin-top: 0.25rem;
    padding: 0.25rem;
    border-radius: 6px;
    color: color-mix(in srgb, var(--success) 80%, var(--text));
    background: color-mix(in srgb, var(--success) 10%, transparent);
  }

  .giveaway-study {
    display: grid;
    width: min(100%, 760px);
    gap: 0.85rem;
    margin-inline: auto;
    padding: 1rem;
    border-color: color-mix(in srgb, #e6a83b 38%, var(--line));
    background:
      radial-gradient(circle at 94% 0%, color-mix(in srgb, #e6a83b 12%, transparent), transparent 30%),
      color-mix(in srgb, var(--surface-strong) 92%, transparent);
  }

  .giveaway-study-head {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.75rem;
    align-items: start;
  }

  .policy-shield {
    display: grid;
    width: 2.35rem;
    height: 2.35rem;
    place-items: center;
    border-radius: 12px;
    color: #b7780e;
    background: color-mix(in srgb, #e6a83b 17%, var(--surface-strong));
  }

  .policy-shield svg {
    width: 1.25rem;
    height: 1.25rem;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.7;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .giveaway-study-head > div {
    display: grid;
    gap: 0.18rem;
  }

  .giveaway-study-head span,
  .giveaway-decision > span {
    color: #b7780e;
    font: 750 0.5rem/1 var(--mono);
    letter-spacing: 0.1em;
  }

  .giveaway-study-head h3 {
    margin: 0;
    color: var(--text);
    font: 780 1rem/1.15 var(--display);
    letter-spacing: -0.025em;
  }

  .giveaway-study-head p,
  .giveaway-decision p {
    margin: 0;
    color: var(--muted);
    font-size: 0.62rem;
  }

  .giveaway-cases {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.4rem;
  }

  .giveaway-cases > div {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.13rem 0.5rem;
    padding: 0.65rem;
    border: 1px solid var(--line);
    border-radius: 11px;
    background: color-mix(in srgb, var(--surface-strong) 74%, transparent);
  }

  .giveaway-cases span {
    grid-row: 1 / 4;
    color: #b7780e;
    font: 750 0.45rem/1 var(--mono);
  }

  .giveaway-cases strong {
    color: var(--text);
    font-size: 0.63rem;
  }

  .giveaway-cases small,
  .giveaway-cases em {
    color: var(--muted);
    font-size: 0.5rem;
  }

  .giveaway-cases em {
    color: var(--accent-strong);
    font-style: normal;
  }

  .giveaway-decision {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.65rem;
    align-items: center;
    padding: 0.7rem;
    border: 1px dashed #e6a83b;
    border-radius: 11px;
    background: color-mix(in srgb, #e6a83b 7%, transparent);
  }

  .giveaway-decision strong {
    color: var(--text);
  }

  .pg-footer {
    align-items: center;
    gap: 1rem;
  }

  .pg-footer p {
    flex: 1;
    margin: 0;
    color: var(--muted);
    font-size: 0.7rem;
  }

  .pg-footer a {
    color: var(--accent-strong);
    font-size: 0.68rem;
  }

  :global(html[data-theme='arcade']) .pg-header h1,
  :global(html[data-theme='arcade']) .study-heading h2 {
    line-height: 1.5;
    letter-spacing: 0;
  }

  @media (max-width: 700px) {
    .pg-header,
    .pg-footer {
      align-items: flex-start;
      flex-direction: column;
    }

    .pg-header-actions {
      align-items: flex-start;
    }

    .study-nav {
      grid-template-columns: repeat(2, 1fr);
    }

    .law-track {
      grid-template-columns: 1fr;
    }

    .law-track > i,
    .law-track .submit-arrow {
      grid-column: 1;
      padding: 0.2rem;
    }

    .giveaway-cases {
      grid-template-columns: 1fr;
    }

    .giveaway-decision {
      grid-template-columns: 1fr;
    }

  }

  @media (max-width: 460px) {
    .study-nav {
      grid-template-columns: 1fr;
    }
  }
</style>
