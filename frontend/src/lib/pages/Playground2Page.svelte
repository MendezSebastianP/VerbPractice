<script lang="ts">
  import EnglishVerbOption from '../components/playground2/EnglishVerbOption.svelte';
  import { href } from '../router';

  type TenseKey = 'past' | 'participle';

  let selectedTenses: TenseKey[] = ['past', 'participle'];

  function toggleTense(tense: TenseKey): void {
    if (selectedTenses.includes(tense)) {
      if (selectedTenses.length === 1) return;
      selectedTenses = selectedTenses.filter((entry) => entry !== tense);
      return;
    }
    selectedTenses = tense === 'past'
      ? ['past', ...selectedTenses]
      : [...selectedTenses, 'participle'];
  }
</script>

<section class="pg2-shell">
  <header class="pg2-hero">
    <div class="hero-copy">
      <p class="eyebrow">Playground 2 · English verb tables</p>
      <h1>Practice the forms that actually change.</h1>
      <p>
        English drops the pronoun grid. Each verb gets one answer for <strong>Past</strong>,
        <strong>Past participle</strong>, or both—and the whole batch is checked only at the end.
        Both options below reuse the current Verb Table game frame; only the English form changes.
      </p>
      <div class="hero-actions">
        <a class="text-switch" href={href('/training/verbs?mode=tables')}>
          Open current verb tables →
        </a>
        <span>Concept only · no trainer data is changed here</span>
      </div>
    </div>

    <div class="parts-display" aria-label="Example English principal parts">
      <span class="parts-label">ONE VERB · THREE PRINCIPAL PARTS</span>
      <div class="part-word base-word"><small>Base</small><strong>write</strong></div>
      <i aria-hidden="true"></i>
      <div class="part-word past-word"><small>Past</small><strong>wrote</strong></div>
      <i aria-hidden="true"></i>
      <div class="part-word participle-word"><small>Past participle</small><strong>written</strong></div>
    </div>
  </header>

  <section class="tense-control" aria-labelledby="tense-control-title">
    <div>
      <span>SHARED DEMO SETUP</span>
      <h2 id="tense-control-title">Which forms did the learner pick?</h2>
      <p>Toggle a form to see both concepts adapt. At least one stays selected.</p>
    </div>
    <div class="tense-buttons" role="group" aria-label="Forms to practice">
      <button
        class:tense-on={selectedTenses.includes('past')}
        type="button"
        disabled={selectedTenses.length === 1 && selectedTenses.includes('past')}
        aria-pressed={selectedTenses.includes('past')}
        on:click={() => toggleTense('past')}
      >
        <span class="tense-mark" aria-hidden="true">{selectedTenses.includes('past') ? '✓' : '+'}</span>
        <span><strong>Past</strong><small>went · took · wrote</small></span>
      </button>
      <button
        class:tense-on={selectedTenses.includes('participle')}
        type="button"
        disabled={selectedTenses.length === 1 && selectedTenses.includes('participle')}
        aria-pressed={selectedTenses.includes('participle')}
        on:click={() => toggleTense('participle')}
      >
        <span class="tense-mark" aria-hidden="true">{selectedTenses.includes('participle') ? '✓' : '+'}</span>
        <span><strong>Past participle</strong><small>gone · taken · written</small></span>
      </button>
    </div>
  </section>

  <nav class="option-jump" aria-label="English table options">
    <a href="#option-a">
      <span>A</span>
      <div><strong>Batch matrix</strong><small>See every verb and both forms together</small></div>
    </a>
    <a href="#option-b">
      <span>B</span>
      <div><strong>Guided ledger</strong><small>Reduce the amount that is active at once</small></div>
    </a>
  </nav>

  <section class="concept-section recommended" id="option-a">
    <header class="concept-heading">
      <div class="option-id">
        <span>A</span>
        <em>RECOMMENDED</em>
      </div>
      <div>
        <p>PAIR THE FORMS</p>
        <h2>Batch matrix</h2>
        <span>
          Desktop keeps the requested verb-by-form table, with one shared column track from
          header to rows. Mobile uses the same Verb Table stage but keeps one verb on screen
          with both selected forms stacked, so <em>went</em> and <em>gone</em> stay connected.
        </span>
      </div>
      <ul>
        <li>Fastest to scan and edit on desktop</li>
        <li>Strongest link between the two irregular forms</li>
        <li>One final check; no correctness leaks mid-run</li>
      </ul>
    </header>
    {#key `matrix:${selectedTenses.join(':')}`}
      <EnglishVerbOption variant="matrix" {selectedTenses} />
    {/key}
  </section>

  <section class="concept-section" id="option-b">
    <header class="concept-heading">
      <div class="option-id">
        <span>B</span>
        <em>FOCUS MODE</em>
      </div>
      <div>
        <p>LOWER THE VISUAL LOAD</p>
        <h2>Guided ledger</h2>
        <span>
          Desktop keeps one verb active and puts the selected English forms in the familiar
          Verb Table answer rows. Mobile narrows further to one form at a time while keeping
          the active form, verb position, and remaining count visible above the keyboard.
        </span>
      </div>
      <ul>
        <li>Calmer for longer batches</li>
        <li>Better fit above a small mobile keyboard</li>
        <li>More steps and less side-by-side form comparison</li>
      </ul>
    </header>
    {#key `guided:${selectedTenses.join(':')}`}
      <EnglishVerbOption variant="guided" {selectedTenses} />
    {/key}
  </section>

  <aside class="implementation-note">
    <span>LIVE TRAINER NOTE</span>
    <p>
      These are interaction prototypes. The current conjugation API grades one verb and one
      pronoun-shaped tense table at a time; shipping either option will need an English-only batch
      payload keyed by <strong>verb → tense</strong>. The verb <strong>be</strong> also needs a
      special Past answer such as <strong>was / were</strong>.
    </p>
  </aside>
</section>

<style>
  :global(html) {
    scroll-behavior: smooth;
  }

  .pg2-shell {
    --verb-blue: #244db7;
    --verb-coral: #ad3f26;
    --verb-teal: #176b56;
    --verb-on-accent: #ffffff;
    width: min(100%, 1180px);
    margin-inline: auto;
    display: grid;
    gap: 1.25rem;
  }

  :global(html[data-theme='dark']) .pg2-shell,
  :global(html[data-theme='arcade']) .pg2-shell {
    --verb-blue: #9bb8ff;
    --verb-coral: #ff9d83;
    --verb-teal: #79d9ba;
    --verb-on-accent: #10182b;
  }

  .pg2-hero {
    display: grid;
    grid-template-columns: minmax(0, 1.15fr) minmax(300px, 0.85fr);
    gap: clamp(1.2rem, 4vw, 3rem);
    align-items: center;
    padding: clamp(1.2rem, 4vw, 2.2rem);
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--line) 78%, var(--verb-blue));
    border-radius: 24px;
    background:
      linear-gradient(135deg, color-mix(in srgb, var(--surface-strong) 95%, var(--verb-blue) 5%), var(--surface-strong));
    box-shadow: var(--shadow);
  }

  .hero-copy h1 {
    max-width: 690px;
    margin: 0.38rem 0 0.62rem;
    color: var(--text);
    font: 820 clamp(2rem, 5vw, 3.75rem)/0.96 var(--display);
    letter-spacing: -0.065em;
  }

  .hero-copy > p:not(.eyebrow) {
    max-width: 680px;
    margin: 0;
    color: var(--muted);
    font-size: clamp(0.88rem, 1.5vw, 1rem);
    line-height: 1.6;
  }

  .hero-copy > p strong {
    color: var(--text);
  }

  .hero-actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.7rem 1rem;
    margin-top: 1rem;
  }

  .hero-actions span {
    color: var(--muted);
    font-size: 0.68rem;
  }

  .parts-display {
    position: relative;
    display: grid;
    grid-template-columns: 1fr auto 1fr auto 1fr;
    grid-template-rows: auto 1fr;
    gap: 0.55rem;
    align-items: center;
    min-height: 12rem;
    padding: 1rem;
    border: 1px solid var(--line);
    border-radius: 18px;
    background:
      linear-gradient(150deg, color-mix(in srgb, var(--verb-blue) 11%, var(--surface)), color-mix(in srgb, var(--verb-coral) 9%, var(--surface)));
  }

  .parts-label {
    grid-column: 1 / -1;
    color: var(--muted);
    font: 720 0.58rem/1 var(--mono);
    letter-spacing: 0.11em;
  }

  .part-word {
    display: grid;
    gap: 0.28rem;
    min-width: 0;
    text-align: center;
  }

  .part-word small {
    color: var(--muted);
    font-size: 0.63rem;
  }

  .part-word strong {
    overflow-wrap: anywhere;
    color: var(--text);
    font: 800 clamp(1.05rem, 2.4vw, 1.55rem)/1 var(--mono);
  }

  .parts-display i {
    position: relative;
    width: 1.25rem;
    height: 1px;
    background: color-mix(in srgb, var(--verb-coral) 70%, var(--line));
  }

  .parts-display i::after {
    position: absolute;
    top: 50%;
    right: -1px;
    width: 0.38rem;
    height: 0.38rem;
    border-top: 1px solid var(--verb-coral);
    border-right: 1px solid var(--verb-coral);
    content: '';
    transform: translateY(-50%) rotate(45deg);
  }

  .past-word strong {
    color: var(--verb-blue);
  }

  .participle-word strong {
    color: var(--verb-coral);
  }

  .tense-control {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(360px, 0.85fr);
    gap: 1.25rem;
    align-items: center;
    padding: 1rem 1.1rem;
    border: 1px solid var(--line);
    border-radius: 17px;
    background: color-mix(in srgb, var(--surface-strong) 84%, transparent);
  }

  .tense-control > div:first-child > span,
  .concept-heading > div > p,
  .implementation-note > span {
    color: var(--verb-blue);
    font: 750 0.6rem/1 var(--mono);
    letter-spacing: 0.11em;
  }

  .tense-control h2 {
    margin: 0.32rem 0 0.2rem;
    color: var(--text);
    font: 780 1.08rem/1.1 var(--display);
    letter-spacing: -0.03em;
  }

  .tense-control p {
    margin: 0;
    color: var(--muted);
    font-size: 0.76rem;
  }

  .tense-buttons {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.55rem;
  }

  .tense-buttons button {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.55rem;
    align-items: center;
    min-height: 3.8rem;
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 0.6rem;
    color: var(--muted);
    text-align: left;
    background: color-mix(in srgb, var(--surface) 74%, transparent);
  }

  .tense-buttons button:focus-visible,
  .option-jump a:focus-visible {
    outline: 3px solid color-mix(in srgb, var(--verb-blue) 34%, transparent);
    outline-offset: 2px;
  }

  .tense-buttons .tense-on {
    border-color: color-mix(in srgb, var(--verb-blue) 56%, var(--line));
    color: var(--text);
    background: color-mix(in srgb, var(--verb-blue) 9%, var(--surface));
  }

  .tense-buttons button:disabled {
    cursor: default;
    opacity: 0.7;
  }

  .tense-buttons button:last-child.tense-on {
    border-color: color-mix(in srgb, var(--verb-coral) 56%, var(--line));
    background: color-mix(in srgb, var(--verb-coral) 9%, var(--surface));
  }

  .tense-mark {
    display: grid;
    width: 1.75rem;
    height: 1.75rem;
    place-items: center;
    border-radius: 8px;
    color: var(--muted);
    background: color-mix(in srgb, var(--text) 7%, transparent);
    font: 800 0.7rem/1 var(--mono);
  }

  .tense-on .tense-mark {
    color: var(--verb-on-accent);
    background: var(--verb-blue);
  }

  .tense-on:last-child .tense-mark {
    background: var(--verb-coral);
  }

  .tense-buttons button > span:last-child {
    display: grid;
    min-width: 0;
    gap: 0.13rem;
  }

  .tense-buttons strong {
    font-size: 0.76rem;
  }

  .tense-buttons small {
    overflow: hidden;
    color: var(--muted);
    font-size: 0.61rem;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .option-jump {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.7rem;
  }

  .option-jump a {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.7rem;
    align-items: center;
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 0.75rem;
    color: var(--text);
    text-decoration: none;
    background: color-mix(in srgb, var(--surface-strong) 78%, transparent);
  }

  .option-jump > a > span,
  .option-id > span {
    display: grid;
    width: 2rem;
    height: 2rem;
    place-items: center;
    border-radius: 9px;
    color: var(--verb-on-accent);
    background: var(--verb-blue);
    font: 800 0.68rem/1 var(--mono);
  }

  .option-jump a:last-child > span,
  .concept-section:not(.recommended) .option-id > span {
    background: var(--verb-coral);
  }

  .option-jump a > div {
    display: grid;
    gap: 0.12rem;
  }

  .option-jump strong {
    font-size: 0.8rem;
  }

  .option-jump small {
    color: var(--muted);
    font-size: 0.67rem;
  }

  .concept-section {
    display: grid;
    gap: 1rem;
    padding: clamp(1rem, 3vw, 1.35rem);
    border: 1px solid var(--line);
    border-radius: 22px;
    background: color-mix(in srgb, var(--surface-strong) 78%, transparent);
    scroll-margin-top: 5.5rem;
  }

  .concept-section.recommended {
    border-color: color-mix(in srgb, var(--verb-blue) 40%, var(--line));
  }

  .concept-heading {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) minmax(220px, 0.48fr);
    gap: 0.85rem 1.15rem;
    align-items: start;
  }

  .option-id {
    display: grid;
    justify-items: center;
    gap: 0.35rem;
  }

  .option-id em {
    color: var(--verb-blue);
    font: 720 0.48rem/1 var(--mono);
    font-style: normal;
    letter-spacing: 0.08em;
    writing-mode: vertical-rl;
  }

  .concept-section:not(.recommended) .option-id em,
  .concept-section:not(.recommended) .concept-heading > div > p {
    color: var(--verb-coral);
  }

  .concept-heading > div > p {
    margin: 0 0 0.28rem;
  }

  .concept-heading h2 {
    margin: 0 0 0.35rem;
    color: var(--text);
    font: 810 clamp(1.4rem, 3vw, 2rem)/1 var(--display);
    letter-spacing: -0.048em;
  }

  .concept-heading > div > span {
    display: block;
    max-width: 690px;
    color: var(--muted);
    font-size: 0.79rem;
    line-height: 1.5;
  }

  .concept-heading > div > span em {
    color: var(--text);
    font-style: normal;
    font-weight: 700;
  }

  .concept-heading ul {
    display: grid;
    gap: 0.4rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .concept-heading li {
    position: relative;
    padding-left: 1rem;
    color: var(--muted);
    font-size: 0.68rem;
    line-height: 1.35;
  }

  .concept-heading li::before {
    position: absolute;
    left: 0;
    color: var(--verb-teal);
    content: '✓';
    font-weight: 800;
  }

  .concept-section:not(.recommended) .concept-heading li:last-child::before {
    color: var(--verb-coral);
    content: '△';
  }

  .implementation-note {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.8rem;
    align-items: baseline;
    padding: 0.9rem 1rem;
    border: 1px dashed color-mix(in srgb, var(--verb-coral) 48%, var(--line));
    border-radius: 14px;
    background: color-mix(in srgb, var(--verb-coral) 6%, var(--surface));
  }

  .implementation-note > span {
    color: var(--verb-coral);
  }

  .implementation-note p {
    margin: 0;
    color: var(--muted);
    font-size: 0.7rem;
    line-height: 1.5;
  }

  .implementation-note strong {
    color: var(--text);
  }

  @media (max-width: 820px) {
    .pg2-hero,
    .tense-control {
      grid-template-columns: 1fr;
    }

    .parts-display {
      min-height: 9rem;
    }

    .concept-heading {
      grid-template-columns: auto 1fr;
    }

    .concept-heading ul {
      grid-column: 2;
    }
  }

  @media (max-width: 590px) {
    .pg2-hero {
      padding: 1rem;
      border-radius: 18px;
    }

    .parts-display {
      grid-template-columns: 1fr;
      grid-template-rows: auto repeat(5, auto);
      gap: 0.4rem;
    }

    .parts-label {
      grid-column: 1;
    }

    .parts-display i {
      width: 1px;
      height: 0.85rem;
      margin-inline: auto;
    }

    .parts-display i::after {
      top: auto;
      right: 50%;
      bottom: -1px;
      transform: translateX(50%) rotate(135deg);
    }

    .tense-buttons,
    .option-jump {
      grid-template-columns: 1fr;
    }

    .concept-section {
      padding: 0.75rem;
      border-radius: 17px;
    }

    .concept-heading {
      grid-template-columns: 1fr;
    }

    .option-id {
      display: flex;
      gap: 0.6rem;
      justify-items: initial;
      align-items: center;
      justify-content: flex-start;
    }

    .option-id em {
      font-size: 0.56rem;
      writing-mode: horizontal-tb;
    }

    .concept-heading ul {
      grid-column: 1;
    }

    .implementation-note {
      grid-template-columns: 1fr;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    :global(html) {
      scroll-behavior: auto;
    }
  }
</style>
