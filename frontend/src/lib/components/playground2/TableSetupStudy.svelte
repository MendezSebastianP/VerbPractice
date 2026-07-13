<script lang="ts">
  // Study 01 — Verb tables setup menu. 'current' replicates the production
  // ConjugationPage setup card with its real font sizes (measurement flags
  // mark the offenders). 'readable' keeps the architecture and rebuilds the
  // type scale; 'console' restructures setup into a route + loadout deck.
  export let variant: 'current' | 'readable' | 'console';
  export let index = 'S1';
  export let kicker = '';
  export let title = '';
  export let description = '';

  const LANGS = [
    { code: 'FR', name: 'French', note: '942 verbs', key: 'F', on: true },
    { code: 'ES', name: 'Spanish', note: '810 verbs', key: 'S', on: false },
    { code: 'EN', name: 'English', note: '942 verbs', key: 'E', on: false },
    { code: 'RU', name: 'Russian', note: '655 verbs', key: 'R', on: false },
  ];

  const TIERS = [
    { level: 'L1', label: 'Core', note: 'Start with the essential forms', tenses: ['Présent', 'Passé composé', 'Imparfait'], on: true },
    { level: 'L2', label: 'Expand', note: 'Add everyday range', tenses: ['Futur simple', 'Plus-que-parfait'], on: false },
    { level: 'L3', label: 'Master', note: 'Open the complete corpus', tenses: ['Conditionnel présent', 'Subjonctif présent'], on: false },
  ];

  const SELECTED = new Set(['Présent', 'Passé composé', 'Imparfait']);
</script>

