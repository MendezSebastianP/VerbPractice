<script lang="ts">
  import StudyEntryOption from '../components/playground2/StudyEntryOption.svelte';
  import StudyTableConcept from '../components/playground2/StudyTableConcept.svelte';
  import { navigate } from '../router';

  // PLAYGROUND2 IS PROTECTED AFTER THIS HANDOFF. Another agent owns the main
  // playground work; change this page only when the user explicitly requests it.
</script>

<section class="pg2-shell">
  <header class="glass-panel strong-panel pg2-header">
    <div>
      <p class="eyebrow">Playground 2 · Study pool</p>
      <h1>Study what is new—and what still resists.</h1>
      <p class="section-copy">The expansion always contains six newest items plus six items that need more practice, with duplicates removed. This page stays exploratory; nothing below is wired into the live trainers.</p>
    </div>
    <button class="text-switch" type="button" on:click={() => navigate('/training/words')}>Open current Words →</button>
  </header>

  <aside class="palette-note">
    <span class="palette-swatch violet" aria-hidden="true"></span>
    <span class="palette-swatch coral" aria-hidden="true"></span>
    <div><strong>Palette reset</strong><p>Muted violet identifies “new”; warm coral identifies “needs more practice.” No success green, neon gradients, or generic AI-dashboard glow.</p></div>
  </aside>

  <nav class="study-nav" aria-label="Study pool concepts">
    <a href="#tables"><span>01</span><strong>Three table types</strong><small>All exactly 2 columns</small></a>
    <a href="#entries"><span>02</span><strong>Three entry options</strong><small>Click each to collapse</small></a>
  </nav>

  <section class="study-section" id="tables">
    <header class="study-heading">
      <span class="study-index">01 / CONTENT</span>
      <h2>Three tables, one simple reading rule.</h2>
      <p>Words and translations use grouped two-column lists. Verb tables keep the 12-verb study pool as a selector, then show only pronoun and form. Switch FR, ES, EN, and RU to check the language-specific structure.</p>
    </header>
    <div class="concept-stack">
      <div class="concept-label"><span>A</span><div><strong>Words</strong><small>Word + translation</small></div></div>
      <StudyTableConcept kind="words" />
      <div class="concept-label"><span>B</span><div><strong>Verb translations</strong><small>Infinitive + translation</small></div></div>
      <StudyTableConcept kind="verbs" />
      <div class="concept-label"><span>C</span><div><strong>Verb tables</strong><small>Pronoun + conjugated form</small></div></div>
      <StudyTableConcept kind="conjugation" />
    </div>
  </section>

  <section class="study-section divided" id="entries">
    <header class="study-heading">
      <span class="study-index">02 / PLACEMENT</span>
      <h2>Three ways to open the same study list.</h2>
      <p>Each option is shown inside a reduced Word Rush setup screen. They start expanded so the relationship is visible; click the trigger to test the collapsed state.</p>
    </header>
    <div class="option-grid">
      <div class="option-wrap">
        <div class="option-title"><span>1</span><div><strong>Header utility</strong><small>Quiet and compact; best when study is secondary.</small></div></div>
        <StudyEntryOption variant="header" />
      </div>
      <div class="option-wrap recommended">
        <div class="option-title"><span>2</span><div><strong>Preparation block</strong><small>Recommended: clearly belongs before Play without competing with it.</small></div></div>
        <StudyEntryOption variant="block" />
      </div>
      <div class="option-wrap">
        <div class="option-title"><span>3</span><div><strong>Edge rail</strong><small>Distinctive and space-efficient, but less obvious on mobile.</small></div></div>
        <StudyEntryOption variant="rail" />
      </div>
    </div>
  </section>

  <footer class="pg2-footer">
    <strong>Playground2 handoff</strong>
    <span>Prototype only. No study control has been added to Words or Verb Lab yet.</span>
  </footer>
</section>

