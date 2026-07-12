<script lang="ts">
  // Public experiment bench (/playground) — no login required. Anything we
  // want to evaluate before shipping gets a section here.
  import { navigate } from '../router';

  let seedA = 0;
  let seedB = 0;
  let seedC = 0;

  function setTheme(next: 'light' | 'dark' | 'arcade'): void {
    document.documentElement.setAttribute('data-theme', next);
  }

  function replayAll(): void {
    seedA += 1;
    seedB += 1;
    seedC += 1;
  }
</script>

<section class="pg-shell">
  <header class="glass-panel strong-panel pg-header">
    <div>
      <p class="eyebrow">Playground · experiments before they ship</p>
      <h1 class="pg-title">VerbPractice Lab</h1>
      <p class="section-copy">Public sandbox — no login needed. Click any card to replay its animation.</p>
    </div>
    <div class="pg-header-actions">
      <div class="pg-theme-row" role="group" aria-label="Preview theme">
        <button class="option-chip" type="button" on:click={() => setTheme('light')}>Light</button>
        <button class="option-chip" type="button" on:click={() => setTheme('dark')}>Dark</button>
        <button class="option-chip" type="button" on:click={() => setTheme('arcade')}>Arcade</button>
      </div>
      <button class="text-switch" type="button" on:click={() => navigate('/')}>Enter the app →</button>
    </div>
  </header>

  <!-- ============ EXPERIMENT 1: correct-answer feedback ============ -->
  <article class="glass-panel">
    <div class="section-head">
      <div>
        <p class="eyebrow">Experiment 01</p>
        <h2>Correct-answer feedback — 3 options</h2>
      </div>
      <button class="secondary-button pg-replay" type="button" on:click={replayAll}>↻ Replay all</button>
    </div>
    <p class="section-copy">Replaces the green “Correct!” text. No words, no green — the card itself confirms.</p>

    <div class="pg-grid">
      <!-- Option A: check draw -->
      <button class="pg-option" type="button" on:click={() => (seedA += 1)}>
        <div class="pg-option-name"><span class="kbd-chip">A</span> Check draw <span class="shipped-chip">✓ shipped</span></div>
        {#key seedA}
          <div class="demo-card">
            <div class="demo-count">3/5 · es → en</div>
            <div class="demo-prompt">verdad</div>
            <div class="demo-input-wrap">
              <span class="demo-input a-underline">truth</span>
              <svg class="check-svg" viewBox="0 0 24 24" aria-hidden="true">
                <path class="check-path" d="M4 12.5 L10 18 L20 6" />
              </svg>
            </div>
          </div>
        {/key}
        <p class="pg-note">A check draws itself at the end of the line while the underline surges in accent. Quiet, fast, zero layout shift.</p>
      </button>

      <!-- Option B: stamp -->
      <button class="pg-option" type="button" on:click={() => (seedB += 1)}>
        <div class="pg-option-name"><span class="kbd-chip">B</span> Seal stamp</div>
        {#key seedB}
          <div class="demo-card">
            <div class="demo-count">3/5 · es → en</div>
            <div class="demo-prompt-stack">
              <div class="demo-prompt">ciudad</div>
              <span class="stamp" aria-hidden="true">
                <span class="stamp-ring"></span>
                ✓
              </span>
            </div>
            <div class="demo-input-wrap">
              <span class="demo-input">city</span>
            </div>
          </div>
        {/key}
        <p class="pg-note">An accent seal slams over the word with a ring ripple, then fades as the next word arrives. Arcade-friendly, very “stage cleared”.</p>
      </button>

      <!-- Option C: word morph + combo surge -->
      <button class="pg-option" type="button" on:click={() => (seedC += 1)}>
        <div class="pg-option-name"><span class="kbd-chip">C</span> Morph &amp; combo surge</div>
        {#key seedC}
          <div class="demo-card">
            <div class="demo-count">3/5 · es → en <span class="demo-combo c-swell">combo ×3</span></div>
            <div class="morph-stack">
              <div class="demo-prompt c-out">luego</div>
              <div class="demo-prompt c-in">aquí</div>
            </div>
            <div class="demo-input-wrap">
              <span class="demo-input c-dim">then</span>
            </div>
            <div class="sheen" aria-hidden="true"></div>
          </div>
        {/key}
        <p class="pg-note">The answered word lifts away, the next drops in, the combo counter swells, and a light sheen sweeps the card. The reward *is* the momentum.</p>
      </button>
    </div>
  </article>

  <!-- ============ EXPERIMENT 2: logo options ============ -->
  <article class="glass-panel">
    <div class="section-head">
      <div>
        <p class="eyebrow">Experiment 02</p>
        <h2>VerbPractice logo — 3 options</h2>
      </div>
    </div>
    <p class="section-copy">Hover each mark. All three ride the theme tokens — switch the preview theme above to see them adapt.</p>

    <div class="pg-grid">
      <!-- Logo 1: playmark tile -->
      <div class="pg-option logo-card">
        <div class="pg-option-name"><span class="kbd-chip">1</span> Playmark tile</div>
        <div class="logo-stage">
          <div class="logo1">
            <span class="logo1-tile">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5 L18.5 12 L8 18.5 Z" fill="currentColor" /></svg>
            </span>
            <span class="logo1-word">Verb<em>Practice</em></span>
          </div>
        </div>
        <p class="pg-note">A play-button tile carries the brand: practice = press play. Works at 16px favicon size.</p>
      </div>

      <!-- Logo 2: VP monogram -->
      <div class="pg-option logo-card">
        <div class="pg-option-name"><span class="kbd-chip">2</span> VP monogram <span class="shipped-chip">✓ shipped</span></div>
        <div class="logo-stage">
          <div class="logo2">
            <span class="logo2-badge">
              <span class="logo2-v">V</span><span class="logo2-p">P</span>
              <span class="logo2-notch" aria-hidden="true"></span>
            </span>
            <span class="logo2-word">Verb Practice</span>
          </div>
        </div>
        <p class="pg-note">Stacked monogram badge with a progress notch that fills on hover — the “level up” identity.</p>
      </div>

      <!-- Logo 3: HUD slashes -->
      <div class="pg-option logo-card">
        <div class="pg-option-name"><span class="kbd-chip">3</span> verb//practice</div>
        <div class="logo-stage">
          <div class="logo3">
            <span class="logo3-word">verb<span class="logo3-slash">//</span>practice<span class="logo3-cursor" aria-hidden="true">▊</span></span>
          </div>
        </div>
        <p class="pg-note">Terminal/HUD wordmark with a live cursor. The nerdy one — strongest in arcade, still clean in light.</p>
      </div>
    </div>
  </article>
</section>

<style>
  .pg-shell {
    max-width: 720px;
    margin-inline: auto;
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .pg-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .pg-title {
    font-family: var(--display);
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    margin: 0.3rem 0 0.4rem;
    color: var(--text);
  }

  :global(html[data-theme='arcade']) .pg-title {
    font-size: 1.1rem;
    line-height: 1.6;
    text-shadow: 0 0 12px color-mix(in srgb, var(--accent) 90%, transparent);
  }

  .pg-header-actions {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.6rem;
  }

  .pg-theme-row {
    display: flex;
    gap: 0.4rem;
  }

  .pg-replay {
    padding: 0.5rem 1rem;
    font-size: 0.85rem;
  }

  .pg-grid {
    display: grid;
    gap: 1rem;
    margin-top: 1rem;
    grid-template-columns: 1fr;
  }

  .pg-option {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    text-align: left;
    background: transparent;
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 1rem;
    cursor: pointer;
    color: inherit;
    font: inherit;
  }

  .pg-option:hover {
    border-color: color-mix(in srgb, var(--accent) 45%, transparent);
  }

  .logo-card {
    cursor: default;
  }

  .pg-option-name {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 700;
    color: var(--text);
    font-family: var(--display);
    font-size: 0.95rem;
  }

  .pg-note {
    font-size: 0.82rem;
    color: var(--muted);
    line-height: 1.45;
    margin: 0;
  }

  .shipped-chip {
    margin-left: auto;
    font-family: var(--mono);
    font-size: 0.62rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: var(--accent-strong);
    border: 1px solid color-mix(in srgb, var(--accent) 45%, transparent);
    border-radius: 999px;
    padding: 0.15rem 0.55rem;
    background: var(--accent-soft);
  }

  /* --- shared demo session card --- */
  .demo-card {
    position: relative;
    overflow: hidden;
    border: 1px solid var(--line-strong);
    border-radius: 14px;
    background: color-mix(in srgb, var(--surface-strong) 80%, transparent);
    padding: 1rem 1.25rem 1.25rem;
    text-align: center;
    min-height: 150px;
  }

  .demo-count {
    display: flex;
    justify-content: space-between;
    font-family: var(--mono);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: var(--muted);
  }

  .demo-prompt {
    font-family: var(--display);
    font-size: 1.9rem;
    font-weight: 700;
    color: var(--text);
    margin: 0.8rem 0;
  }

  :global(html[data-theme='arcade']) .demo-prompt {
    font-size: 1.15rem;
    line-height: 1.6;
  }

  .demo-input-wrap {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
  }

  .demo-input {
    display: inline-block;
    min-width: 130px;
    border-bottom: 2px solid color-mix(in srgb, var(--accent) 35%, transparent);
    padding: 4px 8px;
    font-size: 1.05rem;
    color: var(--text);
  }

  /* --- option A: check draw --- */
  .a-underline {
    animation: underline-surge 0.8s ease-out both;
  }

  @keyframes underline-surge {
    0% { border-bottom-color: color-mix(in srgb, var(--accent) 35%, transparent); box-shadow: none; }
    30% { border-bottom-color: var(--accent); box-shadow: 0 10px 18px -12px var(--accent); }
    100% { border-bottom-color: color-mix(in srgb, var(--accent) 35%, transparent); box-shadow: none; }
  }

  .check-svg {
    width: 22px;
    height: 22px;
    overflow: visible;
  }

  .check-path {
    fill: none;
    stroke: var(--accent);
    stroke-width: 3.2;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-dasharray: 32;
    stroke-dashoffset: 32;
    filter: drop-shadow(0 0 6px color-mix(in srgb, var(--accent) 60%, transparent));
    animation: check-draw 0.4s 0.15s cubic-bezier(0.3, 0.9, 0.4, 1) forwards;
  }

  @keyframes check-draw {
    to { stroke-dashoffset: 0; }
  }

  /* --- option B: stamp --- */
  .demo-prompt-stack {
    position: relative;
    display: inline-block;
  }

  .stamp {
    position: absolute;
    left: 50%;
    top: 50%;
    width: 56px;
    height: 56px;
    margin: -28px 0 0 -28px;
    border: 3px solid var(--accent);
    border-radius: 50%;
    display: grid;
    place-items: center;
    font-size: 1.6rem;
    font-weight: 800;
    color: var(--accent);
    background: color-mix(in srgb, var(--accent) 10%, transparent);
    text-shadow: 0 0 10px color-mix(in srgb, var(--accent) 60%, transparent);
    animation:
      stamp-in 0.38s cubic-bezier(0.2, 1.3, 0.4, 1) both,
      stamp-out 0.5s 1.15s ease-out forwards;
  }

  @keyframes stamp-in {
    0% { transform: scale(2.4) rotate(-20deg); opacity: 0; }
    100% { transform: scale(1) rotate(-8deg); opacity: 1; }
  }

  @keyframes stamp-out {
    to { opacity: 0; transform: scale(1.06) rotate(-8deg); }
  }

  .stamp-ring {
    position: absolute;
    inset: -3px;
    border: 2px solid var(--accent);
    border-radius: 50%;
    animation: ring-out 0.7s 0.3s ease-out both;
  }

  @keyframes ring-out {
    0% { transform: scale(1); opacity: 0.8; }
    100% { transform: scale(1.9); opacity: 0; }
  }

  /* --- option C: morph + combo surge --- */
  .demo-combo {
    font-family: var(--display);
    font-size: 0.72rem;
    color: var(--accent-strong);
    text-transform: uppercase;
  }

  .c-swell {
    display: inline-block;
    animation: combo-swell 0.55s 0.25s cubic-bezier(0.3, 1.4, 0.5, 1) both;
  }

  @keyframes combo-swell {
    0% { transform: scale(1); }
    45% { transform: scale(1.45); text-shadow: 0 0 12px color-mix(in srgb, var(--accent) 80%, transparent); }
    100% { transform: scale(1); }
  }

  .morph-stack {
    position: relative;
    height: 3.6rem;
    margin: 0.6rem 0;
  }

  .morph-stack .demo-prompt {
    position: absolute;
    inset: 0;
    margin: 0;
  }

  .c-out {
    animation: word-rise 0.45s ease-in both;
  }

  @keyframes word-rise {
    0% { opacity: 1; transform: translateY(0); filter: blur(0); }
    100% { opacity: 0; transform: translateY(-20px); filter: blur(6px); }
  }

  .c-in {
    animation: word-drop 0.4s 0.3s ease-out both;
  }

  @keyframes word-drop {
    0% { opacity: 0; transform: translateY(16px); filter: blur(8px); }
    100% { opacity: 1; transform: translateY(0); filter: blur(0); }
  }

  .c-dim {
    animation: input-clear 0.4s 0.25s ease-out both;
  }

  @keyframes input-clear {
    to { opacity: 0.25; }
  }

  .sheen {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: linear-gradient(115deg, transparent 30%, color-mix(in srgb, var(--accent) 22%, transparent) 50%, transparent 70%);
    transform: translateX(-110%);
    animation: sheen-sweep 0.7s 0.15s ease-out both;
  }

  @keyframes sheen-sweep {
    to { transform: translateX(110%); }
  }

  /* --- logos --- */
  .logo-stage {
    display: grid;
    place-items: center;
    min-height: 110px;
    border: 1px dashed var(--line);
    border-radius: 12px;
    background: color-mix(in srgb, var(--surface-strong) 55%, transparent);
    padding: 1rem;
  }

  .logo1 {
    display: flex;
    align-items: center;
    gap: 0.7rem;
  }

  .logo1-tile {
    width: 44px;
    height: 44px;
    border-radius: 11px;
    display: grid;
    place-items: center;
    color: #fff;
    background: linear-gradient(135deg, var(--accent-strong), var(--accent), var(--accent-2));
    box-shadow: var(--button-shadow);
    transition: transform 0.3s cubic-bezier(0.3, 1.3, 0.5, 1);
  }

  .logo1-tile svg {
    width: 22px;
    height: 22px;
    transition: transform 0.3s;
  }

  .logo1:hover .logo1-tile {
    transform: rotate(-6deg) scale(1.06);
  }

  .logo1:hover .logo1-tile svg {
    transform: translateX(2px);
  }

  .logo1-word {
    font-family: var(--display);
    font-size: 1.55rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: var(--text);
  }

  .logo1-word em {
    font-style: normal;
    background: linear-gradient(135deg, var(--accent-strong), var(--accent), var(--accent-2));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }

  .logo2 {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.55rem;
  }

  .logo2-badge {
    position: relative;
    width: 58px;
    height: 58px;
    border-radius: 16px;
    border: 2px solid color-mix(in srgb, var(--accent) 60%, transparent);
    background: color-mix(in srgb, var(--accent) 10%, transparent);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1px;
    font-family: var(--display);
    font-size: 1.35rem;
    font-weight: 800;
    overflow: hidden;
    transition: box-shadow 0.3s;
  }

  .logo2:hover .logo2-badge {
    box-shadow: 0 0 22px color-mix(in srgb, var(--accent) 40%, transparent);
  }

  .logo2-v { color: var(--text); }
  .logo2-p { color: var(--accent); }

  .logo2-notch {
    position: absolute;
    left: 0;
    bottom: 0;
    height: 5px;
    width: 34%;
    background: linear-gradient(90deg, var(--accent), var(--accent-2));
    transition: width 0.45s cubic-bezier(0.25, 0.8, 0.3, 1);
  }

  .logo2:hover .logo2-notch {
    width: 100%;
  }

  .logo2-word {
    font-family: var(--mono);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.28em;
    color: var(--muted);
  }

  .logo3-word {
    font-family: var(--mono);
    font-size: 1.7rem;
    color: var(--text);
    letter-spacing: 0.02em;
  }

  .logo3-slash {
    color: var(--accent);
    text-shadow: 0 0 10px color-mix(in srgb, var(--accent) 70%, transparent);
  }

  .logo3-cursor {
    margin-left: 4px;
    color: var(--accent-strong);
    animation: cursor-blink 1.1s step-end infinite;
  }

  @keyframes cursor-blink {
    0%, 49% { opacity: 1; }
    50%, 100% { opacity: 0; }
  }

  @media (min-width: 620px) {
    .pg-grid {
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    }
  }
</style>
