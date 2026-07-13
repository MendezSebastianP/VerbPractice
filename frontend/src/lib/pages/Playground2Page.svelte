<script lang="ts">
  import { onMount } from 'svelte';
  import ArcadeTypeStudy from '../components/playground2/ArcadeTypeStudy.svelte';
  import SessionHudStudy from '../components/playground2/SessionHudStudy.svelte';
  import StageClearStudy from '../components/playground2/StageClearStudy.svelte';
  import TableSetupStudy from '../components/playground2/TableSetupStudy.svelte';
  import { navigate } from '../router';

  // The bench compares options against arcade first — but every study also
  // renders correctly in light/dark, so nothing chosen here forks the themes.
  let previewTheme: 'light' | 'dark' | 'arcade' = 'arcade';

  function setTheme(next: 'light' | 'dark' | 'arcade'): void {
    previewTheme = next;
    document.documentElement.setAttribute('data-theme', next);
  }

  onMount(() => {
    const active = document.documentElement.getAttribute('data-theme');
    previewTheme = active === 'light' || active === 'dark' || active === 'arcade' ? active : 'arcade';
  });

  const FINDINGS = [
    { where: 'Tables setup · tense chips', now: '11.5px', floor: '15px + 44px target', worst: false },
    { where: 'Tables setup · shortcut keycaps', now: '6.4–7.7px', floor: '11px, desktop only', worst: true },
    { where: 'Tables setup · shortcut footer', now: '9.6px', floor: '12.5px, trimmed', worst: false },
    { where: 'G1 game · tense strip', now: '7.4–9.9px', floor: '12–14.4px', worst: false },
    { where: 'G1 game · utility row', now: '7.7–8px at 48% white', floor: '11.5px at 72% white', worst: false },
    { where: 'G1 game · input hint pill', now: '6.1px', floor: '10px, moved off the input', worst: true },
    { where: 'Topbar · level chip (arcade)', now: '8.8px Press Start 2P', floor: '11.5px Space Grotesk', worst: false },
    { where: 'Menu · play caption (arcade)', now: '8px Press Start 2P', floor: '12.8px, wide tracking', worst: false },
  ];
</script>

