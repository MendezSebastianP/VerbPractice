<script lang="ts">
  export let variant: 'blueprint' | 'deal' | 'thread';
  export let index = 'T1';
  export let kicker = '';
  export let title = '';
  export let description = '';

  let replayKey = 0;
</script>

<article class="transition-concept" data-transition-variant={variant}>
  <header class="concept-intro">
    <span class="concept-number">{index}</span>
    <div><p>{kicker}</p><h3>{title}</h3><span>{description}</span></div>
    <button class="replay-button" type="button" on:click={() => (replayKey += 1)}><span>↻</span> Replay</button>
  </header>

  {#key replayKey}
    <div class={`transition-stage transition-${variant}`} aria-label={`${title} transition preview`}>
      {#if variant === 'blueprint'}
        <div class="source-setup blueprint-source">
          <span>RUN READY · FR</span><strong>3 tenses × 3 verbs</strong>
          <div><i>Présent</i><i>Futur</i><i>Passé composé</i></div>
        </div>
        <div class="blueprint-grid" aria-hidden="true">
          <span class="draft-line line-x"></span><span class="draft-line line-y"></span>
          {#each Array(6) as _, cell}<i style={`--cell: ${cell}`}></i>{/each}
        </div>
        <div class="arrival-card blueprint-arrival">
          <div class="arrival-top"><span>TABLE RUN / 01</span><small>Présent · 1/3</small></div>
          <div class="arrival-prompt"><span>CURRENT VERB</span><strong>prendre</strong></div>
          <div class="arrival-rows"><i></i><i></i><i></i></div>
        </div>
        <div class="blueprint-stamp">TABLE BUILT</div>
      {:else if variant === 'deal'}
        <div class="deal-source">
          <span>YOUR TENSE LOAD</span><strong>French · Level 1</strong>
        </div>
        <div class="deal-deck" aria-hidden="true">
          {#each ['Présent', 'Futur', 'Passé composé'] as tense, card}
            <div class="deal-card" style={`--card: ${card}; --deal-x: ${card * 72 - 122}%; --deal-rotate: ${card * 8 - 8}deg`}><small>0{card + 1}</small><strong>{tense}</strong><i>TABLE COLUMN</i></div>
          {/each}
        </div>
        <div class="arrival-card deal-arrival">
          <div class="arrival-top"><span>TABLE SHORTCUTS ON</span><small>verb 1 of 3</small></div>
          <div class="arrival-prompt"><span>ACTIVE COLUMN</span><strong>Présent</strong></div>
          <div class="arrival-rows"><i></i><i></i><i></i></div>
        </div>
        <div class="deal-flash" aria-hidden="true"></div>
      {:else}
        <div class="thread-source">
          <span>ROUTE LOCKED</span>
          <div><i>Présent</i><i>Futur</i><i>Passé composé</i></div>
        </div>
        <svg class="thread-path" viewBox="0 0 760 300" preserveAspectRatio="none" aria-hidden="true">
          <path d="M94 68 C240 68 175 146 352 146 S510 232 666 232"></path>
        </svg>
        <span class="thread-runner" aria-hidden="true"></span>
        <div class="thread-nodes" aria-hidden="true"><i></i><i></i><i></i></div>
        <div class="arrival-card thread-arrival">
          <div class="arrival-top"><span>ANSWER PATH ARMED</span><small>Enter ↓</small></div>
          <div class="arrival-prompt"><span>JE + ALLER</span><strong>vais</strong></div>
          <div class="thread-rows"><i class="row-live"></i><i></i><i></i></div>
        </div>
      {/if}

      <div class="transition-timeline"><span>SETUP</span><i></i><strong>TABLE</strong></div>
    </div>
  {/key}
</article>

<style>
  .transition-concept { width: min(100%, 820px); margin-inline: auto; }
  .concept-intro { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 0.85rem; align-items: start; margin-bottom: 0.8rem; padding-inline: 0.25rem; }
  .concept-number { display: grid; width: 2.45rem; height: 2.45rem; place-items: center; border: 1px solid var(--line-strong); border-radius: 13px; color: var(--accent-strong); background: var(--accent-soft); font: 800 0.7rem/1 var(--mono); }
  .concept-intro p { margin: 0 0 0.12rem; color: var(--accent-strong); font: 750 0.5rem/1 var(--mono); letter-spacing: 0.12em; text-transform: uppercase; }
  .concept-intro h3 { margin: 0 0 0.25rem; color: var(--text); font: 800 clamp(1.08rem, 3vw, 1.4rem)/1.1 var(--display); letter-spacing: -0.035em; }
  .concept-intro div > span { color: var(--muted); font-size: 0.74rem; }
  .replay-button { display: flex; gap: 0.4rem; align-items: center; padding: 0.58rem 0.7rem; border: 1px solid var(--line); border-radius: 10px; color: var(--muted); background: var(--surface); font: 700 0.58rem/1 var(--mono); }
  .replay-button:hover { border-color: var(--accent); color: var(--accent-strong); }
  .replay-button span { font-size: 0.9rem; }

  .transition-stage {
    position: relative;
    height: clamp(18rem, 42vw, 22rem);
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--accent) 38%, var(--line));
    border-radius: 24px;
    color: white;
    background:
      linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px),
      radial-gradient(circle at 50% 10%, color-mix(in srgb, var(--accent) 18%, transparent), transparent 42%),
      color-mix(in srgb, var(--surface-dark) 94%, black);
    background-size: 28px 28px, 28px 28px, auto, auto;
    box-shadow: 0 22px 50px rgba(5, 8, 20, 0.2);
  }

  .source-setup,
  .deal-source,
  .thread-source {
    position: absolute;
    display: grid;
    gap: 0.5rem;
    padding: 1rem;
    border: 1px solid rgba(255,255,255,.15);
    border-radius: 14px;
    background: rgba(8, 12, 30, 0.92);
    box-shadow: 0 18px 35px rgba(0,0,0,.28);
  }
  .source-setup span,.deal-source span,.thread-source > span { color: var(--accent-2); font: 750 .48rem/1 var(--mono); letter-spacing: .12em; }
  .source-setup strong,.deal-source strong { font: 800 1rem/1.1 var(--display); }
  .source-setup div,.thread-source div { display: flex; gap: .35rem; flex-wrap: wrap; }
  .source-setup i,.thread-source i { padding: .4rem .48rem; border: 1px solid rgba(255,255,255,.12); border-radius: 7px; color: rgba(255,255,255,.7); background: rgba(255,255,255,.04); font: 700 .5rem/1 var(--mono); font-style: normal; }

  .arrival-card { position: absolute; display: grid; gap: .65rem; width: min(72%, 32rem); padding: .85rem; border: 1px solid color-mix(in srgb, var(--accent-2) 55%, transparent); border-radius: 17px; background: rgba(7, 11, 28, .96); box-shadow: 0 24px 55px rgba(0,0,0,.38), 0 0 30px color-mix(in srgb, var(--accent) 16%, transparent); }
  .arrival-top,.arrival-prompt { display: flex; justify-content: space-between; gap: .7rem; align-items: center; }
  .arrival-top { color: rgba(255,255,255,.5); font: 700 .45rem/1 var(--mono); }
  .arrival-prompt { min-height: 4.5rem; padding: .7rem; border: 1px solid rgba(255,255,255,.1); border-radius: 11px; background: rgba(255,255,255,.025); }
  .arrival-prompt span { color: var(--accent-2); font: 750 .46rem/1 var(--mono); letter-spacing: .1em; }
  .arrival-prompt strong { font: 850 clamp(1.2rem, 4vw, 2rem)/1 var(--display); overflow-wrap: anywhere; }
  .arrival-rows,.thread-rows { display: grid; gap: .36rem; }
  .arrival-rows i,.thread-rows i { height: 2rem; border: 1px solid rgba(255,255,255,.1); border-radius: 7px; background: rgba(255,255,255,.035); }
  .arrival-rows i:first-child,.thread-rows .row-live { border-color: var(--accent-2); background: color-mix(in srgb, var(--accent) 22%, transparent); box-shadow: inset 3px 0 0 var(--accent-2); }
  .transition-timeline { position: absolute; right: 1rem; bottom: .7rem; left: 1rem; display: flex; align-items: center; gap: .6rem; color: rgba(255,255,255,.38); font: 700 .42rem/1 var(--mono); letter-spacing: .12em; }
  .transition-timeline i { height: 1px; flex: 1; background: linear-gradient(90deg, rgba(255,255,255,.12), var(--accent-2)); transform-origin: left; animation: timeline-fill 2.4s ease both; }
  .transition-timeline strong { color: var(--accent-2); }

  .blueprint-source { top: 50%; left: 50%; width: min(72%, 30rem); transform: translate(-50%,-50%); animation: blueprint-source 2.7s ease both; }
  .blueprint-grid { position: absolute; inset: 12% 10% 16%; border: 1px solid color-mix(in srgb, var(--accent-2) 45%, transparent); opacity: 0; animation: blueprint-grid 2.7s ease both; }
  .draft-line { position: absolute; display: block; background: color-mix(in srgb, var(--accent-2) 55%, transparent); }
  .line-x { top: 30%; right: 0; left: 0; height: 1px; transform-origin: left; animation: draft-x 2.7s ease both; }
  .line-y { top: 0; bottom: 0; left: 32%; width: 1px; transform-origin: top; animation: draft-y 2.7s ease both; }
  .blueprint-grid i { position: absolute; right: 5%; bottom: calc(10% + var(--cell) * 10%); left: 38%; height: 6%; border: 1px solid color-mix(in srgb, var(--accent-2) 32%, transparent); opacity: 0; animation: blueprint-cell 2.7s calc(var(--cell) * 45ms) ease both; }
  .blueprint-arrival { top: 48%; left: 50%; transform: translate(-50%,-50%); animation: blueprint-arrival 2.7s cubic-bezier(.2,.8,.2,1) both; }
  .blueprint-stamp { position: absolute; top: 1.2rem; right: 1.3rem; padding: .45rem .55rem; border: 1px solid #55ee9b; color: #55ee9b; font: 800 .5rem/1 var(--mono); letter-spacing: .12em; opacity: 0; transform: rotate(-4deg) scale(1.5); animation: stamp-in 2.7s ease both; }
  @keyframes blueprint-source { 0%,18% { opacity:1; transform:translate(-50%,-50%) scale(1); } 38%,100% { opacity:0; transform:translate(-50%,-50%) scale(.84); } }
  @keyframes blueprint-grid { 0%,20% { opacity:0; transform:scale(.92); } 38%,62% { opacity:1; transform:scale(1); } 78%,100% { opacity:0; } }
  @keyframes draft-x { 0%,25% { transform:scaleX(0); } 52%,100% { transform:scaleX(1); } }
  @keyframes draft-y { 0%,30% { transform:scaleY(0); } 56%,100% { transform:scaleY(1); } }
  @keyframes blueprint-cell { 0%,38% { opacity:0; transform:translateX(2rem); } 60%,72% { opacity:1; transform:translateX(0); } 85%,100% { opacity:0; } }
  @keyframes blueprint-arrival { 0%,62% { opacity:0; transform:translate(-50%,-42%) scale(.94); } 82%,100% { opacity:1; transform:translate(-50%,-50%) scale(1); } }
  @keyframes stamp-in { 0%,82% { opacity:0; transform:rotate(-4deg) scale(1.5); } 88%,100% { opacity:1; transform:rotate(-4deg) scale(1); } }

  .deal-source { top: 1.1rem; left: 1.2rem; animation: deal-source 2.7s ease both; }
  .deal-deck { position: absolute; inset: 0; }
  .deal-card { position: absolute; top: 48%; left: 50%; display: grid; width: min(42%, 13rem); min-height: 7rem; align-content: center; gap: .35rem; padding: .8rem; border: 1px solid color-mix(in srgb, var(--accent-2) 52%, transparent); border-radius: 13px; background: linear-gradient(145deg, color-mix(in srgb, var(--accent) 26%, #0a1027), #070b1c); box-shadow: 0 18px 36px rgba(0,0,0,.35); transform: translate(-50%,-50%); animation: deal-card 2.8s cubic-bezier(.2,.8,.2,1) both; animation-delay: calc(var(--card) * 90ms); }
  .deal-card small,.deal-card i { color: var(--accent-2); font: 750 .44rem/1 var(--mono); font-style: normal; letter-spacing: .1em; }
  .deal-card strong { font: 820 .95rem/1.2 var(--display); }
  .deal-arrival { top: 48%; left: 50%; transform: translate(-50%,-50%); animation: deal-arrival 2.8s ease both; }
  .deal-flash { position:absolute; inset:0; background:linear-gradient(90deg,transparent,var(--accent-2),transparent); opacity:0; transform:scaleX(0); animation:deal-flash 2.8s ease both; }
  @keyframes deal-source { 0%,20% { opacity:1; transform:translateY(0); } 36%,100% { opacity:0; transform:translateY(-1rem); } }
  @keyframes deal-card { 0%,18% { opacity:0; transform:translate(-50%,-35%) rotate(0); } 38% { opacity:1; transform:translate(var(--deal-x),-50%) rotate(var(--deal-rotate)); } 62% { opacity:1; transform:translate(-50%,-50%) rotate(0) scale(.86); } 74%,100% { opacity:0; transform:translate(-50%,-50%) scale(.72); } }
  @keyframes deal-arrival { 0%,68% { opacity:0; transform:translate(-50%,-50%) scale(.72); } 84%,100% { opacity:1; transform:translate(-50%,-50%) scale(1); } }
  @keyframes deal-flash { 0%,66% { opacity:0; transform:scaleX(0); } 72% { opacity:.45; transform:scaleX(1); } 82%,100% { opacity:0; transform:scaleX(1); } }

  .thread-source { top: 1.2rem; left: 50%; width: min(76%, 34rem); transform:translateX(-50%); animation:thread-source 2.8s ease both; }
  .thread-source div { justify-content:center; }
  .thread-path { position:absolute; inset:0; width:100%; height:100%; overflow:visible; }
  .thread-path path { fill:none; stroke:var(--accent-2); stroke-width:2; stroke-dasharray:1000; stroke-dashoffset:1000; filter:drop-shadow(0 0 7px var(--accent)); animation:thread-draw 2.8s ease both; }
  .thread-runner { position:absolute; top:63%; left:86%; width:.75rem; height:.75rem; border-radius:50%; background:#f6c84c; box-shadow:0 0 16px #f6c84c; opacity:0; animation:runner-in 2.8s ease both; }
  .thread-nodes i { position:absolute; width:.55rem; height:.55rem; border:1px solid var(--accent-2); border-radius:50%; background:#0a1027; opacity:0; animation:node-in 2.8s ease both; }
  .thread-nodes i:nth-child(1) { top:20%; left:12%; }
  .thread-nodes i:nth-child(2) { top:46%; left:46%; animation-delay:80ms; }
  .thread-nodes i:nth-child(3) { top:72%; left:86%; animation-delay:160ms; }
  .thread-arrival { top:52%; left:50%; transform:translate(-50%,-50%); animation:thread-arrival 2.8s ease both; }
  @keyframes thread-source { 0%,22% { opacity:1; } 42%,100% { opacity:0; transform:translateX(-50%) translateY(-.8rem); } }
  @keyframes thread-draw { 0%,22% { stroke-dashoffset:1000; opacity:0; } 30% { opacity:1; } 68% { stroke-dashoffset:0; opacity:1; } 82%,100% { stroke-dashoffset:0; opacity:0; } }
  @keyframes node-in { 0%,32% { opacity:0; transform:scale(.4); } 48%,70% { opacity:1; transform:scale(1); } 82%,100% { opacity:0; } }
  @keyframes runner-in { 0%,58% { opacity:0; transform:scale(.4); } 68%,76% { opacity:1; transform:scale(1.35); } 86%,100% { opacity:0; } }
  @keyframes thread-arrival { 0%,72% { opacity:0; clip-path:inset(0 100% 0 0); } 90%,100% { opacity:1; clip-path:inset(0 0 0 0); } }
  @keyframes timeline-fill { from { transform:scaleX(0); } to { transform:scaleX(1); } }

  @media (max-width: 560px) {
    .concept-intro { grid-template-columns: auto minmax(0, 1fr); }
    .replay-button { grid-column: 2; justify-self: start; }
    .arrival-card { width: 82%; }
    .deal-card { width: 48%; }
    .source-setup,.thread-source { width: 82%; }
    .arrival-prompt { align-items:flex-start; flex-direction:column; }
  }

  @media (prefers-reduced-motion: reduce) {
    .transition-stage * { animation-duration: 1ms !important; animation-delay: 0ms !important; }
  }
</style>
