<script lang="ts">
  import { onDestroy, onMount } from 'svelte';

  type Direction = {
    id: string;
    name: string;
    thesis: string;
    character: string;
    display: string;
    body: string;
    tokens: { label: string; value: string }[];
  };

  const directions: Direction[] = [
    {
      id: 'velvet-vanta',
      name: 'Velvet Vanta',
      thesis: 'Soft black. Orchid lacquer. Quiet drama.',
      character: 'Cinematic / tactile / nocturnal',
      display: 'Instrument Serif',
      body: 'Figtree + IBM Plex Mono',
      tokens: [
        { label: 'Field', value: '#08070B' },
        { label: 'Panel', value: '#121017' },
        { label: 'Ink', value: '#F1ECE6' },
        { label: 'Core', value: '#9D7BFF' },
        { label: 'Spark', value: '#E68AC4' }
      ]
    },
    {
      id: 'petrol-copper',
      name: 'Petrol Copper',
      thesis: 'Deep petrol. Aged copper. Precise warmth.',
      character: 'Instrumental / grounded / exact',
      display: 'Anybody',
      body: 'Space Grotesk + IBM Plex Mono',
      tokens: [
        { label: 'Field', value: '#061011' },
        { label: 'Panel', value: '#0D1B1B' },
        { label: 'Ink', value: '#E9E3D6' },
        { label: 'Core', value: '#45B8A7' },
        { label: 'Spark', value: '#D9925B' }
      ]
    },
    {
      id: 'oxblood-ivory',
      name: 'Oxblood Ivory',
      thesis: 'Wine-black depth. Ivory type. Gilded signals.',
      character: 'Editorial / intimate / assured',
      display: 'Instrument Serif Italic',
      body: 'Schibsted Grotesk + IBM Plex Mono',
      tokens: [
        { label: 'Field', value: '#100708' },
        { label: 'Panel', value: '#1B0C10' },
        { label: 'Ink', value: '#F2E9DC' },
        { label: 'Core', value: '#C44C61' },
        { label: 'Spark', value: '#D8B56C' }
      ]
    },
    {
      id: 'cobalt-noir',
      name: 'Cobalt Noir',
      thesis: 'Blue-black glass. Cobalt voltage. Frosted data.',
      character: 'Futurist / crystalline / fast',
      display: 'Unbounded',
      body: 'Space Grotesk + VT323',
      tokens: [
        { label: 'Field', value: '#050812' },
        { label: 'Panel', value: '#0B1020' },
        { label: 'Ink', value: '#E9ECF5' },
        { label: 'Core', value: '#627DFF' },
        { label: 'Spark', value: '#8ED8D2' }
      ]
    },
    {
      id: 'graphite-moss',
      name: 'Graphite Moss',
      thesis: 'Mineral charcoal. Moss phosphor. Amber reward.',
      character: 'Organic-tech / calm / clever',
      display: 'Bricolage Grotesque',
      body: 'Figtree + IBM Plex Mono',
      tokens: [
        { label: 'Field', value: '#090B09' },
        { label: 'Panel', value: '#121610' },
        { label: 'Ink', value: '#EDF0E5' },
        { label: 'Core', value: '#A6C85E' },
        { label: 'Spark', value: '#D7A95B' }
      ]
    },
    {
      id: 'ink-saffron',
      name: 'Ink Saffron',
      thesis: 'Black ink. Saffron light. Vermilion punctuation.',
      character: 'Graphic / cultured / decisive',
      display: 'Syne',
      body: 'Schibsted Grotesk + IBM Plex Mono',
      tokens: [
        { label: 'Field', value: '#0B0906' },
        { label: 'Panel', value: '#16110C' },
        { label: 'Ink', value: '#F0E7D8' },
        { label: 'Core', value: '#E6A528' },
        { label: 'Spark', value: '#D75B4B' }
      ]
    }
  ];

  let playing = '';
  let timer: ReturnType<typeof setTimeout> | null = null;

  function runPreview(id: string): void {
    if (timer) clearTimeout(timer);
    playing = '';
    requestAnimationFrame(() => {
      playing = id;
      timer = setTimeout(() => (playing = ''), 1100);
    });
  }

  onMount(() => {
    const root = document.documentElement;
    const previousTheme = root.getAttribute('data-theme');
    const previousPlayground = root.getAttribute('data-playground');
    root.setAttribute('data-theme', 'dark');
    root.setAttribute('data-playground', 'dark-directions');

    return () => {
      if (previousTheme) root.setAttribute('data-theme', previousTheme);
      else root.removeAttribute('data-theme');
      if (previousPlayground) root.setAttribute('data-playground', previousPlayground);
      else root.removeAttribute('data-playground');
    };
  });

  onDestroy(() => {
    if (timer) clearTimeout(timer);
  });
