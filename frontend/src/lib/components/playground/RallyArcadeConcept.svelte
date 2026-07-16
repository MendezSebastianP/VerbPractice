<script lang="ts">
  import { onDestroy, tick } from 'svelte';

  type Screen = 'home' | 'setup' | 'run' | 'clear';
  type FeedbackTone = 'idle' | 'success' | 'error' | 'hint';

  const prompts = [
    { source: 'aller', answer: 'to go', hint: 'movement from here to there' },
    { source: 'partir', answer: 'to leave', hint: 'the opposite of arriving' },
    { source: 'savoir', answer: 'to know', hint: 'knowledge, not familiarity' },
  ];
  const weekdayLabel = new Intl.DateTimeFormat(undefined, { weekday: 'long' }).format(new Date());

  let screen: Screen = 'home';
  let phase: 'ready' | 'leaving' | 'entering' = 'ready';
  let sessionLength = 10;
  let direction = 'FR → EN';
  let promptIndex = 0;
  let answer = '';
  let feedback = '';
  let feedbackTone: FeedbackTone = 'idle';
  let rally = 4;
  let score = 320;
  let answerInput: HTMLInputElement | null = null;
  const timers: ReturnType<typeof setTimeout>[] = [];
  let navigationTimer: ReturnType<typeof setTimeout> | null = null;
  let settleTimer: ReturnType<typeof setTimeout> | null = null;

  $: prompt = prompts[promptIndex % prompts.length];
  $: runProgress = Math.min(100, ((promptIndex + 1) / prompts.length) * 100);

  function later(callback: () => void, delay: number): void {
    timers.push(setTimeout(callback, delay));
  }

  function canAutoFocus(): boolean {
    return window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  }

  function resetRun(): void {
    promptIndex = 0;
    answer = '';
    feedback = '';
    feedbackTone = 'idle';
    rally = 4;
    score = 320;
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
      settleTimer = setTimeout(() => (phase = 'ready'), 320);
    }, 190);
  }

  function submitAnswer(): void {
    if (!answer.trim() || feedbackTone === 'success') return;
    const normalized = answer.trim().toLocaleLowerCase();
    if (normalized === prompt.answer) {
      feedback = `Point won · ${prompt.source} → ${prompt.answer}`;
      feedbackTone = 'success';
      rally += 1;
      score += 80;
      later(() => {
        if (promptIndex >= prompts.length - 1) {
          go('clear');
          return;
        }
        promptIndex += 1;
        answer = '';
        feedback = '';
        feedbackTone = 'idle';
        void tick().then(() => answerInput?.focus());
      }, 620);
      return;
    }
    feedback = 'Out. Keep the rally alive — one more try.';
    feedbackTone = 'error';
    rally = Math.max(0, rally - 1);
    later(() => {
      if (feedbackTone === 'error') feedbackTone = 'idle';
    }, 520);
  }

  function showHint(): void {
    feedback = `Clue · ${prompt.hint}`;
    feedbackTone = 'hint';
    answerInput?.focus();
  }

  function skipPrompt(): void {
    feedback = `${prompt.source} means “${prompt.answer}”`;
    feedbackTone = 'hint';
    later(() => {
      if (promptIndex >= prompts.length - 1) {
        go('clear');
        return;
      }
      promptIndex += 1;
      answer = '';
      feedback = '';
      feedbackTone = 'idle';
      void tick().then(() => answerInput?.focus());
    }, 700);
  }

  onDestroy(() => {
    timers.forEach(clearTimeout);
    if (navigationTimer) clearTimeout(navigationTimer);
    if (settleTimer) clearTimeout(settleTimer);
  });
</script>

