<script lang="ts">
  import { onDestroy, onMount, tick } from 'svelte';

  type FeedbackTone = 'right' | 'wrong' | '';

  const playOptions = [
    {
      id: 'relay',
      name: 'Saffron Relay',
      note: 'A twelve-cell launch sequence. Crisp, quick and closest to the game grid.'
    },
    {
      id: 'aperture',
      name: 'Ink Aperture',
      note: 'Two mechanical shutters close on the word, then release the session.'
    },
    {
      id: 'needle',
      name: 'Signal Needle',
      note: 'A playable instrument: the dial winds, the needle fires, the signal travels.'
    }
  ] as const;

  const feedbackOptions = [
    {
      id: 'reeds',
      name: 'Reed Wave',
      note: 'Razor Line over a field of fine vertical reeds: radiating when right, whipping when wrong.'
    },
    {
      id: 'contours',
      name: 'Contour Wave',
      note: 'Razor Line over drawn contours: expanding when right, collapsing off-axis when wrong.'
    },
    {
      id: 'horizons',
      name: 'Horizon Wave',
      note: 'Razor Line over broad ink ribbons: flowing through a hit, tearing apart on a miss.'
    }
  ] as const;

  let playRun = '';
  let feedbackState: Record<string, FeedbackTone> = {};
  const timers = new Map<string, ReturnType<typeof setTimeout>>();

  function clearTimer(key: string): void {
    const timer = timers.get(key);
    if (timer) clearTimeout(timer);
    timers.delete(key);
  }

  async function runPlay(id: string): Promise<void> {
    clearTimer('play');
    playRun = '';
    await tick();
    requestAnimationFrame(() => {
      playRun = id;
      timers.set('play', setTimeout(() => (playRun = ''), 1450));
    });
  }

  async function runFeedback(id: string, tone: Exclude<FeedbackTone, ''>): Promise<void> {
    clearTimer(`feedback-${id}`);
    feedbackState = { ...feedbackState, [id]: '' };
    await tick();
    requestAnimationFrame(() => {
      feedbackState = { ...feedbackState, [id]: tone };
      timers.set(`feedback-${id}`, setTimeout(() => {
        feedbackState = { ...feedbackState, [id]: '' };
      }, 1700));
    });
  }

  function moveAperturePointer(event: PointerEvent): void {
    const button = event.currentTarget as HTMLButtonElement;
    const rect = button.getBoundingClientRect();
    const x = Math.max(0, Math.min(rect.width, event.clientX - rect.left));
    const y = Math.max(0, Math.min(rect.height, event.clientY - rect.top));
    const nx = rect.width ? x / rect.width : 0.5;
    const ny = rect.height ? y / rect.height : 0.5;
    button.style.setProperty('--pointer-x', `${x.toFixed(1)}px`);
    button.style.setProperty('--pointer-y', `${y.toFixed(1)}px`);
    button.style.setProperty('--left-pull', `${((1 - nx) * 15).toFixed(1)}px`);
    button.style.setProperty('--right-pull', `${(nx * 15).toFixed(1)}px`);
    button.style.setProperty('--slat-y', `${((ny - 0.5) * 9).toFixed(1)}px`);
    button.style.setProperty('--core-x', `${((nx - 0.5) * 7).toFixed(1)}px`);
    button.style.setProperty('--core-y', `${((ny - 0.5) * 4).toFixed(1)}px`);
    button.classList.add('tracking');
  }

  function resetAperturePointer(event: PointerEvent): void {
    const button = event.currentTarget as HTMLButtonElement;
    button.classList.remove('tracking');
    button.style.removeProperty('--pointer-x');
    button.style.removeProperty('--pointer-y');
    button.style.removeProperty('--left-pull');
    button.style.removeProperty('--right-pull');
    button.style.removeProperty('--slat-y');
    button.style.removeProperty('--core-x');
    button.style.removeProperty('--core-y');
  }

  onMount(() => {
    const root = document.documentElement;
    const previousTheme = root.getAttribute('data-theme');
    const previousPlayground = root.getAttribute('data-playground');
    root.setAttribute('data-theme', 'dark');
    root.setAttribute('data-playground', 'ink-interactions');

    return () => {
      if (previousTheme) root.setAttribute('data-theme', previousTheme);
      else root.removeAttribute('data-theme');
      if (previousPlayground) root.setAttribute('data-playground', previousPlayground);
      else root.removeAttribute('data-playground');
    };
  });

  onDestroy(() => {
    for (const timer of timers.values()) clearTimeout(timer);
  });
</script>

<svelte:head>
  <title>Ink Saffron Interaction Forge · VerbPractice</title>
  <meta name="description" content="Three Play controls and three right/wrong feedback systems for VerbPractice Ink Saffron mode." />
</svelte:head>