<section class="pg2-shell">
  <header class="glass-panel strong-panel pg2-header">
    <div>
      <p class="eyebrow">Playground 2 · Arcade refit bench</p>
      <h1>Readability joins the arcade.</h1>
      <p class="section-copy">
        A full front-end pass with the arcade theme in focus. All four studies are decided and live:
        S1-A, H1-B1, T1-A and C1-A shipped to production. The bench stays as the record of what was
        compared and why.
      </p>
    </div>
    <div class="pg2-header-actions">
      <div class="pg2-theme-row" role="group" aria-label="Preview theme">
        <button class:option-on={previewTheme === 'light'} class="option-chip" type="button" on:click={() => setTheme('light')}>Light</button>
        <button class:option-on={previewTheme === 'dark'} class="option-chip" type="button" on:click={() => setTheme('dark')}>Dark</button>
        <button class:option-on={previewTheme === 'arcade'} class="option-chip" type="button" on:click={() => setTheme('arcade')}>Arcade</button>
      </div>
      <button class="text-switch" type="button" on:click={() => navigate('/playground')}>Bench 1: verb tables →</button>
      <button class="text-switch" type="button" on:click={() => navigate('/training/verbs')}>Open working Verb Lab →</button>
    </div>
  </header>

  <article class="glass-panel evidence-panel">
    <div class="evidence-head">
      <span class="evidence-badge" aria-hidden="true">
        <svg viewBox="0 0 24 24"><path d="M12 3v10.5M12 13.5 8.5 10M12 13.5 15.5 10" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8"></path><path d="M5 15.5v2A2.5 2.5 0 0 0 7.5 20h9a2.5 2.5 0 0 0 2.5-2.5v-2" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="1.8"></path></svg>
      </span>
      <div>
        <h2>The small-type inventory</h2>
        <p>Measured in the production CSS. The arcade fonts make it worse: Press Start 2P is extremely wide, so it got shrunk to fit; VT323 draws about 30% smaller than its declared size.</p>
      </div>
    </div>
    <div class="evidence-table" role="table" aria-label="Font size findings">
      <div class="evidence-row evidence-row-head" role="row">
        <span role="columnheader">Where</span><span role="columnheader">Today</span><span role="columnheader">Proposed floor</span>
      </div>
      {#each FINDINGS as f}
        <div class="evidence-row" role="row">
          <span role="cell">{f.where}</span>
          <span role="cell" class="evidence-now" class:evidence-worst={f.worst}>{f.now}</span>
          <span role="cell" class="evidence-floor">{f.floor}</span>
        </div>
      {/each}
    </div>
  </article>

  <nav class="study-nav" aria-label="Playground 2 studies">
    <a href="#hud-study2"><span>02</span><strong>In-game HUD</strong><small>✓ H1-B1 shipped</small></a>
    <a href="#setup-study2"><span>01</span><strong>Tables setup menu</strong><small>✓ S1-A shipped</small></a>
    <a href="#type-study2"><span>03</span><strong>Arcade type system</strong><small>✓ T1-A shipped</small></a>
    <a href="#clear-study2"><span>04</span><strong>Stage clear</strong><small>✓ C1-A shipped</small></a>
  </nav>

  <section class="study-section" id="hud-study2">
    <header class="study-heading">
      <span class="study-index">02 / IN-GAME HUD · DECIDED</span>
      <h2>H1-B1: named segments won.</h2>
      <p>Sebastián's calls, in order: the LED strip stays, previous and next tenses must stay identifiable — and full names beat abbreviations. Both labeling systems remain below at 3 and 9 tenses, with the unlabeled original for reference.</p>
    </header>
    <div class="concept-stack">
      <SessionHudStudy
        variant="marquee"
        index="H1-B"
        kicker="Chosen direction · unlabeled reference"
        title="The strip as decided — blocks carry no names"
        description="Reference point: the winning marquee concept exactly as picked. Its weakness is the one Sebastián named — away from the active tense, the blocks are anonymous."
      />
      <SessionHudStudy
        variant="names"
        index="H1-B1"
        kicker="Variation 1 · ✓ Shipped to production"
        title="Full tense names ride inside the blocks"
        description="Every segment is a labeled tab. Maximum orientation at core-tense runs; at nine tenses the long French names truncate and the strip needs two rows on a phone."
      />
      <SessionHudStudy
        variant="abbr"
        index="H1-B2"
        kicker="Variation 2 · Abbreviation slabs"
        title="Short codes keep the LED rhythm"
        description="PRÉ · PC · IMP · PQP — compact codes in the terminal font. Nine tenses stay on one row at any width, and the gold marquee still spells out the active tense in full."
      />
    </div>
  </section>

  <section class="study-section decision-study" id="setup-study2">
    <header class="study-heading">
      <span class="study-index">01 / TABLES SETUP MENU · DECIDED</span>
      <h2>The setup screen you squint at.</h2>
      <p>Sebastián flagged this menu first. The current card packs six shortcut systems and three tiers into 6–12px type. Both options keep every capability and raise the floor to readable.</p>
    </header>
    <div class="concept-stack">
      <TableSetupStudy
        variant="current"
        index="OLD"
        kicker="Previous production design · replaced"
        title="Everything is here — at 6 to 12 pixels"
        description="Faithful replica of the live setup card with its real sizes. The red flags mark measured values; in arcade mode the VT323 keycaps render even smaller than the numbers suggest."
      />
      <TableSetupStudy
        variant="readable"
        index="S1-A"
        kicker="Option A · ✓ Shipped to production"
        title="Keep the staircase, rebuild the type scale"
        description="Zero re-learning: identical layout and flow. Tense chips become 44px targets at 15px text, keycaps grow and vanish on touch screens, and the footer keeps only the three shortcuts that earn their place."
      />
      <TableSetupStudy
        variant="console"
        index="S1-B"
        kicker="Option B · Console deck"
        title="Route on the left, loadout on the right"
        description="A restructure: levels become three big radio rows, the chosen tenses live once in a loadout panel with removable chips, and run size / support turn into chunky segmented dials. Boldest change, fewest words."
      />
    </div>
  </section>

  <section class="study-section decision-study" id="type-study2">
    <header class="study-heading">
      <span class="study-index">03 / ARCADE TYPE SYSTEM</span>
      <h2>Press Start 2P deserves a stage, not a chip.</h2>
      <p>The root cause behind most tiny text: the arcade theme routes every display role through a very wide pixel font, so components shrink it to fit. Two ways to fix the system, shown on the same six specimens.</p>
    </header>
    <div class="concept-stack">
      <ArcadeTypeStudy
        variant="current"
        index="OLD"
        kicker="Previous production rules · replaced"
        title="One pixel font for every role"
        description="Live arcade values: titles at 20px work, but the same font gets crushed to 8.8px chips and 8px captions, and VT323 eyebrows render around 10px optical."
      />
      <ArcadeTypeStudy
        variant="discipline"
        index="T1-A"
        kicker="Option A · ✓ Shipped to production"
        title="Same fonts, strict roles"
        description="No new downloads. Press Start 2P becomes marquee-only, VT323 handles numbers at a compensated size, and Space Grotesk — already loaded — takes over every button, chip and caption."
      />
      <ArcadeTypeStudy
        variant="cabinet"
        index="T1-B"
        kicker="Option B · New cabinet stack"
        title="Russo One + Chakra Petch"
        description="A second retro voice that stays legible at UI sizes: Russo One for display, Chakra Petch for labels, VT323 for numerals — and Press Start 2P retires to the logo and STAGE CLEAR stamp."
      />
    </div>
  </section>

  <section class="study-section decision-study" id="clear-study2">
    <header class="study-heading">
      <span class="study-index">04 / STAGE CLEAR</span>
      <h2>The win screen should feel like a win.</h2>
      <p>Today the results appear all at once and the dots are the only texture. Both options stage the reveal — grade first or scoreboard rows — and both collapse to a static screen under reduced motion.</p>
    </header>
    <div class="concept-stack">
      <StageClearStudy
        variant="current"
        index="OLD"
        kicker="Previous production design · replaced"
        title="Everything lands in one frame"
        description="Faithful replica of the arcade Stage Clear: title glow, one stat line, GG copy, binary dots, two buttons. Correct — but the moment is over before it starts."
      />
      <StageClearStudy
        variant="rank"
        index="C1-A"
        kicker="Option A · ✓ Shipped to production"
        title="Grade it: S, A, B, C"
        description="A letter grade stamps in, the score counts up with tabular digits, the segment bar fills verb by verb, then the actions rise. About 1.3 seconds of ceremony, fully skipped under reduced motion."
      />
      <StageClearStudy
        variant="scoreboard"
        index="C1-B"
        kicker="Option B · High-score board"
        title="Results as a cabinet scoreboard"
        description="Score, accuracy, combo and verbs slide in as dotted-leader rows; records flash NEW BEST! in place, and a blinking PRESS ENTER caps the screen like a real cabinet."
      />
    </div>
  </section>

  <footer class="pg2-footer glass-panel">
    <span>REFIT BENCH</span>
    <p>All decided: S1-A, H1-B1, T1-A and C1-A are live in production. This bench closes — the next round of experiments gets a fresh page.</p>
    <a href="#hud-study2">Back to the first study ↑</a>
  </footer>
</section>

<style>
  :global(html) {
    scroll-behavior: smooth;
  }

  .pg2-shell {
    width: min(100%, 940px);
    margin-inline: auto;
    display: flex;
    flex-direction: column;
    gap: 1.35rem;
  }

  .pg2-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1.25rem;
  }

  .pg2-header h1 {
    max-width: 670px;
    margin: 0.25rem 0 0.45rem;
    color: var(--text);
    font: 800 clamp(1.55rem, 4vw, 2.45rem)/1.06 var(--display);
    letter-spacing: -0.05em;
  }

  .pg2-header-actions {
    flex: 0 0 auto;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.7rem;
  }

  .pg2-theme-row {
    display: flex;
    gap: 0.35rem;
  }

  .evidence-panel {
    display: grid;
    gap: 0.9rem;
  }

  .evidence-head {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.8rem;
    align-items: start;
  }

  .evidence-badge {
    display: grid;
    width: 2.35rem;
    height: 2.35rem;
    place-items: center;
    border-radius: 12px;
    color: var(--danger);
    background: color-mix(in srgb, var(--danger) 12%, transparent);
  }

  .evidence-badge svg { width: 1.25rem; height: 1.25rem; }

  .evidence-head h2 {
    margin: 0 0 0.2rem;
    color: var(--text);
    font: 800 1.15rem/1.2 var(--display);
    letter-spacing: -0.03em;
  }

  .evidence-head p {
    margin: 0;
    color: var(--muted);
    font-size: 0.84rem;
    line-height: 1.5;
  }

  .evidence-table {
    display: grid;
    border: 1px solid var(--line);
    border-radius: 14px;
    overflow: hidden;
  }

  .evidence-row {
    display: grid;
    grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr) minmax(0, 1.2fr);
    gap: 0.7rem;
    padding: 0.55rem 0.85rem;
    border-bottom: 1px solid var(--line);
    font-size: 0.82rem;
    color: var(--text);
  }

  .evidence-row:last-child { border-bottom: 0; }
  .evidence-row:nth-child(even) { background: color-mix(in srgb, var(--surface-strong) 55%, transparent); }

  .evidence-row-head {
    color: var(--muted);
    font: 700 0.72rem/1.4 var(--mono);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    background: color-mix(in srgb, var(--surface-strong) 80%, transparent) !important;
  }

  .evidence-now { color: var(--danger); font-weight: 700; font-variant-numeric: tabular-nums; }
  .evidence-worst::after { content: ' ●'; font-size: 0.6em; vertical-align: middle; }
  .evidence-floor { color: var(--success); font-weight: 600; }

  .study-nav {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
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
    font: 700 0.68rem/1 var(--mono);
  }

  .study-nav a strong { font-size: 0.82rem; }
  .study-nav a small { color: var(--muted); font-size: 0.72rem; }

  .study-section {
    display: flex;
    flex-direction: column;
    gap: 1.4rem;
    padding-top: 1rem;
    scroll-margin-top: 6rem;
  }

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
    font: 700 0.68rem/1 var(--mono);
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
    font-size: 0.86rem;
    line-height: 1.55;
  }

  .concept-stack {
    display: flex;
    flex-direction: column;
    gap: 2.6rem;
  }

  .pg2-footer {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .pg2-footer > span {
    color: var(--accent-strong);
    font: 700 0.68rem/1 var(--mono);
    letter-spacing: 0.14em;
  }

  .pg2-footer p {
    flex: 1;
    margin: 0;
    color: var(--muted);
    font-size: 0.8rem;
  }

  .pg2-footer a {
    color: var(--accent-strong);
    font-size: 0.78rem;
  }

  :global(html[data-theme='arcade']) .pg2-header h1,
  :global(html[data-theme='arcade']) .study-heading h2 {
    line-height: 1.5;
    letter-spacing: 0;
  }

  @media (max-width: 700px) {
    .pg2-header,
    .pg2-footer {
      align-items: flex-start;
      flex-direction: column;
    }

    .pg2-header-actions {
      align-items: flex-start;
    }

    .study-nav {
      grid-template-columns: repeat(2, 1fr);
    }

    .evidence-row {
      grid-template-columns: 1fr;
      gap: 0.15rem;
    }

    .evidence-row-head { display: none; }
    .evidence-row span:first-child { font-weight: 600; }
  }

  @media (max-width: 460px) {
    .study-nav {
      grid-template-columns: 1fr;
    }
  }
</style>
