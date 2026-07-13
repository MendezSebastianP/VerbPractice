<script lang="ts">
  // Study 02 — G1 in-game HUD. 'current' replicates the production utility
  // row + tense strip + verb prompt at their real sizes; 'readable' rescales
  // the same layout; 'marquee' consolidates the HUD into one LED strip line.
  // 'names' and 'abbr' are the H1-B follow-ups: labeled segments so the
  // previous/next tenses stay identifiable, demoed at 3 and 9 tenses.
  export let variant: 'current' | 'readable' | 'marquee' | 'names' | 'abbr';
  export let index = 'H1';
  export let kicker = '';
  export let title = '';
  export let description = '';

  const TENSES = [
    { name: 'Présent', state: 'done', score: '5/6 correct' },
    { name: 'Imparfait', state: 'active', score: 'filling now' },
    { name: 'Futur simple', state: 'waiting', score: 'waiting' },
  ];

  const TENSES3 = [
    { name: 'Présent', abbr: 'PRÉ', state: 'done' },
    { name: 'Imparfait', abbr: 'IMP', state: 'active' },
    { name: 'Futur simple', abbr: 'FUT', state: 'waiting' },
  ];

  const TENSES9 = [
    { name: 'Présent', abbr: 'PRÉ', state: 'done' },
    { name: 'Passé composé', abbr: 'PC', state: 'done' },
    { name: 'Imparfait', abbr: 'IMP', state: 'done' },
    { name: 'Plus-que-parfait', abbr: 'PQP', state: 'done' },
    { name: 'Futur simple', abbr: 'FUT', state: 'active' },
    { name: 'Futur antérieur', abbr: 'FA', state: 'waiting' },
    { name: 'Conditionnel présent', abbr: 'COND', state: 'waiting' },
    { name: 'Subjonctif présent', abbr: 'SUBJ', state: 'waiting' },
    { name: 'Passé simple', abbr: 'PS', state: 'waiting' },
  ];
</script>