<section class="interaction-lab" id="forge-top">
  <header class="forge-hero">
    <div class="hero-status">
      <span><i></i> MOON_MODE / INTERACTION FORGE</span>
      <span>INK SAFFRON · ROUND 02</span>
    </div>
    <div class="hero-main">
      <p class="hero-kicker">Press them. Miss on purpose.</p>
      <h1>Find the game’s<br /><em>fingerprint.</em></h1>
      <div class="hero-brief">
        <span>06 LIVE TESTS</span>
        <p>Same logic. Same space. Six new ways for the game to answer your hand.</p>
      </div>
    </div>
    <nav class="hero-nav" aria-label="Playground sections">
      <a href="#play-options"><b>01</b> Play controls</a>
      <a href="#feedback-options"><b>02</b> Right / wrong</a>
    </nav>
  </header>

  <main>
    <section class="forge-section" id="play-options">
      <header class="section-heading">
        <div><span>01 / LAUNCH</span><h2>Three ways to say Play.</h2></div>
        <p>Every control below is exactly <strong>274 × 106</strong>—the current game footprint. Click repeatedly; each launch rearms itself.</p>
      </header>

      <div class="play-grid">
        {#each playOptions as option, index (option.id)}
          <article class={`concept play-concept ${option.id}`}>
            <header class="concept-head">
              <span>A{index + 1}</span>
              <div><h3>{option.name}</h3><p>{option.note}</p></div>
            </header>

            <div class="button-bay">
              {#if option.id === 'relay'}
                <button class:running={playRun === option.id} class="play-button relay-button" type="button" on:click={() => runPlay(option.id)}>
                  <span class="relay-grid" aria-hidden="true">
                    {#each Array(12) as _, cellIndex}
                      <i style={`--i:${cellIndex}`}></i>
                    {/each}
                  </span>
                  <span class="button-copy"><b>▶</b> PLAY</span>
                  <small>12 / READY</small>
                </button>
              {:else if option.id === 'aperture'}
                <button
                  class:running={playRun === option.id}
                  class="play-button aperture-button"
                  type="button"
                  on:click={() => runPlay(option.id)}
                  on:pointermove={moveAperturePointer}
                  on:pointerleave={resetAperturePointer}
                  on:pointercancel={resetAperturePointer}
                >
                  <span class="gate gate-left" aria-hidden="true"><i></i><i></i><i></i></span>
                  <span class="gate gate-right" aria-hidden="true"><i></i><i></i><i></i></span>
                  <span class="aperture-response" aria-hidden="true"><i></i></span>
                  <span class="aperture-core"><b>PLAY</b><i>ENTER</i></span>
                  <span class="corner-index">OPEN / 01</span>
                </button>
              {:else}
                <button class:running={playRun === option.id} class="play-button needle-button" type="button" on:click={() => runPlay(option.id)}>
                  <span class="needle-dial" aria-hidden="true"><i></i><b>▶</b></span>
                  <span class="needle-track" aria-hidden="true"><i></i><b></b></span>
                  <span class="needle-copy"><b>PLAY</b><small>SIGNAL READY</small></span>
                </button>
              {/if}
            </div>

            <footer class="concept-foot"><span>{option.id === 'aperture' ? 'MOVE + CLICK' : 'CLICK TO FIRE'}</span><i></i><span>274 × 106</span></footer>
          </article>
        {/each}
      </div>
    </section>

    <section class="forge-section feedback-section" id="feedback-options">
      <header class="section-heading">
        <div><span>02 / GRADING</span><h2>One verdict. Three waves.</h2></div>
        <p>Every card keeps B1’s Razor Line foreground. Only the Ink Saffron wave behind it changes—and each wave behaves differently for right and wrong.</p>
      </header>

      <div class="feedback-grid">
        {#each feedbackOptions as option, index (option.id)}
          <article class={`concept feedback-concept ${option.id}`}>
            <header class="concept-head">
              <span>B{index + 1}</span>
              <div><h3>{option.name}</h3><p>{option.note}</p></div>
            </header>

            <div
              class="answer-stage"
              class:right={feedbackState[option.id] === 'right'}
              class:wrong={feedbackState[option.id] === 'wrong'}
              aria-live="polite"
            >
              {#if option.id === 'reeds'}
                <div class="background-wave reed-wave" aria-hidden="true">
                  {#each Array(21) as _, waveIndex}
                    <i style={`--i:${waveIndex};--distance:${Math.abs(waveIndex - 10)};--height:${24 + ((waveIndex * 13) % 58)}px`}></i>
                  {/each}
                </div>
              {:else if option.id === 'contours'}
                <div class="background-wave contour-wave" aria-hidden="true">
                  {#each Array(7) as _, waveIndex}
                    <i style={`--i:${waveIndex};--offset:${waveIndex % 2 ? 14 : -14}px;--contour-width:${112 + waveIndex * 31}px;--contour-height:${46 + waveIndex * 17}px`}></i>
                  {/each}
                </div>
              {:else}
                <div class="background-wave horizon-wave" aria-hidden="true">
                  {#each Array(6) as _, waveIndex}
                    <i style={`--i:${waveIndex};--from:${waveIndex % 2 ? 112 : -112}%;--to:${waveIndex % 2 ? -112 : 112}%`}></i>
                  {/each}
                </div>
              {/if}

              <div class="stage-hud"><span>6 / 10</span><span>EN → ES</span><b>COMBO ×5</b></div>
              <h4>still</h4>

              <div class="razor-answer">
                <span class="typed-word">todavía</span>
                <i class="razor-rule" aria-hidden="true"></i>
                <b class="verdict right-verdict">LOCKED ✓</b>
                <b class="verdict wrong-verdict">CUT / AGAIN</b>
              </div>

              <div class="stage-feedback" aria-hidden="true">
                <span class="right-message">Correct. Keep the run alive.</span>
                <span class="wrong-message">Not yet. Your hint is ready.</span>
              </div>
            </div>

            <div class="test-controls" aria-label={`Test ${option.name}`}>
              <button type="button" class="right-trigger" on:click={() => runFeedback(option.id, 'right')}><span>✓</span> Run right</button>
              <button type="button" class="wrong-trigger" on:click={() => runFeedback(option.id, 'wrong')}><span>×</span> Run wrong</button>
            </div>
          </article>
        {/each}
      </div>
    </section>
  </main>

  <footer class="forge-footer">
    <div><span>MAKE THE CALL</span><h2>Choose one A<br />and one wave.</h2></div>
    <p>The foreground verdict is settled. Now choose which background motion gives that verdict the right amount of force.</p>
    <a href="#forge-top">Back to top ↑</a>
  </footer>
</section>

<style>
  :global(html[data-playground='ink-interactions']) {
    scroll-behavior: smooth;
    background: #0b0906;
  }

  :global(html[data-playground='ink-interactions'] body) {
    background:
      linear-gradient(90deg, rgba(230, 165, 40, .025) 1px, transparent 1px),
      #0b0906;
    background-size: 46px 100%;
  }

  :global(html[data-playground='ink-interactions'] body::after),
  :global(html[data-playground='ink-interactions'] .page-floor) { display: none; }

  :global(html[data-playground='ink-interactions'] .workspace-shell) {
    max-width: 1500px;
    padding-top: 1rem;
    padding-bottom: 5rem;
  }

  .interaction-lab {
    --field: #0b0906;
    --panel: #16110c;
    --raised: #211a11;
    --ivory: #f0e7d8;
    --muted: #9e9181;
    --saffron: #e6a528;
    --saffron-hi: #f0bd52;
    --vermilion: #d75b4b;
    --sage: #89b879;
    --line: rgba(240, 231, 216, .14);
    width: min(100%, 1440px);
    margin-inline: auto;
    color: var(--ivory);
    font-family: "Schibsted Grotesk", sans-serif;
  }

  .forge-hero {
    position: relative;
    overflow: hidden;
    min-height: 650px;
    border: 1px solid var(--line);
    border-radius: 0 28px 0 28px;
    background:
      linear-gradient(90deg, transparent 0 65%, rgba(230,165,40,.045) 65% 65.2%, transparent 65.2%),
      radial-gradient(circle at 74% 54%, rgba(230,165,40,.13), transparent 26rem),
      var(--panel);
    box-shadow: inset 6px 0 0 var(--vermilion), 0 28px 90px rgba(0,0,0,.34);
  }

  .forge-hero::after {
    content: 'PLAY / FAIL / LEARN / REPEAT';
    position: absolute;
    right: -5.5rem;
    bottom: 8.5rem;
    transform: rotate(-90deg);
    color: rgba(240,231,216,.14);
    font: 600 .62rem/1 "IBM Plex Mono", monospace;
    letter-spacing: .25em;
  }

  .hero-status {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    padding: 1rem 1.3rem 1rem 1.55rem;
    border-bottom: 1px solid var(--line);
    color: var(--muted);
    font: 500 .62rem/1 "IBM Plex Mono", monospace;
    letter-spacing: .12em;
  }

  .hero-status span:first-child { display: flex; align-items: center; gap: .65rem; }
  .hero-status i { width: 7px; height: 7px; border-radius: 50%; background: var(--saffron); animation: status-blink 1.8s steps(1) infinite; }

  .hero-main {
    display: grid;
    min-height: 510px;
    grid-template-columns: minmax(0, 1.2fr) minmax(230px, .38fr);
    gap: 3rem;
    align-content: center;
    align-items: end;
    padding: clamp(2rem, 6vw, 6rem);
  }

  .hero-kicker {
    grid-column: 1 / -1;
    margin: 0 0 -1rem;
    color: var(--saffron);
    font: 600 .68rem/1 "IBM Plex Mono", monospace;
    letter-spacing: .15em;
    text-transform: uppercase;
  }

  .hero-main h1 {
    margin: 0;
    font: 650 clamp(4rem, 9vw, 9rem)/.8 "Syne", sans-serif;
    letter-spacing: -.075em;
  }

  .hero-main h1 em { color: var(--saffron); font-style: normal; }
  .hero-brief { max-width: 280px; padding: 1.2rem 0 0 1.2rem; border-left: 3px solid var(--vermilion); }
  .hero-brief span { color: var(--saffron); font: 600 .6rem/1 "IBM Plex Mono", monospace; letter-spacing: .12em; }
  .hero-brief p { margin: .9rem 0 0; color: var(--muted); font-size: 1rem; line-height: 1.55; }

  .hero-nav { display: grid; grid-template-columns: repeat(2, 1fr); border-top: 1px solid var(--line); }
  .hero-nav a { display: flex; min-height: 70px; gap: .9rem; align-items: center; padding: 1rem 1.4rem; color: var(--ivory); text-decoration: none; transition: color 180ms ease, background 180ms ease; }
  .hero-nav a + a { border-left: 1px solid var(--line); }
  .hero-nav b { color: var(--saffron); font: 600 .62rem/1 "IBM Plex Mono", monospace; }
  .hero-nav a:hover { color: var(--saffron-hi); background: rgba(230,165,40,.045); }
  .hero-nav a:focus-visible { outline: 2px solid var(--saffron); outline-offset: -4px; }

  .forge-section { scroll-margin-top: 1rem; padding-top: clamp(5rem, 10vw, 10rem); }
  .section-heading { display: grid; grid-template-columns: minmax(0, 1fr) minmax(240px, .38fr); gap: 3rem; align-items: end; margin-bottom: 2rem; }
  .section-heading span { color: var(--saffron); font: 600 .63rem/1 "IBM Plex Mono", monospace; letter-spacing: .14em; }
  .section-heading h2 { margin: .8rem 0 0; font: 650 clamp(2.7rem, 5vw, 5.5rem)/.9 "Syne", sans-serif; letter-spacing: -.06em; }
  .section-heading p { margin: 0; color: var(--muted); line-height: 1.58; }
  .section-heading strong { color: var(--ivory); font-family: "IBM Plex Mono", monospace; font-size: .82em; }

  .play-grid, .feedback-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; }
  .concept { min-width: 0; overflow: hidden; border: 1px solid var(--line); background: var(--panel); }
  .concept:nth-child(2) { border-radius: 0 20px 0 20px; }
  .concept:nth-child(3) { border-top-color: rgba(230,165,40,.38); }
  .concept-head { display: grid; min-height: 140px; grid-template-columns: auto 1fr; gap: 1rem; padding: 1.25rem; border-bottom: 1px solid var(--line); }
  .concept-head > span { color: var(--vermilion); font: 700 .66rem/1 "IBM Plex Mono", monospace; }
  .concept-head h3 { margin: 0; font: 650 1.65rem/1 "Syne", sans-serif; letter-spacing: -.035em; }
  .concept-head p { margin: .7rem 0 0; color: var(--muted); font-size: .88rem; line-height: 1.5; }

  .button-bay { display: grid; min-height: 290px; place-items: center; padding: 2rem 1rem; background: linear-gradient(transparent 49.7%, rgba(230,165,40,.07) 49.7% 50.3%, transparent 50.3%), var(--field); }
  .play-button { position: relative; display: block; width: 274px; height: 106px; max-width: 100%; overflow: hidden; padding: 0; color: var(--ivory); cursor: pointer; touch-action: manipulation; -webkit-tap-highlight-color: transparent; }
  .play-button:focus-visible { outline: 3px solid var(--saffron-hi); outline-offset: 5px; }
  .play-button:active { transform: scale(.98); }

  .relay-button { border: 1px solid rgba(230,165,40,.58); border-radius: 0 16px 0 16px; background: var(--panel); box-shadow: inset 4px 0 var(--vermilion); }
  .relay-grid { position: absolute; inset: 9px; display: grid; grid-template-columns: repeat(6, 1fr); grid-template-rows: repeat(2, 1fr); gap: 4px; }
  .relay-grid i { opacity: .22; background: var(--saffron); transform: scale(.72); transition: opacity 140ms ease, transform 140ms ease; }
  .relay-button:hover .relay-grid i { opacity: calc(.25 + var(--i) * .025); transform: scale(.82); }
  .relay-button .button-copy { position: absolute; z-index: 2; inset: 25px 55px; display: flex; align-items: center; justify-content: center; gap: .65rem; color: var(--ivory); background: rgba(11,9,6,.88); font: 700 .92rem/1 "Syne", sans-serif; letter-spacing: .16em; }
  .relay-button .button-copy b { color: var(--saffron); font-size: .7rem; }
  .relay-button small { position: absolute; z-index: 3; right: 9px; bottom: 5px; color: var(--muted); font: 500 .48rem/1 "IBM Plex Mono", monospace; letter-spacing: .08em; }
  .relay-button.running .relay-grid i { animation: relay-fire 560ms cubic-bezier(.2,.8,.2,1) calc(var(--i) * 36ms) both; }
  .relay-button.running .button-copy { animation: relay-copy 900ms cubic-bezier(.2,.8,.2,1) 180ms both; }

  .aperture-button { --pointer-x: 137px; --pointer-y: 53px; border: 1px solid rgba(230,165,40,.48); border-radius: 53px; background: var(--field); }
  .aperture-button::after { content: ''; position: absolute; z-index: 1; inset: 8px; border: 1px solid rgba(240,231,216,.13); border-radius: 45px; }
  .gate { position: absolute; z-index: 2; top: 0; bottom: 0; width: 50.5%; display: grid; grid-template-columns: repeat(3, 1fr); gap: 3px; padding: 8px 3px; transition: transform 110ms cubic-bezier(.2,.8,.2,1); }
  .gate i { background: linear-gradient(180deg, var(--saffron-hi), #b97608); transition: transform 90ms ease-out, filter 120ms ease; }
  .gate-left { left: 0; transform: translateX(calc(-78% + var(--left-pull, 0px))); }
  .gate-right { right: 0; transform: translateX(calc(78% - var(--right-pull, 0px))); }
  .gate-left i:first-child, .gate-right i:last-child { background: var(--vermilion); }
  .gate-left i:nth-child(2) { transform: translateY(var(--slat-y, 0px)); }
  .gate-right i:nth-child(2) { transform: translateY(calc(0px - var(--slat-y, 0px))); }
  .aperture-response { position: absolute; z-index: 5; left: var(--pointer-x); top: var(--pointer-y); width: 19px; height: 19px; opacity: 0; transform: translate(-50%, -50%) scale(.65); border: 1px solid rgba(240,189,82,.8); border-radius: 50%; pointer-events: none; transition: opacity 100ms ease, transform 100ms ease; }
  .aperture-response::before, .aperture-response::after { content: ''; position: absolute; left: 50%; top: 50%; background: rgba(240,189,82,.46); transform: translate(-50%, -50%); }
  .aperture-response::before { width: 39px; height: 1px; }
  .aperture-response::after { width: 1px; height: 39px; }
  .aperture-response i { position: absolute; inset: 6px; border-radius: 50%; background: var(--vermilion); }
  .aperture-button.tracking .aperture-response { opacity: .88; transform: translate(-50%, -50%) scale(1); }
  .aperture-button.tracking .gate i { filter: brightness(1.08); }
  .aperture-core { position: absolute; z-index: 3; inset: 0; display: grid; place-content: center; gap: .48rem; transform: translate(var(--core-x, 0), var(--core-y, 0)); transition: transform 100ms ease-out; }
  .aperture-core b { font: 750 1rem/1 "Syne", sans-serif; letter-spacing: .18em; }
  .aperture-core i { color: var(--saffron); font: 500 .48rem/1 "IBM Plex Mono", monospace; font-style: normal; letter-spacing: .16em; }
  .corner-index { position: absolute; z-index: 4; right: 26px; bottom: 13px; color: var(--muted); font: 500 .45rem/1 "IBM Plex Mono", monospace; letter-spacing: .08em; }
  .aperture-button.running .gate-left { animation: gate-left-fire 1s cubic-bezier(.7,0,.2,1) both; }
  .aperture-button.running .gate-right { animation: gate-right-fire 1s cubic-bezier(.7,0,.2,1) both; }
  .aperture-button.running .aperture-core { animation: aperture-word 1s steps(1) both; }

  .needle-button { border: 1px solid rgba(240,231,216,.18); border-radius: 0 16px 0 16px; background: var(--raised); box-shadow: inset 0 -3px var(--vermilion); }
  .needle-dial { position: absolute; left: 14px; top: 14px; width: 76px; height: 76px; border: 1px solid var(--saffron); border-radius: 50%; background: repeating-radial-gradient(circle, transparent 0 7px, rgba(230,165,40,.16) 8px 9px); }
  .needle-dial::before { content: ''; position: absolute; inset: 19px; border: 1px solid var(--saffron); border-radius: 50%; background: var(--field); }
  .needle-dial i { position: absolute; z-index: 2; left: 50%; top: 5px; width: 2px; height: 33px; transform-origin: 50% 33px; transform: rotate(42deg); background: var(--vermilion); }
  .needle-dial b { position: absolute; z-index: 3; inset: 0; display: grid; place-items: center; color: var(--saffron); font-size: .65rem; }
  .needle-track { position: absolute; left: 104px; right: 14px; top: 30px; height: 25px; overflow: hidden; border-bottom: 1px solid rgba(230,165,40,.32); }
  .needle-track::before { content: ''; position: absolute; inset: 10px 0 auto; height: 1px; background: repeating-linear-gradient(90deg, var(--muted) 0 3px, transparent 3px 8px); opacity: .45; }
  .needle-track i { position: absolute; z-index: 2; left: 0; top: 3px; width: 9px; height: 17px; background: var(--saffron); clip-path: polygon(0 45%, 65% 45%, 100% 0, 100% 100%, 65% 55%, 0 55%); }
  .needle-track b { position: absolute; right: 0; top: 7px; width: 5px; height: 5px; border-radius: 50%; background: var(--vermilion); }
  .needle-copy { position: absolute; left: 105px; right: 15px; bottom: 13px; display: flex; justify-content: space-between; align-items: baseline; }
  .needle-copy > b { font: 750 .96rem/1 "Syne", sans-serif; letter-spacing: .16em; }
  .needle-copy small { color: var(--muted); font: 500 .45rem/1 "IBM Plex Mono", monospace; letter-spacing: .08em; }
  .needle-button:hover .needle-dial { border-color: var(--saffron-hi); }
  .needle-button.running .needle-dial { animation: dial-fire 1.1s cubic-bezier(.2,.8,.2,1) both; }
  .needle-button.running .needle-dial i { animation: needle-wind 1.1s cubic-bezier(.2,.8,.2,1) both; }
  .needle-button.running .needle-track i { animation: signal-run 900ms cubic-bezier(.15,.8,.2,1) 180ms both; }
  .needle-button.running .needle-track b { animation: receiver-hit 1.1s ease 250ms both; }

  .concept-foot { display: grid; min-height: 39px; grid-template-columns: auto 1fr auto; gap: .7rem; align-items: center; padding: .7rem 1rem; border-top: 1px solid var(--line); color: var(--muted); font: 500 .48rem/1 "IBM Plex Mono", monospace; letter-spacing: .1em; }
  .concept-foot i { height: 1px; background: var(--line); }

  .feedback-section { padding-top: clamp(7rem, 12vw, 12rem); }
  .answer-stage { position: relative; isolation: isolate; min-height: 356px; overflow: hidden; margin: 1rem; padding: 1rem; border: 1px solid rgba(230,165,40,.28); border-radius: 0 18px 0 18px; background: radial-gradient(circle at 50% 42%, rgba(230,165,40,.055), transparent 12rem), var(--field); box-shadow: inset 4px 0 0 var(--vermilion); }
  .stage-hud { position: relative; z-index: 2; display: flex; justify-content: space-between; gap: .7rem; color: var(--muted); font: 600 .54rem/1 "IBM Plex Mono", monospace; letter-spacing: .08em; }
  .stage-hud b { color: var(--saffron); }
  .answer-stage h4 { position: relative; z-index: 2; margin: 3.7rem 0 2.5rem; text-align: center; font: 650 2.8rem/1 "Syne", sans-serif; letter-spacing: -.04em; }
  .typed-word { display: block; font: 650 1.45rem/1 "Schibsted Grotesk", sans-serif; }
  .verdict { opacity: 0; }

  .razor-answer { position: relative; z-index: 2; width: min(100%, 300px); min-height: 64px; margin-inline: auto; padding: 0 .75rem 1rem; border-bottom: 2px solid var(--saffron); }
  .razor-rule { position: absolute; z-index: 3; left: 0; right: 0; bottom: -2px; height: 2px; transform-origin: left; background: var(--saffron-hi); }
  .feedback-concept .verdict { position: absolute; right: .6rem; top: .25rem; font: 700 .55rem/1 "IBM Plex Mono", monospace; letter-spacing: .08em; }
  .feedback-concept .right-verdict { color: var(--sage); }
  .feedback-concept .wrong-verdict { color: var(--vermilion); }
  .feedback-concept .answer-stage.right .razor-rule { animation: razor-lock 760ms cubic-bezier(.2,.8,.2,1) both; }
  .feedback-concept .answer-stage.right .typed-word { animation: word-seat 620ms cubic-bezier(.2,.9,.2,1) 160ms both; }
  .feedback-concept .answer-stage.right .right-verdict { animation: verdict-in 430ms steps(4) 540ms both; }
  .feedback-concept .answer-stage.wrong .razor-rule { background: var(--vermilion); animation: razor-cut 620ms cubic-bezier(.8,0,.2,1) both; }
  .feedback-concept .answer-stage.wrong .typed-word { animation: word-shear 620ms cubic-bezier(.8,0,.2,1) both; }
  .feedback-concept .answer-stage.wrong .wrong-verdict { animation: verdict-in 430ms steps(4) 500ms both; }

  .background-wave { position: absolute; z-index: 0; inset: 43px 0 55px; overflow: hidden; pointer-events: none; }

  .reed-wave { display: flex; align-items: center; justify-content: center; gap: 6px; padding-inline: 22px; mask-image: linear-gradient(90deg, transparent, #000 12%, #000 88%, transparent); }
  .reed-wave i { width: 2px; height: var(--height); flex: 1 1 2px; max-width: 3px; opacity: 0; background: var(--saffron); transform: scaleY(.08); }
  .reeds .answer-stage.right .reed-wave i { animation: reeds-right 1s cubic-bezier(.2,.8,.2,1) calc(var(--distance) * 28ms) both; }
  .reeds .answer-stage.wrong .reed-wave i { animation: reeds-wrong 780ms cubic-bezier(.7,0,.2,1) calc(var(--i) * 14ms) both; }

  .contour-wave { inset: 40px 0 52px; overflow: visible; }
  .contour-wave i { position: absolute; left: 50%; top: 57%; width: var(--contour-width); height: var(--contour-height); opacity: 0; transform: translate(-50%, -50%) scale(.45); border: 1px solid var(--saffron); border-radius: 0 20px 0 20px; }
  .contours .answer-stage.right .contour-wave i { animation: contours-right 1.05s cubic-bezier(.2,.8,.2,1) calc(var(--i) * 62ms) both; }
  .contours .answer-stage.wrong .contour-wave i { animation: contours-wrong 820ms cubic-bezier(.7,0,.2,1) calc(var(--i) * 38ms) both; }

  .horizon-wave { inset: 46px -16% 58px; display: grid; align-content: center; gap: 4px; transform: rotate(-3deg); }
  .horizon-wave i { display: block; height: 17px; opacity: 0; background: linear-gradient(90deg, transparent, rgba(230,165,40,.72) 16% 84%, transparent); clip-path: polygon(0 25%, 12% 5%, 28% 30%, 43% 0, 62% 35%, 78% 8%, 100% 28%, 100% 78%, 83% 95%, 66% 68%, 45% 100%, 23% 66%, 0 90%); }
  .horizons .answer-stage.right .horizon-wave i { animation: horizons-right 1.05s cubic-bezier(.2,.8,.2,1) calc(var(--i) * 58ms) both; }
  .horizons .answer-stage.wrong .horizon-wave i { animation: horizons-wrong 820ms cubic-bezier(.75,0,.2,1) calc(var(--i) * 34ms) both; }

  .stage-feedback { position: absolute; z-index: 2; right: 1rem; bottom: 1rem; left: 1.35rem; min-height: 24px; padding-top: .75rem; border-top: 1px solid var(--line); color: var(--muted); font-size: .72rem; }
  .stage-feedback span { display: none; }
  .answer-stage.right .right-message, .answer-stage.wrong .wrong-message { display: block; animation: message-in 420ms ease 600ms both; }
  .answer-stage.right .right-message { color: var(--sage); }
  .answer-stage.wrong .wrong-message { color: #dc7b6e; }

  .test-controls { display: grid; grid-template-columns: 1fr 1fr; border-top: 1px solid var(--line); }
  .test-controls button { display: flex; min-height: 58px; align-items: center; justify-content: center; gap: .55rem; border: 0; color: var(--ivory); background: transparent; cursor: pointer; font: 650 .76rem/1 "Schibsted Grotesk", sans-serif; transition: background 150ms ease, color 150ms ease; }
  .test-controls button + button { border-left: 1px solid var(--line); }
  .test-controls span { font-family: "IBM Plex Mono", monospace; }
  .right-trigger:hover { color: var(--field); background: var(--sage); }
  .wrong-trigger:hover { color: var(--field); background: var(--vermilion); }
  .test-controls button:focus-visible { outline: 2px solid var(--saffron); outline-offset: -4px; }

  .forge-footer { display: grid; grid-template-columns: minmax(0, 1fr) minmax(240px, .38fr); gap: 3rem; align-items: end; margin-top: clamp(7rem, 13vw, 13rem); padding: clamp(2rem, 5vw, 5rem); border: 1px solid var(--line); border-radius: 0 28px 0 28px; background: linear-gradient(125deg, rgba(230,165,40,.09), transparent 42%), var(--panel); box-shadow: inset 6px 0 var(--vermilion); }
  .forge-footer span { color: var(--saffron); font: 600 .62rem/1 "IBM Plex Mono", monospace; letter-spacing: .14em; }
  .forge-footer h2 { margin: .9rem 0 0; font: 650 clamp(3rem, 6vw, 6.5rem)/.84 "Syne", sans-serif; letter-spacing: -.065em; }
  .forge-footer p { margin: 0; color: var(--muted); line-height: 1.6; }
  .forge-footer a { grid-column: 2; color: var(--ivory); font: 500 .58rem/1 "IBM Plex Mono", monospace; letter-spacing: .08em; text-decoration: none; }

  @keyframes status-blink { 0%, 58% { opacity: 1; } 59%, 100% { opacity: .25; } }
  @keyframes relay-fire { 0% { opacity: .18; transform: scale(.72); } 45% { opacity: 1; transform: scale(1); background: var(--saffron-hi); } 100% { opacity: .3; transform: scale(.82); } }
  @keyframes relay-copy { 0%, 100% { color: var(--ivory); background: rgba(11,9,6,.88); } 35%, 58% { color: var(--field); background: var(--saffron-hi); letter-spacing: .24em; } }
  @keyframes gate-left-fire { 0%, 100% { transform: translateX(-78%); } 38%, 58% { transform: translateX(0); } }
  @keyframes gate-right-fire { 0%, 100% { transform: translateX(78%); } 38%, 58% { transform: translateX(0); } }
  @keyframes aperture-word { 0%, 37%, 60%, 100% { opacity: 1; } 38%, 59% { opacity: 0; } }
  @keyframes dial-fire { 0% { transform: rotate(0); } 65% { transform: rotate(300deg); } 100% { transform: rotate(360deg); } }
  @keyframes needle-wind { 0% { transform: rotate(42deg); } 38% { transform: rotate(-34deg); } 66%, 100% { transform: rotate(138deg); } }
  @keyframes signal-run { 0% { left: 0; transform: scaleX(1); } 72% { left: calc(100% - 9px); transform: scaleX(2.4); } 100% { left: calc(100% - 9px); transform: scaleX(.4); opacity: 0; } }
  @keyframes receiver-hit { 0%, 52%, 100% { transform: scale(1); box-shadow: none; } 70% { transform: scale(2.7); box-shadow: 0 0 0 7px rgba(215,91,75,.18); } }
  @keyframes razor-lock { 0% { transform: scaleX(0); } 48% { transform: scaleX(1); height: 2px; } 70% { transform: scaleX(1); height: 8px; background: var(--sage); } 100% { transform: scaleX(1); height: 2px; background: var(--sage); } }
  @keyframes razor-cut { 0% { transform: translateX(105%) scaleX(.1); } 52% { transform: translateX(0) scaleX(1); height: 4px; } 100% { transform: translateX(-8%) scaleX(.84); height: 2px; } }
  @keyframes word-seat { 0% { transform: translateY(0); } 48% { transform: translateY(-7px); color: var(--saffron-hi); } 100% { transform: translateY(-3px); color: var(--ivory); } }
  @keyframes word-shear { 0%, 100% { transform: translateX(0) skewX(0); } 35% { transform: translateX(-6px) skewX(-12deg); color: var(--vermilion); } 56% { transform: translateX(5px) skewX(9deg); color: var(--vermilion); } }
  @keyframes verdict-in { 0% { opacity: 0; transform: translateY(4px); } 100% { opacity: 1; transform: translateY(0); } }
  @keyframes reeds-right {
    0% { opacity: 0; transform: scaleY(.08); background: var(--saffron); }
    38% { opacity: .32; transform: scaleY(1.2); background: var(--saffron-hi); }
    66% { opacity: .2; transform: scaleY(.72); background: var(--sage); }
    100% { opacity: 0; transform: scaleY(.18); background: var(--sage); }
  }
  @keyframes reeds-wrong {
    0% { opacity: 0; transform: translateX(-12px) scaleY(.18) skewX(0); background: var(--vermilion); }
    34% { opacity: .34; transform: translateX(6px) scaleY(1.15) skewX(-24deg); background: var(--vermilion); }
    58% { opacity: .22; transform: translateX(-4px) scaleY(.65) skewX(18deg); background: #b9473c; }
    100% { opacity: 0; transform: translateX(14px) scaleY(.24) skewX(-9deg); background: #b9473c; }
  }
  @keyframes contours-right {
    0% { opacity: 0; transform: translate(-50%, -50%) scale(.45); border-color: var(--saffron); }
    34% { opacity: .24; transform: translate(-50%, -50%) scale(.7); border-color: var(--saffron-hi); }
    70% { opacity: .15; transform: translate(-50%, -50%) scale(1); border-color: var(--sage); }
    100% { opacity: 0; transform: translate(-50%, -50%) scale(1.15); border-color: var(--sage); }
  }
  @keyframes contours-wrong {
    0% { opacity: 0; transform: translate(-50%, -50%) scale(1.12) rotate(0); border-color: var(--vermilion); }
    42% { opacity: .28; transform: translate(calc(-50% + var(--offset)), calc(-50% + 7px)) scale(.62) rotate(-3deg); border-color: var(--vermilion); }
    68% { opacity: .18; transform: translate(calc(-50% - var(--offset)), calc(-50% - 4px)) scale(.4) rotate(2deg); border-color: #b9473c; }
    100% { opacity: 0; transform: translate(-50%, -50%) scale(.16) rotate(-4deg); border-color: #b9473c; }
  }
  @keyframes horizons-right {
    0% { opacity: 0; transform: translateX(-86%) scaleX(.7); }
    44% { opacity: .22; transform: translateX(0) scaleX(1); }
    68% { opacity: .14; transform: translateX(18%) scaleX(.92); background-color: var(--sage); }
    100% { opacity: 0; transform: translateX(86%) scaleX(.7); background-color: var(--sage); }
  }
  @keyframes horizons-wrong {
    0% { opacity: 0; transform: translateX(var(--from)) scaleX(.6) skewX(-18deg); background: var(--vermilion); }
    42% { opacity: .28; transform: translateX(0) scaleX(1) skewX(12deg); background: var(--vermilion); }
    62% { opacity: .2; transform: translateX(0) scaleX(.7) skewX(-20deg); background: #b9473c; }
    100% { opacity: 0; transform: translateX(var(--to)) scaleX(.35) skewX(24deg); background: #b9473c; }
  }
  @keyframes message-in { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

  @media (max-width: 1100px) {
    .play-grid, .feedback-grid { grid-template-columns: 1fr; }
    .concept { display: grid; grid-template-columns: minmax(240px, .48fr) 1fr; }
    .concept-head { min-height: 0; border-bottom: 0; border-right: 1px solid var(--line); }
    .button-bay { min-height: 250px; }
    .concept-foot, .test-controls { grid-column: 1 / -1; }
    .answer-stage { min-height: 325px; }
  }

  @media (max-width: 700px) {
    :global(html[data-playground='ink-interactions'] .workspace-shell) { padding: .55rem; padding-top: .55rem; }
    .forge-hero { min-height: auto; }
    .hero-status span:last-child { display: none; }
    .hero-main { min-height: 510px; grid-template-columns: 1fr; gap: 2rem; padding: 2.4rem 1.4rem; }
    .hero-kicker { margin-bottom: -1rem; }
    .hero-main h1 { font-size: clamp(3.9rem, 18vw, 6.5rem); }
    .hero-brief { max-width: 250px; }
    .section-heading { grid-template-columns: 1fr; gap: 1.2rem; }
    .concept { display: block; }
    .concept-head { min-height: 130px; border-right: 0; border-bottom: 1px solid var(--line); }
    .button-bay { min-height: 245px; padding-inline: .7rem; }
    .answer-stage { min-height: 340px; margin: .55rem; }
    .answer-stage h4 { margin-top: 3.25rem; }
    .forge-footer { grid-template-columns: 1fr; padding: 2rem 1.4rem; }
    .forge-footer a { grid-column: 1; }
  }

  @media (prefers-reduced-motion: reduce) {
    :global(html[data-playground='ink-interactions']) { scroll-behavior: auto; }
    .hero-status i, .relay-button.running *, .aperture-button.running *, .needle-button.running *, .answer-stage *, .answer-stage { animation-duration: 1ms !important; animation-delay: 0ms !important; }
    .gate, .test-controls button, .hero-nav a { transition: none; }
  }
</style>
