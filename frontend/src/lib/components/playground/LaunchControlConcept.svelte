<script lang="ts">
  export let variant: 'command' | 'gate' | 'ticket';
  export let index = 'L1';
  export let kicker = '';
  export let title = '';
  export let description = '';
</script>

<article class="launch-concept" data-launch-variant={variant}>
  <header class="concept-intro">
    <span class="concept-number">{index}</span>
    <div><p>{kicker}</p><h3>{title}</h3><span>{description}</span></div>
  </header>

  <div class={`launch-stage launch-${variant}`}>
    {#if variant === 'command'}
      <div class="command-copy"><span>READY LOADOUT</span><strong>French · 3 tenses · 3 verbs</strong><small>Blank table · no guides</small></div>
      <button type="button"><span>START RUN</span><i>Enter ↵</i></button>
    {:else if variant === 'gate'}
      <div class="gate-head"><span>FRENCH / LEVEL 1</span><small>3 × 3 · BLANK</small></div>
      <button type="button"><i aria-hidden="true"></i><span><small>OPEN THE GATE</small><strong>Start table run</strong></span><b>→</b></button>
      <div class="gate-foot"><span>ENTER</span><i></i><small>launch shortcut armed</small></div>
    {:else}
      <div class="ticket-main"><span>RUN TICKET · FR-03</span><strong>3 verbs</strong><small>Présent · Futur · Passé composé</small></div>
      <div class="ticket-perf" aria-hidden="true">••••••••••••</div>
      <button type="button"><small>VALIDATE</small><strong>PLAY</strong><span>↗</span></button>
    {/if}
  </div>
</article>

<style>
  .launch-concept { width: min(100%, 760px); margin-inline: auto; }
  .concept-intro { display: grid; grid-template-columns: auto 1fr; gap: 0.85rem; align-items: start; margin-bottom: 0.8rem; padding-inline: 0.25rem; }
  .concept-number { display: grid; width: 2.45rem; height: 2.45rem; place-items: center; border: 1px solid var(--line-strong); border-radius: 13px; color: var(--accent-strong); background: var(--accent-soft); font: 800 0.7rem/1 var(--mono); }
  .concept-intro p { margin: 0 0 0.12rem; color: var(--accent-strong); font: 750 0.5rem/1 var(--mono); letter-spacing: 0.12em; text-transform: uppercase; }
  .concept-intro h3 { margin: 0 0 0.25rem; color: var(--text); font: 800 clamp(1.08rem, 3vw, 1.4rem)/1.1 var(--display); letter-spacing: -0.035em; }
  .concept-intro div > span { color: var(--muted); font-size: 0.74rem; }

  .launch-stage {
    min-height: 8.5rem;
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--accent) 34%, var(--line));
    border-radius: 20px;
    color: white;
    background: color-mix(in srgb, var(--surface-dark) 92%, black);
    box-shadow: 0 18px 42px rgba(5, 8, 20, 0.18);
  }

  button { cursor: pointer; color: inherit; font-family: inherit; }

  .launch-command { display: grid; grid-template-columns: 1fr minmax(12rem, 0.72fr); gap: 0.8rem; align-items: stretch; padding: 0.8rem; }
  .command-copy { display: grid; align-content: center; gap: 0.2rem; padding: 0.7rem; }
  .command-copy span { color: var(--accent-2); font: 750 0.47rem/1 var(--mono); letter-spacing: 0.12em; }
  .command-copy strong { font-size: 0.92rem; }
  .command-copy small { color: rgba(255, 255, 255, 0.48); font-size: 0.6rem; }
  .launch-command button { position: relative; display: grid; grid-template-columns: 1fr auto; gap: 0.6rem; align-items: center; padding: 1rem; overflow: hidden; border: 1px solid var(--accent-2); border-radius: 13px; background: color-mix(in srgb, var(--accent) 26%, rgba(255, 255, 255, 0.03)); }
  .launch-command button::before { position: absolute; inset: 0; background: linear-gradient(105deg, transparent 38%, color-mix(in srgb, var(--accent-2) 18%, transparent) 50%, transparent 62%); content: ''; transform: translateX(-100%); transition: transform 380ms ease; }
  .launch-command button:hover::before { transform: translateX(100%); }
  .launch-command button span { z-index: 1; font: 850 1.05rem/1 var(--display); text-align: left; }
  .launch-command button i { z-index: 1; padding: 0.35rem 0.45rem; border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 6px; font: 750 0.5rem/1 var(--mono); font-style: normal; }

  .launch-gate { display: grid; gap: 0.55rem; padding: 0.8rem; background: radial-gradient(circle at 50% 110%, color-mix(in srgb, var(--accent) 22%, transparent), transparent 45%), color-mix(in srgb, var(--surface-dark) 92%, black); }
  .gate-head,.gate-foot { display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; color: rgba(255, 255, 255, 0.48); font: 700 0.46rem/1 var(--mono); }
  .launch-gate button { display: grid; grid-template-columns: auto 1fr auto; gap: 0.75rem; align-items: center; padding: 0.85rem; border: 1px solid color-mix(in srgb, #f6c84c 54%, transparent); border-radius: 12px; text-align: left; background: color-mix(in srgb, #f6c84c 8%, rgba(255, 255, 255, 0.025)); }
  .launch-gate button > i { width: 0.65rem; height: 3.1rem; border-radius: 999px; background: repeating-linear-gradient(0deg, var(--accent-2), var(--accent-2) 4px, transparent 4px, transparent 8px); }
  .launch-gate button > span { display: grid; gap: 0.18rem; }
  .launch-gate button small { color: #f6c84c; font: 750 0.45rem/1 var(--mono); letter-spacing: 0.12em; }
  .launch-gate button strong { font: 820 1.15rem/1 var(--display); }
  .launch-gate button b { display: grid; width: 2.2rem; height: 2.2rem; place-items: center; border-radius: 50%; color: #191300; background: #f6c84c; font-size: 1.2rem; transition: transform 180ms ease; }
  .launch-gate button:hover b { transform: translateX(0.25rem); }
  .gate-foot i { flex: 1; height: 1px; background: rgba(255, 255, 255, 0.1); }

  .launch-ticket { display: grid; grid-template-columns: minmax(0, 1fr) 1.2rem minmax(8rem, 0.42fr); min-height: 9.5rem; background: linear-gradient(120deg, color-mix(in srgb, var(--accent) 15%, transparent), transparent 55%), color-mix(in srgb, var(--surface-dark) 92%, black); }
  .ticket-main { display: grid; align-content: center; gap: 0.28rem; padding: 1.2rem; }
  .ticket-main span { color: var(--accent-2); font: 750 0.47rem/1 var(--mono); letter-spacing: 0.12em; }
  .ticket-main strong { font: 850 1.65rem/1 var(--display); }
  .ticket-main small { color: rgba(255, 255, 255, 0.5); font-size: 0.58rem; }
  .ticket-perf { overflow: hidden; padding-block: 0.25rem; color: rgba(255, 255, 255, 0.22); font: 800 0.72rem/0.72rem var(--mono); text-align: center; word-break: break-all; writing-mode: vertical-rl; }
  .launch-ticket button { display: grid; align-content: center; justify-items: center; gap: 0.18rem; padding: 0.8rem; border: 0; border-left: 1px dashed rgba(255, 255, 255, 0.22); background: color-mix(in srgb, var(--accent) 24%, rgba(255, 255, 255, 0.02)); }
  .launch-ticket button small { color: rgba(255, 255, 255, 0.52); font: 750 0.44rem/1 var(--mono); }
  .launch-ticket button strong { font: 900 1.35rem/1 var(--display); }
  .launch-ticket button span { margin-top: 0.25rem; font-size: 1.15rem; transition: transform 180ms ease; }
  .launch-ticket button:hover span { transform: translate(0.2rem, -0.2rem); }

  @media (max-width: 560px) {
    .launch-command { grid-template-columns: 1fr; }
    .launch-ticket { grid-template-columns: minmax(0, 1fr) 0.8rem minmax(6.5rem, 0.5fr); }
    .ticket-main { padding: 0.85rem; }
    .launch-gate button strong { font-size: 0.95rem; }
  }
</style>