</script>

<svelte:head>
  <title>Into the Dark · VerbPractice Style Lab</title>
  <meta name="description" content="Six very dark palette and typography directions for VerbPractice Moon mode." />
</svelte:head>

<section class="dark-lab" id="dark-top">
  <header class="lab-hero">
    <div class="hero-rail">
      <span><i></i>MOON_MODE / IDENTITY STUDY</span>
      <span>ONE SYSTEM · SIX ATMOSPHERES</span>
      <span>16.07.26</span>
    </div>

    <div class="hero-body">
      <div class="hero-copy">
        <p>Palette + type exploration</p>
        <h1>Six ways<br />into the <em>dark.</em></h1>
      </div>

      <div class="hero-manifesto">
        <div class="hero-mark" aria-hidden="true">
          <span>V</span><span>P</span><i></i>
        </div>
        <p>Not Arcade with the lights off. Not a productivity dashboard in charcoal. Six identities for a quieter player who still wants tension, reward and a little danger.</p>
        <small>The mini-game anatomy stays identical in every card. Compare the identity, not the layout.</small>
      </div>
    </div>

    <div class="hero-index" aria-label="The six dark mode directions">
      {#each directions as direction, index}
        <a href={`#${direction.id}`}><span>0{index + 1}</span>{direction.name}</a>
      {/each}
    </div>
  </header>

  <main class="direction-grid">
    {#each directions as direction, index (direction.id)}
      <article id={direction.id} class={`direction ${direction.id}`} class:is-playing={playing === direction.id}>
        <header class="direction-head">
          <div class="direction-number">0{index + 1}</div>
          <div>
            <p>{direction.character}</p>
            <h2>{direction.name}</h2>
            <span>{direction.thesis}</span>
          </div>
          <i class="status-light" aria-hidden="true"></i>
        </header>

        <div class="game-frame">
          <div class="game-rail">
            <div class="mini-brand" aria-label="VerbPractice logo preview">
              <span class="mini-badge"><b>V</b><b>P</b><i></i></span>
              <span>Verb Practice</span>
            </div>
            <div class="run-data"><span>WORDS</span><b>03 / 12</b></div>
          </div>

          <div class="prompt-zone">
            <div class="prompt-meta"><span>TRANSLATE</span><span>EN → ES</span></div>
            <h3>still</h3>
            <div class="signal-wave" aria-hidden="true">
              {#each Array(13) as _, waveIndex}
                <i style={`--wave-index:${waveIndex};--wave-height:${7 + (waveIndex % 5) * 5}px`}></i>
              {/each}
            </div>
          </div>

          <div class="answer-zone">
            <div class="answer-field"><span>todavía</span><i></i></div>
            <button type="button" on:click={() => runPreview(direction.id)} aria-label={`Preview ${direction.name} action`}>
              <span>Play</span><b>↗</b>
            </button>
          </div>

          <div class="progress-rail" aria-label="Three of twelve words complete">
            {#each Array(12) as _, progressIndex}
              <i class:complete={progressIndex < 3}></i>
            {/each}
          </div>
        </div>

        <div class="identity-spec">
          <div class="palette" aria-label={`${direction.name} color palette`}>
            {#each direction.tokens as token}
              <div>
                <i style={`--swatch:${token.value}`}></i>
                <span><b>{token.label}</b><code>{token.value}</code></span>
              </div>
            {/each}
          </div>

          <div class="type-specimen">
            <div>
              <span>DISPLAY / {direction.display}</span>
              <strong>Learn after midnight.</strong>
            </div>
            <div class="type-notes">
              <span>BODY</span><b>{direction.body}</b>
              <p>Each answer sharpens the signal. Keep moving.</p>
            </div>
          </div>
        </div>

        <footer class="direction-foot">
          <span>Same logo</span><span>Same footprint</span><span>New atmosphere</span>
        </footer>
      </article>
    {/each}
  </main>

  <footer class="lab-footer">
    <div><span>MOON MODE / ROUND 01</span><h2>Pick the night<br />you want to play in.</h2></div>
    <p>Every option is deliberately darker than the current mode, but none relies on pure black or generic neon. Core handles action; Spark is reserved for moments worth noticing.</p>
    <a href="#dark-top">Return to index ↑</a>
  </footer>
</section>

<style>
  :global(html[data-playground='dark-directions']) {
    scroll-behavior: smooth;
    background: #050506;
  }

  :global(html[data-playground='dark-directions'] body) {
    background:
      radial-gradient(circle at 50% -20%, rgba(112, 94, 142, .16), transparent 42rem),
      linear-gradient(180deg, #09090b, #050506 38rem);
    background-attachment: fixed;
  }

  :global(html[data-playground='dark-directions'] body::after),
  :global(html[data-playground='dark-directions'] .page-floor) { display: none; }

  :global(html[data-playground='dark-directions'] .workspace-shell) {
    max-width: 1520px;
    padding-top: 1rem;
    padding-bottom: 5rem;
  }

  :global(html[data-playground='dark-directions'] .topbar-shell) {
    border-color: rgba(242, 237, 230, .1);
    background: rgba(7, 7, 9, .88);
  }

  .dark-lab {
    --lab-field: #050506;
    --lab-panel: #0d0d10;
    --lab-ink: #eeeae4;
    --lab-muted: #8b8790;
    width: min(100%, 1480px);
    margin-inline: auto;
    color: var(--lab-ink);
    font-family: "Figtree", sans-serif;
  }

  .lab-hero {
    position: relative;
    overflow: hidden;
    min-height: 690px;
    border: 1px solid rgba(238, 234, 228, .14);
    background:
      linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px),
      linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
      #0a0a0d;
    background-size: 44px 44px;
  }

  .lab-hero::before {
    content: '';
    position: absolute;
    width: min(60vw, 780px);
    height: min(60vw, 780px);
    right: -16%;
    bottom: -66%;
    border: 1px solid rgba(230, 138, 196, .22);
    border-radius: 50%;
    box-shadow: 0 0 0 7vw rgba(157, 123, 255, .025), 0 0 0 15vw rgba(142, 216, 210, .018);
  }

  .hero-rail {
    position: relative;
    z-index: 2;
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 1rem 1.2rem;
    border-bottom: 1px solid rgba(238, 234, 228, .14);
    color: #aaa5af;
    font: 500 .66rem/1 "IBM Plex Mono", monospace;
    letter-spacing: .12em;
  }

  .hero-rail span:first-child { display: flex; align-items: center; gap: .6rem; }
  .hero-rail i { width: 6px; height: 6px; border-radius: 50%; background: #e68ac4; box-shadow: 0 0 12px rgba(230, 138, 196, .72); }

  .hero-body {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: minmax(0, 1.25fr) minmax(280px, .5fr);
    gap: clamp(3rem, 10vw, 11rem);
    align-items: end;
    min-height: 540px;
    padding: clamp(2rem, 6vw, 5.6rem);
  }

  .hero-copy > p {
    margin: 0 0 1.2rem;
    color: #9d7bff;
    font: 600 .68rem/1 "IBM Plex Mono", monospace;
    letter-spacing: .14em;
    text-transform: uppercase;
  }

  .hero-copy h1 {
    max-width: 9ch;
    margin: 0;
    font: 600 clamp(4.2rem, 10vw, 9.8rem)/.78 "Syne", sans-serif;
    letter-spacing: -.09em;
    text-wrap: balance;
  }

  .hero-copy h1 em {
    color: #b1a2d9;
    font-family: "Instrument Serif", Georgia, serif;
    font-weight: 400;
    letter-spacing: -.04em;
  }

  .hero-manifesto { display: grid; gap: 1.4rem; padding-bottom: .25rem; }
  .hero-manifesto p { margin: 0; color: #cbc6cf; font-size: 1.05rem; line-height: 1.62; }
  .hero-manifesto small { color: #77727d; font: 500 .65rem/1.55 "IBM Plex Mono", monospace; text-transform: uppercase; letter-spacing: .07em; }

  .hero-mark {
    position: relative;
    display: flex;
    width: 54px;
    height: 54px;
    align-items: center;
    justify-content: center;
    gap: 1px;
    overflow: hidden;
    border: 1px solid #75688e;
    border-radius: 15px;
    background: #111016;
    font: 800 1.15rem/1 "Press Start 2P", monospace;
  }

  .hero-mark span:last-of-type { color: #9d7bff; }
  .hero-mark i { position: absolute; right: 0; bottom: 0; left: 0; width: 38%; height: 4px; background: linear-gradient(90deg, #9d7bff, #e68ac4); }

  .hero-index {
    position: relative;
    z-index: 2;
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    border-top: 1px solid rgba(238, 234, 228, .14);
  }

  .hero-index a {
    display: grid;
    min-height: 68px;
    grid-template-columns: auto 1fr;
    gap: .7rem;
    align-items: center;
    padding: .8rem 1rem;
    color: #b7b2bc;
    font: 600 .67rem/1.2 "Figtree", sans-serif;
    text-decoration: none;
    transition: color 180ms ease, background 180ms ease;
  }

  .hero-index a + a { border-left: 1px solid rgba(238, 234, 228, .14); }
  .hero-index a span { color: #66616c; font: 500 .58rem/1 "IBM Plex Mono", monospace; }
  .hero-index a:hover { color: #fff; background: rgba(157, 123, 255, .09); }
  .hero-index a:focus-visible { outline: 2px solid #e68ac4; outline-offset: -3px; }

  .direction-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: clamp(1rem, 2vw, 1.6rem);
    margin-top: clamp(5rem, 9vw, 9rem);
  }

  .direction {
    /* Primitive tokens are declared per direction below. */
    --surface-field: var(--primitive-field);
    --surface-panel: var(--primitive-panel);
    --surface-raised: var(--primitive-raised);
    --content-primary: var(--primitive-ink);
    --content-muted: var(--primitive-muted);
    --action-primary: var(--primitive-core);
    --signal-accent: var(--primitive-spark);
    --border-subtle: color-mix(in srgb, var(--content-primary) 13%, transparent);
    --border-active: color-mix(in srgb, var(--action-primary) 58%, transparent);
    --font-display: "Syne", sans-serif;
    --font-body: "Figtree", sans-serif;
    --font-data: "IBM Plex Mono", monospace;
    min-width: 0;
    overflow: hidden;
    scroll-margin-top: 1rem;
    border: 1px solid var(--border-subtle);
    border-radius: var(--card-radius, 18px);
    color: var(--content-primary);
    background: var(--surface-field);
    box-shadow: 0 24px 80px rgba(0, 0, 0, .36);
    transition: transform 240ms cubic-bezier(.2,.8,.2,1), border-color 240ms ease;
  }

  .direction:hover { transform: translateY(-3px); border-color: var(--border-active); }

  .velvet-vanta {
    --primitive-field: #08070b;
    --primitive-panel: #121017;
    --primitive-raised: #1b1722;
    --primitive-ink: #f1ece6;
    --primitive-muted: #99919f;
    --primitive-core: #9d7bff;
    --primitive-spark: #e68ac4;
    --card-radius: 28px;
    --font-display: "Instrument Serif", Georgia, serif;
  }

  .petrol-copper {
    --primitive-field: #061011;
    --primitive-panel: #0d1b1b;
    --primitive-raised: #142625;
    --primitive-ink: #e9e3d6;
    --primitive-muted: #879b95;
    --primitive-core: #45b8a7;
    --primitive-spark: #d9925b;
    --card-radius: 4px;
    --font-display: "Anybody", sans-serif;
    --font-body: "Space Grotesk", sans-serif;
  }

  .oxblood-ivory {
    --primitive-field: #100708;
    --primitive-panel: #1b0c10;
    --primitive-raised: #281218;
    --primitive-ink: #f2e9dc;
    --primitive-muted: #aa8d8d;
    --primitive-core: #c44c61;
    --primitive-spark: #d8b56c;
    --card-radius: 14px;
    --font-display: "Instrument Serif", Georgia, serif;
    --font-body: "Schibsted Grotesk", sans-serif;
  }

  .cobalt-noir {
    --primitive-field: #050812;
    --primitive-panel: #0b1020;
    --primitive-raised: #121a31;
    --primitive-ink: #e9ecf5;
    --primitive-muted: #858ea8;
    --primitive-core: #627dff;
    --primitive-spark: #8ed8d2;
    --card-radius: 2px;
    --font-display: "Unbounded", sans-serif;
    --font-body: "Space Grotesk", sans-serif;
    --font-data: "VT323", monospace;
  }

  .graphite-moss {
    --primitive-field: #090b09;
    --primitive-panel: #121610;
    --primitive-raised: #1a2118;
    --primitive-ink: #edf0e5;
    --primitive-muted: #929c88;
    --primitive-core: #a6c85e;
    --primitive-spark: #d7a95b;
    --card-radius: 30px 12px 30px 12px;
    --font-display: "Bricolage Grotesque", sans-serif;
  }

  .ink-saffron {
    --primitive-field: #0b0906;
    --primitive-panel: #16110c;
    --primitive-raised: #211a11;
    --primitive-ink: #f0e7d8;
    --primitive-muted: #9e9181;
    --primitive-core: #e6a528;
    --primitive-spark: #d75b4b;
    --card-radius: 0 20px 0 20px;
    --font-display: "Syne", sans-serif;
    --font-body: "Schibsted Grotesk", sans-serif;
  }

  .direction-head {
    position: relative;
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 1rem;
    align-items: start;
    min-height: 146px;
    padding: 1.35rem;
    border-bottom: 1px solid var(--border-subtle);
    background: var(--surface-panel);
  }

  .direction-number { color: var(--action-primary); font: 500 .72rem/1 var(--font-data); letter-spacing: .08em; }
  .direction-head p { margin: 0 0 .7rem; color: var(--content-muted); font: 500 .56rem/1 var(--font-data); letter-spacing: .09em; text-transform: uppercase; }
  .direction-head h2 { margin: 0; font: 600 clamp(2.3rem, 4vw, 4.1rem)/.9 var(--font-display); letter-spacing: -.045em; }
  .direction-head > div > span { display: block; margin-top: .8rem; color: var(--content-muted); font: 500 .85rem/1.35 var(--font-body); }
  .status-light { width: 8px; height: 8px; border: 1px solid var(--action-primary); border-radius: 50%; background: color-mix(in srgb, var(--action-primary) 36%, transparent); }

  .game-frame {
    position: relative;
    margin: clamp(.8rem, 2vw, 1.35rem);
    overflow: hidden;
    border: 1px solid var(--border-subtle);
    border-radius: calc(var(--card-radius, 18px) * .56);
    background: var(--surface-panel);
  }

  .game-frame::before {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: radial-gradient(circle at 76% 42%, color-mix(in srgb, var(--action-primary) 12%, transparent), transparent 35%);
  }

  .game-rail {
    position: relative;
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
    min-height: 58px;
    padding: .7rem .9rem;
    border-bottom: 1px solid var(--border-subtle);
  }

  .mini-brand { display: flex; gap: .6rem; align-items: center; color: var(--content-muted); font: 600 .5rem/1 var(--font-data); letter-spacing: .17em; text-transform: uppercase; }
  .mini-badge { position: relative; display: flex; width: 31px; height: 31px; flex: 0 0 auto; align-items: center; justify-content: center; gap: 1px; overflow: hidden; border: 1px solid var(--border-active); border-radius: 9px; background: var(--surface-raised); font: 800 .65rem/1 "Press Start 2P", monospace; }
  .mini-badge b:last-of-type { color: var(--action-primary); }
  .mini-badge i { position: absolute; right: 0; bottom: 0; left: 0; width: 37%; height: 3px; background: linear-gradient(90deg, var(--action-primary), var(--signal-accent)); transition: width 420ms cubic-bezier(.2,.8,.2,1); }
  .direction:hover .mini-badge i { width: 100%; }
  .run-data { display: flex; gap: .6rem; align-items: baseline; color: var(--content-muted); font: 500 .55rem/1 var(--font-data); letter-spacing: .08em; }
  .run-data b { color: var(--content-primary); font-size: .73rem; }

  .prompt-zone { position: relative; min-height: 210px; padding: 1.3rem clamp(1rem, 3vw, 2rem); }
  .prompt-meta { display: flex; justify-content: space-between; gap: 1rem; color: var(--content-muted); font: 500 .54rem/1 var(--font-data); letter-spacing: .11em; }
  .prompt-zone h3 { position: relative; z-index: 1; margin: 2.25rem 0 0; font: 600 clamp(4rem, 8vw, 7.4rem)/.72 var(--font-display); letter-spacing: -.055em; }

  .signal-wave {
    position: absolute;
    right: clamp(1rem, 3vw, 2rem);
    bottom: 1.5rem;
    display: flex;
    height: 42px;
    gap: 3px;
    align-items: center;
    opacity: .72;
  }

  .signal-wave i { width: 2px; height: var(--wave-height); background: color-mix(in srgb, var(--action-primary) 72%, var(--content-muted)); animation: signal-breathe 2.2s ease-in-out infinite; animation-delay: calc(var(--wave-index) * -80ms); }

  .answer-zone {
    position: relative;
    display: grid;
    grid-template-columns: 1fr 124px;
    min-height: 62px;
    margin: 0 clamp(1rem, 3vw, 2rem) 1.4rem;
    border: 1px solid var(--border-subtle);
    border-radius: calc(var(--card-radius, 18px) * .38);
    background: var(--surface-raised);
  }

  .answer-field { position: relative; display: flex; align-items: center; min-width: 0; padding: .8rem 1rem; color: var(--content-primary); font: 500 1.03rem/1 var(--font-body); }
  .answer-field i { width: 1px; height: 1.25em; margin-left: 2px; background: var(--action-primary); animation: caret-blink 1s steps(1) infinite; }
  .answer-zone button { display: flex; min-width: 0; align-items: center; justify-content: space-between; gap: .6rem; border: 0; border-left: 1px solid var(--border-subtle); border-radius: 0 calc(var(--card-radius, 18px) * .34) calc(var(--card-radius, 18px) * .34) 0; padding: .75rem 1rem; color: var(--surface-field); background: var(--action-primary); font: 700 .72rem/1 var(--font-body); letter-spacing: .08em; text-transform: uppercase; transition: filter 180ms ease, transform 120ms ease; touch-action: manipulation; }
  .answer-zone button b { font-size: 1rem; transition: transform 200ms ease; }
  .answer-zone button:hover { filter: brightness(1.12); }
  .answer-zone button:hover b { transform: translate(2px, -2px); }
  .answer-zone button:active { transform: scale(.97); }
  .answer-zone button:focus-visible { outline: 2px solid var(--signal-accent); outline-offset: -4px; }

  .progress-rail { position: relative; display: grid; grid-template-columns: repeat(12, 1fr); gap: 4px; padding: 0 clamp(1rem, 3vw, 2rem) 1.2rem; }
  .progress-rail i { height: 3px; border-radius: 99px; background: color-mix(in srgb, var(--content-muted) 23%, transparent); }
  .progress-rail i.complete { background: var(--action-primary); }

  .identity-spec { border-top: 1px solid var(--border-subtle); }

  .palette { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); border-bottom: 1px solid var(--border-subtle); }
  .palette > div { min-width: 0; padding: .75rem; }
  .palette > div + div { border-left: 1px solid var(--border-subtle); }
  .palette i { display: block; height: 34px; margin-bottom: .55rem; border: 1px solid color-mix(in srgb, var(--content-primary) 16%, transparent); border-radius: 6px; background: var(--swatch); }
  .palette span { display: grid; gap: .25rem; }
  .palette b { color: var(--content-muted); font: 500 .5rem/1 var(--font-data); text-transform: uppercase; }
  .palette code { overflow: hidden; color: var(--content-primary); font: 500 .56rem/1 var(--font-data); text-overflow: ellipsis; }

  .type-specimen { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(160px, .7fr); gap: 1.2rem; min-height: 166px; padding: 1.3rem; background: var(--surface-panel); }
  .type-specimen span { display: block; margin-bottom: .8rem; color: var(--action-primary); font: 500 .5rem/1 var(--font-data); letter-spacing: .09em; text-transform: uppercase; }
  .type-specimen strong { display: block; max-width: 11ch; font: 600 clamp(2rem, 3.7vw, 3.35rem)/.9 var(--font-display); letter-spacing: -.035em; }
  .type-notes { align-self: end; }
  .type-notes b { display: block; color: var(--content-primary); font: 600 .68rem/1.3 var(--font-data); }
  .type-notes p { margin: .75rem 0 0; color: var(--content-muted); font: 500 .78rem/1.5 var(--font-body); }

  .direction-foot { display: grid; grid-template-columns: repeat(3, 1fr); border-top: 1px solid var(--border-subtle); }
  .direction-foot span { display: grid; min-height: 42px; place-items: center; padding: .5rem; color: var(--content-muted); font: 500 .5rem/1 var(--font-data); text-transform: uppercase; letter-spacing: .05em; }
  .direction-foot span + span { border-left: 1px solid var(--border-subtle); }

  .velvet-vanta .game-frame { box-shadow: inset 0 0 55px rgba(157,123,255,.045); }
  .velvet-vanta .prompt-zone h3, .oxblood-ivory .prompt-zone h3 { font-weight: 400; }
  .oxblood-ivory .prompt-zone h3, .oxblood-ivory .type-specimen strong { font-style: italic; }
  .petrol-copper .game-frame { border-left: 3px solid var(--primitive-spark); }
  .petrol-copper .signal-wave i { width: 3px; border-radius: 0; }
  .cobalt-noir .game-frame { background: linear-gradient(145deg, rgba(98,125,255,.08), transparent 40%), var(--surface-panel); clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 14px 100%, 0 calc(100% - 14px)); }
  .cobalt-noir .direction-head h2 { font-size: clamp(1.8rem, 3.1vw, 3rem); letter-spacing: -.06em; }
  .graphite-moss .game-frame { background: radial-gradient(circle at 20% 20%, rgba(166,200,94,.055) 1px, transparent 1.5px), var(--surface-panel); background-size: 12px 12px; }
  .graphite-moss .signal-wave i { border-radius: 99px; }
  .ink-saffron .direction-head { box-shadow: inset 5px 0 0 var(--primitive-spark); }
  .ink-saffron .answer-zone button { color: #16110c; }

  .direction.is-playing .answer-zone button { animation: action-charge 900ms cubic-bezier(.2,.8,.2,1); }
  .direction.is-playing .signal-wave i { animation: signal-fire 520ms cubic-bezier(.2,.8,.2,1) both; animation-delay: calc(var(--wave-index) * 24ms); }
  .direction.is-playing .progress-rail i:nth-child(4) { animation: progress-flash 900ms ease both; }
  .direction.is-playing .game-frame { border-color: var(--border-active); }

  .lab-footer {
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) minmax(280px, .65fr);
    gap: clamp(2rem, 8vw, 8rem);
    align-items: end;
    margin-top: clamp(6rem, 12vw, 12rem);
    padding: clamp(2rem, 5vw, 4.5rem);
    border: 1px solid rgba(238,234,228,.14);
    background: #0a0a0d;
  }

  .lab-footer span { color: #9d7bff; font: 500 .6rem/1 "IBM Plex Mono", monospace; letter-spacing: .1em; }
  .lab-footer h2 { margin: 1rem 0 0; font: 600 clamp(3rem, 6vw, 6.8rem)/.82 "Syne", sans-serif; letter-spacing: -.07em; }
  .lab-footer p { margin: 0; color: #aaa5af; line-height: 1.65; }
  .lab-footer a { grid-column: 2; width: fit-content; color: #e9e4dc; font: 500 .62rem/1 "IBM Plex Mono", monospace; text-decoration: none; text-transform: uppercase; letter-spacing: .08em; }
  .lab-footer a:hover { color: #e68ac4; }

  @keyframes signal-breathe { 0%, 100% { transform: scaleY(.72); opacity: .42; } 50% { transform: scaleY(1); opacity: .9; } }
  @keyframes caret-blink { 0%, 48% { opacity: 1; } 49%, 100% { opacity: 0; } }
  @keyframes signal-fire { 0% { transform: scaleY(.25); opacity: .35; } 48% { transform: scaleY(1.75); background: var(--signal-accent); opacity: 1; } 100% { transform: scaleY(.65); opacity: .6; } }
  @keyframes action-charge { 0%, 100% { box-shadow: inset 0 0 0 0 var(--signal-accent); } 38% { box-shadow: inset 124px 0 0 0 var(--signal-accent); } }
  @keyframes progress-flash { 0%, 100% { background: color-mix(in srgb, var(--content-muted) 23%, transparent); } 45% { background: var(--signal-accent); box-shadow: 0 0 12px var(--signal-accent); } }

  @media (max-width: 1050px) {
    .hero-body { grid-template-columns: 1fr; align-items: start; gap: 3rem; }
    .hero-manifesto { max-width: 560px; }
    .hero-index { grid-template-columns: repeat(3, 1fr); }
    .hero-index a:nth-child(4) { border-left: 0; }
    .hero-index a:nth-child(n + 4) { border-top: 1px solid rgba(238, 234, 228, .14); }
    .direction-grid { grid-template-columns: 1fr; }
  }

  @media (max-width: 680px) {
    :global(html[data-playground='dark-directions'] .workspace-shell) { padding: .55rem; padding-top: .55rem; }
    .lab-hero { min-height: auto; }
    .hero-rail span:nth-child(2) { display: none; }
    .hero-body { min-height: 540px; padding: 2rem 1.25rem; }
    .hero-copy h1 { font-size: clamp(4rem, 20vw, 6.2rem); }
    .hero-index { grid-template-columns: repeat(2, 1fr); }
    .hero-index a:nth-child(odd) { border-left: 0; }
    .hero-index a:nth-child(n + 3) { border-top: 1px solid rgba(238, 234, 228, .14); }
    .hero-index a:nth-child(4) { border-left: 1px solid rgba(238, 234, 228, .14); }
    .direction-grid { margin-top: 4rem; }
    .direction { --card-radius: 12px; }
    .direction-head { min-height: 132px; padding: 1rem; }
    .direction-head h2 { font-size: clamp(2rem, 10vw, 3.25rem); }
    .game-frame { margin: .55rem; }
    .game-rail { padding-inline: .7rem; }
    .mini-brand > span:last-child { display: none; }
    .prompt-zone { min-height: 176px; padding: 1rem; }
    .prompt-zone h3 { margin-top: 2rem; font-size: clamp(3.7rem, 20vw, 5.6rem); }
    .signal-wave { right: 1rem; bottom: 1rem; }
    .answer-zone { grid-template-columns: 1fr 104px; margin: 0 .7rem 1rem; }
    .answer-zone button { padding-inline: .75rem; }
    .progress-rail { padding-inline: .7rem; gap: 3px; }
    .palette { grid-template-columns: repeat(5, 1fr); }
    .palette > div { padding: .45rem; }
    .palette i { height: 28px; }
    .palette code { font-size: .45rem; }
    .type-specimen { grid-template-columns: 1fr; min-height: 0; }
    .type-notes { max-width: 290px; }
    .lab-footer { grid-template-columns: 1fr; padding: 2rem 1.25rem; }
    .lab-footer a { grid-column: 1; }
  }

  @media (prefers-reduced-motion: reduce) {
    :global(html[data-playground='dark-directions']) { scroll-behavior: auto; }
    .direction, .mini-badge i, .answer-zone button, .answer-zone button b { transition: none; }
    .signal-wave i, .answer-field i, .direction.is-playing .signal-wave i, .direction.is-playing .answer-zone button, .direction.is-playing .progress-rail i:nth-child(4) { animation: none; }
  }
</style>
