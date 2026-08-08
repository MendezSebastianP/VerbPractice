<script lang="ts">
  import { onDestroy, tick } from 'svelte';

  type Screen = 'home' | 'setup' | 'run' | 'clear';
  type Verdict = 'idle' | 'correct' | 'retry' | 'hint';

  const deck = [
    { source: 'only', answer: 'solo', hint: 'Just one; no more than this.' },
    { source: 'never', answer: 'nunca', hint: 'Not at any time.' },
    { source: 'life', answer: 'vida', hint: 'The time between birth and death.' },
  ];

  let screen: Screen = 'home';
  let phase: 'ready' | 'leaving' | 'entering' = 'ready';
  let runLength = 10;
  let source = 'EN';
  let target = 'ES';
  let focus = 'Priority';
  let index = 0;
  let answer = '';
  let verdict: Verdict = 'idle';
  let message = '';
  let score = 50;
  let combo = 3;
  let answerInput: HTMLInputElement | null = null;
  const timers: ReturnType<typeof setTimeout>[] = [];
  let navigationTimer: ReturnType<typeof setTimeout> | null = null;
  let settleTimer: ReturnType<typeof setTimeout> | null = null;
  const now = new Date();
  const todayLabel = new Intl.DateTimeFormat(undefined, { day: '2-digit', month: 'short', year: 'numeric' }).format(now).toLocaleUpperCase();
  const timeLabel = new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit' }).format(now);

  $: card = deck[index % deck.length];

  function later(callback: () => void, delay: number): void {
    timers.push(setTimeout(callback, delay));
  }

  function canAutoFocus(): boolean {
    return window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  }

  function resetRun(): void {
    index = 0;
    answer = '';
    verdict = 'idle';
    message = '';
    score = 50;
    combo = 3;
  }

  function go(next: Screen): void {
    if (next === screen && phase === 'ready') return;
    if (navigationTimer) clearTimeout(navigationTimer);
    if (settleTimer) clearTimeout(settleTimer);
    phase = 'leaving';
    navigationTimer = setTimeout(() => {
      screen = next;
      if (next === 'run') resetRun();
      phase = 'entering';
      void tick().then(() => {
        if (next === 'run' && canAutoFocus()) answerInput?.focus();
      });
      settleTimer = setTimeout(() => (phase = 'ready'), 340);
    }, 210);
  }

  function swapRoute(): void {
    const previous = source;
    source = target;
    target = previous;
  }

  function submit(): void {
    if (!answer.trim() || verdict === 'correct') return;
    if (answer.trim().toLocaleLowerCase() === card.answer) {
      verdict = 'correct';
      message = `Impression accepted · ${card.source} / ${card.answer}`;
      score += 120;
      combo += 1;
      later(() => {
        if (index >= deck.length - 1) {
          go('clear');
          return;
        }
        index += 1;
        answer = '';
        verdict = 'idle';
        message = '';
        void tick().then(() => answerInput?.focus());
      }, 660);
      return;
    }

    verdict = 'retry';
    message = 'Carriage refused · check the spelling and strike again.';
    combo = 0;
    later(() => {
      if (verdict === 'retry') verdict = 'idle';
    }, 500);
  }

  function hint(): void {
    verdict = 'hint';
    message = `Proof note · ${card.hint}`;
    answerInput?.focus();
  }

  function reveal(): void {
    answer = card.answer;
    verdict = 'hint';
    message = `Filed for review · ${card.source} / ${card.answer}`;
    answerInput?.focus();
  }

  onDestroy(() => {
    timers.forEach(clearTimeout);
    if (navigationTimer) clearTimeout(navigationTimer);
    if (settleTimer) clearTimeout(settleTimer);
  });
</script>