<article class="setup-study" data-variant={variant}>
  <header class="concept-intro" class:intro-current={variant === 'current'}>
    <span class="concept-number">{index}</span>
    <div><p>{kicker}</p><h3>{title}</h3><span>{description}</span></div>
  </header>

  {#if variant === 'current'}
    <!-- ======= CURRENT PRODUCTION SIZES (faithful replica) ======= -->
    <div class="stage stage-current">
      <div class="cur-lead">
        <div><span class="cur-eyebrow">Build a table run</span><strong>Choose the tense load, then fill every open cell.</strong></div>
        <small>Enter moves down each pronoun, then crosses to the next tense.</small>
      </div>

      <div class="cur-step">
        <div class="cur-step-head"><span>01</span><div><strong>Language</strong><small>All four corpora are measured live.</small></div></div>
        <div class="cur-lang-grid">
          {#each LANGS as lang}
            <button type="button" class:cur-lang-on={lang.on}>
              <span class="cur-lang-code">{lang.code}</span>
              <span class="cur-lang-copy"><strong>{lang.name}</strong><small>{lang.note}</small></span>
              <kbd>{lang.key}</kbd>
            </button>
          {/each}
        </div>
      </div>

      <div class="cur-step">
        <div class="cur-step-head"><span>02</span><div><strong>Climb from core to mastery</strong><small>Each level adds a new tier of tenses.</small></div></div>
        {#each TIERS as tier}
          <div class="cur-stair" class:cur-stair-on={tier.on}>
            <button type="button" class="cur-stair-level"><strong>{tier.level}</strong><kbd>Alt+{tier.level.slice(1)}</kbd></button>
            <div class="cur-stair-copy"><strong>{tier.label}</strong><small>{tier.note}</small></div>
            <div class="cur-tense-row">
              {#each tier.tenses as tense, i}
                <button type="button" class:cur-tense-on={SELECTED.has(tense)}><span>{tense}</span><kbd>Ctrl+Shift+{i + 1}</kbd></button>
              {/each}
            </div>
          </div>
        {/each}
        <i class="px-flag" aria-hidden="true">tense chips 11.5px · keycaps 6.4px</i>
      </div>

      <div class="cur-launch">
        <div><span>French</span><strong>3 tenses × 5 verbs</strong></div>
        <button type="button" class="cur-launch-btn">Start table run <kbd>Enter</kbd> →</button>
      </div>

      <div class="cur-footer">
        <span><kbd>E/S/F/R</kbd> language</span>
        <span><kbd>Alt+1…4</kbd> tense route</span>
        <span><kbd>Ctrl+Shift+1…0</kbd> individual tenses</span>
        <span><kbd>1/2/3</kbd> run size</span>
        <span><kbd>Shift+1…3</kbd> support</span>
        <span><kbd>Enter</kbd> start</span>
        <i class="px-flag" aria-hidden="true">footer 9.6px</i>
      </div>
    </div>
  {:else if variant === 'readable'}
    <!-- ======= OPTION A — same bones, readable skin ======= -->
    <div class="stage stage-readable">
      <div class="rd-lead">
        <div><span class="rd-eyebrow">Build a table run</span><strong>Choose the tense load, then fill every open cell.</strong></div>
      </div>

      <div class="rd-step">
        <div class="rd-step-head"><span>01</span><strong>Language</strong></div>
        <div class="rd-lang-grid">
          {#each LANGS as lang}
            <button type="button" class:rd-lang-on={lang.on}>
              <span class="rd-lang-code">{lang.code}</span>
              <span class="rd-lang-copy"><strong>{lang.name}</strong><small>{lang.note}</small></span>
              <kbd class="rd-cap">{lang.key}</kbd>
            </button>
          {/each}
        </div>
      </div>

      <div class="rd-step">
        <div class="rd-step-head"><span>02</span><strong>Climb from core to mastery</strong></div>
        {#each TIERS as tier}
          <div class="rd-stair" class:rd-stair-on={tier.on}>
            <button type="button" class="rd-stair-level"><strong>{tier.level}</strong><kbd class="rd-cap">Alt+{tier.level.slice(1)}</kbd></button>
            <div class="rd-stair-copy"><strong>{tier.label}</strong><small>{tier.note}</small></div>
            <div class="rd-tense-row">
              {#each tier.tenses as tense}
                <button type="button" class:rd-tense-on={SELECTED.has(tense)}>
                  {#if SELECTED.has(tense)}<i aria-hidden="true">✓</i>{/if}<span>{tense}</span>
                </button>
              {/each}
            </div>
          </div>
        {/each}
      </div>

      <div class="rd-launch">
        <div><span>French</span><strong>3 tenses × 5 verbs</strong></div>
        <button type="button" class="rd-launch-btn">Start table run <kbd class="rd-cap rd-cap-launch">Enter</kbd></button>
      </div>

      <div class="rd-footer">
        <span><kbd class="rd-cap">E S F R</kbd> language</span>
        <span><kbd class="rd-cap">Alt+1…4</kbd> route</span>
        <span><kbd class="rd-cap">1/2/3</kbd> size</span>
        <button type="button" class="rd-more">All shortcuts…</button>
      </div>
    </div>
    <ul class="study-notes">
      <li>Tense chips 0.95rem (15.2px) with a 2.75rem min-height — real touch targets instead of 11.5px text.</li>
      <li>Keycaps grow to 0.68rem, gain contrast, and disappear entirely on touch screens — they are desktop hints.</li>
      <li>Footer keeps the three shortcuts you actually reach for; the rest folds behind “All shortcuts…”.</li>
    </ul>
  {:else}
    <!-- ======= OPTION B — console deck restructure ======= -->
    <div class="stage stage-console">
      <div class="cs-lang-row">
        {#each LANGS as lang}
          <button type="button" class:cs-lang-on={lang.on}>
            <strong>{lang.code}</strong><span>{lang.name}</span>
          </button>
        {/each}
      </div>

      <div class="cs-deck">
        <div class="cs-panel">
          <span class="cs-panel-label">Route</span>
          {#each TIERS as tier}
            <button type="button" class="cs-route" class:cs-route-on={tier.on}>
              <i aria-hidden="true">{tier.on ? '◉' : '○'}</i>
              <span><strong>{tier.level} · {tier.label}</strong><small>{tier.on ? `${tier.tenses.length} tenses` : `+${tier.tenses.length} tenses`}</small></span>
            </button>
          {/each}
          <button type="button" class="cs-route cs-route-custom"><i aria-hidden="true">✦</i><span><strong>Custom route</strong><small>Pick tenses one by one</small></span></button>
        </div>

        <div class="cs-panel">
          <span class="cs-panel-label">Loadout</span>
          <div class="cs-loadout-chips">
            {#each [...SELECTED] as tense}
              <span class="cs-chip">{tense}<button type="button" aria-label={`Remove ${tense}`}>×</button></span>
            {/each}
          </div>
          <div class="cs-dials">
            <div class="cs-dial">
              <span>Verbs</span>
              <div class="cs-seg">
                <button type="button">3</button>
                <button type="button" class="cs-seg-on">5</button>
                <button type="button">8</button>
              </div>
            </div>
            <div class="cs-dial">
              <span>Support</span>
              <div class="cs-seg">
                <button type="button">Guided</button>
                <button type="button">Hints</button>
                <button type="button" class="cs-seg-on">Blank</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="cs-launch">
        <div class="cs-launch-sum"><span>FR · 3 tenses · 5 verbs · blank</span><strong>Ready to run</strong></div>
        <button type="button" class="cs-launch-btn"><span>▶ START</span><kbd>Enter</kbd></button>
      </div>
    </div>
    <ul class="study-notes">
      <li>Levels become three big radio rows; the tense list lives once, in the loadout, instead of inside every stair.</li>
      <li>Run size and support are chunky segmented dials — one glance, one tap, nothing under 0.8rem.</li>
      <li>The launch bar reads like an arcade cabinet coin slot: summary left, one oversized START right.</li>
    </ul>
  {/if}
</article>

<style>
  .setup-study { width: min(100%, 760px); margin-inline: auto; }
  .concept-intro { display: grid; grid-template-columns: auto 1fr; gap: 0.85rem; align-items: start; margin-bottom: 0.8rem; padding-inline: 0.25rem; }
  .concept-number { display: grid; width: 2.45rem; height: 2.45rem; place-items: center; border: 1px solid var(--line-strong); border-radius: 13px; color: var(--accent-strong); background: var(--accent-soft); font: 800 0.7rem/1 var(--mono); }
  .intro-current .concept-number { color: var(--muted); background: transparent; border-style: dashed; }
  .concept-intro p { margin: 0 0 0.12rem; color: var(--accent-strong); font: 750 0.62rem/1 var(--mono); letter-spacing: 0.12em; text-transform: uppercase; }
  .intro-current p { color: var(--muted); }
  .concept-intro h3 { margin: 0 0 0.25rem; color: var(--text); font: 800 clamp(1.08rem, 3vw, 1.4rem)/1.15 var(--display); letter-spacing: -0.035em; }
  .concept-intro div > span { color: var(--muted); font-size: 0.82rem; line-height: 1.45; }

  .stage {
    position: relative;
    display: grid;
    gap: 1rem;
    padding: clamp(0.9rem, 3vw, 1.35rem);
    border: 1px solid var(--line-strong);
    border-radius: 20px;
    background: color-mix(in srgb, var(--surface-strong) 92%, transparent);
    box-shadow: var(--shadow);
  }

  .stage-current { border-style: dashed; }

  button { cursor: pointer; color: inherit; font-family: inherit; background: transparent; }

  .px-flag {
    justify-self: end;
    width: fit-content;
    padding: 0.22rem 0.5rem;
    border: 1px solid color-mix(in srgb, var(--danger) 55%, transparent);
    border-radius: 999px;
    color: var(--danger);
    background: color-mix(in srgb, var(--danger) 10%, transparent);
    font: 700 0.68rem/1.3 var(--ui);
    font-style: normal;
  }

  .study-notes { display: grid; gap: 0.3rem; margin: 0.7rem 0 0; padding-left: 1.1rem; }
  .study-notes li { color: var(--muted); font-size: 0.82rem; line-height: 1.5; }
  .study-notes li::marker { color: var(--accent-strong); }

  /* ===== CURRENT — production values kept on purpose ===== */
  .cur-lead { display: flex; align-items: flex-start; justify-content: space-between; gap: 1.25rem; }
  .cur-lead > div { display: grid; gap: 0.25rem; }
  .cur-eyebrow { color: var(--muted); font: 500 0.75rem/1.4 var(--mono); letter-spacing: 0.18em; text-transform: uppercase; }
  .cur-lead strong { font: 700 clamp(1.1rem, 2.6vw, 1.5rem)/1.2 var(--display); letter-spacing: -0.035em; color: var(--text); }
  .cur-lead small { max-width: 16rem; color: var(--muted); font-size: 0.86rem; text-align: right; }

  .cur-step { display: grid; gap: 0.7rem; padding-top: 0.9rem; border-top: 1px solid var(--line); }
  .cur-step-head { display: flex; align-items: center; gap: 0.75rem; }
  .cur-step-head > span { display: grid; place-items: center; width: 2rem; height: 2rem; border: 1px solid color-mix(in srgb, var(--accent) 38%, var(--line)); border-radius: 10px; color: var(--accent-strong); font: 700 0.68rem/1 var(--mono); }
  .cur-step-head strong { font-size: 1rem; color: var(--text); }
  .cur-step-head small { display: block; color: var(--muted); font-size: 0.72rem; }

  .cur-lang-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.55rem; }
  .cur-lang-grid button { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 0.55rem; min-width: 0; padding: 0.8rem 0.6rem; border: 1px solid var(--line); border-radius: 16px; text-align: left; color: var(--text); }
  .cur-lang-on { border-color: color-mix(in srgb, var(--accent) 55%, var(--line)) !important; background: color-mix(in srgb, var(--accent-soft) 155%, transparent); }
  .cur-lang-code { display: grid; place-items: center; width: 2.2rem; height: 2.2rem; border-radius: 12px; color: var(--accent-strong); background: var(--accent-soft); font: 800 0.72rem/1 var(--mono); }
  .cur-lang-copy { display: grid; min-width: 0; }
  .cur-lang-copy strong { font-size: 0.95rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .cur-lang-copy small { color: var(--muted); font-size: 0.72rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  /* the production 0.4–0.48rem keycaps, kept tiny on purpose */
  .cur-lang-grid kbd, .cur-stair kbd, .cur-footer kbd, .cur-launch-btn kbd {
    padding: 0.2rem 0.32rem;
    border: 1px solid var(--line-strong);
    border-radius: 6px;
    color: var(--muted);
    font: 750 0.48rem/1 var(--mono);
    white-space: nowrap;
  }
  .cur-tense-row kbd { font-size: 0.4rem; padding: 0.15rem 0.24rem; }

  .cur-stair { display: grid; grid-template-columns: auto minmax(6.5rem, 0.75fr) minmax(0, 2fr); gap: 0.75rem; align-items: center; padding: 0.62rem; border: 1px solid var(--line); border-radius: 15px; }
  .cur-stair-on { border-color: color-mix(in srgb, var(--accent) 62%, var(--line)); background: color-mix(in srgb, var(--accent-soft) 64%, transparent); }
  .cur-stair-level { display: grid; gap: 0.22rem; place-items: center; width: 2.45rem; min-height: 2.65rem; padding: 0.3rem; border: 1px solid var(--line-strong); border-radius: 11px; color: var(--muted); }
  .cur-stair-on .cur-stair-level { border-color: var(--accent); color: var(--accent-strong); }
  .cur-stair-level strong { font: 800 0.66rem/1 var(--mono); }
  .cur-stair-copy { display: grid; gap: 0.15rem; min-width: 0; }
  .cur-stair-copy strong { font-size: 0.94rem; color: var(--text); }
  .cur-stair-copy small { color: var(--muted); font-size: 0.68rem; }
  .cur-tense-row { display: flex; flex-wrap: wrap; gap: 0.4rem; }
  .cur-tense-row button { display: inline-flex; gap: 0.35rem; align-items: center; padding: 0.46rem 0.58rem; border: 1px solid var(--line); border-radius: 8px; color: var(--muted); font-size: 0.72rem; }
  .cur-tense-on { border-color: color-mix(in srgb, var(--accent) 68%, var(--line)) !important; color: var(--text) !important; background: var(--accent-soft); }

  .cur-launch { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 1rem; border: 1px solid color-mix(in srgb, var(--accent) 30%, var(--line)); border-radius: 18px; background: linear-gradient(120deg, color-mix(in srgb, var(--accent-soft) 135%, transparent), transparent); }
  .cur-launch span { display: block; color: var(--accent-strong); font: 700 0.67rem/1.4 var(--mono); letter-spacing: 0.12em; text-transform: uppercase; }
  .cur-launch strong { color: var(--text); }
  .cur-launch-btn { display: inline-flex; align-items: center; gap: 0.65rem; padding: 0.75rem 1.25rem; border: 1px solid color-mix(in srgb, var(--accent) 45%, transparent); border-radius: 12px; color: var(--accent-strong); background: var(--accent-soft); font-family: var(--display); font-weight: 600; }

  .cur-footer { display: flex; flex-wrap: wrap; gap: 0.55rem 0.9rem; justify-content: center; color: var(--muted); font: 650 0.6rem/1.4 var(--mono); }
  .cur-footer span { display: inline-flex; gap: 0.35rem; align-items: center; }

  /* ===== OPTION A — readable pass ===== */
  .rd-lead strong { font: 700 clamp(1.15rem, 2.6vw, 1.5rem)/1.25 var(--display); letter-spacing: -0.03em; color: var(--text); }
  .rd-eyebrow { display: block; margin-bottom: 0.25rem; color: var(--accent-strong); font: 600 0.78rem/1.4 var(--mono); letter-spacing: 0.14em; text-transform: uppercase; }

  .rd-step { display: grid; gap: 0.75rem; padding-top: 1rem; border-top: 1px solid var(--line); }
  .rd-step-head { display: flex; align-items: center; gap: 0.7rem; }
  .rd-step-head > span { display: grid; place-items: center; width: 2.1rem; height: 2.1rem; border: 1px solid color-mix(in srgb, var(--accent) 38%, var(--line)); border-radius: 10px; color: var(--accent-strong); font: 700 0.78rem/1 var(--mono); }
  .rd-step-head strong { font-size: 1.05rem; color: var(--text); }

  .rd-cap { padding: 0.24rem 0.42rem; border: 1px solid color-mix(in srgb, var(--accent) 34%, var(--line-strong)); border-radius: 6px; color: color-mix(in srgb, var(--accent-strong) 80%, var(--text)); background: color-mix(in srgb, var(--surface-strong) 82%, transparent); font: 700 0.68rem/1 var(--mono); white-space: nowrap; }
  @media (pointer: coarse) { .rd-cap { display: none; } }

  .rd-lang-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(9.5rem, 1fr)); gap: 0.6rem; }
  .rd-lang-grid > button { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 0.65rem; min-height: 3.25rem; padding: 0.7rem 0.8rem; border: 1px solid var(--line); border-radius: 14px; text-align: left; color: var(--text); transition: border-color 180ms ease, background 180ms ease, transform 180ms ease; }
  .rd-lang-grid > button:hover { transform: translateY(-1px); border-color: color-mix(in srgb, var(--accent) 45%, var(--line)); }
  .rd-lang-on { border-color: color-mix(in srgb, var(--accent) 62%, var(--line)) !important; background: color-mix(in srgb, var(--accent-soft) 150%, transparent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 12%, transparent); }
  .rd-lang-code { display: grid; place-items: center; width: 2.4rem; height: 2.4rem; border-radius: 12px; color: var(--accent-strong); background: var(--accent-soft); font: 800 0.85rem/1 var(--mono); }
  .rd-lang-copy { display: grid; gap: 0.1rem; min-width: 0; }
  .rd-lang-copy strong { font-size: 1rem; }
  .rd-lang-copy small { color: var(--muted); font-size: 0.8rem; }

  .rd-stair { display: grid; grid-template-columns: auto minmax(6.5rem, 0.7fr) minmax(0, 2fr); gap: 0.8rem; align-items: center; padding: 0.75rem; border: 1px solid var(--line); border-radius: 15px; }
  .rd-stair-on { border-color: color-mix(in srgb, var(--accent) 62%, var(--line)); background: color-mix(in srgb, var(--accent-soft) 64%, transparent); }
  .rd-stair-level { display: grid; gap: 0.28rem; place-items: center; min-width: 3rem; min-height: 3rem; padding: 0.4rem; border: 1px solid var(--line-strong); border-radius: 11px; color: var(--muted); }
  .rd-stair-on .rd-stair-level { border-color: var(--accent); color: var(--accent-strong); box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 10%, transparent); }
  .rd-stair-level strong { font: 800 0.85rem/1 var(--mono); }
  .rd-stair-copy { display: grid; gap: 0.18rem; min-width: 0; }
  .rd-stair-copy strong { font-size: 1.02rem; color: var(--text); }
  .rd-stair-copy small { color: var(--muted); font-size: 0.82rem; line-height: 1.35; }
  .rd-tense-row { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .rd-tense-row button { display: inline-flex; gap: 0.4rem; align-items: center; min-height: 2.75rem; padding: 0.6rem 0.85rem; border: 1px solid var(--line); border-radius: 10px; color: var(--muted); font-size: 0.95rem; font-weight: 500; transition: border-color 160ms ease, background 160ms ease, color 160ms ease; }
  .rd-tense-row button:hover { border-color: color-mix(in srgb, var(--accent) 45%, var(--line)); color: var(--text); }
  .rd-tense-on { border-color: color-mix(in srgb, var(--accent) 68%, var(--line)) !important; color: var(--text) !important; background: var(--accent-soft); font-weight: 600; }
  .rd-tense-row i { color: var(--accent-strong); font-style: normal; font-weight: 800; }

  .rd-launch { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 1rem 1.1rem; border: 1px solid color-mix(in srgb, var(--accent) 34%, var(--line)); border-radius: 16px; background: linear-gradient(120deg, color-mix(in srgb, var(--accent-soft) 135%, transparent), transparent); }
  .rd-launch span { display: block; color: var(--accent-strong); font: 700 0.78rem/1.4 var(--mono); letter-spacing: 0.1em; text-transform: uppercase; }
  .rd-launch strong { color: var(--text); font-size: 1.05rem; }
  .rd-launch-btn { display: inline-flex; align-items: center; gap: 0.65rem; min-height: 3rem; padding: 0.7rem 1.4rem; border: 1px solid color-mix(in srgb, var(--accent) 55%, transparent); border-radius: 12px; color: var(--accent-strong); background: var(--accent-soft); font-family: var(--ui); font-size: 1rem; font-weight: 700; transition: transform 180ms ease, box-shadow 180ms ease; }
  .rd-launch-btn:hover { transform: translateY(-1px); box-shadow: 0 8px 22px -12px color-mix(in srgb, var(--accent) 70%, transparent); }
  .rd-cap-launch { border-color: currentColor; color: inherit; background: color-mix(in srgb, currentColor 10%, transparent); }

  .rd-footer { display: flex; flex-wrap: wrap; align-items: center; gap: 0.6rem 1.1rem; justify-content: center; color: var(--muted); font: 600 0.78rem/1.5 var(--ui); }
  .rd-footer span { display: inline-flex; gap: 0.4rem; align-items: center; }
  .rd-more { padding: 0.3rem 0.6rem; border: 0; color: var(--accent-strong); font-size: 0.78rem; font-weight: 600; text-decoration: underline; text-underline-offset: 3px; }

  /* ===== OPTION B — console deck ===== */
  .stage-console { gap: 0.85rem; }
  .cs-lang-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.55rem; }
  .cs-lang-row button { display: grid; gap: 0.15rem; justify-items: center; min-height: 3.4rem; padding: 0.6rem 0.4rem; border: 1px solid var(--line); border-radius: 14px; color: var(--muted); transition: 180ms ease; }
  .cs-lang-row button:hover { transform: translateY(-1px); border-color: color-mix(in srgb, var(--accent) 45%, var(--line)); }
  .cs-lang-on { border-color: color-mix(in srgb, var(--accent) 70%, var(--line)) !important; color: var(--text) !important; background: var(--accent-soft); box-shadow: 0 0 16px color-mix(in srgb, var(--accent) 22%, transparent); }
  .cs-lang-row strong { font: 800 1.05rem/1 var(--mono); color: inherit; }
  .cs-lang-row span { font-size: 0.8rem; }

  .cs-deck { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 0.7rem; }
  .cs-panel { display: grid; align-content: start; gap: 0.55rem; padding: 0.85rem; border: 1px solid var(--line); border-radius: 16px; background: color-mix(in srgb, var(--surface-strong) 70%, transparent); }
  .cs-panel-label { color: var(--accent-strong); font: 700 0.8rem/1 var(--mono); letter-spacing: 0.16em; text-transform: uppercase; }

  .cs-route { display: grid; grid-template-columns: auto 1fr; gap: 0.6rem; align-items: center; min-height: 3.1rem; padding: 0.55rem 0.7rem; border: 1px solid var(--line); border-radius: 12px; text-align: left; color: var(--muted); transition: 160ms ease; }
  .cs-route:hover { border-color: color-mix(in srgb, var(--accent) 45%, var(--line)); color: var(--text); }
  .cs-route-on { border-color: color-mix(in srgb, var(--accent) 68%, var(--line)); color: var(--text); background: var(--accent-soft); }
  .cs-route i { color: var(--accent-strong); font-size: 1rem; font-style: normal; }
  .cs-route span { display: grid; gap: 0.1rem; min-width: 0; }
  .cs-route strong { font-size: 0.95rem; }
  .cs-route small { font-size: 0.8rem; color: var(--muted); }
  .cs-route-custom { border-style: dashed; }

  .cs-loadout-chips { display: flex; flex-wrap: wrap; gap: 0.45rem; }
  .cs-chip { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.45rem 0.4rem 0.45rem 0.7rem; border: 1px solid color-mix(in srgb, var(--accent) 45%, var(--line)); border-radius: 10px; color: var(--text); background: var(--accent-soft); font-size: 0.88rem; font-weight: 600; }
  .cs-chip button { display: grid; place-items: center; width: 1.5rem; height: 1.5rem; border: 0; border-radius: 7px; color: var(--muted); font-size: 0.95rem; line-height: 1; transition: 140ms ease; }
  .cs-chip button:hover { color: var(--danger); background: color-mix(in srgb, var(--danger) 12%, transparent); }

  .cs-dials { display: grid; gap: 0.55rem; }
  .cs-dial { display: grid; gap: 0.3rem; }
  .cs-dial > span { color: var(--muted); font: 600 0.78rem/1 var(--mono); letter-spacing: 0.1em; text-transform: uppercase; }
  .cs-seg { display: grid; grid-auto-flow: column; grid-auto-columns: 1fr; gap: 0.3rem; padding: 0.25rem; border: 1px solid var(--line); border-radius: 11px; }
  .cs-seg button { min-height: 2.5rem; padding: 0.35rem 0.4rem; border: 1px solid transparent; border-radius: 8px; color: var(--muted); font-size: 0.88rem; font-weight: 600; transition: 150ms ease; }
  .cs-seg button:hover { color: var(--text); }
  .cs-seg-on { border-color: color-mix(in srgb, var(--accent) 55%, var(--line)) !important; color: var(--text) !important; background: var(--accent-soft); }

  .cs-launch { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 0.85rem 0.85rem 0.85rem 1.1rem; border: 1px solid color-mix(in srgb, var(--accent) 40%, var(--line)); border-radius: 16px; background: linear-gradient(100deg, color-mix(in srgb, var(--accent-soft) 150%, transparent), transparent 70%); }
  .cs-launch-sum { display: grid; gap: 0.15rem; min-width: 0; }
  .cs-launch-sum span { color: var(--accent-strong); font: 700 0.8rem/1.3 var(--mono); letter-spacing: 0.08em; text-transform: uppercase; }
  .cs-launch-sum strong { color: var(--text); font-size: 1rem; }
  .cs-launch-btn { display: inline-flex; align-items: center; gap: 0.7rem; min-height: 3.25rem; padding: 0.7rem 1.5rem; border: 1px solid color-mix(in srgb, var(--accent) 65%, transparent); border-radius: 13px; color: var(--text); background: color-mix(in srgb, var(--accent) 22%, transparent); transition: transform 180ms ease, box-shadow 180ms ease; }
  .cs-launch-btn:hover { transform: translateY(-1px); box-shadow: 0 0 22px color-mix(in srgb, var(--accent) 40%, transparent); }
  .cs-launch-btn span { font: 800 1.05rem/1 var(--display); letter-spacing: 0.04em; }
  .cs-launch-btn kbd { padding: 0.24rem 0.42rem; border: 1px solid currentColor; border-radius: 6px; font: 700 0.68rem/1 var(--mono); opacity: 0.85; }
  @media (pointer: coarse) { .cs-launch-btn kbd { display: none; } }

  :global(html[data-theme='arcade']) .cs-launch-btn span { font-size: 0.8rem; line-height: 1.4; }
  :global(html[data-theme='arcade']) .rd-launch-btn,
  :global(html[data-theme='arcade']) .rd-tense-row button { font-family: var(--ui); }
  :global(html[data-theme='arcade']) .rd-eyebrow,
  :global(html[data-theme='arcade']) .cs-panel-label,
  :global(html[data-theme='arcade']) .cs-dial > span { font-size: 0.95rem; letter-spacing: 0.12em; }

  @media (max-width: 640px) {
    .cur-lang-grid, .cs-lang-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .cur-stair, .rd-stair { grid-template-columns: auto 1fr; }
    .cur-tense-row, .rd-tense-row { grid-column: 1 / -1; }
    .cs-deck { grid-template-columns: 1fr; }
    .cur-lead { flex-direction: column; }
    .cur-lead small { text-align: left; max-width: none; }
    .rd-launch, .cs-launch { flex-direction: column; align-items: stretch; text-align: center; }
    .rd-launch-btn, .cs-launch-btn { justify-content: center; }
  }
</style>
