<script lang="ts">
  export let variant: 'header' | 'block' | 'rail';
  let expanded = true;
  const preview = [
    ['azotea', 'rooftop'], ['anochecer', 'nightfall'],
    ['aunque', 'although'], ['lograr', 'to achieve'],
  ];
</script>

<article class="entry-option" class:option-block={variant === 'block'} class:option-rail={variant === 'rail'}>
  <div class="fake-screen">
    <header class="fake-head">
      <div><span>WORD RUSH</span><strong>Spanish → English</strong></div>
      {#if variant === 'header'}
        <button class="header-trigger" type="button" aria-expanded={expanded} on:click={() => (expanded = !expanded)}><i aria-hidden="true">▤</i> Study 12 <b>{expanded ? '−' : '+'}</b></button>
      {/if}
    </header>

    <div class="fake-controls"><span>5 words</span><span class="selected">10 words</span><span>20 words</span></div>

    {#if variant === 'block'}
      <button class="block-trigger" type="button" aria-expanded={expanded} on:click={() => (expanded = !expanded)}>
        <span class="block-icon" aria-hidden="true">◫</span>
        <span><strong>Study before you play</strong><small>6 newest + 6 that need more practice</small></span>
        <b>{expanded ? 'Close' : 'Open'} <i aria-hidden="true">{expanded ? '↑' : '↓'}</i></b>
      </button>
    {/if}

    {#if variant === 'rail'}
      <button class="rail-trigger" type="button" aria-expanded={expanded} on:click={() => (expanded = !expanded)}>
        <span><b>12</b><small>study cards</small></span>
        <i aria-hidden="true">{expanded ? '−' : '+'}</i>
      </button>
    {/if}

    {#if expanded}
      <section class="expanded-study">
        <div class="expanded-title"><div><span>STUDY LIST</span><strong>Know what just entered your pool.</strong></div><small>2-column preview</small></div>
        <div class="mini-table">
          <div class="mini-head"><span>Word</span><span>Translation</span></div>
          {#each preview as row, index}
            {#if index === 0}<div class="mini-group">Newest 6</div>{/if}
            {#if index === 2}<div class="mini-group focus">Needs more practice</div>{/if}
            <div class="mini-row"><strong>{row[0]}</strong><span>{row[1]}</span></div>
          {/each}
        </div>
        <p>Full expansion contains 12 unique rows; this placement mock shows four.</p>
      </section>
    {/if}

    <button class="fake-play" type="button">Start word run →</button>
  </div>
</article>

<style>
  .entry-option { --violet: #7065e8; --coral: #e56f52; padding: 1rem; border: 1px solid var(--line); border-radius: 18px; background: color-mix(in srgb, var(--surface-strong) 78%, transparent); }
  .fake-screen { position: relative; display: grid; gap: 0.8rem; min-height: 22rem; padding: 1rem; overflow: hidden; border: 1px solid color-mix(in srgb, var(--line) 84%, #7065e8); border-radius: 14px; background: linear-gradient(150deg, color-mix(in srgb, var(--surface) 94%, #7065e8 6%), var(--surface)); }
  .fake-head { display: flex; align-items: center; justify-content: space-between; gap: 0.7rem; }
  .fake-head > div { display: grid; gap: 0.18rem; }
  .fake-head span { color: var(--muted); font: 700 0.58rem/1 var(--mono); letter-spacing: 0.13em; }
  .fake-head strong { color: var(--text); font-size: 0.92rem; }
  button { font-family: var(--body); }
  .header-trigger { display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.48rem 0.62rem; border: 1px solid color-mix(in srgb, var(--violet) 42%, var(--line)); border-radius: 9px; color: var(--violet); background: color-mix(in srgb, var(--violet) 10%, var(--surface)); font-size: 0.72rem; font-weight: 750; }
  .header-trigger i { font-style: normal; } .header-trigger b { font-size: 0.9rem; }
  .fake-controls { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.35rem; }
  .fake-controls span { padding: 0.48rem; border: 1px solid var(--line); border-radius: 8px; color: var(--muted); text-align: center; font-size: 0.68rem; }
  .fake-controls .selected { border-color: color-mix(in srgb, var(--violet) 40%, var(--line)); color: var(--violet); background: color-mix(in srgb, var(--violet) 8%, transparent); }
  .block-trigger { display: grid; grid-template-columns: auto 1fr auto; gap: 0.65rem; align-items: center; width: 100%; padding: 0.68rem; border: 1px solid color-mix(in srgb, var(--violet) 36%, var(--line)); border-radius: 12px; color: var(--text); text-align: left; background: linear-gradient(90deg, color-mix(in srgb, var(--violet) 11%, var(--surface)), color-mix(in srgb, var(--coral) 6%, var(--surface))); }
  .block-icon { display: grid; width: 2rem; height: 2rem; place-items: center; border-radius: 8px; color: var(--violet); background: color-mix(in srgb, var(--violet) 12%, transparent); }
  .block-trigger > span:nth-child(2) { display: grid; gap: 0.15rem; }
  .block-trigger small { color: var(--muted); }
  .block-trigger > b { color: var(--violet); font-size: 0.68rem; } .block-trigger > b i { font-style: normal; }
  .rail-trigger { position: absolute; top: 5rem; right: 0; z-index: 2; display: flex; align-items: center; gap: 0.45rem; padding: 0.5rem 0.45rem 0.5rem 0.62rem; border: 1px solid color-mix(in srgb, var(--coral) 46%, var(--line)); border-right: 0; border-radius: 10px 0 0 10px; color: var(--coral); background: color-mix(in srgb, var(--surface-strong) 94%, var(--coral) 6%); box-shadow: -8px 8px 22px color-mix(in srgb, #171525 12%, transparent); }
  .rail-trigger > span { display: grid; } .rail-trigger b { font: 800 0.82rem/1 var(--mono); } .rail-trigger small { font-size: 0.54rem; } .rail-trigger i { font-size: 1rem; font-style: normal; }
  .option-rail .expanded-study { margin-right: 3.1rem; }
  .expanded-study { display: grid; gap: 0.55rem; padding: 0.7rem; border: 1px solid var(--line); border-radius: 12px; background: color-mix(in srgb, var(--surface-strong) 84%, transparent); }
  .expanded-title { display: flex; justify-content: space-between; gap: 0.5rem; }
  .expanded-title > div { display: grid; gap: 0.18rem; }
  .expanded-title span { color: var(--violet); font: 750 0.55rem/1 var(--mono); letter-spacing: 0.12em; }
  .expanded-title strong { color: var(--text); font-size: 0.78rem; }
  .expanded-title small { color: var(--muted); font-size: 0.62rem; }
  .mini-table { overflow: hidden; border: 1px solid var(--line); border-radius: 9px; }
  .mini-head, .mini-row { display: grid; grid-template-columns: 1fr 1fr; }
  .mini-head { color: var(--violet); background: color-mix(in srgb, var(--violet) 8%, transparent); font: 750 0.56rem/1 var(--mono); letter-spacing: 0.09em; text-transform: uppercase; }
  .mini-head span, .mini-row > * { padding: 0.38rem 0.45rem; }
  .mini-head span + span, .mini-row > * + * { border-left: 1px solid var(--line); }
  .mini-row { border-top: 1px solid var(--line); font-size: 0.67rem; }
  .mini-row strong { color: var(--text); } .mini-row span { color: var(--muted); }
  .mini-group { padding: 0.3rem 0.45rem; border-top: 1px solid var(--line); color: var(--violet); background: color-mix(in srgb, var(--violet) 7%, transparent); font-size: 0.58rem; font-weight: 750; }
  .mini-group.focus { color: var(--coral); background: color-mix(in srgb, var(--coral) 7%, transparent); }
  .expanded-study p { margin: 0; color: var(--muted); font-size: 0.62rem; }
  .fake-play { justify-self: end; margin-top: auto; padding: 0.58rem 0.72rem; border: 0; border-radius: 9px; color: white; background: var(--violet); font-size: 0.72rem; font-weight: 750; }
  @media (max-width: 520px) { .fake-head { align-items: flex-start; } .block-trigger { grid-template-columns: auto 1fr; } .block-trigger > b { grid-column: 2; } }
</style>
