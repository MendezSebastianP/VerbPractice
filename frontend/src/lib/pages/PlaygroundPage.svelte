<script lang="ts">
  // Public experiment bench (/playground) — no login required. Anything we
  // want to evaluate before shipping gets a section here; once a winner ships,
  // the experiment is cleaned out (past ones live in git history: answer
  // feedback, logos, word selection, primary button, photo capture entry).
  import { navigate } from '../router';

  function setTheme(next: 'light' | 'dark' | 'arcade'): void {
    document.documentElement.setAttribute('data-theme', next);
  }
</script>

<section class="pg-shell">
  <header class="glass-panel strong-panel pg-header">
    <div>
      <p class="eyebrow">Playground · experiments before they ship</p>
      <h1 class="pg-title">VerbPractice Lab</h1>
      <p class="section-copy">Public sandbox — no login needed. Switch the preview theme to judge each option everywhere.</p>
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

  <article class="glass-panel pg-empty">
    <p class="eyebrow">Nothing cooking</p>
    <h2>The bench is clean</h2>
    <p class="section-copy">
      Every open experiment has shipped. The next idea worth trying before it goes live lands here.
    </p>
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

  .pg-empty {
    text-align: center;
    padding-block: 2.5rem;
  }

  .pg-empty h2 {
    margin: 0.3rem 0 0.5rem;
    font-family: var(--display);
  }
</style>