<style>
  :global(html) { scroll-behavior: smooth; }
  .pg2-shell { width: min(100%, 980px); margin-inline: auto; display: grid; gap: 1.35rem; }
  .pg2-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 1.2rem; }
  .pg2-header h1 { max-width: 700px; margin: 0.3rem 0 0.48rem; color: var(--text); font: 800 clamp(1.7rem, 4vw, 2.7rem)/1.04 var(--display); letter-spacing: -0.06em; }
  .pg2-header .section-copy { max-width: 690px; margin: 0; }
  .palette-note { display: grid; grid-template-columns: auto auto 1fr; gap: 0.5rem; align-items: center; padding: 0.78rem 0.9rem; border: 1px solid color-mix(in srgb, #7065e8 24%, var(--line)); border-radius: 13px; background: color-mix(in srgb, var(--surface-strong) 85%, transparent); }
  .palette-swatch { width: 1.1rem; height: 2.3rem; border-radius: 999px; } .palette-swatch.violet { background: #7065e8; } .palette-swatch.coral { background: #e56f52; }
  .palette-note div { margin-left: 0.3rem; } .palette-note strong { color: var(--text); font-size: 0.8rem; } .palette-note p { margin: 0.15rem 0 0; color: var(--muted); font-size: 0.75rem; line-height: 1.4; }
  .study-nav { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.6rem; }
  .study-nav a { display: grid; grid-template-columns: auto 1fr; grid-template-rows: auto auto; gap: 0.05rem 0.65rem; align-items: center; padding: 0.82rem; border: 1px solid var(--line); border-radius: 14px; color: var(--text); text-decoration: none; background: color-mix(in srgb, var(--surface-strong) 78%, transparent); }
  .study-nav a:hover { border-color: color-mix(in srgb, #7065e8 48%, var(--line)); transform: translateY(-1px); }
  .study-nav a > span { grid-row: 1 / 3; display: grid; width: 2rem; height: 2rem; place-items: center; border-radius: 9px; color: #7065e8; background: color-mix(in srgb, #7065e8 10%, transparent); font: 750 0.68rem/1 var(--mono); }
  .study-nav a strong { font-size: 0.82rem; } .study-nav a small { color: var(--muted); font-size: 0.7rem; }
  .study-section { display: grid; gap: 1.3rem; padding-top: 1rem; scroll-margin-top: 5.5rem; }
  .study-section.divided { padding-top: 2.4rem; border-top: 1px solid var(--line); }
  .study-heading { width: min(100%, 760px); margin-inline: auto; text-align: center; }
  .study-index { display: inline-flex; padding: 0.32rem 0.55rem; border: 1px solid var(--line); border-radius: 999px; color: #7065e8; background: color-mix(in srgb, #7065e8 10%, transparent); font: 750 0.66rem/1 var(--mono); letter-spacing: 0.12em; }
  .study-heading h2 { margin: 0.7rem 0 0.42rem; color: var(--text); font: 800 clamp(1.4rem, 4vw, 2rem)/1.08 var(--display); letter-spacing: -0.048em; }
  .study-heading p { margin: 0; color: var(--muted); font-size: 0.86rem; line-height: 1.55; }
  .concept-stack { display: grid; gap: 0.75rem; }
  .concept-label, .option-title { display: flex; align-items: center; gap: 0.65rem; margin-top: 1rem; }
  .concept-label > span, .option-title > span { display: grid; flex: 0 0 auto; width: 1.8rem; height: 1.8rem; place-items: center; border-radius: 8px; color: #7065e8; background: color-mix(in srgb, #7065e8 10%, transparent); font: 800 0.66rem/1 var(--mono); }
  .concept-label > div, .option-title > div { display: grid; gap: 0.12rem; } .concept-label strong, .option-title strong { color: var(--text); font-size: 0.83rem; } .concept-label small, .option-title small { color: var(--muted); font-size: 0.72rem; }
  .option-grid { display: grid; gap: 2rem; }
  .option-wrap { display: grid; gap: 0.65rem; }
  .option-wrap.recommended .option-title > span { color: white; background: #7065e8; }
  .pg2-footer { display: flex; justify-content: space-between; gap: 1rem; padding: 0.8rem 0; border-top: 1px solid var(--line); color: var(--muted); font-size: 0.75rem; } .pg2-footer strong { color: #e56f52; }
  @media (max-width: 650px) { .pg2-header, .pg2-footer { align-items: flex-start; flex-direction: column; } .study-nav { grid-template-columns: 1fr; } }
</style>
