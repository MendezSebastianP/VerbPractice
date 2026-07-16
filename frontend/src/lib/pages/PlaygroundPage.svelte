<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import MatchaLaunchDemo from '../components/playground/MatchaLaunchDemo.svelte';
  import MatchaPlayButton from '../components/playground/MatchaPlayButton.svelte';
  import MatchaVerbTable from '../components/playground/MatchaVerbTable.svelte';
  import MatchaWordGame from '../components/playground/MatchaWordGame.svelte';

  let vectorLaunch: MatchaLaunchDemo | null = null;
  let bioLaunch: MatchaLaunchDemo | null = null;
  const timers: ReturnType<typeof setTimeout>[] = [];

  function launchAfter(target: MatchaLaunchDemo | null): void {
    timers.push(setTimeout(() => target?.run(), 130));
  }

  onMount(() => {
    const root = document.documentElement;
    const previousTheme = root.getAttribute('data-theme');
    const previousPlayground = root.getAttribute('data-playground');
    root.setAttribute('data-theme', 'light');
    root.setAttribute('data-playground', 'matcha-systems');

    return () => {
      if (previousTheme) root.setAttribute('data-theme', previousTheme);
      else root.removeAttribute('data-theme');
      if (previousPlayground) root.setAttribute('data-playground', previousPlayground);
      else root.removeAttribute('data-playground');
    };
  });

  onDestroy(() => timers.forEach(clearTimeout));
</script>

<svelte:head>
  <title>Matcha Overdrive · Interaction Lab</title>
  <meta name="description" content="Two Matcha Overdrive alternatives for VerbPractice play, launch, Words feedback and verb tables." />
</svelte:head>

