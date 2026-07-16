<script lang="ts">
  export let variant: 'vector' | 'bio' = 'vector';

  const rows = [
    { pronoun: 'yo', form: 'hablo' },
    { pronoun: 'tú', form: 'hablas' },
    { pronoun: 'él / ella', form: 'habla' },
    { pronoun: 'nosotros', form: 'hablamos' },
    { pronoun: 'vosotros', form: 'habláis' },
    { pronoun: 'ellos', form: 'hablan' },
  ];

  let answers = ['hablo', 'hablas', 'hablaa', '', '', ''];
  let active = 2;
  let review = false;

  function moveNext(index: number): void {
    active = Math.min(rows.length - 1, index + 1);
  }
</script>

<div class={`table-demo ${variant}`}>
  <div class="table-toolbar">
    <span>LIVE TABLE STATE</span>
    <div role="group" aria-label={`${variant} verb table state`}>
      <button type="button" class:active={!review} aria-pressed={!review} on:click={() => (review = false)}>Answering</button>
      <button type="button" class:active={review} aria-pressed={review} on:click={() => (review = true)}>Review</button>
    </div>
  </div>

  <article class="table-card">
    <header class="progress-head">
      <span><i>VERB PROGRESS</i><b>02 / 10</b></span>
      <span class="progress-track" aria-hidden="true"><i></i></span>
    </header>

    <div class="tense-block">
      <div><span>TENSE 1 / 3</span><strong>Present</strong></div>
      <div class="tense-strip" aria-label="Selected tenses">
        <span class="done">Present</span><span>Preterite</span><span>Imperfect</span>
      </div>
    </div>

    <div class="verb-hero">
      <span>{review ? 'TENSE FEEDBACK' : 'CURRENT VERB'}</span>
      <strong>hablar</strong>
      <i>{review ? '5 / 6 RIGHT' : `${rows[active].pronoun} + hablar`}</i>
    </div>

    <div class:review class="conj-table" role="table" aria-label="Present tense of hablar">
      <div class="table-head" role="row">
        <span role="columnheader">Slot</span><span role="columnheader">Pronoun</span><span role="columnheader">Your answer</span>
      </div>
      <div class="row-list">
        {#each rows as row, index}
          <div
            class="table-row"
            class:current={!review && active === index}
            class:correct={review && index !== 2}
            class:wrong={review && index === 2}
            style={`--row-index:${index}`}
            role="row"
          >
            <span class="row-marker" role="cell">{review ? index === 2 ? '×' : '✓' : active === index ? '▶' : index < active ? '✓' : '·'}</span>
            <span class="pronoun" role="cell"><small>{String(index + 1).padStart(2, '0')}</small><b>{row.pronoun}</b></span>
            <span class="answer-cell" role="cell">
              {#if review}
                {#if index === 2}
                  <span class="wrong-answer"><del>{answers[index]}</del><b>{row.form}</b><small>CORRECT</small></span>
                {:else}
                  <span class="right-answer"><b>{answers[index] || row.form}</b><small>RIGHT</small></span>
                {/if}
              {:else}
                <input
                  bind:value={answers[index]}
                  aria-label={`${row.pronoun}, present tense of hablar`}
                  autocomplete="off"
                  autocapitalize="off"
                  spellcheck="false"
                  tabindex={active === index ? 0 : -1}
                  on:focus={() => (active = index)}
                  on:keydown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault();
                      moveNext(index);
                    }
                  }}
                />
              {/if}
            </span>
          </div>
        {/each}
      </div>
    </div>

    <footer class="table-footer"><span><kbd>Enter</kbd> Next cell</span><i></i><span><kbd>Backspace</kbd> Back</span><i></i><span><kbd>Esc ×2</kbd> Finish</span></footer>
  </article>
</div>