<div class="rally-frame" data-phase={phase}>
  <div class="rally-wipe" aria-hidden="true"><span>CHANGE ENDS</span></div>

  <header class="rally-topbar">
    <button class="rally-brand" type="button" aria-label="Rally home" on:click={() => go('home')}>
      <span class="rally-mark" aria-hidden="true">R</span>
      <span><strong>Verb Rally</strong><small>Call. Recall. Return.</small></span>
    </button>

    <nav class="rally-nav" aria-label="Rally prototype navigation">
      <button class:nav-on={screen === 'home'} type="button" aria-current={screen === 'home' ? 'page' : undefined} on:click={() => go('home')}>Clubhouse</button>
      <button class:nav-on={screen === 'setup'} type="button" aria-current={screen === 'setup' ? 'page' : undefined} on:click={() => go('setup')}>Next match</button>
      <button class:nav-on={screen === 'run'} type="button" aria-current={screen === 'run' ? 'page' : undefined} on:click={() => go('run')}>Live court</button>
    </nav>

    <div class="rally-profile" aria-label="Player streak and level">
      <span><small>Streak</small><strong>07</strong></span>
      <i aria-hidden="true"></i>
      <span><small>Seed</small><strong>12</strong></span>
    </div>
  </header>

  <div class="rally-screen">
    {#key screen}
      {#if screen === 'home'}
        <section class="rally-view home-view" aria-labelledby="rally-home-title">
          <div class="rally-hero-copy">
            <p class="rally-kicker"><span>07 day streak</span> · {weekdayLabel} club match</p>
            <h2 id="rally-home-title">Keep the rally <em>alive.</em></h2>
            <p class="rally-lede">A practice session should feel like an exchange, not a settings form. Return ten French verbs before the rhythm breaks.</p>
            <div class="hero-actions">
              <button class="rally-primary" type="button" on:click={() => go('setup')}>
                <span>Serve the next deck</span>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h13M13 7l5 5-5 5" /></svg>
              </button>
              <button class="rally-link" type="button" on:click={() => go('run')}>Preview the live court</button>
            </div>
          </div>

          <div class="court-board" aria-label="Today's practice deck">
            <div class="court-scorebar">
              <span>Today’s court</span>
              <strong>FR <i>↔</i> EN</strong>
              <span>Best rally <b>14</b></span>
            </div>
            <div class="court-lines" aria-hidden="true">
              <span class="court-net"></span>
              <span class="court-ball"></span>
            </div>
            <div class="court-stage-list">
              <button type="button" on:click={() => go('setup')}>
                <span class="stage-number">01</span>
                <span><small>Priority match</small><strong>Verb return</strong></span>
                <span class="stage-meta"><b>10</b><small>returns</small></span>
              </button>
              <button type="button" on:click={() => go('setup')}>
                <span class="stage-number">02</span>
                <span><small>Recovery match</small><strong>Weak words</strong></span>
                <span class="stage-meta"><b>06</b><small>returns</small></span>
              </button>
            </div>
          </div>

          <div class="rally-ticker" aria-label="Current performance summary">
            <span><small>Accuracy</small><strong>84%</strong></span>
            <span><small>Words returned</small><strong>146</strong></span>
            <span><small>Pressure list</small><strong>09</strong></span>
            <p>Next milestone <b>250 XP</b><i><span style="width: 68%"></span></i></p>
          </div>
        </section>
      {:else if screen === 'setup'}
        <section class="rally-view setup-view" aria-labelledby="rally-setup-title">
          <div class="setup-intro">
            <p class="rally-kicker">Match setup · one decision per line</p>
            <h2 id="rally-setup-title">Choose the pace.<br />Own the return.</h2>
            <p>The old menu makes every control shout at once. This setup gives the next irreversible action the visual weight.</p>
          </div>

          <div class="match-card">
            <div class="match-row match-length">
              <div><span>01</span><p><strong>Rally length</strong><small>How long do you want to stay in rhythm?</small></p></div>
              <div class="length-pills" role="group" aria-label="Session length">
                {#each [5, 10, 20] as option}
                  <button class:length-on={sessionLength === option} type="button" aria-pressed={sessionLength === option} on:click={() => (sessionLength = option)}>
                    <strong>{option}</strong><small>{option === 5 ? 'Warm-up' : option === 10 ? 'Match' : 'Open set'}</small>
                  </button>
                {/each}
              </div>
            </div>

            <div class="match-row match-direction">
              <div><span>02</span><p><strong>Direction of play</strong><small>The prompt serves; your answer returns.</small></p></div>
              <button class="direction-control" type="button" aria-label="Swap language direction" on:click={() => (direction = direction === 'FR → EN' ? 'EN → FR' : 'FR → EN')}>
                <span><small>Serve</small><strong>{direction.slice(0, 2)}</strong></span>
                <i aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M5 9h12M14 6l3 3-3 3M19 15H7M10 12l-3 3 3 3" /></svg></i>
                <span><small>Return</small><strong>{direction.slice(-2)}</strong></span>
              </button>
            </div>

            <div class="match-launch">
              <div><span>Ready</span><strong>{sessionLength} returns · {direction}</strong></div>
              <button type="button" on:click={() => go('run')}><span>Start match</span><small>Enter ↵</small></button>
            </div>
          </div>
        </section>
      {:else if screen === 'run'}
        <section class="rally-view run-view" aria-labelledby="rally-prompt">
          <div class="live-scoreboard">
            <span><small>Point</small><strong>{String(promptIndex + 1).padStart(2, '0')}<i>/</i>{String(prompts.length).padStart(2, '0')}</strong></span>
            <p><i aria-hidden="true"></i> Live · {direction}</p>
            <span><small>Rally</small><strong>×{rally}</strong></span>
            <span><small>Score</small><strong>{score}</strong></span>
          </div>

          <div class="live-court" class:point-won={feedbackTone === 'success'} class:point-missed={feedbackTone === 'error'}>
            <div class="court-language serve-language"><span>Serve</span><strong>{direction.slice(0, 2)}</strong></div>
            <div class="court-language return-language"><span>Return</span><strong>{direction.slice(-2)}</strong></div>
            <div class="live-net" aria-hidden="true"></div>
            <div class="word-flight" aria-hidden="true"><span>{prompt.source}</span></div>

            <div class="prompt-zone">
              <span class="prompt-call">Translate the serve</span>
              <h2 id="rally-prompt">{prompt.source}</h2>
              <form on:submit|preventDefault={submitAnswer}>
                <label for="rally-answer">Your return</label>
                <div class="rally-input-wrap">
                  <input id="rally-answer" name="rally-answer" bind:this={answerInput} bind:value={answer} autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="e.g. to go…" />
                  <button type="submit" aria-label="Return answer">
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h13M13 7l5 5-5 5" /></svg>
                  </button>
                </div>
              </form>
              <div class={`rally-feedback ${feedbackTone}`} role="status" aria-live="polite">{feedback || 'Return cleanly to build your combo.'}</div>
            </div>
          </div>

          <div class="court-controls">
            <div class="point-progress" aria-label={`${Math.round(runProgress)} percent complete`}>
              {#each prompts as _, i}
                <span class:done={i < promptIndex} class:active={i === promptIndex}></span>
              {/each}
            </div>
            <div>
              <button type="button" on:click={showHint}><kbd>H</kbd> Hint</button>
              <button type="button" on:click={skipPrompt}><kbd>S</kbd> Skip</button>
              <button type="button" on:click={() => go('setup')}><kbd>Esc</kbd> End match</button>
            </div>
          </div>
        </section>
      {:else}
        <section class="rally-view clear-view" aria-labelledby="rally-clear-title">
          <p class="rally-kicker">Match complete · personal best</p>
          <div class="clear-score" aria-hidden="true"><span>10</span><i>—</i><span>08</span></div>
          <h2 id="rally-clear-title">You held the rally.</h2>
          <p>Three clean returns moved <b>savoir</b> and <b>partir</b> out of the pressure list.</p>
          <div class="clear-stats">
            <span><small>Accuracy</small><strong>88%</strong></span>
            <span><small>Best rally</small><strong>×{rally}</strong></span>
            <span><small>Match XP</small><strong>+{score}</strong></span>
          </div>
          <div class="clear-actions">
            <button class="rally-primary" type="button" on:click={() => go('run')}>Play the return leg</button>
            <button class="rally-link" type="button" on:click={() => go('home')}>Back to clubhouse</button>
          </div>
        </section>
      {/if}
    {/key}
  </div>
</div>

<style>
  .rally-frame {
    --r-ink: #071510;
    --r-court: #0e3b2b;
    --r-court-light: #15543d;
    --r-lime: #e7ff63;
    --r-coral: #ff6b57;
    --r-cream: #f4f3e8;
    --r-mint: #b9f5d8;
    position: relative;
    min-height: 720px;
    overflow: hidden;
    border: 1px solid rgba(231, 255, 99, 0.28);
    border-radius: 30px;
    color: var(--r-cream);
    background:
      radial-gradient(circle at 80% -10%, rgba(231, 255, 99, 0.12), transparent 30%),
      var(--r-ink);
    box-shadow: 0 28px 80px rgba(0, 0, 0, 0.34);
    font-family: "Space Grotesk", sans-serif;
    isolation: isolate;
  }

  button,
  input { touch-action: manipulation; -webkit-tap-highlight-color: transparent; }
  button { font: inherit; }

  button:focus-visible,
  input:focus-visible {
    outline: 3px solid var(--r-lime);
    outline-offset: 3px;
  }

  .rally-wipe {
    position: absolute;
    inset: 0;
    z-index: 20;
    display: grid;
    place-items: center;
    color: var(--r-ink);
    background: var(--r-lime);
    transform: scaleX(0);
    pointer-events: none;
  }

  .rally-wipe span {
    font: 800 clamp(1.2rem, 4vw, 3.4rem)/1 "IBM Plex Mono", monospace;
    letter-spacing: -0.06em;
  }

  [data-phase='leaving'] .rally-wipe { animation: rally-wipe-in 200ms cubic-bezier(0.7, 0, 0.3, 1) both; }
  [data-phase='entering'] .rally-wipe { animation: rally-wipe-out 300ms cubic-bezier(0.7, 0, 0.3, 1) both; }

  @keyframes rally-wipe-in { from { transform: scaleX(0); transform-origin: left; } to { transform: scaleX(1); transform-origin: left; } }
  @keyframes rally-wipe-out { from { transform: scaleX(1); transform-origin: right; } to { transform: scaleX(0); transform-origin: right; } }

  .rally-topbar {
    position: relative;
    z-index: 3;
    display: grid;
    grid-template-columns: minmax(190px, 0.7fr) minmax(300px, 1.2fr) auto;
    gap: 1.25rem;
    align-items: center;
    min-height: 76px;
    padding: 0 1.5rem;
    border-bottom: 1px solid rgba(244, 243, 232, 0.14);
    background: rgba(7, 21, 16, 0.86);
  }

  .rally-brand {
    display: inline-flex;
    min-height: 44px;
    gap: 0.7rem;
    align-items: center;
    padding: 0;
    border: 0;
    color: inherit;
    background: transparent;
    text-align: left;
  }

  .rally-mark {
    display: grid;
    width: 39px;
    height: 39px;
    place-items: center;
    border-radius: 50%;
    color: var(--r-ink);
    background: var(--r-lime);
    font-weight: 900;
    transition: transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1);
  }

  .rally-brand:hover .rally-mark { transform: rotate(-12deg) scale(1.05); }
  .rally-brand > span:last-child { display: grid; gap: 0.1rem; }
  .rally-brand strong { font-size: 0.92rem; letter-spacing: -0.03em; }
  .rally-brand small { color: rgba(244, 243, 232, 0.58); font: 500 0.59rem/1.2 "IBM Plex Mono", monospace; text-transform: uppercase; }

  .rally-nav {
    display: flex;
    justify-content: center;
    gap: 0.25rem;
  }

  .rally-nav button {
    min-height: 44px;
    padding: 0.7rem 1rem;
    border: 0;
    border-radius: 999px;
    color: rgba(244, 243, 232, 0.58);
    background: transparent;
    font-weight: 650;
    transition: color 160ms ease, background 160ms ease;
  }

  .rally-nav button:hover,
  .rally-nav .nav-on { color: var(--r-cream); background: rgba(244, 243, 232, 0.09); }

  .rally-profile {
    display: flex;
    align-items: center;
    gap: 0.7rem;
  }

  .rally-profile span { display: grid; gap: 0.05rem; }
  .rally-profile small { color: rgba(244, 243, 232, 0.52); font: 500 0.55rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .rally-profile strong { font: 750 0.95rem/1 "IBM Plex Mono", monospace; font-variant-numeric: tabular-nums; }
  .rally-profile i { width: 1px; height: 28px; background: rgba(244, 243, 232, 0.18); }

  .rally-screen { position: relative; min-height: 644px; }
  .rally-view { min-height: 644px; animation: rally-view-in 360ms cubic-bezier(0.2, 0.85, 0.3, 1) both; }
  @keyframes rally-view-in { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }

  .home-view {
    display: grid;
    grid-template-columns: minmax(0, 0.82fr) minmax(420px, 1.18fr);
    grid-template-rows: 1fr auto;
    gap: 1.2rem 2.2rem;
    padding: clamp(2rem, 5vw, 4.4rem);
    background: linear-gradient(108deg, transparent 0 48%, rgba(14, 59, 43, 0.44) 48% 100%);
  }

  .rally-hero-copy { align-self: center; }
  .rally-kicker { margin: 0 0 1rem; color: var(--r-mint); font: 650 0.68rem/1.3 "IBM Plex Mono", monospace; letter-spacing: 0.08em; text-transform: uppercase; }
  .rally-kicker span { color: var(--r-ink); background: var(--r-lime); padding: 0.34rem 0.5rem; }

  .rally-hero-copy h2,
  .setup-intro h2,
  .clear-view h2 {
    max-width: 8ch;
    margin: 0;
    font-size: clamp(3.4rem, 7.4vw, 7.1rem);
    font-weight: 780;
    line-height: 0.82;
    letter-spacing: -0.085em;
    text-wrap: balance;
  }

  .rally-hero-copy h2 em { color: var(--r-lime); font-style: normal; }
  .rally-lede { max-width: 31rem; margin: 1.5rem 0 0; color: rgba(244, 243, 232, 0.68); font-size: 1rem; line-height: 1.65; }
  .hero-actions, .clear-actions { display: flex; flex-wrap: wrap; gap: 0.85rem; align-items: center; margin-top: 1.7rem; }

  .rally-primary {
    display: inline-flex;
    min-height: 52px;
    gap: 1rem;
    align-items: center;
    justify-content: center;
    padding: 0.85rem 1.1rem 0.85rem 1.25rem;
    border: 1px solid var(--r-lime);
    border-radius: 7px;
    color: var(--r-ink);
    background: var(--r-lime);
    font-weight: 760;
    box-shadow: 5px 5px 0 var(--r-coral);
    transition: transform 160ms ease, box-shadow 160ms ease;
  }

  .rally-primary:hover { transform: translate(-2px, -2px); box-shadow: 8px 8px 0 var(--r-coral); }
  .rally-primary:active { transform: translate(2px, 2px); box-shadow: 2px 2px 0 var(--r-coral); }
  .rally-primary svg { width: 21px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }

  .rally-link {
    min-height: 44px;
    padding: 0.6rem 0.75rem;
    border: 0;
    border-bottom: 1px solid rgba(244, 243, 232, 0.28);
    color: var(--r-cream);
    background: transparent;
    font-weight: 650;
  }

  .court-board {
    position: relative;
    align-self: center;
    min-height: 410px;
    overflow: hidden;
    border: 1px solid rgba(244, 243, 232, 0.26);
    border-radius: 18px;
    background: var(--r-court);
    box-shadow: 18px 18px 0 rgba(255, 107, 87, 0.86);
  }

  .court-scorebar {
    position: relative;
    z-index: 2;
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
    min-height: 58px;
    padding: 0 1rem;
    color: rgba(244, 243, 232, 0.72);
    background: rgba(7, 21, 16, 0.72);
    font: 600 0.63rem/1 "IBM Plex Mono", monospace;
    text-transform: uppercase;
  }

  .court-scorebar strong { color: var(--r-lime); font-size: 0.84rem; }
  .court-scorebar strong i { color: var(--r-coral); font-style: normal; }
  .court-scorebar b { color: var(--r-cream); }

  .court-lines { position: absolute; inset: 58px 0 0; opacity: 0.5; pointer-events: none; }
  .court-lines::before { content: ''; position: absolute; inset: 8% 6%; border: 2px solid rgba(244, 243, 232, 0.34); }
  .court-lines::after { content: ''; position: absolute; left: 6%; right: 6%; top: 50%; border-top: 2px solid rgba(244, 243, 232, 0.34); }
  .court-net { position: absolute; top: 8%; bottom: 8%; left: 50%; border-left: 3px dashed rgba(244, 243, 232, 0.4); }
  .court-ball { position: absolute; top: 38%; left: 36%; width: 16px; height: 16px; border-radius: 50%; background: var(--r-lime); box-shadow: 0 0 0 7px rgba(231, 255, 99, 0.12); }

  .court-stage-list {
    position: absolute;
    z-index: 2;
    right: 1rem;
    bottom: 1rem;
    left: 1rem;
    display: grid;
    gap: 0.55rem;
  }

  .court-stage-list button {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 0.85rem;
    align-items: center;
    min-height: 70px;
    padding: 0.75rem;
    border: 1px solid rgba(244, 243, 232, 0.18);
    border-radius: 9px;
    color: var(--r-cream);
    background: rgba(7, 21, 16, 0.88);
    text-align: left;
    transition: border-color 160ms ease, transform 160ms ease;
  }

  .court-stage-list button:hover { border-color: var(--r-lime); transform: translateX(4px); }
  .stage-number { display: grid; width: 36px; height: 36px; place-items: center; border-radius: 50%; color: var(--r-ink); background: var(--r-lime); font: 750 0.7rem/1 "IBM Plex Mono", monospace; }
  .court-stage-list button > span:nth-child(2) { display: grid; gap: 0.16rem; }
  .court-stage-list small { color: rgba(244, 243, 232, 0.52); font: 500 0.58rem/1.2 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .court-stage-list strong { font-size: 1rem; }
  .stage-meta { display: grid; justify-items: end; }
  .stage-meta b { color: var(--r-lime); font: 700 1.2rem/1 "IBM Plex Mono", monospace; }

  .rally-ticker {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: repeat(3, auto) minmax(200px, 1fr);
    gap: 1.5rem;
    align-items: center;
    padding-top: 1.2rem;
    border-top: 1px solid rgba(244, 243, 232, 0.15);
  }

  .rally-ticker > span { display: flex; gap: 0.6rem; align-items: baseline; }
  .rally-ticker small { color: rgba(244, 243, 232, 0.48); font: 500 0.58rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .rally-ticker strong { font: 700 1rem/1 "IBM Plex Mono", monospace; }
  .rally-ticker p { display: grid; grid-template-columns: auto 1fr; gap: 0.3rem 0.8rem; align-items: center; margin: 0; color: rgba(244, 243, 232, 0.56); font-size: 0.72rem; }
  .rally-ticker p i { grid-column: 1 / -1; height: 4px; overflow: hidden; background: rgba(244, 243, 232, 0.12); }
  .rally-ticker p i span { display: block; height: 100%; background: var(--r-coral); }

  .setup-view {
    display: grid;
    grid-template-columns: minmax(260px, 0.7fr) minmax(480px, 1.3fr);
    gap: clamp(2rem, 5vw, 5rem);
    align-items: center;
    padding: clamp(2rem, 5vw, 4rem);
  }

  .setup-intro h2 { max-width: 9ch; font-size: clamp(2.8rem, 5.8vw, 5.4rem); }
  .setup-intro > p:last-child { max-width: 28rem; color: rgba(244, 243, 232, 0.62); line-height: 1.65; }
  .match-card { overflow: hidden; border: 1px solid rgba(244, 243, 232, 0.2); border-radius: 18px; background: rgba(244, 243, 232, 0.045); }
  .match-row { display: grid; gap: 1rem; padding: 1.4rem; border-bottom: 1px solid rgba(244, 243, 232, 0.15); }
  .match-row > div:first-child { display: flex; gap: 0.8rem; align-items: flex-start; }
  .match-row > div:first-child > span { color: var(--r-lime); font: 700 0.7rem/1.4 "IBM Plex Mono", monospace; }
  .match-row p { display: grid; gap: 0.2rem; margin: 0; }
  .match-row p strong { font-size: 1rem; }
  .match-row p small { color: rgba(244, 243, 232, 0.5); line-height: 1.4; }

  .length-pills { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.55rem; }
  .length-pills button {
    display: grid;
    min-height: 74px;
    gap: 0.15rem;
    place-content: center;
    border: 1px solid rgba(244, 243, 232, 0.16);
    border-radius: 8px;
    color: rgba(244, 243, 232, 0.6);
    background: transparent;
    transition: color 160ms ease, border-color 160ms ease, background 160ms ease;
  }
  .length-pills button:hover,
  .length-pills .length-on { color: var(--r-ink); border-color: var(--r-lime); background: var(--r-lime); }
  .length-pills strong { font: 750 1.35rem/1 "IBM Plex Mono", monospace; }
  .length-pills small { font-size: 0.66rem; }

  .direction-control {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 0.75rem;
    align-items: center;
    min-height: 88px;
    padding: 0.7rem;
    border: 1px solid rgba(244, 243, 232, 0.16);
    border-radius: 8px;
    color: var(--r-cream);
    background: var(--r-court);
  }
  .direction-control > span { display: grid; gap: 0.2rem; justify-items: center; }
  .direction-control small { color: rgba(244, 243, 232, 0.48); font: 500 0.58rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .direction-control strong { font: 750 1.5rem/1 "IBM Plex Mono", monospace; }
  .direction-control i { display: grid; width: 42px; height: 42px; place-items: center; border-radius: 50%; color: var(--r-ink); background: var(--r-lime); transition: transform 240ms ease; }
  .direction-control:hover i { transform: rotate(180deg); }
  .direction-control svg { width: 21px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }

  .match-launch { display: flex; gap: 1rem; align-items: center; justify-content: space-between; padding: 1rem 1rem 1rem 1.4rem; background: var(--r-coral); }
  .match-launch > div { display: grid; gap: 0.2rem; color: var(--r-ink); }
  .match-launch > div span { font: 700 0.58rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .match-launch > div strong { font-size: 0.9rem; }
  .match-launch > button { display: flex; min-height: 52px; gap: 1rem; align-items: center; padding: 0.65rem 0.8rem 0.65rem 1.1rem; border: 0; border-radius: 7px; color: var(--r-cream); background: var(--r-ink); font-weight: 750; }
  .match-launch > button small { padding: 0.38rem; border: 1px solid rgba(244, 243, 232, 0.3); border-radius: 4px; font: 500 0.58rem/1 "IBM Plex Mono", monospace; }

  .run-view { padding: clamp(1rem, 2.5vw, 1.8rem); background: var(--r-court); }
  .live-scoreboard {
    display: grid;
    grid-template-columns: auto 1fr auto auto;
    gap: 1rem;
    align-items: center;
    min-height: 72px;
    padding: 0.5rem 1rem;
    border-radius: 10px 10px 0 0;
    color: var(--r-cream);
    background: var(--r-ink);
  }
  .live-scoreboard > span { display: grid; gap: 0.15rem; }
  .live-scoreboard small { color: rgba(244, 243, 232, 0.48); font: 500 0.58rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .live-scoreboard strong { color: var(--r-lime); font: 750 1.25rem/1 "IBM Plex Mono", monospace; font-variant-numeric: tabular-nums; }
  .live-scoreboard strong i { color: rgba(244, 243, 232, 0.32); font-style: normal; }
  .live-scoreboard p { justify-self: center; margin: 0; color: rgba(244, 243, 232, 0.64); font: 600 0.65rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .live-scoreboard p i { display: inline-block; width: 7px; height: 7px; margin-right: 0.4rem; border-radius: 50%; background: var(--r-coral); box-shadow: 0 0 0 4px rgba(255, 107, 87, 0.16); }

  .live-court {
    position: relative;
    display: grid;
    min-height: 450px;
    place-items: center;
    overflow: hidden;
    border: 2px solid rgba(244, 243, 232, 0.34);
    border-top: 0;
    background:
      linear-gradient(90deg, transparent calc(50% - 1px), rgba(244, 243, 232, 0.35) calc(50% - 1px) calc(50% + 1px), transparent calc(50% + 1px)),
      linear-gradient(rgba(244, 243, 232, 0.18) 1px, transparent 1px);
    background-size: 100% 100%, 100% 50%;
  }
  .live-court::before { content: ''; position: absolute; inset: 7%; border: 2px solid rgba(244, 243, 232, 0.28); pointer-events: none; }
  .live-net { position: absolute; top: 6%; bottom: 6%; left: 50%; border-left: 4px dashed rgba(244, 243, 232, 0.36); }
  .court-language { position: absolute; top: 1.4rem; display: grid; gap: 0.2rem; padding: 0.6rem; }
  .serve-language { left: 1.5rem; }
  .return-language { right: 1.5rem; justify-items: end; }
  .court-language span { color: rgba(244, 243, 232, 0.52); font: 500 0.55rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .court-language strong { font: 750 1.1rem/1 "IBM Plex Mono", monospace; }

  .prompt-zone { position: relative; z-index: 3; width: min(86%, 580px); padding: 2rem; border-radius: 12px; color: var(--r-ink); background: var(--r-cream); box-shadow: 12px 12px 0 rgba(7, 21, 16, 0.28); text-align: center; }
  .prompt-call { color: rgba(7, 21, 16, 0.56); font: 650 0.63rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; letter-spacing: 0.1em; }
  .prompt-zone h2 { margin: 0.75rem 0 1.3rem; overflow-wrap: anywhere; font-size: clamp(2.8rem, 6vw, 5rem); line-height: 0.95; letter-spacing: -0.075em; text-wrap: balance; }
  .prompt-zone form { display: grid; gap: 0.45rem; text-align: left; }
  .prompt-zone label { font-size: 0.75rem; font-weight: 700; }
  .rally-input-wrap { display: grid; grid-template-columns: 1fr auto; border-bottom: 3px solid var(--r-ink); }
  .rally-input-wrap input { min-width: 0; min-height: 54px; padding: 0.65rem 0.2rem; border: 0; color: var(--r-ink); background: transparent; font-size: 1.1rem; font-weight: 650; }
  .rally-input-wrap input::placeholder { color: rgba(7, 21, 16, 0.4); }
  .rally-input-wrap button { display: grid; width: 48px; height: 48px; place-items: center; align-self: center; border: 0; border-radius: 50%; color: var(--r-ink); background: var(--r-lime); transition: transform 150ms ease; }
  .rally-input-wrap button:hover { transform: translateX(3px); }
  .rally-input-wrap svg { width: 22px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
  .rally-feedback { min-height: 24px; margin-top: 0.8rem; color: rgba(7, 21, 16, 0.54); font-size: 0.78rem; font-weight: 620; }
  .rally-feedback.success { color: #0a6843; }
  .rally-feedback.error { color: #b9232c; }
  .rally-feedback.hint { color: #2b559f; }

  .word-flight { position: absolute; z-index: 5; top: 50%; left: 10%; opacity: 0; pointer-events: none; }
  .word-flight span { display: block; padding: 0.45rem 0.6rem; border-radius: 5px; color: var(--r-ink); background: var(--r-lime); font: 700 0.75rem/1 "IBM Plex Mono", monospace; }
  .point-won .word-flight { animation: word-return 580ms cubic-bezier(0.2, 0.8, 0.2, 1) both; }
  @keyframes word-return { 0% { opacity: 0; transform: translate(0, -60px) rotate(-8deg); } 18% { opacity: 1; } 100% { opacity: 0; transform: translate(720px, 90px) rotate(8deg); } }
  .point-won .prompt-zone { animation: point-pop 360ms ease-out both; }
  .point-missed .prompt-zone { animation: court-shake 360ms ease-out both; }
  @keyframes point-pop { 50% { transform: scale(1.025); } }
  @keyframes court-shake { 25% { transform: translateX(-7px); } 55% { transform: translateX(6px); } 80% { transform: translateX(-3px); } }

  .court-controls { display: flex; justify-content: space-between; gap: 1rem; align-items: center; min-height: 68px; padding: 0.65rem 1rem; border-radius: 0 0 10px 10px; color: var(--r-cream); background: var(--r-ink); }
  .point-progress { display: flex; gap: 0.35rem; }
  .point-progress span { width: 28px; height: 5px; border-radius: 999px; background: rgba(244, 243, 232, 0.18); }
  .point-progress span.done { background: var(--r-mint); }
  .point-progress span.active { background: var(--r-lime); box-shadow: 0 0 0 3px rgba(231, 255, 99, 0.13); }
  .court-controls > div:last-child { display: flex; gap: 0.3rem; }
  .court-controls button { min-height: 44px; padding: 0.45rem 0.55rem; border: 0; color: rgba(244, 243, 232, 0.62); background: transparent; font-size: 0.7rem; }
  .court-controls button:hover { color: var(--r-cream); }
  .court-controls kbd { margin-right: 0.2rem; padding: 0.2rem 0.3rem; border: 1px solid rgba(244, 243, 232, 0.24); border-radius: 3px; font: 600 0.6rem/1 "IBM Plex Mono", monospace; }

  .clear-view { display: grid; justify-items: center; align-content: center; padding: clamp(2rem, 6vw, 5rem); text-align: center; background: radial-gradient(circle at 50% 35%, rgba(231, 255, 99, 0.12), transparent 30%); }
  .clear-score { display: flex; align-items: center; gap: clamp(0.6rem, 3vw, 2rem); color: var(--r-lime); font: 780 clamp(5rem, 16vw, 11rem)/0.78 "IBM Plex Mono", monospace; letter-spacing: -0.12em; }
  .clear-score i { color: var(--r-coral); font-style: normal; }
  .clear-view h2 { max-width: none; margin-top: 1.1rem; font-size: clamp(2.3rem, 5vw, 4.8rem); }
  .clear-view > p:not(.rally-kicker) { max-width: 38rem; color: rgba(244, 243, 232, 0.62); }
  .clear-stats { display: grid; grid-template-columns: repeat(3, 1fr); width: min(100%, 570px); margin-top: 1.2rem; border-block: 1px solid rgba(244, 243, 232, 0.16); }
  .clear-stats span { display: grid; gap: 0.35rem; padding: 1rem; }
  .clear-stats span + span { border-left: 1px solid rgba(244, 243, 232, 0.16); }
  .clear-stats small { color: rgba(244, 243, 232, 0.48); font: 500 0.58rem/1 "IBM Plex Mono", monospace; text-transform: uppercase; }
  .clear-stats strong { font: 750 1.25rem/1 "IBM Plex Mono", monospace; }

  @media (max-width: 920px) {
    .rally-topbar { grid-template-columns: 1fr auto; }
    .rally-nav { grid-column: 1 / -1; grid-row: 2; order: 3; padding-bottom: 0.6rem; }
    .rally-profile { justify-self: end; }
    .home-view,
    .setup-view { grid-template-columns: 1fr; }
    .home-view { background: linear-gradient(180deg, transparent 0 42%, rgba(14, 59, 43, 0.4) 42% 100%); }
    .rally-hero-copy h2 { max-width: 9ch; }
    .court-board { width: min(100%, 650px); justify-self: center; }
    .rally-ticker { grid-template-columns: repeat(3, 1fr); }
    .rally-ticker p { grid-column: 1 / -1; }
    .setup-intro { text-align: center; }
    .setup-intro h2,
    .setup-intro > p:last-child { margin-inline: auto; }
  }

  @media (max-width: 620px) {
    .rally-frame { min-height: 700px; border-radius: 20px; }
    .rally-topbar { gap: 0.6rem; padding: 0.7rem; }
    .rally-brand small { display: none; }
    .rally-profile { gap: 0.45rem; }
    .rally-profile span:first-child,
    .rally-profile i { display: none; }
    .rally-nav { justify-content: stretch; overflow-x: auto; }
    .rally-nav button { flex: 1; min-width: max-content; padding-inline: 0.65rem; font-size: 0.75rem; }
    .rally-screen,
    .rally-view { min-height: 600px; }
    .home-view,
    .setup-view { padding: 1.25rem; }
    .rally-hero-copy h2 { font-size: clamp(3rem, 17vw, 4.8rem); }
    .rally-lede { font-size: 0.9rem; }
    .court-board { min-height: 390px; box-shadow: 7px 7px 0 var(--r-coral); }
    .court-scorebar span:first-child { display: none; }
    .court-lines { overflow: hidden; }
    .court-ball { animation: none; }
    .court-stage-list button { min-height: 76px; }
    .rally-ticker { grid-template-columns: 1fr 1fr; gap: 1rem; }
    .rally-ticker > span:nth-child(3) { display: none; }
    .match-row { padding: 1rem; }
    .length-pills { gap: 0.35rem; }
    .length-pills button { min-height: 68px; }
    .match-launch { align-items: stretch; flex-direction: column; }
    .match-launch > button { justify-content: space-between; }
    .run-view { padding: 0.7rem; }
    .live-scoreboard { grid-template-columns: auto 1fr auto; gap: 0.6rem; }
    .live-scoreboard > span:last-child { display: none; }
    .live-scoreboard p { justify-self: start; font-size: 0.58rem; }
    .live-court { min-height: 430px; background-size: 100% 100%, 100% 50%; }
    .prompt-zone { width: 88%; padding: 1.35rem 1rem; }
    .prompt-zone h2 { font-size: 3.2rem; }
    .court-controls { align-items: flex-start; flex-direction: column; }
    .point-progress { width: 100%; }
    .point-progress span { flex: 1; }
    .court-controls > div:last-child { width: 100%; justify-content: space-between; }
    .court-controls button { padding-inline: 0.2rem; }
    .court-controls button:last-child kbd { display: none; }
    .clear-score { font-size: clamp(4.2rem, 23vw, 7rem); }
    .clear-stats { grid-template-columns: 1fr; }
    .clear-stats span + span { border-left: 0; border-top: 1px solid rgba(244, 243, 232, 0.16); }
    .clear-actions { justify-content: center; }
  }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 1ms !important; animation-iteration-count: 1 !important; scroll-behavior: auto !important; transition-duration: 1ms !important; }
    .court-ball,
    .word-flight { display: none; }
  }
</style>