<article class="hud-study" data-variant={variant}>
  <header class="concept-intro" class:intro-current={variant === 'current'}>
    <span class="concept-number">{index}</span>
    <div><p>{kicker}</p><h3>{title}</h3><span>{description}</span></div>
  </header>

  <div class="stage" class:stage-current={variant === 'current'}>
    {#if variant === 'current'}
      <!-- ======= CURRENT PRODUCTION SIZES ======= -->
      <div class="cur-utility">
        <span><i aria-hidden="true"></i> TABLE SHORTCUTS ON</span>
        <small>Enter next / repeat · Backspace returns · Esc ×2 finishes</small>
      </div>
      <i class="px-flag" aria-hidden="true">utility row 8px · 48% contrast</i>

      <div class="cur-strip">
        {#each TENSES as tense, i}
          <div class="cur-tense" class:cur-tense-active={tense.state === 'active'} class:cur-tense-done={tense.state === 'done'}>
            <span>{String(i + 1).padStart(2, '0')}</span>
            <div><strong>{tense.name}</strong><small>{tense.score}</small></div>
            <i aria-hidden="true">{tense.state === 'done' ? '✓' : tense.state === 'active' ? '↓' : '·'}</i>
          </div>
        {/each}
      </div>
      <i class="px-flag" aria-hidden="true">tense names 9.9px · status 7.4px</i>

      <div class="cur-prompt">
        <div><span>CURRENT VERB</span><strong>prendre</strong></div>
        <div>
          <span>Imparfait · active answer</span>
          <strong><em>tu</em> + prendre</strong>
          <small>Only the active answer receives the pointer.</small>
        </div>
        <div><span>TENSE</span><strong>2/3</strong><small>tu -&gt; Imparfait</small></div>
      </div>

      <div class="cur-row">
        <span class="cur-marker" aria-hidden="true">▶</span>
        <span class="row-label"><small>02</small><strong>tu</strong></span>
        <div class="cur-input-shell">
          <span class="cur-input">prenais</span>
          <span class="cur-shortcut">ENTER = NEXT · EMPTY REPEATS</span>
        </div>
      </div>
      <i class="px-flag" aria-hidden="true">input hint 6.1px</i>
    {:else if variant === 'readable'}
      <!-- ======= OPTION A — same zones, readable scale ======= -->
      <div class="rd-utility">
        <span><i aria-hidden="true"></i> Shortcuts on</span>
        <small><b>Enter</b> next · <b>Backspace</b> back · <b>Esc ×2</b> finish</small>
      </div>

      <div class="rd-strip">
        {#each TENSES as tense, i}
          <div class="rd-tense" class:rd-tense-active={tense.state === 'active'} class:rd-tense-done={tense.state === 'done'}>
            <span>{String(i + 1).padStart(2, '0')}</span>
            <div><strong>{tense.name}</strong><small>{tense.score}</small></div>
            <i aria-hidden="true">{tense.state === 'done' ? '✓' : tense.state === 'active' ? '▶' : '·'}</i>
          </div>
        {/each}
      </div>

      <div class="rd-prompt">
        <div><span>Verb</span><strong>prendre</strong></div>
        <div>
          <span>Imparfait</span>
          <strong><em>tu</em> + prendre</strong>
        </div>
        <div><span>Tense</span><strong>2<small>/3</small></strong></div>
      </div>

      <div class="rd-row">
        <span class="row-label"><small>02</small><strong>tu</strong></span>
        <div class="rd-input-shell">
          <span class="rd-input">prenais</span>
        </div>
        <span class="rd-hint"><b>Enter</b> next</span>
      </div>
    {:else if variant === 'marquee'}
      <!-- ======= OPTION B — marquee LED strip ======= -->
      <div class="mq-top">
        <div class="mq-led-block">
          <div class="mq-led-row" role="img" aria-label="Tense 2 of 3, Imparfait active">
            {#each TENSES as tense}
              <span
                class="mq-led"
                class:mq-led-done={tense.state === 'done'}
                class:mq-led-active={tense.state === 'active'}
              ></span>
            {/each}
          </div>
          <span class="mq-led-count">TENSE 2/3</span>
        </div>
        <strong class="mq-tense-name">Imparfait</strong>
      </div>

      <div class="mq-hero">
        <span>Current verb</span>
        <strong>prendre</strong>
        <em><b>tu</b> + prendre</em>
      </div>

      <div class="mq-row">
        <span class="row-label"><small>02</small><strong>tu</strong></span>
        <div class="mq-input-shell"><span class="mq-input">prenais</span></div>
      </div>

      <div class="mq-utility">
        <span><b>Enter</b> next</span><i></i><span><b>Backspace</b> back</span><i></i><span><b>Esc ×2</b> finish</span>
      </div>
    {:else if variant === 'names'}
      <!-- ======= H1-B1 — full names in the segments ======= -->
      <div class="lab-demo">
        <span class="lab-tag">3 tenses</span>
        <div class="nm-top">
          <div class="nm-strip" role="img" aria-label="Tense 2 of 3, Imparfait active">
            {#each TENSES3 as t}
              <span class="nm-seg" class:seg-done={t.state === 'done'} class:seg-active={t.state === 'active'}>{t.name}</span>
            {/each}
          </div>
          <div class="nm-marquee"><span>TENSE 2/3</span><strong>Imparfait</strong></div>
        </div>
      </div>
      <div class="lab-demo">
        <span class="lab-tag">9 tenses</span>
        <div class="nm-top nm-top-stack">
          <div class="nm-marquee nm-marquee-row"><span>TENSE 5/9</span><strong>Futur simple</strong></div>
          <div class="nm-strip nm-strip-many" role="img" aria-label="Tense 5 of 9, Futur simple active">
            {#each TENSES9 as t}
              <span class="nm-seg" class:seg-done={t.state === 'done'} class:seg-active={t.state === 'active'}>{t.name}</span>
            {/each}
          </div>
        </div>
      </div>
    {:else}
      <!-- ======= H1-B2 — abbreviation slabs ======= -->
      <div class="lab-demo">
        <span class="lab-tag">3 tenses</span>
        <div class="ab-top">
          <div class="ab-block">
            <div class="ab-strip" role="img" aria-label="Tense 2 of 3, Imparfait active">
              {#each TENSES3 as t}
                <span class="ab-seg" class:seg-done={t.state === 'done'} class:seg-active={t.state === 'active'}>{t.abbr}</span>
              {/each}
            </div>
            <span class="ab-count">TENSE 2/3</span>
          </div>
          <strong class="ab-name">Imparfait</strong>
        </div>
      </div>
      <div class="lab-demo">
        <span class="lab-tag">9 tenses</span>
        <div class="ab-top">
          <div class="ab-block">
            <div class="ab-strip" role="img" aria-label="Tense 5 of 9, Futur simple active">
              {#each TENSES9 as t}
                <span class="ab-seg" class:seg-done={t.state === 'done'} class:seg-active={t.state === 'active'}>{t.abbr}</span>
              {/each}
            </div>
            <span class="ab-count">TENSE 5/9</span>
          </div>
          <strong class="ab-name">Futur simple</strong>
        </div>
      </div>
    {/if}
  </div>

  {#if variant === 'readable'}
    <ul class="study-notes">
      <li>Every HUD label lands at 0.7rem (11.2px) or above; secondary text moves from 48% to 72% white for real contrast.</li>
      <li>Tense cards grow to a 3rem row: name 0.9rem, status 0.75rem — readable at arm's length while playing.</li>
      <li>The keyboard hint leaves the input and becomes a calm caption beside it, instead of a 6px pill on top of your typing.</li>
    </ul>
  {:else if variant === 'marquee'}
    <ul class="study-notes">
      <li>The tense strip collapses into an LED segment bar — the active tense is named once, big, instead of three shrunken cards.</li>
      <li>One utility line at the bottom holds the three shortcuts that matter, at 0.78rem with full contrast.</li>
      <li>Less text on screen overall: the verb is the hero, everything else is instrument-panel glanceable.</li>
    </ul>
  {:else if variant === 'names'}
    <ul class="study-notes">
      <li>Full names ride inside the segments at 0.78rem, so previous and next tenses read without moving your eyes to a legend.</li>
      <li>At 3–4 tenses this is the most informative option. At 9, equal-width segments truncate the long names (Conditionn…, Subjoncti…) — the honest cost of full labels.</li>
      <li>On phones the 9-tense strip wraps to two rows instead of shrinking below readable size.</li>
    </ul>
  {:else if variant === 'abbr'}
    <ul class="study-notes">
      <li>Fixed slabs carry 2–4 letter codes (PRÉ, PC, IMP, PQP…) in VT323 — the LED look survives, and even 9 tenses fit one row on a phone.</li>
      <li>The full active-tense name still gets the big gold marquee, so the code only has to identify neighbours, not teach them.</li>
      <li>Abbreviations come from the tense list per language — French shown here; RU/EN/ES lists provide their own codes.</li>
    </ul>
  {/if}
</article>

<style>
  .hud-study { width: min(100%, 760px); margin-inline: auto; }
  .concept-intro { display: grid; grid-template-columns: auto 1fr; gap: 0.85rem; align-items: start; margin-bottom: 0.8rem; padding-inline: 0.25rem; }
  .concept-number { display: grid; width: 2.45rem; height: 2.45rem; place-items: center; border: 1px solid var(--line-strong); border-radius: 13px; color: var(--accent-strong); background: var(--accent-soft); font: 800 0.7rem/1 var(--mono); }
  .intro-current .concept-number { color: var(--muted); background: transparent; border-style: dashed; }
  .concept-intro p { margin: 0 0 0.12rem; color: var(--accent-strong); font: 750 0.62rem/1 var(--mono); letter-spacing: 0.12em; text-transform: uppercase; }
  .intro-current p { color: var(--muted); }
  .concept-intro h3 { margin: 0 0 0.25rem; color: var(--text); font: 800 clamp(1.08rem, 3vw, 1.4rem)/1.15 var(--display); letter-spacing: -0.035em; }
  .concept-intro div > span { color: var(--muted); font-size: 0.82rem; line-height: 1.45; }

  /* All three stages live on the dark G1 frame so the comparison is honest */
  .stage {
    display: grid;
    gap: 0.85rem;
    padding: clamp(0.9rem, 3vw, 1.2rem);
    border: 1px solid color-mix(in srgb, var(--accent) 38%, rgba(255, 255, 255, 0.14));
    border-radius: 20px;
    color: white;
    background:
      radial-gradient(circle at 92% 0%, color-mix(in srgb, var(--accent) 20%, transparent), transparent 31%),
      color-mix(in srgb, var(--surface-dark) 91%, black 9%);
  }
  .stage-current { border-style: dashed; }

  .px-flag {
    justify-self: end;
    margin-top: -0.5rem;
    width: fit-content;
    padding: 0.22rem 0.5rem;
    border: 1px solid color-mix(in srgb, var(--danger) 65%, transparent);
    border-radius: 999px;
    color: #ff91a3;
    background: color-mix(in srgb, var(--danger) 14%, transparent);
    font: 700 0.68rem/1.3 var(--ui);
    font-style: normal;
  }

  .study-notes { display: grid; gap: 0.3rem; margin: 0.7rem 0 0; padding-left: 1.1rem; }
  .study-notes li { color: var(--muted); font-size: 0.82rem; line-height: 1.5; }
  .study-notes li::marker { color: var(--accent-strong); }

  /* ===== CURRENT — production values ===== */
  .cur-utility { display: flex; align-items: center; justify-content: space-between; gap: 0.8rem; color: rgba(255, 255, 255, 0.48); font: 700 0.5rem/1 var(--mono); letter-spacing: 0.1em; }
  .cur-utility > span { display: flex; align-items: center; gap: 0.45rem; }
  .cur-utility i { width: 0.45rem; height: 0.45rem; border-radius: 50%; background: #55ee9b; box-shadow: 0 0 9px #55ee9b; }
  .cur-utility small { font-size: 0.48rem; letter-spacing: 0; }

  .cur-strip { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.4rem; }
  .cur-tense { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 0.45rem; align-items: center; padding: 0.58rem; border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 10px; color: rgba(255, 255, 255, 0.5); background: rgba(255, 255, 255, 0.035); }
  .cur-tense > span { color: var(--accent-2); font: 750 0.45rem/1 var(--mono); }
  .cur-tense strong { display: block; font-size: 0.62rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .cur-tense small { display: block; font-size: 0.46rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .cur-tense i { font-style: normal; font-weight: 850; }
  .cur-tense-active { border-color: var(--accent-2); color: white; background: color-mix(in srgb, var(--accent) 22%, transparent); box-shadow: inset 0 -2px 0 var(--accent-2); }
  .cur-tense-done { border-color: color-mix(in srgb, #55ee9b 45%, transparent); color: #55ee9b; background: color-mix(in srgb, #55ee9b 9%, transparent); }

  .cur-prompt { display: grid; grid-template-columns: minmax(5rem, 0.65fr) minmax(0, 1.8fr) auto; gap: 0.8rem; align-items: center; padding: 0.8rem; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; background: rgba(8, 13, 31, 0.54); }
  .cur-prompt > div { display: grid; gap: 0.16rem; min-width: 0; }
  .cur-prompt > div:nth-child(2) { justify-items: center; text-align: center; }
  .cur-prompt > div:last-child { justify-items: end; text-align: right; }
  .cur-prompt span { color: var(--accent-2); font: 750 0.48rem/1 var(--mono); letter-spacing: 0.1em; }
  .cur-prompt > div:first-child > strong { font: 820 clamp(1.2rem, 4vw, 1.8rem)/1 var(--display); }
  .cur-prompt > div:nth-child(2) > strong { font: 780 clamp(1rem, 3vw, 1.6rem)/1.1 var(--display); }
  .cur-prompt em { color: #f6c84c; font-style: normal; }
  .cur-prompt small { color: rgba(255, 255, 255, 0.5); font-size: 0.5rem; }

  .cur-row { display: grid; grid-template-columns: auto 7rem minmax(0, 1fr); gap: 0.7rem; align-items: center; padding: 0.58rem 0.65rem; border: 1px solid var(--accent-2); border-radius: 5px; background: color-mix(in srgb, var(--accent) 18%, rgba(255, 255, 255, 0.025)); }
  .cur-marker { width: 0.75rem; color: var(--accent-2); font: 800 0.56rem/1 var(--mono); text-align: center; }
  .cur-row .row-label { display: grid; grid-template-columns: 1.5rem 1fr; gap: 0.35rem; align-items: center; }
  .cur-row .row-label small { color: var(--accent-2); font: 750 0.44rem/1 var(--mono); }
  .cur-row .row-label strong { color: white; font-size: 1.05rem; font-weight: 820; }
  .cur-input-shell { position: relative; min-width: 0; }
  .cur-input { display: block; padding: 0.72rem 0.8rem; border: 1px solid var(--accent-2); border-radius: 8px; color: white; background: rgba(6, 8, 24, 0.72); font: 680 0.95rem/1 var(--display); box-shadow: inset 0 -2px 0 var(--accent-2); }
  .cur-shortcut { position: absolute; right: 0.35rem; bottom: -0.28rem; padding: 0.13rem 0.3rem; border-radius: 999px; color: #191300; background: #f6c84c; font: 850 0.38rem/1 var(--mono); }

  /* ===== OPTION A — readable pass ===== */
  .rd-utility { display: flex; align-items: center; justify-content: space-between; gap: 0.8rem; color: rgba(255, 255, 255, 0.72); font: 600 0.72rem/1.3 var(--mono); letter-spacing: 0.06em; text-transform: uppercase; }
  .rd-utility > span { display: flex; align-items: center; gap: 0.5rem; }
  .rd-utility i { width: 0.5rem; height: 0.5rem; border-radius: 50%; background: #55ee9b; box-shadow: 0 0 9px #55ee9b; }
  .rd-utility small { font-size: 0.72rem; text-transform: none; letter-spacing: 0.02em; }
  .rd-utility b { color: white; font-weight: 700; }

  .rd-strip { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0.5rem; }
  .rd-tense { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 0.55rem; align-items: center; min-height: 3rem; padding: 0.6rem 0.7rem; border: 1px solid rgba(255, 255, 255, 0.14); border-radius: 11px; color: rgba(255, 255, 255, 0.72); background: rgba(255, 255, 255, 0.035); }
  .rd-tense > span { color: var(--accent-2); font: 750 0.7rem/1 var(--mono); }
  .rd-tense strong { display: block; font-size: 0.9rem; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .rd-tense small { display: block; color: rgba(255, 255, 255, 0.66); font-size: 0.75rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .rd-tense i { font-style: normal; font-weight: 850; font-size: 0.9rem; }
  .rd-tense-active { border-color: var(--accent-2); color: white; background: color-mix(in srgb, var(--accent) 22%, transparent); box-shadow: inset 0 -3px 0 var(--accent-2); }
  .rd-tense-active small { color: rgba(255, 255, 255, 0.78); }
  .rd-tense-done { border-color: color-mix(in srgb, #55ee9b 50%, transparent); color: #78f2ad; background: color-mix(in srgb, #55ee9b 9%, transparent); }
  .rd-tense-done small { color: color-mix(in srgb, #78f2ad 80%, white); }

  .rd-prompt { display: grid; grid-template-columns: minmax(5rem, 0.7fr) minmax(0, 1.6fr) auto; gap: 0.8rem; align-items: center; padding: 0.9rem; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; background: rgba(8, 13, 31, 0.54); }
  .rd-prompt > div { display: grid; gap: 0.25rem; min-width: 0; }
  .rd-prompt > div:nth-child(2) { justify-items: center; text-align: center; }
  .rd-prompt > div:last-child { justify-items: end; text-align: right; }
  .rd-prompt span { color: color-mix(in srgb, var(--accent-2) 88%, white); font: 700 0.7rem/1 var(--mono); letter-spacing: 0.12em; text-transform: uppercase; }
  .rd-prompt > div:first-child > strong { font: 820 clamp(1.25rem, 4vw, 1.9rem)/1 var(--display); }
  .rd-prompt > div:nth-child(2) > strong { font: 700 clamp(1.05rem, 3vw, 1.6rem)/1.15 var(--ui); }
  .rd-prompt > div:last-child > strong { font: 700 1.5rem/1 var(--mono); font-variant-numeric: tabular-nums; }
  .rd-prompt > div:last-child small { font-size: 0.95rem; color: rgba(255, 255, 255, 0.66); }
  .rd-prompt em { color: #f6c84c; font-style: normal; }

  .rd-row { display: grid; grid-template-columns: 7rem minmax(0, 1fr) auto; gap: 0.75rem; align-items: center; padding: 0.65rem 0.75rem; border: 1px solid var(--accent-2); border-radius: 10px; background: color-mix(in srgb, var(--accent) 18%, rgba(255, 255, 255, 0.025)); }
  .rd-row .row-label { display: grid; grid-template-columns: 1.6rem 1fr; gap: 0.4rem; align-items: center; }
  .rd-row .row-label small { color: var(--accent-2); font: 750 0.68rem/1 var(--mono); }
  .rd-row .row-label strong { color: white; font-size: 1.1rem; font-weight: 800; }
  .rd-input-shell { min-width: 0; }
  .rd-input { display: block; padding: 0.75rem 0.85rem; border: 1px solid var(--accent-2); border-radius: 9px; color: white; background: rgba(6, 8, 24, 0.72); font: 650 1.05rem/1 var(--ui); box-shadow: inset 0 -2px 0 var(--accent-2); }
  .rd-hint { color: rgba(255, 255, 255, 0.72); font-size: 0.78rem; white-space: nowrap; }
  .rd-hint b { color: #f6c84c; font-weight: 700; }
  @media (pointer: coarse) { .rd-hint { display: none; } }

  /* ===== OPTION B — marquee LED strip ===== */
  .mq-top { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
  .mq-led-block { display: grid; gap: 0.35rem; }
  .mq-led-row { display: flex; gap: 0.4rem; }
  .mq-led { width: 2.4rem; height: 0.85rem; border-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.18); background: rgba(255, 255, 255, 0.06); }
  .mq-led-done { border-color: #55ee9b; background: color-mix(in srgb, #55ee9b 55%, transparent); box-shadow: 0 0 10px color-mix(in srgb, #55ee9b 45%, transparent); }
  .mq-led-active { border-color: #f6c84c; background: color-mix(in srgb, #f6c84c 60%, transparent); box-shadow: 0 0 12px color-mix(in srgb, #f6c84c 55%, transparent); animation: mq-led-pulse 1.3s ease-in-out infinite; }
  @keyframes mq-led-pulse { 50% { opacity: 0.55; } }
  @media (prefers-reduced-motion: reduce) { .mq-led-active { animation: none; } }
  .mq-led-count { color: rgba(255, 255, 255, 0.72); font: 700 0.78rem/1 var(--mono); letter-spacing: 0.14em; font-variant-numeric: tabular-nums; }
  .mq-tense-name { font: 800 1.3rem/1.1 var(--display); color: #f6c84c; text-shadow: 0 0 16px color-mix(in srgb, #f6c84c 45%, transparent); }

  .mq-hero { display: grid; gap: 0.3rem; justify-items: center; padding: 1.2rem 0.8rem 1.1rem; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; text-align: center; background: rgba(8, 13, 31, 0.54); }
  .mq-hero span { color: rgba(255, 255, 255, 0.66); font: 700 0.72rem/1 var(--mono); letter-spacing: 0.16em; text-transform: uppercase; }
  .mq-hero strong { font: 820 clamp(1.7rem, 5vw, 2.4rem)/1 var(--ui); }
  .mq-hero em { color: rgba(255, 255, 255, 0.8); font-size: 1.05rem; font-style: normal; }
  .mq-hero em b { color: #f6c84c; font-weight: 800; }

  .mq-row { display: grid; grid-template-columns: 7rem minmax(0, 1fr); gap: 0.75rem; align-items: center; padding: 0.65rem 0.75rem; border: 1px solid var(--accent-2); border-radius: 10px; background: color-mix(in srgb, var(--accent) 18%, rgba(255, 255, 255, 0.025)); }
  .mq-row .row-label { display: grid; grid-template-columns: 1.6rem 1fr; gap: 0.4rem; align-items: center; }
  .mq-row .row-label small { color: var(--accent-2); font: 750 0.68rem/1 var(--mono); }
  .mq-row .row-label strong { color: white; font-size: 1.1rem; font-weight: 800; }
  .mq-input-shell { min-width: 0; }
  .mq-input { display: block; padding: 0.75rem 0.85rem; border: 1px solid var(--accent-2); border-radius: 9px; color: white; background: rgba(6, 8, 24, 0.72); font: 650 1.05rem/1 var(--ui); box-shadow: inset 0 -2px 0 var(--accent-2); }

  .mq-utility { display: flex; align-items: center; justify-content: center; gap: 0.7rem; color: rgba(255, 255, 255, 0.72); font-size: 0.78rem; }
  .mq-utility b { color: white; font-weight: 700; }
  .mq-utility i { width: 1px; height: 0.9rem; background: rgba(255, 255, 255, 0.18); }

  /* ===== H1-B1 / H1-B2 shared demo frame ===== */
  .lab-demo { display: grid; gap: 0.5rem; padding: 0.85rem; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 14px; background: rgba(8, 13, 31, 0.45); }
  .lab-tag { width: fit-content; padding: 0.22rem 0.55rem; border: 1px solid color-mix(in srgb, var(--accent) 45%, transparent); border-radius: 999px; color: color-mix(in srgb, var(--accent-strong) 85%, white); background: color-mix(in srgb, var(--accent) 14%, transparent); font: 700 0.72rem/1 var(--mono); letter-spacing: 0.14em; text-transform: uppercase; }

  /* H1-B1 — names inside the segments */
  .nm-top { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
  .nm-top-stack { flex-direction: column; align-items: stretch; gap: 0.55rem; }
  .nm-marquee { display: grid; gap: 0.25rem; justify-items: end; text-align: right; flex-shrink: 0; }
  .nm-marquee-row { grid-auto-flow: column; align-items: baseline; justify-content: space-between; justify-items: start; text-align: left; }
  .nm-marquee span { color: rgba(255, 255, 255, 0.72); font: 700 0.78rem/1 var(--mono); letter-spacing: 0.14em; font-variant-numeric: tabular-nums; }
  .nm-marquee strong { font: 800 1.25rem/1.1 var(--display); color: #f6c84c; text-shadow: 0 0 16px color-mix(in srgb, #f6c84c 45%, transparent); }
  .nm-strip { display: flex; flex-wrap: wrap; gap: 0.4rem; min-width: 0; flex: 1; }
  .nm-seg {
    flex: 1 1 0;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-align: center;
    padding: 0.42rem 0.55rem;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 6px;
    color: rgba(255, 255, 255, 0.6);
    background: rgba(255, 255, 255, 0.05);
    font-size: 0.78rem;
    font-weight: 600;
  }
  .nm-strip-many .nm-seg { flex-basis: 5.5rem; }
  .nm-seg.seg-done { border-color: #55ee9b; color: #78f2ad; background: color-mix(in srgb, #55ee9b 14%, transparent); box-shadow: 0 0 8px color-mix(in srgb, #55ee9b 25%, transparent); }
  .nm-seg.seg-active { border-color: #f6c84c; color: #191300; background: color-mix(in srgb, #f6c84c 88%, transparent); font-weight: 800; box-shadow: 0 0 12px color-mix(in srgb, #f6c84c 55%, transparent); animation: mq-led-pulse 1.3s ease-in-out infinite; }

  /* H1-B2 — abbreviation slabs */
  .ab-top { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
  .ab-block { display: grid; gap: 0.35rem; min-width: 0; }
  .ab-strip { display: flex; flex-wrap: wrap; gap: 0.4rem; }
  .ab-seg {
    display: grid;
    place-items: center;
    min-width: 2.9rem;
    padding: 0.32rem 0.45rem;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 5px;
    color: rgba(255, 255, 255, 0.6);
    background: rgba(255, 255, 255, 0.05);
    font: 400 1.05rem/1 var(--mono);
    letter-spacing: 0.05em;
  }
  .ab-seg.seg-done { border-color: #55ee9b; color: #78f2ad; background: color-mix(in srgb, #55ee9b 14%, transparent); box-shadow: 0 0 8px color-mix(in srgb, #55ee9b 25%, transparent); }
  .ab-seg.seg-active { border-color: #f6c84c; color: #191300; background: color-mix(in srgb, #f6c84c 88%, transparent); font-weight: 700; box-shadow: 0 0 12px color-mix(in srgb, #f6c84c 55%, transparent); animation: mq-led-pulse 1.3s ease-in-out infinite; }
  .ab-count { color: rgba(255, 255, 255, 0.72); font: 700 0.78rem/1 var(--mono); letter-spacing: 0.14em; font-variant-numeric: tabular-nums; }
  .ab-name { font: 800 1.25rem/1.1 var(--display); color: #f6c84c; text-shadow: 0 0 16px color-mix(in srgb, #f6c84c 45%, transparent); flex-shrink: 0; }

  @media (prefers-reduced-motion: reduce) {
    .nm-seg.seg-active, .ab-seg.seg-active { animation: none; }
  }

  :global(html[data-theme='arcade']) .mq-tense-name { font-size: 0.95rem; line-height: 1.5; }
  :global(html[data-theme='arcade']) .rd-prompt > div:first-child > strong { font-size: clamp(1.05rem, 3.4vw, 1.5rem); line-height: 1.3; }
  :global(html[data-theme='arcade']) .nm-marquee strong,
  :global(html[data-theme='arcade']) .ab-name { font-family: var(--marquee); font-size: 0.95rem; line-height: 1.5; }

  @media (max-width: 640px) {
    .cur-strip, .rd-strip { grid-template-columns: 1fr; }
    .cur-prompt, .rd-prompt { grid-template-columns: 1fr; }
    .cur-prompt > div, .rd-prompt > div { justify-items: start !important; text-align: left !important; }
    .cur-row { grid-template-columns: auto 1fr; }
    .cur-input-shell { grid-column: 1 / -1; }
    .rd-row { grid-template-columns: 1fr; }
    .mq-top { flex-direction: column; align-items: flex-start; gap: 0.5rem; }
    .mq-row { grid-template-columns: 1fr; }
    .mq-utility { flex-wrap: wrap; }
    .nm-top, .ab-top { flex-direction: column; align-items: stretch; }
    .nm-marquee { justify-items: start; text-align: left; }
    .nm-strip-many .nm-seg { flex-basis: 42%; }
  }
</style>