<div class="cabinet-frame" data-phase={phase}>
  <div class="carriage-sweep" aria-hidden="true"><span></span><i></i></div>

  <header class="cabinet-topbar">
    <button class="cabinet-brand" type="button" aria-label="Cabinet home" on:click={() => go('home')}>
      <span aria-hidden="true">VP</span>
      <strong>Cabinet 73</strong>
    </button>

    <nav class="cabinet-nav" aria-label="Cabinet prototype navigation">
      <button class:key-on={screen === 'home'} type="button" aria-current={screen === 'home' ? 'page' : undefined} on:click={() => go('home')}>Home</button>
      <button class:key-on={screen === 'setup'} type="button" aria-current={screen === 'setup' ? 'page' : undefined} on:click={() => go('setup')}>Words</button>
      <button type="button" disabled aria-label="Verbs — outside this prototype">Verbs</button>
      <button type="button" disabled aria-label="Add word — outside this prototype">Add</button>
    </nav>

    <div class="score-reels" aria-label="Player status">
      <span><small>Streak</small><strong>01</strong></span>
      <span><small>Level</small><strong>1</strong></span>
      <span><small>Score</small><strong>0050</strong></span>
    </div>
  </header>

  <div class="cabinet-screen">
    {#key screen}
      {#if screen === 'home'}
        <section class="cabinet-view cabinet-home" aria-labelledby="cabinet-home-title">
          <div class="cabinet-label-row">
            <span>Machine ready</span>
            <span>Deck 04 / weighted recall</span>
            <span>{todayLabel}</span>
          </div>

          <div class="cabinet-workspace">
            <article class="relay-console">
              <div class="console-head">
                <div>
                  <p>Current programme · {source} → {target}</p>
                  <h2 id="cabinet-home-title">Word relay</h2>
                </div>
                <div class="mechanical-count"><small>Words filed</small><strong>1 4 6</strong></div>
              </div>

              <div class="next-ticket">
                <div class="ticket-copy">
                  <span>Next feed / priority stock</span>
                  <strong>10 cards</strong>
                  <p>Built from nine weak translations and one fresh arrival.</p>
                </div>
                <div class="ticket-route"><span>{source}</span><i>to</i><span>{target}</span></div>
              </div>

              <div class="pressure-strip" aria-label="Words under pressure">
                <span>Pressure tray</span>
                <button type="button" on:click={() => go('setup')}><strong>only</strong><small>solo</small></button>
                <button type="button" on:click={() => go('setup')}><strong>part</strong><small>parte</small></button>
                <button type="button" on:click={() => go('setup')}><strong>never</strong><small>nunca</small></button>
              </div>

              <div class="console-launch">
                <div><span>Last relay</span><strong>82% · combo ×7</strong></div>
                <button class="lever-button" type="button" on:click={() => go('setup')}>
                  <span><small>Load</small><strong>Next relay</strong></span>
                  <i aria-hidden="true"></i>
                </button>
              </div>
            </article>

            <aside class="telemetry-panel" aria-label="Today’s practice telemetry">
              <div class="telemetry-head"><span>Today</span><strong>{timeLabel}</strong></div>
              <div class="telemetry-dial"><span><strong>68</strong><small>%</small></span><p>Deck pressure</p></div>
              <ul>
                <li><span>Accuracy</span><strong>84%</strong></li>
                <li><span>Best combo</span><strong>×14</strong></li>
                <li><span>Cards due</span><strong>09</strong></li>
              </ul>
              <button type="button" on:click={() => go('clear')}>Print activity slip</button>
            </aside>
          </div>

          <footer class="cabinet-statusbar">
            <span><i class="ready-dot"></i> Relay motor online</span>
            <span>One primary action. No animated wallpaper.</span>
            <span><kbd>Enter</kbd> load relay</span>
          </footer>
        </section>
      {:else if screen === 'setup'}
        <section class="cabinet-view setup-bench" aria-labelledby="cabinet-setup-title">
          <header class="bench-heading">
            <div><p>Programme setup / Word relay</p><h2 id="cabinet-setup-title">Set the machine.</h2></div>
            <span>Three banks. One lever.</span>
          </header>

          <div class="setup-workbench">
            <div class="control-banks">
              <fieldset class="control-bank">
                <legend><span>01</span> Run length</legend>
                <p>Choose the amount of paper, not a fake difficulty.</p>
                <div class="bank-keys">
                  {#each [5, 10, 20] as option}
                    <button class:bank-key-on={runLength === option} type="button" aria-pressed={runLength === option} on:click={() => (runLength = option)}>
                      <strong>{option}</strong><small>{option === 5 ? 'Quick' : option === 10 ? 'Standard' : 'Long run'}</small>
                    </button>
                  {/each}
                </div>
              </fieldset>

              <fieldset class="control-bank">
                <legend><span>02</span> Route reel</legend>
                <p>The card feeds from prompt to answer.</p>
                <button class="route-reel" type="button" aria-label="Swap language route" on:click={swapRoute}>
                  <span><small>Prompt</small><strong>{source}</strong></span>
                  <i aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 8h12M14 5l3 3-3 3M19 16H7M10 13l-3 3 3 3" /></svg></i>
                  <span><small>Answer</small><strong>{target}</strong></span>
                </button>
              </fieldset>

              <fieldset class="control-bank">
                <legend><span>03</span> Card stock</legend>
                <p>Priority is the useful default; alternatives stay one tap away.</p>
                <div class="stock-keys" role="group" aria-label="Card stock">
                  {#each ['Priority', 'Everything', 'Travel set'] as option}
                    <button class:stock-on={focus === option} type="button" aria-pressed={focus === option} on:click={() => (focus = option)}>{option}</button>
                  {/each}
                </div>
              </fieldset>
            </div>

            <aside class="preview-ticket" aria-label="Run summary">
              <div class="ticket-teeth" aria-hidden="true"></div>
              <span class="ticket-overline">Run order / VP–073</span>
              <h3>Word relay</h3>
              <dl>
                <div><dt>Route</dt><dd>{source} → {target}</dd></div>
                <div><dt>Cards</dt><dd>{runLength}</dd></div>
                <div><dt>Stock</dt><dd>{focus}</dd></div>
                <div><dt>Expected</dt><dd>{runLength <= 5 ? '2 min' : runLength <= 10 ? '4 min' : '8 min'}</dd></div>
              </dl>
              <div class="ticket-barcode" aria-hidden="true"></div>
              <button class="start-lever" type="button" on:click={() => go('run')}>
                <span><small>Ready</small><strong>Pull to start</strong></span>
                <i aria-hidden="true"><b></b></i>
              </button>
              <p><kbd>Enter</kbd> starts the run</p>
            </aside>
          </div>
        </section>
      {:else if screen === 'run'}
        <section class="cabinet-view live-machine" aria-labelledby="cabinet-prompt">
          <header class="machine-readout">
            <div><span>Run</span><strong>{String(index + 1).padStart(2, '0')} / {String(deck.length).padStart(2, '0')}</strong></div>
            <div class="run-route"><span>{source}</span><i>→</i><span>{target}</span></div>
            <div><span>Combo</span><strong>×{combo}</strong></div>
            <div><span>Score</span><strong>{String(score).padStart(4, '0')}</strong></div>
          </header>

          <div class="machine-stage">
            <div class="paper-bay">
              <div class="roller" aria-hidden="true"><i></i><i></i></div>
              <article class:paper-correct={verdict === 'correct'} class:paper-retry={verdict === 'retry'} class="prompt-ticket">
                <div class="ticket-teeth" aria-hidden="true"></div>
                <div class="paper-meta"><span>Card {String(index + 1).padStart(2, '0')}</span><span>{source} prompt</span></div>
                <p>Translate and strike the carriage</p>
                <h2 id="cabinet-prompt">{card.source}</h2>

                <form on:submit|preventDefault={submit}>
                  <label for="cabinet-answer">{target} impression</label>
                  <div class="answer-carriage">
                    <span class="carriage-stop" aria-hidden="true"></span>
                    <input id="cabinet-answer" name="cabinet-answer" bind:this={answerInput} bind:value={answer} autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="e.g. solo…" />
                    <button type="submit"><span>Strike</span><kbd>↵</kbd></button>
                    <i class="carriage-head" aria-hidden="true"></i>
                  </div>
                </form>

                <div class={`proof-message ${verdict}`} role="status" aria-live="polite">{message || 'The carriage is ready.'}</div>
                {#if verdict === 'correct'}<div class="accepted-stamp" aria-hidden="true">ACCEPTED</div>{/if}
                {#if verdict === 'retry'}<div class="proof-slash" aria-hidden="true"></div>{/if}
              </article>
            </div>

            <aside class="run-telemetry">
              <div class="notch-head"><span>Card feed</span><strong>{Math.round(((index + 1) / deck.length) * 100)}%</strong></div>
              <div class="feed-notches" aria-label={`${index + 1} of ${deck.length} cards`}>
                {#each deck as _, i}
                  <span class:printed={i < index} class:printing={i === index}><b>{String(i + 1).padStart(2, '0')}</b></span>
                {/each}
              </div>
              <div class="run-actions">
                <button type="button" on:click={hint}><kbd>F2</kbd><span><strong>Proof note</strong><small>Show a clue</small></span></button>
                <button type="button" on:click={reveal}><kbd>Alt ↵</kbd><span><strong>File answer</strong><small>Reveal without scoring</small></span></button>
                <button type="button" on:click={() => go('setup')}><kbd>Esc</kbd><span><strong>Stop motor</strong><small>End this run</small></span></button>
              </div>
            </aside>
          </div>
        </section>
      {:else}
        <section class="cabinet-view result-bay" aria-labelledby="cabinet-clear-title">
          <div class="result-machine">
            <div class="result-slot" aria-hidden="true"><span></span></div>
            <article class="result-ticket">
              <div class="ticket-teeth" aria-hidden="true"></div>
              <p>VerbPractice · result slip</p>
              <h2 id="cabinet-clear-title">Run filed.</h2>
              <div class="result-grade" aria-label="Grade A"><span>A</span><small>Clean copy</small></div>
              <dl>
                <div><dt>Accuracy</dt><dd>88%</dd></div>
                <div><dt>Best combo</dt><dd>×{combo}</dd></div>
                <div><dt>Cards printed</dt><dd>{deck.length}</dd></div>
                <div><dt>Score filed</dt><dd>+{score}</dd></div>
              </dl>
              <div class="review-note"><span>Return tray</span><strong>never · nunca</strong><small>Review once tomorrow.</small></div>
              <div class="ticket-barcode" aria-hidden="true"></div>
            </article>
          </div>

          <div class="result-copy">
            <p>Relay complete / personal record</p>
            <h3>One stamp is enough.</h3>
            <span>The result arrives as a useful receipt: score, one thing to review, and two obvious exits.</span>
            <div>
              <button class="cabinet-primary" type="button" on:click={() => go('run')}>Print another run</button>
              <button class="cabinet-secondary" type="button" on:click={() => go('home')}>Return home</button>
            </div>
          </div>
        </section>
      {/if}
    {/key}
  </div>
</div>

<style>
  .cabinet-frame {
    --c-petrol: #12363b;
    --c-petrol-hi: #1c4c52;
    --c-carbon: #101617;
    --c-paper: #f4e7c5;
    --c-paper-hi: #fff7df;
    --c-orange: #ff6647;
    --c-amber: #f5c64e;
    --c-mint: #63c6a8;
    --c-red: #cf3d32;
    position: relative;
    min-height: 720px;
    overflow: hidden;
    border: 6px solid var(--c-carbon);
    border-radius: 16px;
    color: var(--c-carbon);
    background: var(--c-petrol);
    box-shadow: 0 30px 80px rgba(0, 0, 0, 0.34), inset 0 0 0 2px rgba(244, 231, 197, 0.14);
    font-family: "Space Grotesk", sans-serif;
    isolation: isolate;
  }

  button,
  input { touch-action: manipulation; -webkit-tap-highlight-color: transparent; }
  button { font: inherit; }
  button:focus-visible,
  input:focus-visible { outline: 3px solid var(--c-amber); outline-offset: 3px; }

  .carriage-sweep {
    position: absolute;
    inset: 0;
    z-index: 30;
    display: flex;
    width: 46px;
    background: var(--c-carbon);
    box-shadow: 8px 0 0 var(--c-orange);
    transform: translateX(-80px);
    pointer-events: none;
  }
  .carriage-sweep span { width: 12px; margin: 10px auto; background: repeating-linear-gradient(180deg, var(--c-amber) 0 8px, transparent 8px 16px); }
  .carriage-sweep i { position: absolute; top: 50%; right: -18px; width: 32px; height: 32px; border: 5px solid var(--c-carbon); border-radius: 50%; background: var(--c-orange); }
  [data-phase='leaving'] .carriage-sweep { animation: sweep-in 220ms cubic-bezier(0.45, 0, 0.55, 1) both; }
  [data-phase='entering'] .carriage-sweep { animation: sweep-out 320ms cubic-bezier(0.2, 0.8, 0.3, 1) both; }
  @keyframes sweep-in { from { transform: translateX(-80px); } to { transform: translateX(calc(100vw + 80px)); } }
  @keyframes sweep-out { from { transform: translateX(-80px); } to { transform: translateX(calc(100vw + 80px)); } }

  .cabinet-topbar {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 1.4rem;
    align-items: stretch;
    min-height: 72px;
    border-bottom: 5px solid var(--c-carbon);
    background: var(--c-paper);
  }

  .cabinet-brand {
    display: flex;
    gap: 0.6rem;
    align-items: center;
    padding: 0.6rem 1rem;
    border: 0;
    border-right: 3px solid var(--c-carbon);
    color: var(--c-carbon);
    background: transparent;
  }
  .cabinet-brand > span { display: grid; width: 39px; height: 39px; place-items: center; border: 3px solid var(--c-carbon); border-radius: 5px; color: var(--c-paper); background: var(--c-petrol); font: 800 0.75rem/1 "IBM Plex Mono", monospace; box-shadow: 3px 3px 0 var(--c-orange); }
  .cabinet-brand strong { font-size: 0.92rem; font-weight: 850; letter-spacing: -0.04em; text-transform: uppercase; }

  .cabinet-nav { display: flex; gap: 0.45rem; align-items: center; }
  .cabinet-nav button {
    min-width: 74px;
    min-height: 42px;
    padding: 0.55rem 0.75rem;
    border: 2px solid var(--c-carbon);
    border-radius: 5px;
    color: var(--c-carbon);
    background: var(--c-paper-hi);
    box-shadow: 0 4px 0 var(--c-carbon);
    font-size: 0.72rem;
    font-weight: 750;
    text-transform: uppercase;
    transition: transform 90ms ease, box-shadow 90ms ease, background 120ms ease;
  }
  .cabinet-nav button:hover,
  .cabinet-nav .key-on { background: var(--c-amber); }
  .cabinet-nav button:active { transform: translateY(3px); box-shadow: 0 1px 0 var(--c-carbon); }
  .cabinet-nav button:disabled { opacity: 0.48; cursor: not-allowed; box-shadow: none; }

  .score-reels { display: flex; border-left: 3px solid var(--c-carbon); background: var(--c-carbon); }
  .score-reels span { display: grid; min-width: 68px; gap: 0.2rem; align-content: center; padding: 0.55rem 0.65rem; border-right: 1px solid rgba(244, 231, 197, 0.2); color: var(--c-paper); }
  .score-reels small { color: rgba(244, 231, 197, 0.6); font: 500 0.52rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .score-reels strong { color: var(--c-amber); font: 700 0.95rem/1 "IBM Plex Mono", monospace; font-variant-numeric: tabular-nums; letter-spacing: 0.08em; }

  .cabinet-screen { min-height: 638px; }
  .cabinet-view { min-height: 638px; animation: cabinet-view-in 340ms cubic-bezier(0.2, 0.85, 0.3, 1) both; }
  @keyframes cabinet-view-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

  .cabinet-home { display: flex; flex-direction: column; padding: 1.2rem; }
  .cabinet-label-row { display: flex; justify-content: space-between; gap: 1rem; padding: 0 0.25rem 0.8rem; color: rgba(244, 231, 197, 0.7); font: 550 0.58rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .cabinet-workspace { display: grid; flex: 1; grid-template-columns: minmax(0, 1fr) 260px; gap: 1rem; }

  .relay-console { display: flex; min-width: 0; flex-direction: column; overflow: hidden; border: 4px solid var(--c-carbon); border-radius: 8px; background: var(--c-paper); box-shadow: 8px 8px 0 rgba(16, 22, 23, 0.34); }
  .console-head { display: flex; justify-content: space-between; gap: 1rem; align-items: center; padding: 1.2rem; border-bottom: 3px solid var(--c-carbon); }
  .console-head p,
  .bench-heading p,
  .result-copy > p { margin: 0 0 0.3rem; font: 650 0.62rem/1 "IBM Plex Mono", monospace; letter-spacing: 0.08em; text-transform: uppercase; }
  .console-head h2,
  .bench-heading h2 { margin: 0; font-size: clamp(2.2rem, 5vw, 4.8rem); font-weight: 900; line-height: 0.9; letter-spacing: -0.075em; text-wrap: balance; text-transform: uppercase; }
  .mechanical-count { display: grid; gap: 0.25rem; justify-items: end; }
  .mechanical-count small { font: 500 0.55rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .mechanical-count strong { padding: 0.45rem 0.55rem; border: 3px solid var(--c-carbon); border-radius: 4px; color: var(--c-amber); background: var(--c-carbon); font: 700 1.1rem/1 "IBM Plex Mono", monospace; font-variant-numeric: tabular-nums; letter-spacing: 0.24em; }

  .next-ticket { display: grid; grid-template-columns: 1fr auto; gap: 1rem; align-items: center; margin: 1.2rem; padding: 1.2rem; border: 2px dashed var(--c-carbon); background: var(--c-paper-hi); box-shadow: 5px 5px 0 rgba(16, 22, 23, 0.12); }
  .ticket-copy { display: grid; gap: 0.3rem; }
  .ticket-copy > span,
  .ticket-overline { font: 650 0.58rem/1 "IBM Plex Mono", monospace; letter-spacing: 0.07em; text-transform: uppercase; }
  .ticket-copy strong { font-size: clamp(2rem, 4vw, 3.8rem); line-height: 0.95; letter-spacing: -0.065em; }
  .ticket-copy p { max-width: 32rem; margin: 0; color: rgba(16, 22, 23, 0.66); font-size: 0.82rem; }
  .ticket-route { display: flex; align-items: center; gap: 0.55rem; }
  .ticket-route span { display: grid; width: 54px; height: 54px; place-items: center; border: 3px solid var(--c-carbon); background: var(--c-amber); font: 750 1rem/1 "IBM Plex Mono", monospace; }
  .ticket-route i { font: 650 0.6rem/1 "IBM Plex Mono", monospace; font-style: normal; text-transform: uppercase; }

  .pressure-strip { display: grid; grid-template-columns: auto repeat(3, 1fr); gap: 0.55rem; align-items: stretch; padding: 0 1.2rem 1.2rem; }
  .pressure-strip > span { display: grid; min-width: 86px; align-content: center; font: 650 0.58rem/1.4 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .pressure-strip button { display: flex; min-height: 58px; justify-content: space-between; gap: 0.5rem; align-items: center; padding: 0.65rem; border: 2px solid var(--c-carbon); border-radius: 4px; color: var(--c-carbon); background: transparent; text-align: left; transition: background 120ms ease, transform 90ms ease; }
  .pressure-strip button:hover { background: var(--c-amber); transform: translateY(-2px); }
  .pressure-strip button strong { font-size: 0.86rem; }
  .pressure-strip button small { color: rgba(16, 22, 23, 0.58); font: 500 0.6rem/1 "IBM Plex Mono", monospace; }

  .console-launch { display: flex; justify-content: space-between; gap: 1rem; align-items: center; margin-top: auto; padding: 0.85rem 1rem 0.85rem 1.2rem; border-top: 3px solid var(--c-carbon); background: var(--c-mint); }
  .console-launch > div { display: grid; gap: 0.2rem; }
  .console-launch > div span { font: 650 0.55rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .console-launch > div strong { font-size: 0.92rem; }
  .lever-button { display: grid; grid-template-columns: 1fr auto; gap: 1rem; align-items: center; min-width: 210px; min-height: 62px; padding: 0.6rem 0.65rem 0.6rem 1rem; border: 3px solid var(--c-carbon); border-radius: 5px; color: var(--c-paper-hi); background: var(--c-carbon); box-shadow: 4px 4px 0 var(--c-orange); text-align: left; transition: transform 100ms ease, box-shadow 100ms ease; }
  .lever-button:hover { transform: translate(-2px, -2px); box-shadow: 7px 7px 0 var(--c-orange); }
  .lever-button:active { transform: translate(3px, 3px); box-shadow: 1px 1px 0 var(--c-orange); }
  .lever-button > span { display: grid; gap: 0.15rem; }
  .lever-button small { color: rgba(244, 231, 197, 0.65); font: 500 0.54rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .lever-button strong { font-size: 0.84rem; text-transform: uppercase; }
  .lever-button i { position: relative; width: 24px; height: 38px; border-radius: 999px; background: var(--c-paper); }
  .lever-button i::after { content: ''; position: absolute; top: 2px; left: 2px; width: 20px; height: 20px; border-radius: 50%; background: var(--c-orange); transition: transform 120ms ease; }
  .lever-button:active i::after { transform: translateY(14px); }

  .telemetry-panel { display: flex; flex-direction: column; padding: 1rem; border: 4px solid var(--c-carbon); border-radius: 8px; color: var(--c-paper); background: var(--c-carbon); }
  .telemetry-head { display: flex; justify-content: space-between; padding-bottom: 0.75rem; border-bottom: 1px solid rgba(244, 231, 197, 0.2); font: 600 0.6rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .telemetry-head strong { color: var(--c-amber); }
  .telemetry-dial { display: grid; justify-items: center; margin: 1.2rem 0; }
  .telemetry-dial > span { display: grid; width: 118px; height: 118px; place-items: center; border: 12px solid var(--c-petrol-hi); border-top-color: var(--c-amber); border-right-color: var(--c-orange); border-radius: 50%; transform: rotate(14deg); }
  .telemetry-dial strong { font: 750 2rem/1 "IBM Plex Mono", monospace; transform: rotate(-14deg); }
  .telemetry-dial small { margin-left: 2.2rem; margin-top: -3rem; transform: rotate(-14deg); }
  .telemetry-dial p { margin: 0.6rem 0 0; color: rgba(244, 231, 197, 0.6); font: 500 0.55rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .telemetry-panel ul { display: grid; gap: 0; margin: 0; padding: 0; list-style: none; }
  .telemetry-panel li { display: flex; justify-content: space-between; padding: 0.65rem 0; border-top: 1px solid rgba(244, 231, 197, 0.15); font-size: 0.74rem; }
  .telemetry-panel li span { color: rgba(244, 231, 197, 0.56); }
  .telemetry-panel li strong { font-family: "IBM Plex Mono", monospace; }
  .telemetry-panel > button { min-height: 44px; margin-top: auto; border: 1px solid rgba(244, 231, 197, 0.35); border-radius: 4px; color: var(--c-paper); background: transparent; font-size: 0.68rem; }

  .cabinet-statusbar { display: flex; justify-content: space-between; gap: 1rem; padding: 0.9rem 0.25rem 0; color: rgba(244, 231, 197, 0.72); font: 500 0.55rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .ready-dot { display: inline-block; width: 8px; height: 8px; margin-right: 0.35rem; border-radius: 50%; background: var(--c-mint); }
  .cabinet-statusbar kbd { padding: 0.18rem 0.25rem; border: 1px solid rgba(244, 231, 197, 0.35); border-radius: 3px; }

  .setup-bench { padding: clamp(1.2rem, 3vw, 2.2rem); background: var(--c-paper); }
  .bench-heading { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-end; padding-bottom: 1.2rem; border-bottom: 4px solid var(--c-carbon); }
  .bench-heading h2 { font-size: clamp(2.5rem, 6vw, 5rem); }
  .bench-heading > span { padding: 0.45rem 0.55rem; color: var(--c-paper); background: var(--c-petrol); font: 650 0.58rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .setup-workbench { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 1.4rem; padding-top: 1.4rem; }
  .control-banks { display: grid; gap: 0.8rem; }
  .control-bank { min-width: 0; margin: 0; padding: 1rem; border: 3px solid var(--c-carbon); background: var(--c-paper-hi); }
  .control-bank legend { padding: 0 0.45rem; font-size: 0.86rem; font-weight: 800; text-transform: uppercase; }
  .control-bank legend span { margin-right: 0.35rem; color: var(--c-orange); font-family: "IBM Plex Mono", monospace; }
  .control-bank > p { margin: 0 0 0.7rem; color: rgba(16, 22, 23, 0.62); font-size: 0.75rem; }
  .bank-keys { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.55rem; }
  .bank-keys button { display: grid; min-height: 60px; place-content: center; gap: 0.12rem; border: 2px solid var(--c-carbon); border-radius: 4px; color: var(--c-carbon); background: var(--c-paper); box-shadow: 0 4px 0 var(--c-carbon); transition: transform 90ms ease, box-shadow 90ms ease, background 120ms ease; }
  .bank-keys button:active { transform: translateY(3px); box-shadow: 0 1px 0 var(--c-carbon); }
  .bank-keys .bank-key-on { background: var(--c-amber); }
  .bank-keys strong { font: 750 1.1rem/1 "IBM Plex Mono", monospace; }
  .bank-keys small { font-size: 0.62rem; }

  .route-reel { display: grid; grid-template-columns: 1fr auto 1fr; gap: 0.6rem; align-items: center; width: 100%; min-height: 68px; padding: 0.5rem; border: 3px solid var(--c-carbon); color: var(--c-paper); background: var(--c-petrol); }
  .route-reel > span { display: grid; gap: 0.15rem; justify-items: center; }
  .route-reel small { color: rgba(244, 231, 197, 0.6); font: 500 0.52rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .route-reel strong { font: 750 1.2rem/1 "IBM Plex Mono", monospace; }
  .route-reel i { display: grid; width: 42px; height: 42px; place-items: center; border: 3px solid var(--c-carbon); border-radius: 50%; color: var(--c-carbon); background: var(--c-orange); transition: transform 200ms ease; }
  .route-reel:hover i { transform: rotate(180deg); }
  .route-reel svg { width: 20px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }

  .stock-keys { display: flex; flex-wrap: wrap; gap: 0.5rem; }
  .stock-keys button { min-height: 44px; padding: 0.6rem 0.8rem; border: 2px solid var(--c-carbon); border-radius: 999px; color: var(--c-carbon); background: transparent; font-size: 0.7rem; font-weight: 700; }
  .stock-keys .stock-on { color: var(--c-paper); background: var(--c-petrol); }

  .preview-ticket { position: relative; align-self: start; overflow: hidden; padding: 1.4rem 1.2rem 1.2rem; border: 3px solid var(--c-carbon); background: var(--c-paper-hi); box-shadow: 8px 8px 0 var(--c-orange); }
  .ticket-teeth { position: absolute; top: -7px; right: 0; left: 0; height: 14px; background: radial-gradient(circle at 7px 7px, transparent 0 5px, currentColor 5.5px) 0 0 / 14px 14px repeat-x; color: var(--c-petrol); }
  .preview-ticket h3 { margin: 0.55rem 0 1rem; font-size: 2rem; line-height: 0.9; letter-spacing: -0.06em; text-transform: uppercase; }
  .preview-ticket dl,
  .result-ticket dl { display: grid; gap: 0; margin: 0; }
  .preview-ticket dl div,
  .result-ticket dl div { display: flex; justify-content: space-between; gap: 1rem; padding: 0.65rem 0; border-top: 1px dashed rgba(16, 22, 23, 0.38); }
  .preview-ticket dt,
  .result-ticket dt { color: rgba(16, 22, 23, 0.58); font-size: 0.68rem; }
  .preview-ticket dd,
  .result-ticket dd { margin: 0; font: 700 0.72rem/1 "IBM Plex Mono", monospace; text-align: right; }
  .ticket-barcode { height: 26px; margin: 1rem 0; background: repeating-linear-gradient(90deg, var(--c-carbon) 0 2px, transparent 2px 4px, var(--c-carbon) 4px 5px, transparent 5px 8px); }
  .start-lever { display: grid; grid-template-columns: 1fr auto; gap: 1rem; align-items: center; width: 100%; min-height: 68px; padding: 0.65rem 0.7rem 0.65rem 0.9rem; border: 3px solid var(--c-carbon); border-radius: 5px; color: var(--c-paper); background: var(--c-orange); box-shadow: 0 5px 0 var(--c-carbon); text-align: left; transition: transform 100ms ease, box-shadow 100ms ease; }
  .start-lever:active { transform: translateY(4px); box-shadow: 0 1px 0 var(--c-carbon); }
  .start-lever > span { display: grid; gap: 0.15rem; }
  .start-lever small { color: rgba(16, 22, 23, 0.66); font: 700 0.55rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .start-lever strong { color: var(--c-carbon); font-size: 0.88rem; text-transform: uppercase; }
  .start-lever > i { display: block; width: 35px; height: 48px; padding: 3px; border: 3px solid var(--c-carbon); border-radius: 999px; background: var(--c-paper); }
  .start-lever > i b { display: block; width: 23px; height: 23px; border-radius: 50%; background: var(--c-carbon); transition: transform 120ms ease; }
  .start-lever:active > i b { transform: translateY(13px); }
  .preview-ticket > p { margin: 0.8rem 0 0; color: rgba(16, 22, 23, 0.55); font-size: 0.62rem; text-align: center; }
  .preview-ticket kbd { padding: 0.14rem 0.2rem; border: 1px solid rgba(16, 22, 23, 0.4); border-radius: 3px; }

  .live-machine { padding: 1.2rem; background: var(--c-petrol); }
  .machine-readout { display: grid; grid-template-columns: auto 1fr auto auto; gap: 0.8rem; align-items: center; min-height: 68px; padding: 0.6rem 0.8rem; border: 4px solid var(--c-carbon); border-radius: 7px 7px 0 0; color: var(--c-paper); background: var(--c-carbon); }
  .machine-readout > div { display: grid; gap: 0.15rem; }
  .machine-readout > div:not(.run-route) { padding-right: 0.8rem; border-right: 1px solid rgba(244, 231, 197, 0.18); }
  .machine-readout span { color: rgba(244, 231, 197, 0.55); font: 500 0.52rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .machine-readout strong { color: var(--c-amber); font: 700 0.94rem/1 "IBM Plex Mono", monospace; }
  .run-route { display: flex !important; justify-self: center; flex-direction: row !important; gap: 0.55rem !important; align-items: center; }
  .run-route span { display: grid; width: 34px; height: 28px; place-items: center; border: 1px solid rgba(244, 231, 197, 0.3); color: var(--c-paper); }
  .run-route i { color: var(--c-orange); font-style: normal; }

  .machine-stage { display: grid; grid-template-columns: minmax(0, 1fr) 260px; min-height: 520px; border: 4px solid var(--c-carbon); border-top: 0; background: var(--c-paper); }
  .paper-bay { position: relative; display: grid; min-width: 0; place-items: center; overflow: hidden; padding: 3.2rem 2rem 2rem; background: linear-gradient(90deg, rgba(16, 22, 23, 0.06) 1px, transparent 1px) 0 0 / 18px 18px, var(--c-paper); }
  .roller { position: absolute; top: 0; right: 8%; left: 8%; height: 32px; border: 4px solid var(--c-carbon); border-top: 0; background: var(--c-petrol); }
  .roller i { position: absolute; top: 8px; width: 12px; height: 12px; border: 3px solid var(--c-carbon); border-radius: 50%; background: var(--c-orange); }
  .roller i:first-child { left: 8px; }
  .roller i:last-child { right: 8px; }

  .prompt-ticket { position: relative; width: min(100%, 620px); box-sizing: border-box; padding: 1.5rem 1.7rem; border: 3px solid var(--c-carbon); background: var(--c-paper-hi); box-shadow: 9px 9px 0 rgba(16, 22, 23, 0.22); }
  .prompt-ticket .ticket-teeth { color: var(--c-paper); }
  .paper-meta { display: flex; justify-content: space-between; gap: 1rem; padding-bottom: 0.7rem; border-bottom: 1px dashed rgba(16, 22, 23, 0.35); font: 650 0.56rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .prompt-ticket > p { margin: 1.3rem 0 0.4rem; color: rgba(16, 22, 23, 0.56); font-size: 0.72rem; font-weight: 650; text-transform: uppercase; }
  .prompt-ticket h2 { margin: 0 0 1.5rem; overflow-wrap: anywhere; font-size: clamp(3.5rem, 8vw, 7.4rem); line-height: 0.82; letter-spacing: -0.085em; text-wrap: balance; }
  .prompt-ticket form { display: grid; gap: 0.4rem; }
  .prompt-ticket label { font: 700 0.62rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .answer-carriage { position: relative; display: grid; grid-template-columns: 1fr auto; min-height: 62px; border: 3px solid var(--c-carbon); background: var(--c-paper); box-shadow: inset 0 -6px 0 rgba(16, 22, 23, 0.1); }
  .answer-carriage input { min-width: 0; padding: 0.8rem 1rem; border: 0; color: var(--c-carbon); background: transparent; font: 600 1.05rem/1.2 "IBM Plex Mono", monospace; }
  .answer-carriage input::placeholder { color: rgba(16, 22, 23, 0.38); }
  .answer-carriage button { display: flex; min-width: 104px; gap: 0.55rem; align-items: center; justify-content: center; border: 0; border-left: 3px solid var(--c-carbon); color: var(--c-carbon); background: var(--c-orange); font-size: 0.72rem; font-weight: 800; text-transform: uppercase; }
  .answer-carriage kbd { padding: 0.2rem 0.28rem; border: 1px solid rgba(16, 22, 23, 0.45); border-radius: 3px; }
  .carriage-stop { position: absolute; right: 0; bottom: -13px; left: 0; height: 5px; background: var(--c-carbon); }
  .carriage-head { position: absolute; bottom: -21px; left: 0; width: 26px; height: 21px; border: 3px solid var(--c-carbon); border-radius: 3px; background: var(--c-amber); }
  .paper-correct .carriage-head { animation: carriage-advance 540ms cubic-bezier(0.2, 0.8, 0.2, 1) both; }
  @keyframes carriage-advance { 0% { transform: translateX(0); } 70% { transform: translateX(510px); } 100% { transform: translateX(0); } }
  .paper-retry .answer-carriage { animation: carriage-refuse 360ms ease-out both; }
  @keyframes carriage-refuse { 20% { transform: translateX(-6px); } 50% { transform: translateX(5px); } 80% { transform: translateX(-2px); } }

  .proof-message { min-height: 22px; margin-top: 1.2rem; color: rgba(16, 22, 23, 0.58); font-size: 0.7rem; font-weight: 650; }
  .proof-message.correct { color: #176b55; }
  .proof-message.retry { color: var(--c-red); }
  .proof-message.hint { color: #225b7a; }
  .accepted-stamp { position: absolute; right: 1.6rem; bottom: 1.2rem; padding: 0.35rem 0.5rem; border: 4px double #176b55; color: #176b55; font: 800 0.85rem/1 "IBM Plex Mono", monospace; transform: rotate(-7deg); animation: stamp-in 260ms cubic-bezier(0.2, 1.5, 0.4, 1) both; }
  @keyframes stamp-in { from { opacity: 0; transform: rotate(-7deg) scale(1.8); } to { opacity: 1; transform: rotate(-7deg) scale(1); } }
  .proof-slash { position: absolute; right: 2rem; bottom: 1.4rem; width: 34px; border-top: 5px solid var(--c-red); transform: rotate(-24deg); }

  .run-telemetry { display: flex; min-width: 0; flex-direction: column; padding: 1rem; border-left: 4px solid var(--c-carbon); color: var(--c-paper); background: var(--c-petrol); }
  .notch-head { display: flex; justify-content: space-between; padding-bottom: 0.7rem; border-bottom: 1px solid rgba(244, 231, 197, 0.25); font: 600 0.58rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .notch-head strong { color: var(--c-amber); }
  .feed-notches { display: grid; gap: 0.45rem; padding: 1rem 0; }
  .feed-notches span { display: flex; height: 26px; align-items: center; border: 2px solid rgba(244, 231, 197, 0.2); background: rgba(16, 22, 23, 0.18); }
  .feed-notches span::after { content: ''; width: 18%; height: 100%; background: rgba(244, 231, 197, 0.16); }
  .feed-notches b { width: 36px; padding-left: 0.4rem; color: rgba(244, 231, 197, 0.45); font: 650 0.58rem/1 "IBM Plex Mono", monospace; }
  .feed-notches .printed { border-color: var(--c-mint); background: rgba(99, 198, 168, 0.16); }
  .feed-notches .printed::after { width: calc(100% - 36px); background: var(--c-mint); }
  .feed-notches .printing { border-color: var(--c-amber); }
  .feed-notches .printing::after { background: var(--c-amber); }
  .run-actions { display: grid; gap: 0.5rem; margin-top: auto; }
  .run-actions button { display: grid; grid-template-columns: 50px 1fr; gap: 0.65rem; align-items: center; min-height: 58px; padding: 0.5rem; border: 1px solid rgba(244, 231, 197, 0.26); border-radius: 4px; color: var(--c-paper); background: rgba(16, 22, 23, 0.18); text-align: left; }
  .run-actions button:hover { border-color: var(--c-amber); }
  .run-actions kbd { display: grid; min-height: 32px; place-items: center; border: 2px solid rgba(244, 231, 197, 0.32); border-radius: 3px; font: 600 0.58rem/1 "IBM Plex Mono", monospace; }
  .run-actions button > span { display: grid; gap: 0.12rem; }
  .run-actions strong { font-size: 0.72rem; }
  .run-actions small { color: rgba(244, 231, 197, 0.54); font-size: 0.6rem; }

  .result-bay { display: grid; grid-template-columns: minmax(300px, 0.85fr) minmax(300px, 1.15fr); gap: clamp(2rem, 6vw, 6rem); align-items: center; padding: clamp(2rem, 5vw, 4rem); background: var(--c-paper); }
  .result-machine { position: relative; min-height: 480px; padding-top: 32px; }
  .result-slot { position: absolute; z-index: 2; top: 0; right: 0; left: 0; height: 58px; border: 5px solid var(--c-carbon); border-radius: 9px; background: var(--c-petrol); }
  .result-slot span { position: absolute; right: 8%; bottom: 10px; left: 8%; height: 9px; border: 3px solid var(--c-carbon); background: var(--c-carbon); }
  .result-ticket { position: relative; width: 82%; box-sizing: border-box; margin: 0 auto; padding: 2rem 1.4rem 1.4rem; border: 3px solid var(--c-carbon); background: var(--c-paper-hi); box-shadow: 8px 8px 0 var(--c-orange); animation: ticket-feed 650ms cubic-bezier(0.2, 0.8, 0.2, 1) both; }
  @keyframes ticket-feed { from { opacity: 0; transform: translateY(-220px); } to { opacity: 1; transform: translateY(0); } }
  .result-ticket > p { margin: 0; font: 600 0.56rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .result-ticket h2 { margin: 0.6rem 0 0.8rem; font-size: 2.3rem; line-height: 0.9; letter-spacing: -0.065em; text-transform: uppercase; }
  .result-grade { display: flex; justify-content: space-between; align-items: end; margin: 0.6rem 0 1rem; padding: 0.8rem; border: 4px double var(--c-petrol); color: var(--c-petrol); transform: rotate(-2deg); }
  .result-grade span { font-size: 4.2rem; font-weight: 900; line-height: 0.78; }
  .result-grade small { font: 700 0.64rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .review-note { display: grid; gap: 0.2rem; padding: 0.8rem; border: 2px solid var(--c-carbon); background: var(--c-amber); }
  .review-note span { font: 700 0.55rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .review-note strong { font-size: 0.9rem; }
  .review-note small { color: rgba(16, 22, 23, 0.6); }

  .result-copy > p { color: var(--c-red); }
  .result-copy h3 { max-width: 7ch; margin: 0; font-size: clamp(3rem, 7vw, 6.5rem); font-weight: 900; line-height: 0.82; letter-spacing: -0.085em; text-wrap: balance; text-transform: uppercase; }
  .result-copy > span { display: block; max-width: 30rem; margin-top: 1.2rem; color: rgba(16, 22, 23, 0.66); line-height: 1.6; }
  .result-copy > div { display: flex; flex-wrap: wrap; gap: 0.7rem; margin-top: 1.4rem; }
  .cabinet-primary,
  .cabinet-secondary { min-height: 50px; padding: 0.75rem 1rem; border: 3px solid var(--c-carbon); border-radius: 4px; font-weight: 800; text-transform: uppercase; box-shadow: 4px 4px 0 var(--c-carbon); transition: transform 90ms ease, box-shadow 90ms ease; }
  .cabinet-primary { color: var(--c-carbon); background: var(--c-orange); }
  .cabinet-secondary { color: var(--c-carbon); background: transparent; }
  .cabinet-primary:active,
  .cabinet-secondary:active { transform: translate(3px, 3px); box-shadow: 1px 1px 0 var(--c-carbon); }

  @media (max-width: 940px) {
    .cabinet-topbar { grid-template-columns: auto 1fr; }
    .cabinet-nav { justify-content: flex-end; padding-right: 0.7rem; }
    .score-reels { grid-column: 1 / -1; justify-content: center; border-top: 3px solid var(--c-carbon); border-left: 0; }
    .cabinet-workspace,
    .machine-stage { grid-template-columns: 1fr; }
    .telemetry-panel { display: grid; grid-template-columns: auto 1fr; gap: 1rem; }
    .telemetry-dial { margin: 0; }
    .telemetry-panel ul { align-self: center; }
    .telemetry-panel > button { grid-column: 1 / -1; }
    .run-telemetry { border-top: 4px solid var(--c-carbon); border-left: 0; }
    .run-actions { grid-template-columns: repeat(3, 1fr); }
    .run-actions button { grid-template-columns: 1fr; justify-items: center; text-align: center; }
    .setup-workbench { grid-template-columns: 1fr 270px; }
  }

  @media (max-width: 700px) {
    .cabinet-frame { border-width: 4px; border-radius: 10px; }
    .cabinet-topbar { grid-template-columns: 1fr auto; }
    .cabinet-brand { border-right: 0; }
    .cabinet-brand strong { display: none; }
    .cabinet-nav { gap: 0.3rem; overflow-x: auto; justify-content: flex-start; padding-right: 0.4rem; }
    .cabinet-nav button { min-width: 58px; min-height: 44px; padding-inline: 0.5rem; font-size: 0.62rem; }
    .score-reels span { min-width: 0; flex: 1; }
    .cabinet-label-row span:nth-child(2) { display: none; }
    .cabinet-home { padding: 0.7rem; }
    .cabinet-workspace { gap: 0.7rem; }
    .console-head { align-items: flex-start; padding: 0.9rem; }
    .console-head h2 { font-size: 2.25rem; }
    .mechanical-count small { display: none; }
    .next-ticket { grid-template-columns: 1fr; margin: 0.8rem; padding: 0.9rem; }
    .ticket-copy strong { font-size: 2.5rem; }
    .pressure-strip { grid-template-columns: repeat(3, 1fr); padding: 0 0.8rem 0.8rem; }
    .pressure-strip > span { grid-column: 1 / -1; }
    .pressure-strip button { align-items: flex-start; flex-direction: column; }
    .console-launch { align-items: stretch; flex-direction: column; }
    .lever-button { width: 100%; min-width: 0; }
    .telemetry-panel { grid-template-columns: 1fr; }
    .telemetry-dial { display: none; }
    .cabinet-statusbar span:nth-child(2) { display: none; }
    .setup-bench { padding: 1rem; }
    .bench-heading { align-items: flex-start; flex-direction: column; }
    .setup-workbench { grid-template-columns: 1fr; }
    .preview-ticket { width: 100%; box-sizing: border-box; }
    .machine-readout { grid-template-columns: auto 1fr auto; }
    .machine-readout > div:last-child { display: none; }
    .paper-bay { padding: 3rem 0.7rem 1.2rem; }
    .prompt-ticket { padding: 1.3rem 1rem; }
    .prompt-ticket h2 { font-size: clamp(3.6rem, 20vw, 5.8rem); }
    .answer-carriage { grid-template-columns: 1fr auto; }
    .answer-carriage input { padding-inline: 0.65rem; font-size: 0.9rem; }
    .answer-carriage button { min-width: 66px; }
    .answer-carriage button span { display: none; }
    .accepted-stamp { position: static; display: inline-block; margin-top: 0.4rem; }
    .run-actions { grid-template-columns: repeat(3, 1fr); }
    .run-actions button { min-height: 50px; padding: 0.35rem; }
    .run-actions button span small { display: none; }
    .run-actions kbd { min-height: 26px; border: 0; }
    .result-bay { grid-template-columns: 1fr; padding: 1.2rem; }
    .result-machine { min-height: 450px; }
    .result-copy { text-align: center; }
    .result-copy h3 { max-width: none; font-size: 3.2rem; }
    .result-copy > div { justify-content: center; }
  }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 1ms !important; animation-iteration-count: 1 !important; transition-duration: 1ms !important; }
    .carriage-sweep,
    .carriage-head { display: none; }
  }
</style>