<section class="matcha-lab" id="matcha-top">
  <header class="lab-header">
    <div class="system-line">
      <span><i></i>MATCHA_OVERDRIVE</span>
      <span>INTERACTION LAB</span>
      <span>A / B</span>
    </div>

    <div class="hero-grid">
      <div>
        <p>Palette and type locked.</p>
        <h1>Now give it<br /><strong>a nervous system.</strong></h1>
      </div>
      <div class="hero-side">
        <div class="logo-lockup" aria-label="Verb Practice logo, Matcha recolor">
          <span class="vp-badge-demo" aria-hidden="true"><b>V</b><b>P</b><i></i></span>
          <span>Verb Practice</span>
        </div>
        <p>The logo keeps its badge, monogram, notch and proportions. Only its colors move into Matcha. Every demo below shares the same game data, dimensions and timing.</p>
      </div>
    </div>

    <div class="token-console" aria-label="Locked Matcha Overdrive design tokens">
      <span style="--token:#DCE8A6"><i></i><b>FIELD</b><code>#DCE8A6</code></span>
      <span style="--token:#F0F4CE"><i></i><b>PANEL</b><code>#F0F4CE</code></span>
      <span style="--token:#13281E"><i></i><b>INK</b><code>#13281E</code></span>
      <span style="--token:#236249"><i></i><b>CORE</b><code>#236249</code></span>
      <span style="--token:#FF4C91"><i></i><b>SPARK</b><code>#FF4C91</code></span>
    </div>

    <nav class="lab-nav" aria-label="Matcha playground sections">
      <a href="#play-launch">Play + launch</a>
      <a href="#words-feedback">Words + feedback</a>
      <a href="#verb-table">Verb table</a>
    </nav>
  </header>

  <main>
    <section class="lab-section" id="play-launch" aria-labelledby="play-title">
      <header class="section-head">
        <div><span>PLAY CONTROL + HANDOFF</span><h2 id="play-title">Press either button.<br />Watch the whole launch.</h2></div>
        <p>Both controls are the Arcade-exact 274×106, 10×4 matrix. A click runs its local response, then the real 160-cell transition clock: swap at 700ms, reveal over 600ms.</p>
      </header>

      <div class="compare-grid">
        <article class="option-card vector-option">
          <header><span>A / VECTOR GRID</span><strong>Directional, precise, fast</strong><p>The cells read like a launch surface. Pointer heat reveals the matrix; firing sweeps left-to-right into angular shutters.</p></header>
          <div class="play-stage"><MatchaPlayButton variant="vector" on:fire={() => launchAfter(vectorLaunch)} /></div>
          <MatchaLaunchDemo bind:this={vectorLaunch} variant="vector" />
          <footer><span>40 button cells</span><span>160 transition cells</span><span>700 + 600ms</span></footer>
        </article>

        <article class="option-card bio-option">
          <header><span>B / BIO PULSE</span><strong>Living, playful, responsive</strong><p>The same matrix rests as a single capsule. Proximity wakes its cells; firing blooms from the center into a spore-like cover.</p></header>
          <div class="play-stage"><MatchaPlayButton variant="bio" on:fire={() => launchAfter(bioLaunch)} /></div>
          <MatchaLaunchDemo bind:this={bioLaunch} variant="bio" />
          <footer><span>40 button cells</span><span>160 transition cells</span><span>700 + 600ms</span></footer>
        </article>
      </div>
    </section>

    <section class="lab-section" id="words-feedback" aria-labelledby="words-title">
      <header class="section-head">
        <div><span>WORDS GAME + GRADING</span><h2 id="words-title">Same word run.<br />Two kinds of impact.</h2></div>
        <p>Type <b>still</b> and submit, or use the preview controls. Both keep the production 720px trainer structure, progress rails and 22×11 radial feedback grid.</p>
      </header>

      <div class="compare-grid">
        <article class="option-card game-option vector-option">
          <header><span>A / VECTOR GRID</span><strong>Crosshair feedback</strong><p>Right answers travel as clipped green vectors. Wrong answers interrupt the word with a pink lateral jolt and a recovery hint.</p></header>
          <MatchaWordGame variant="vector" />
          <footer><span>242 feedback cells</span><span>.45s radial delay</span><span>Icon + text verdict</span></footer>
        </article>

        <article class="option-card game-option bio-option">
          <header><span>B / BIO PULSE</span><strong>Cellular feedback</strong><p>Right answers bloom outward; wrong answers contract into pink spores while the prompt absorbs a softer elastic wobble.</p></header>
          <MatchaWordGame variant="bio" />
          <footer><span>242 feedback cells</span><span>.45s radial delay</span><span>Icon + text verdict</span></footer>
        </article>
      </div>
    </section>

    <section class="lab-section" id="verb-table" aria-labelledby="table-title">
      <header class="section-head">
        <div><span>VERB TABLE GAME</span><h2 id="table-title">Dense enough to learn.<br />Alive enough to play.</h2></div>
        <p>The data hierarchy remains unchanged: run progress, tense route, verb hero, active pronoun and six answer rows. Switch each demo to Review to inspect correct and wrong states.</p>
      </header>

      <div class="compare-grid">
        <article class="option-card table-option vector-option">
          <header><span>A / VECTOR GRID</span><strong>Instrument panel</strong><p>Sharper rails and clipped markers make the active cell feel targeted without turning the conjugation table into a spreadsheet.</p></header>
          <MatchaVerbTable variant="vector" />
          <footer><span>Active row locked</span><span>Keyboard route intact</span><span>Staggered review</span></footer>
        </article>

        <article class="option-card table-option bio-option">
          <header><span>B / BIO PULSE</span><strong>Living worksheet</strong><p>Identical content density, softened into connected cells. The current answer feels held by the interface rather than boxed in.</p></header>
          <MatchaVerbTable variant="bio" />
          <footer><span>Active row locked</span><span>Keyboard route intact</span><span>Staggered review</span></footer>
        </article>
      </div>
    </section>
  </main>

  <footer class="lab-footer">
    <div><span>THE DECISION</span><h2>Choose the motion language,<br />not another palette.</h2></div>
    <div><p><b>Vector Grid</b> keeps more Arcade DNA: explicit cells, directional energy, sharper game feel.</p><p><b>Bio Pulse</b> is the stronger Clear-mode personality: futuristic and playful without becoming clinical or quiet.</p></div>
    <a href="#matcha-top">Back to top ↑</a>
  </footer>
</section>