<style>
  .table-demo { display: grid; gap: .6rem; }
  .table-toolbar { display: flex; min-height: 44px; justify-content: space-between; gap: 1rem; align-items: center; font: 400 1rem/1 "VT323", monospace; }
  .table-toolbar > div { display: flex; gap: .45rem; }
  .table-toolbar button { min-height: 44px; padding: .55rem .8rem; border: 1px solid var(--m-ink, #13281e); color: var(--m-ink, #13281e); background: var(--m-panel, #f0f4ce); font: 650 .7rem/1 "Figtree", sans-serif; cursor: pointer; touch-action: manipulation; }
  .table-toolbar button.active { color: var(--m-panel, #f0f4ce); background: var(--m-core, #236249); box-shadow: inset 0 -3px 0 var(--m-spark, #ff4c91); }
  .table-toolbar button:focus-visible { outline: 3px solid var(--m-spark, #ff4c91); outline-offset: 2px; }

  .table-card { overflow: hidden; border: 2px solid var(--m-ink, #13281e); color: var(--m-ink, #13281e); background: var(--m-panel, #f0f4ce); }
  .progress-head { display: grid; gap: .6rem; padding: .85rem 1rem; border-bottom: 1px solid var(--m-ink, #13281e); background: var(--m-field, #dce8a6); }
  .progress-head > span:first-child { display: flex; justify-content: space-between; gap: 1rem; align-items: center; }
  .progress-head i { font: 600 .62rem/1 "Chakra Petch", sans-serif; font-style: normal; letter-spacing: .1em; }
  .progress-head b { font: 400 1rem/1 "VT323", monospace; }
  .progress-track { height: 5px; overflow: hidden; background: color-mix(in srgb, var(--m-core, #236249) 18%, transparent); }
  .progress-track i { display: block; width: 20%; height: 100%; background: var(--m-core, #236249); }

  .tense-block { padding: .85rem 1rem; border-bottom: 1px solid var(--m-ink, #13281e); }
  .tense-block > div:first-child { display: flex; justify-content: space-between; gap: 1rem; align-items: baseline; }
  .tense-block > div:first-child span { font: 400 1rem/1 "VT323", monospace; }
  .tense-block > div:first-child strong { font: 700 1.45rem/1 "Chakra Petch", sans-serif; }
  .tense-strip { display: grid; grid-template-columns: repeat(3, 1fr); margin-top: .65rem; }
  .tense-strip span { min-width: 0; padding: .5rem; border: 1px solid color-mix(in srgb, var(--m-ink, #13281e) 28%, transparent); font: 600 .65rem/1 "Figtree", sans-serif; text-align: center; }
  .tense-strip .done { color: var(--m-panel, #f0f4ce); background: var(--m-core, #236249); box-shadow: inset 0 -3px 0 var(--m-spark, #ff4c91); }

  .verb-hero { position: relative; display: grid; justify-items: center; padding: 1.3rem 1rem 1rem; border-bottom: 1px solid var(--m-ink, #13281e); }
  .verb-hero span { font: 400 1rem/1 "VT323", monospace; }
  .verb-hero strong { font: 700 clamp(2.5rem, 6vw, 4.2rem)/.9 "Chakra Petch", sans-serif; letter-spacing: -.06em; }
  .verb-hero i { color: var(--m-core, #236249); font: 650 .72rem/1 "Figtree", sans-serif; font-style: normal; }

  .conj-table { padding: .7rem; }
  .table-head { display: grid; grid-template-columns: 2.2rem 8rem minmax(0, 1fr); gap: .6rem; padding: .35rem .55rem; color: color-mix(in srgb, var(--m-ink, #13281e) 62%, transparent); font: 400 .9rem/1 "VT323", monospace; }
  .row-list { display: grid; gap: .35rem; }
  .table-row { display: grid; min-height: 54px; grid-template-columns: 2.2rem 8rem minmax(0, 1fr); gap: .6rem; align-items: center; padding: .45rem .55rem; border: 1px solid color-mix(in srgb, var(--m-ink, #13281e) 20%, transparent); background: color-mix(in srgb, var(--m-field, #dce8a6) 25%, transparent); }
  .table-row.current { border-color: var(--m-core, #236249); background: color-mix(in srgb, var(--m-field, #dce8a6) 72%, transparent); box-shadow: inset 4px 0 0 var(--m-spark, #ff4c91); }
  .row-marker { display: grid; width: 25px; height: 25px; place-items: center; color: var(--m-core, #236249); font: 700 .7rem/1 "Chakra Petch", sans-serif; }
  .pronoun { display: grid; grid-template-columns: 1.5rem 1fr; gap: .35rem; align-items: center; }
  .pronoun small { font: 400 1rem/1 "VT323", monospace; }
  .pronoun b { font: 700 .84rem/1 "Chakra Petch", sans-serif; }
  .answer-cell { min-width: 0; }
  input { width: 100%; min-height: 42px; box-sizing: border-box; padding: .55rem .7rem; border: 1px solid color-mix(in srgb, var(--m-core, #236249) 42%, transparent); border-radius: 0; outline: 0; color: var(--m-ink, #13281e); background: var(--m-panel, #f0f4ce); font: 600 1rem/1 "Figtree", sans-serif; }
  input:focus { border-color: var(--m-core, #236249); box-shadow: 0 0 0 3px color-mix(in srgb, var(--m-spark, #ff4c91) 28%, transparent); }
  .right-answer, .wrong-answer { display: grid; min-height: 42px; grid-template-columns: minmax(0, 1fr) auto; gap: .45rem; align-items: center; padding: .5rem .7rem; }
  .right-answer { color: var(--m-core, #236249); background: color-mix(in srgb, var(--m-core, #236249) 10%, transparent); }
  .wrong-answer { grid-template-columns: auto minmax(0, 1fr) auto; color: color-mix(in srgb, var(--m-spark, #ff4c91) 65%, var(--m-ink, #13281e)); background: color-mix(in srgb, var(--m-spark, #ff4c91) 15%, transparent); }
  .right-answer b, .wrong-answer b { font: 700 .9rem/1 "Figtree", sans-serif; }
  .wrong-answer del { opacity: .62; font-size: .75rem; }
  .right-answer small, .wrong-answer small { font: 400 .85rem/1 "VT323", monospace; }
  .table-row.correct { border-color: color-mix(in srgb, var(--m-core, #236249) 45%, transparent); }
  .table-row.wrong { border-color: var(--m-spark, #ff4c91); }
  .review .table-row { animation: verdict-in 240ms cubic-bezier(.2,.8,.2,1) both; animation-delay: calc(var(--row-index) * 45ms); }
  @keyframes verdict-in { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }

  .table-footer { display: flex; justify-content: center; gap: .7rem; align-items: center; padding: .8rem; border-top: 1px solid var(--m-ink, #13281e); font: 600 .62rem/1 "Figtree", sans-serif; }
  .table-footer i { width: 3px; height: 3px; border-radius: 50%; background: var(--m-spark, #ff4c91); }
  kbd { padding: .2rem .35rem; border: 1px solid currentColor; font: 400 .9rem/1 "VT323", monospace; }

  .vector .table-card { clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 18px 100%, 0 calc(100% - 18px)); }
  .vector .row-marker { border: 1px solid var(--m-core, #236249); clip-path: polygon(0 0, 78% 0, 100% 22%, 100% 100%, 22% 100%, 0 78%); }
  .bio .table-card { border-radius: 28px; }
  .bio .progress-track, .bio .progress-track i { border-radius: 999px; }
  .bio .tense-strip { gap: .35rem; }
  .bio .tense-strip span, .bio .table-row, .bio input, .bio .right-answer, .bio .wrong-answer { border-radius: 14px; }
  .bio .row-marker { border: 1px solid var(--m-core, #236249); border-radius: 50%; }
  .bio .table-row.current { box-shadow: inset 0 0 0 3px color-mix(in srgb, var(--m-spark, #ff4c91) 34%, transparent); }

  @media (max-width: 520px) {
    .table-toolbar { align-items: stretch; flex-direction: column; }
    .table-toolbar > div { display: grid; grid-template-columns: 1fr 1fr; }
    .table-head { display: none; }
    .table-row { grid-template-columns: 2rem 6.5rem minmax(0, 1fr); gap: .35rem; padding-inline: .4rem; }
    .pronoun { grid-template-columns: 1fr; }
    .pronoun small { display: none; }
    .wrong-answer { grid-template-columns: 1fr auto; }
    .wrong-answer del { grid-column: 1 / -1; }
    .table-footer { justify-content: flex-start; overflow-x: auto; }
    .table-footer span { flex: 0 0 auto; }
  }

  @media (prefers-reduced-motion: reduce) {
    .review .table-row { animation-duration: 1ms; animation-delay: 0ms; }
  }
</style>
