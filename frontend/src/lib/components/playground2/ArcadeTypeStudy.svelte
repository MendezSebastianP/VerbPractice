<script lang="ts">
  // Study 03 — arcade typography discipline. The same six specimens rendered
  // under three type systems. Fonts are referenced by name (not theme vars)
  // because the study is specifically about the arcade theme's stack.
  export let variant: 'current' | 'discipline' | 'cabinet';
  export let index = 'T1';
  export let kicker = '';
  export let title = '';
  export let description = '';
</script>

<svelte:head>
  {#if variant === 'cabinet'}
    <link
      href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600;700&family=Russo+One&display=swap"
      rel="stylesheet"
    />
  {/if}
</svelte:head>

<article class="type-study" data-variant={variant}>
  <header class="concept-intro" class:intro-current={variant === 'current'}>
    <span class="concept-number">{index}</span>
    <div><p>{kicker}</p><h3>{title}</h3><span>{description}</span></div>
  </header>

  <div class="stage" class:stage-current={variant === 'current'}>
    <div class="spec-grid">
      <div class="spec-cell">
        <span class="spec-tag">Page title</span>
        {#if variant === 'current'}
          <strong class="cur-title">Verb Lab</strong>
          <em class="spec-size">Press Start 2P · 20px</em>
        {:else if variant === 'discipline'}
          <strong class="di-title">Verb Lab</strong>
          <em class="spec-size">Press Start 2P · 17px · lh 1.7 — marquee only</em>
        {:else}
          <strong class="cb-title">VERB LAB</strong>
          <em class="spec-size">Russo One · 22px</em>
        {/if}
      </div>

      <div class="spec-cell">
        <span class="spec-tag">Eyebrow label</span>
        {#if variant === 'current'}
          <span class="cur-eyebrow">Daily stage · ES → FR</span>
          <em class="spec-size">VT323 · 12px (reads ≈10px)</em>
        {:else if variant === 'discipline'}
          <span class="di-eyebrow">Daily stage · ES → FR</span>
          <em class="spec-size">VT323 · 16.8px — compensated for its small eye</em>
        {:else}
          <span class="cb-eyebrow">Daily stage · ES → FR</span>
          <em class="spec-size">Chakra Petch 600 · 12.5px</em>
        {/if}
      </div>

      <div class="spec-cell">
        <span class="spec-tag">Primary button</span>
        {#if variant === 'current'}
          <button type="button" class="cur-button">Start table run</button>
          <em class="spec-size">Press Start 2P · 15px — wide, crushes at this size</em>
        {:else if variant === 'discipline'}
          <button type="button" class="di-button">Start table run</button>
          <em class="spec-size">Space Grotesk 700 · 15.2px</em>
        {:else}
          <button type="button" class="cb-button">Start table run</button>
          <em class="spec-size">Russo One · 15.2px</em>
        {/if}
      </div>

      <div class="spec-cell">
        <span class="spec-tag">Profile chips</span>
        {#if variant === 'current'}
          <span class="chip-row"><span class="cur-level">Lv.7</span><span class="cur-xp">1,250 XP</span></span>
          <em class="spec-size">Press Start 2P · 8.8px / VT323 · 14px</em>
        {:else if variant === 'discipline'}
          <span class="chip-row"><span class="di-level">Lv.7</span><span class="di-xp">1,250 XP</span></span>
          <em class="spec-size">Space Grotesk 700 · 11.5px / VT323 · 17px</em>
        {:else}
          <span class="chip-row"><span class="cb-level">LV.7</span><span class="cb-xp">1,250 XP</span></span>
          <em class="spec-size">Chakra Petch 700 · 11.5px / VT323 · 17px</em>
        {/if}
      </div>

      <div class="spec-cell">
        <span class="spec-tag">Stat tile</span>
        {#if variant === 'current'}
          <span class="stat-tile"><span class="cur-stat-label">Score</span><strong class="cur-stat-value">87%</strong></span>
          <em class="spec-size">VT323 label 12px / VT323 number 25.6px</em>
        {:else if variant === 'discipline'}
          <span class="stat-tile"><span class="di-stat-label">Score</span><strong class="di-stat-value">87%</strong></span>
          <em class="spec-size">Space Grotesk label 12.5px / VT323 number 27px tabular</em>
        {:else}
          <span class="stat-tile"><span class="cb-stat-label">Score</span><strong class="cb-stat-value">87%</strong></span>
          <em class="spec-size">Chakra Petch label 12.5px / VT323 number 27px tabular</em>
        {/if}
      </div>

      <div class="spec-cell">
        <span class="spec-tag">Play caption</span>
        {#if variant === 'current'}
          <span class="cur-caption">Click the grid to start</span>
          <em class="spec-size">Press Start 2P · 8px</em>
        {:else if variant === 'discipline'}
          <span class="di-caption">Click the grid to start</span>
          <em class="spec-size">Space Grotesk 600 · 12.8px, wide tracking</em>
        {:else}
          <span class="cb-caption">Click the grid to start</span>
          <em class="spec-size">Chakra Petch 600 · 12.8px, wide tracking</em>
        {/if}
      </div>
    </div>
  </div>

  {#if variant === 'current'}
    <ul class="study-notes">
      <li>Press Start 2P is the theme's display font for everything — so buttons, chips and captions get shrunk to 8–15px to fit, exactly where a wide pixel face is least legible.</li>
    </ul>
  {:else if variant === 'discipline'}
    <ul class="study-notes">
      <li>Keeps both existing fonts, adds rules: Press Start 2P only for one marquee moment per screen, never below 0.85rem.</li>
      <li>VT323 stays for numbers and eyebrows but never below 1.05rem — it draws ~30% smaller than its declared size.</li>
      <li>Everything interactive (buttons, chips, captions) moves to Space Grotesk 600–700, which the arcade theme already loads.</li>
    </ul>
  {:else}
    <ul class="study-notes">
      <li>New cabinet stack: Russo One for display (reads arcade at any size), Chakra Petch for UI text, VT323 kept for numerals.</li>
      <li>Press Start 2P retires to two ceremonial stamps — the logo and STAGE CLEAR — where it can sit at full size.</li>
      <li>Two extra Google Fonts (~30 KB); loaded on this page only for the demo.</li>
    </ul>
  {/if}
</article>

<style>
  .type-study { width: min(100%, 760px); margin-inline: auto; }
  .concept-intro { display: grid; grid-template-columns: auto 1fr; gap: 0.85rem; align-items: start; margin-bottom: 0.8rem; padding-inline: 0.25rem; }
  .concept-number { display: grid; width: 2.45rem; height: 2.45rem; place-items: center; border: 1px solid var(--line-strong); border-radius: 13px; color: var(--accent-strong); background: var(--accent-soft); font: 800 0.7rem/1 var(--mono); }
  .intro-current .concept-number { color: var(--muted); background: transparent; border-style: dashed; }
  .concept-intro p { margin: 0 0 0.12rem; color: var(--accent-strong); font: 750 0.62rem/1 var(--mono); letter-spacing: 0.12em; text-transform: uppercase; }
  .intro-current p { color: var(--muted); }
  .concept-intro h3 { margin: 0 0 0.25rem; color: var(--text); font: 800 clamp(1.08rem, 3vw, 1.4rem)/1.15 var(--display); letter-spacing: -0.035em; }
  .concept-intro div > span { color: var(--muted); font-size: 0.82rem; line-height: 1.45; }

  /* Fixed arcade-dark stage: the study compares arcade type on arcade ground */
  .stage {
    padding: clamp(0.9rem, 3vw, 1.2rem);
    border: 1px solid color-mix(in srgb, var(--accent) 38%, rgba(255, 255, 255, 0.14));
    border-radius: 20px;
    color: #f0eaff;
    background:
      radial-gradient(circle at 88% 4%, rgba(124, 58, 237, 0.25), transparent 34%),
      #140925;
  }
  .stage-current { border-style: dashed; }

  .spec-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(13.5rem, 1fr)); gap: 0.6rem; }
  .spec-cell { display: grid; align-content: start; gap: 0.55rem; min-height: 7.25rem; padding: 0.8rem; border: 1px solid rgba(167, 139, 250, 0.22); border-radius: 12px; background: rgba(255, 255, 255, 0.025); }
  .spec-tag { color: rgba(240, 234, 255, 0.55); font: 600 0.68rem/1 var(--ui); letter-spacing: 0.14em; text-transform: uppercase; }
  .spec-size { margin-top: auto; color: rgba(240, 234, 255, 0.62); font-size: 0.72rem; font-style: normal; line-height: 1.4; }

  button { cursor: pointer; }
  .chip-row { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
  .stat-tile { display: grid; gap: 0.2rem; }

  /* ===== CURRENT (production arcade rules) ===== */
  .cur-title { font: 400 1.25rem/1.5 'Press Start 2P', monospace; text-shadow: 0 0 14px rgba(167, 139, 250, 0.95); }
  .cur-eyebrow { color: #9d8ec7; font: 400 0.75rem/1.4 'VT323', monospace; letter-spacing: 0.18em; text-transform: uppercase; }
  .cur-button { width: fit-content; padding: 0.75rem 1.25rem; border: 1px solid rgba(167, 139, 250, 0.45); border-radius: 12px; color: #cdbcff; background: rgba(124, 58, 237, 0.18); font: 400 0.95rem/1.4 'Press Start 2P', monospace; }
  .cur-level { padding: 0.2rem 0.5rem; border: 1px solid rgba(167, 139, 250, 0.38); border-radius: 999px; color: #cdbcff; background: rgba(124, 58, 237, 0.18); font: 400 0.55rem/1.6 'Press Start 2P', monospace; }
  .cur-xp { color: #ffda57; font: 400 0.875rem/1 'VT323', monospace; text-shadow: 0 0 10px rgba(255, 218, 87, 0.55); }
  .cur-stat-label { color: #9d8ec7; font: 400 0.75rem/1 'VT323', monospace; letter-spacing: 0.18em; text-transform: uppercase; }
  .cur-stat-value { font: 400 1.6rem/1 'VT323', monospace; }
  .cur-caption { color: #9d8ec7; font: 400 0.5rem/1.6 'Press Start 2P', monospace; letter-spacing: 0.08em; text-transform: uppercase; }

  /* ===== OPTION A — discipline pass (same fonts, new rules) ===== */
  .di-title { font: 400 1.05rem/1.7 'Press Start 2P', monospace; text-shadow: 0 0 14px rgba(167, 139, 250, 0.95); }
  .di-eyebrow { color: #b7a9dd; font: 400 1.05rem/1.2 'VT323', monospace; letter-spacing: 0.14em; text-transform: uppercase; }
  .di-button { width: fit-content; padding: 0.72rem 1.35rem; border: 1px solid rgba(167, 139, 250, 0.55); border-radius: 12px; color: #cdbcff; background: rgba(124, 58, 237, 0.2); font: 700 0.95rem/1.2 'Space Grotesk', sans-serif; letter-spacing: 0.02em; }
  .di-level { padding: 0.22rem 0.55rem; border: 1px solid rgba(167, 139, 250, 0.45); border-radius: 999px; color: #cdbcff; background: rgba(124, 58, 237, 0.2); font: 700 0.72rem/1.3 'Space Grotesk', sans-serif; }
  .di-xp { color: #ffda57; font: 400 1.05rem/1 'VT323', monospace; font-variant-numeric: tabular-nums; text-shadow: 0 0 10px rgba(255, 218, 87, 0.55); }
  .di-stat-label { color: #b7a9dd; font: 600 0.78rem/1 'Space Grotesk', sans-serif; letter-spacing: 0.16em; text-transform: uppercase; }
  .di-stat-value { font: 400 1.7rem/1 'VT323', monospace; font-variant-numeric: tabular-nums; }
  .di-caption { color: #b7a9dd; font: 600 0.8rem/1.4 'Space Grotesk', sans-serif; letter-spacing: 0.16em; text-transform: uppercase; }

  /* ===== OPTION B — cabinet stack (Russo One + Chakra Petch) ===== */
  .cb-title { font: 400 1.35rem/1.25 'Russo One', 'Space Grotesk', sans-serif; letter-spacing: 0.04em; text-shadow: 0 0 14px rgba(167, 139, 250, 0.95); }
  .cb-eyebrow { color: #b7a9dd; font: 600 0.78rem/1.3 'Chakra Petch', 'Space Grotesk', sans-serif; letter-spacing: 0.18em; text-transform: uppercase; }
  .cb-button { width: fit-content; padding: 0.72rem 1.35rem; border: 1px solid rgba(167, 139, 250, 0.55); border-radius: 12px; color: #cdbcff; background: rgba(124, 58, 237, 0.2); font: 400 0.95rem/1.2 'Russo One', 'Space Grotesk', sans-serif; letter-spacing: 0.03em; }
  .cb-level { padding: 0.22rem 0.55rem; border: 1px solid rgba(167, 139, 250, 0.45); border-radius: 999px; color: #cdbcff; background: rgba(124, 58, 237, 0.2); font: 700 0.72rem/1.3 'Chakra Petch', sans-serif; }
  .cb-xp { color: #ffda57; font: 400 1.05rem/1 'VT323', monospace; font-variant-numeric: tabular-nums; text-shadow: 0 0 10px rgba(255, 218, 87, 0.55); }
  .cb-stat-label { color: #b7a9dd; font: 600 0.78rem/1 'Chakra Petch', sans-serif; letter-spacing: 0.16em; text-transform: uppercase; }
  .cb-stat-value { font: 400 1.7rem/1 'VT323', monospace; font-variant-numeric: tabular-nums; }
  .cb-caption { color: #b7a9dd; font: 600 0.8rem/1.4 'Chakra Petch', sans-serif; letter-spacing: 0.16em; text-transform: uppercase; }

  .study-notes { display: grid; gap: 0.3rem; margin: 0.7rem 0 0; padding-left: 1.1rem; }
  .study-notes li { color: var(--muted); font-size: 0.82rem; line-height: 1.5; }
  .study-notes li::marker { color: var(--accent-strong); }
</style>