<style>
  :global(html[data-playground='matcha-systems']) {
    scroll-behavior: smooth;
    background: #cbd594;
  }

  :global(html[data-playground='matcha-systems'] body) {
    background-color: #cbd594;
    background-image: linear-gradient(rgba(19,40,30,.075) 1px, transparent 1px), linear-gradient(90deg, rgba(19,40,30,.075) 1px, transparent 1px);
    background-size: 24px 24px;
  }

  :global(html[data-playground='matcha-systems'] body::after),
  :global(html[data-playground='matcha-systems'] .page-floor) { display: none; }

  :global(html[data-playground='matcha-systems'] .workspace-shell) {
    max-width: 1580px;
    padding-top: 1rem;
    padding-bottom: 4rem;
  }

  :global(html[data-playground='matcha-systems'] .vp-badge) {
    border-color: #236249;
    background: #f0f4ce;
  }
  :global(html[data-playground='matcha-systems'] .vp-v) { color: #13281e; }
  :global(html[data-playground='matcha-systems'] .vp-p) { color: #236249; }
  :global(html[data-playground='matcha-systems'] .vp-notch) { background: linear-gradient(90deg, #236249, #ff4c91); }
  :global(html[data-playground='matcha-systems'] .brand-word) { color: #13281e; }

  .matcha-lab {
    --m-field: #dce8a6;
    --m-panel: #f0f4ce;
    --m-ink: #13281e;
    --m-core: #236249;
    --m-spark: #ff4c91;
    width: min(100%, 1500px);
    margin-inline: auto;
    color: var(--m-ink);
    font-family: "Figtree", sans-serif;
  }

  .lab-header {
    position: relative;
    overflow: hidden;
    border: 2px solid var(--m-ink);
    background: var(--m-panel);
    box-shadow: 9px 9px 0 var(--m-core);
  }

  .lab-header::after {
    content: 'MO';
    position: absolute;
    right: -2rem;
    bottom: 3rem;
    color: color-mix(in srgb, var(--m-core) 9%, transparent);
    font: 700 clamp(12rem, 24vw, 25rem)/.7 "Chakra Petch", sans-serif;
    letter-spacing: -.15em;
    transform: rotate(-7deg);
    pointer-events: none;
  }

  .system-line { position: relative; z-index: 2; display: flex; justify-content: space-between; gap: 1rem; padding: 1rem 1.2rem; border-bottom: 1px solid var(--m-ink); font: 400 1rem/1 "VT323", monospace; }
  .system-line span:first-child { display: flex; align-items: center; gap: .5rem; }
  .system-line i { width: 8px; height: 8px; border-radius: 50%; background: var(--m-spark); box-shadow: 0 0 0 3px color-mix(in srgb, var(--m-spark) 20%, transparent); }

  .hero-grid { position: relative; z-index: 1; display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(290px, .55fr); gap: clamp(2rem, 8vw, 8rem); align-items: end; min-height: 480px; padding: clamp(1.3rem, 4vw, 3.5rem); }
  .hero-grid > div:first-child > p, .section-head > div > span, .lab-footer > div > span { margin: 0 0 .8rem; color: var(--m-core); font: 700 .65rem/1 "Chakra Petch", sans-serif; letter-spacing: .12em; }
  .hero-grid h1 { max-width: 10ch; margin: 0; font: 700 clamp(4rem, 8vw, 8.5rem)/.82 "Chakra Petch", sans-serif; letter-spacing: -.075em; text-wrap: balance; }
  .hero-grid h1 strong { color: var(--m-core); font: inherit; }
  .hero-side { display: grid; gap: 1.4rem; }
  .hero-side > p { margin: 0; font-size: clamp(.95rem, 1.3vw, 1.08rem); line-height: 1.65; }

  .logo-lockup { display: flex; gap: .65rem; align-items: center; font: 600 .68rem/1 "IBM Plex Mono", monospace; letter-spacing: .24em; text-transform: uppercase; }
  .vp-badge-demo { position: relative; display: flex; width: 36px; height: 36px; flex: 0 0 auto; align-items: center; justify-content: center; gap: 1px; overflow: hidden; border: 2px solid var(--m-core); border-radius: 11px; background: var(--m-panel); font: 800 .95rem/1 "Press Start 2P", monospace; letter-spacing: 0; }
  .vp-badge-demo b:first-child { color: var(--m-ink); }
  .vp-badge-demo b:nth-child(2) { color: var(--m-core); }
  .vp-badge-demo i { position: absolute; right: 0; bottom: 0; left: 0; width: 34%; height: 4px; background: linear-gradient(90deg, var(--m-core), var(--m-spark)); }

  .token-console { position: relative; z-index: 2; display: grid; grid-template-columns: repeat(5, 1fr); border-top: 2px solid var(--m-ink); }
  .token-console > span { display: grid; min-width: 0; grid-template-columns: 32px 1fr; gap: .2rem .55rem; align-items: center; padding: .65rem; }
  .token-console > span + span { border-left: 1px solid var(--m-ink); }
  .token-console i { grid-row: 1 / 3; width: 32px; height: 32px; border: 1px solid var(--m-ink); background: var(--token); }
  .token-console b { font: 700 .55rem/1 "Chakra Petch", sans-serif; }
  .token-console code { font: 400 .9rem/1 "VT323", monospace; }

  .lab-nav { position: relative; z-index: 2; display: grid; grid-template-columns: repeat(3, 1fr); border-top: 1px solid var(--m-ink); background: var(--m-field); }
  .lab-nav a { display: grid; min-height: 52px; place-items: center; color: var(--m-ink); font: 700 .68rem/1 "Chakra Petch", sans-serif; text-decoration: none; touch-action: manipulation; }
  .lab-nav a + a { border-left: 1px solid var(--m-ink); }
  .lab-nav a:hover { color: var(--m-panel); background: var(--m-core); }
  .lab-nav a:focus-visible { outline: 4px solid var(--m-spark); outline-offset: -4px; }

  main { display: grid; gap: clamp(6rem, 10vw, 10rem); margin-top: clamp(6rem, 10vw, 10rem); }
  .lab-section { display: grid; gap: 1.5rem; scroll-margin-top: 1rem; }
  .section-head { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(280px, .55fr); gap: clamp(2rem, 8vw, 8rem); align-items: end; }
  .section-head h2 { max-width: 12ch; margin: 0; font: 700 clamp(3rem, 6vw, 6.2rem)/.86 "Chakra Petch", sans-serif; letter-spacing: -.07em; text-wrap: balance; }
  .section-head > p { margin: 0; line-height: 1.65; }
  .section-head > p b { color: var(--m-core); }

  .compare-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; align-items: start; }
  .option-card { min-width: 0; padding: 1rem; border: 2px solid var(--m-ink); background: var(--m-field); }
  .option-card > header { min-height: 145px; padding: 1rem; border: 1px solid var(--m-ink); background: var(--m-panel); }
  .option-card > header > span { font: 400 1rem/1 "VT323", monospace; }
  .option-card > header > strong { display: block; margin-top: .65rem; font: 700 clamp(1.4rem, 2.4vw, 2.1rem)/1 "Chakra Petch", sans-serif; letter-spacing: -.035em; }
  .option-card > header > p { margin: .65rem 0 0; line-height: 1.5; }
  .option-card > footer { display: grid; grid-template-columns: repeat(3, 1fr); margin-top: .8rem; border: 1px solid var(--m-ink); }
  .option-card > footer span { display: grid; min-height: 44px; place-items: center; padding: .45rem; font: 400 .9rem/1 "VT323", monospace; text-align: center; }
  .option-card > footer span + span { border-left: 1px solid var(--m-ink); }
  .vector-option { box-shadow: 7px 7px 0 var(--m-core); }
  .bio-option { border-radius: 24px; box-shadow: 7px 7px 0 var(--m-spark); }
  .bio-option > header { border-radius: 16px; }
  .play-stage { display: grid; min-height: 165px; place-items: center; padding: 1rem; }
  .game-option, .table-option { padding-bottom: 1rem; }

  .lab-footer { display: grid; grid-template-columns: 1fr .8fr auto; gap: clamp(2rem, 7vw, 7rem); align-items: end; margin-top: clamp(6rem, 10vw, 10rem); padding: clamp(1.5rem, 4vw, 3.5rem); color: var(--m-panel); background: var(--m-ink); }
  .lab-footer > div > span { color: var(--m-spark); }
  .lab-footer h2 { margin: 0; font: 700 clamp(2.4rem, 5vw, 5rem)/.88 "Chakra Petch", sans-serif; letter-spacing: -.06em; }
  .lab-footer p { margin: 0 0 1rem; color: color-mix(in srgb, var(--m-panel) 75%, transparent); line-height: 1.6; }
  .lab-footer p b { color: var(--m-panel); }
  .lab-footer a { color: var(--m-panel); font-weight: 700; text-underline-offset: 4px; }
  .lab-footer a:focus-visible { outline: 3px solid var(--m-spark); outline-offset: 4px; }

  @media (max-width: 1080px) {
    .compare-grid { grid-template-columns: 1fr; }
    .option-card { width: 100%; max-width: 720px; margin-inline: auto; box-sizing: border-box; }
  }

  @media (max-width: 760px) {
    .hero-grid, .section-head, .lab-footer { grid-template-columns: 1fr; }
    .hero-grid { align-items: end; }
    .hero-side { max-width: 36rem; }
    .lab-footer { align-items: start; }
  }

  @media (max-width: 520px) {
    :global(html[data-playground='matcha-systems'] .workspace-shell) { padding: .55rem; }
    .lab-header { box-shadow: 5px 5px 0 var(--m-core); }
    .system-line span:nth-child(2) { display: none; }
    .hero-grid { min-height: 560px; padding: 1rem; }
    .hero-grid h1 { font-size: clamp(3.3rem, 16vw, 5.2rem); }
    .token-console { grid-template-columns: 1fr; }
    .token-console > span { grid-template-columns: 28px 1fr auto; }
    .token-console > span + span { border-top: 1px solid var(--m-ink); border-left: 0; }
    .token-console i { grid-row: auto; width: 28px; height: 28px; }
    .lab-nav { grid-template-columns: 1fr; }
    .lab-nav a + a { border-top: 1px solid var(--m-ink); border-left: 0; }
    .section-head h2 { font-size: clamp(2.8rem, 13vw, 4.5rem); }
    .option-card { padding: .55rem; }
    .option-card > header { min-height: 0; }
    .option-card > footer { grid-template-columns: 1fr; }
    .option-card > footer span + span { border-top: 1px solid var(--m-ink); border-left: 0; }
    .play-stage { padding-inline: 0; }
    .lab-footer { padding: 1.3rem; }
  }

  @media (prefers-reduced-motion: reduce) {
    :global(html[data-playground='matcha-systems']) { scroll-behavior: auto; }
  }
</style>
