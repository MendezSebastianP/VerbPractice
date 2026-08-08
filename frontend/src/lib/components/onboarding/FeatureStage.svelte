<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { FeatureDef, FeatureId } from './onboarding';

  export let feature: FeatureDef;
  export let done = false;
  /** Verb Lab's second tab is gated inside the page, not by route. */
  export let tablesUnlocked = false;

  const dispatch = createEventDispatcher<{
    complete: { id: FeatureId };
    switchTo: { id: FeatureId };
  }>();

  // Stand-in content — the bench never calls the trainer API. Words prompts a
  // single word and expects a single word back; the phrasal stuff belongs in
  // Add Word, where a sense needs explaining.
  const wordPrompt = { term: 'oiseau', direction: 'FR → ES', typed: 'pájaro' };
  const verbPrompt = { term: 'finir', direction: 'FR → EN', typed: 'to finish' };
  const pronouns = ['je', 'tu', 'il/elle', 'nous', 'vous', 'ils/elles'];
  const tableCells = ['finis', 'finis', 'finit', 'finissons', 'finissez', 'finissent'];

  function complete(): void {
    dispatch('complete', { id: feature.id });
  }
</script>

<div class="stage-frame">
  <header class="stage-head">
    <div>
      <p class="stage-kicker">{feature.route}</p>
      <h3>{feature.title}</h3>
      <p class="stage-blurb">{feature.blurb}</p>
    </div>
    {#if done}
      <span class="stage-done">Done</span>
    {/if}
  </header>

  {#if feature.id === 'words'}
    <div class="drill">
      <!-- Anchors mirror the real Words setup screen, which is what the tour
           actually points at: length, direction, then the play control. -->
      <div class="length-row" data-tour="words-length">
        <span class="chip">5</span>
        <span class="chip chip-on">10</span>
        <span class="chip">20</span>
        <span class="setup-note">round length</span>
      </div>

      <div class="direction-row" data-tour="words-direction">
        <span class="dir-code">FR</span>
        <span class="dir-arrow" aria-hidden="true">→</span>
        <span class="dir-code">ES</span>
        <span class="setup-note">swap any time</span>
      </div>

      <div class="drill-prompt">
        <span class="drill-dir">{wordPrompt.direction}</span>
        <strong>{wordPrompt.term}</strong>
        <em class="prompt-answer">{wordPrompt.typed}</em>
      </div>

      <div class="play-row" data-tour="words-play">
        <span class="ctl ctl-strong">▶ Play</span>
        <span class="setup-note">or press Enter</span>
      </div>
    </div>
  {:else if feature.id === 'add-word'}
    <div class="drill">
      <div class="add-row">
        <div class="add-field" data-tour="add-input">
          <span class="field-text">flâner</span>
        </div>
        <button class="photo-button" type="button" data-tour="add-photo" aria-label="Capture from a photo">
          <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M4 8.5h3l1.4-2h7.2L17 8.5h3v9.5H4z" />
            <circle cx="12" cy="13" r="3.1" />
          </svg>
        </button>
      </div>

      <div class="sense-list">
        <p class="sense-head">Senses found</p>
        <label class="sense-row"><input type="radio" checked /><span><strong>to stroll</strong> — wander at leisure with no fixed destination</span></label>
        <label class="sense-row"><input type="radio" /><span><strong>to dawdle</strong> — linger, take longer than needed</span></label>
      </div>

      <div class="pool-note" data-tour="add-pool">
        <span class="pool-dot" aria-hidden="true"></span>
        Saved words join your Words rotation — <strong>128 words</strong> in the pool right now.
      </div>
    </div>
  {:else if feature.id === 'verb-translate'}
    <div class="drill">
      <div class="verb-switch" role="tablist" aria-label="Verb workspace mode" data-tour="verb-switch">
        <button class="verb-tab verb-tab-on" type="button" role="tab" aria-selected="true">
          <strong>Translate</strong><small>Infinitive recall</small>
        </button>
        <button
          class="verb-tab"
          class:verb-tab-locked={!tablesUnlocked}
          type="button"
          role="tab"
          aria-selected="false"
          aria-disabled={!tablesUnlocked ? 'true' : undefined}
          title={tablesUnlocked ? 'Fill tables' : 'Unlocks after a verb translation round'}
          on:click={() => dispatch('switchTo', { id: 'verb-tables' })}
        >
          <strong>Fill tables</strong><small>{tablesUnlocked ? 'Tense by tense' : 'Locked'}</small>
          {#if !tablesUnlocked}
            <svg class="tab-lock" viewBox="0 0 16 16" width="11" height="11" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="3.2" y="7" width="9.6" height="6.4" rx="1.6" />
              <path d="M5.6 7V5.2a2.4 2.4 0 0 1 4.8 0V7" />
            </svg>
          {/if}
        </button>
      </div>

      <div class="drill-prompt">
        <span class="drill-dir">{verbPrompt.direction}</span>
        <strong>{verbPrompt.term}</strong>
        <em class="prompt-answer">{verbPrompt.typed}</em>
      </div>

      <div class="play-row" data-tour="words-play">
        <span class="ctl ctl-strong">▶ Play</span>
        <span class="setup-note">same loop as Words</span>
      </div>
    </div>
  {:else}
    <div class="drill">
      <div class="table-setup" data-tour="tables-setup">
        <span class="chip chip-on">Présent</span>
        <span class="chip">Imparfait</span>
        <span class="chip">Futur simple</span>
        <span class="setup-note">finir · FR</span>
      </div>

      <div class="table-grid">
        {#each pronouns as pronoun, i (pronoun)}
          <div class="grid-row">
            <span class="grid-pronoun">{pronoun}</span>
            <span class="grid-cell" class:cell-empty={i > 3}>{i > 3 ? '' : tableCells[i]}</span>
          </div>
        {/each}
      </div>

      <div class="table-foot">
        <span class="foot-note">Nothing is marked until you submit.</span>
        <span class="ctl ctl-strong">Check table</span>
      </div>
    </div>
  {/if}

  <footer class="stage-foot">
    {#if done}
      <p class="foot-done">You already finished this one — it stays open for good.</p>
    {:else}
      <button class="complete-button" type="button" on:click={complete}>{feature.completeLabel}</button>
      <span class="foot-hint">Stands in for actually finishing the drill.</span>
    {/if}
  </footer>
</div>

<style>
  .stage-frame {
    display: grid;
    gap: 0.9rem;
    padding: 1rem 1.1rem;
    border-radius: 14px;
    border: 1px solid var(--line, rgba(0, 0, 0, 0.14));
    background: var(--surface, rgba(255, 255, 255, 0.7));
  }

  .stage-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .stage-kicker {
    margin: 0 0 0.15rem;
    font-family: var(--mono, monospace);
    font-size: 0.7rem;
    color: var(--muted, #666);
  }

  .stage-head h3 {
    margin: 0 0 0.25rem;
    font-size: 1.08rem;
  }

  .stage-blurb {
    margin: 0;
    max-width: 34rem;
    font-size: 0.8rem;
    line-height: 1.5;
    color: var(--muted, #666);
  }

  .stage-done {
    flex: none;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    background: var(--accent, #4c8);
    color: var(--bg, #fff);
    font-size: 0.62rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-weight: 700;
  }

  .drill {
    display: grid;
    gap: 0.7rem;
    padding: 0.9rem;
    border-radius: 12px;
    background: color-mix(in srgb, var(--bg, #fff) 40%, transparent);
    border: 1px solid var(--line, rgba(0, 0, 0, 0.08));
  }

  /* ---- shared drill bits ---- */
  .drill-prompt {
    display: grid;
    gap: 0.2rem;
    justify-items: center;
    padding: 0.9rem 0.75rem;
    border-radius: 11px;
    background: var(--surface-strong, #fff);
    border: 1px solid var(--line, rgba(0, 0, 0, 0.12));
  }

  .drill-dir {
    font-size: 0.64rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted, #666);
  }

  .drill-prompt strong {
    font-size: 1.5rem;
    font-family: var(--display, inherit);
  }

  .prompt-answer {
    font-style: normal;
    font-size: 0.85rem;
    color: var(--accent-strong, var(--accent, #4c8));
  }

  .length-row,
  .direction-row,
  .play-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .dir-code {
    padding: 0.25rem 0.6rem;
    border-radius: 8px;
    border: 1px solid var(--line, rgba(0, 0, 0, 0.14));
    background: var(--surface-strong, #fff);
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 0.06em;
  }

  .dir-arrow {
    color: var(--muted, #666);
  }

  .field-text {
    flex: 1;
    min-width: 0;
    font-size: 0.88rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .ctl {
    padding: 0.32rem 0.7rem;
    border-radius: 8px;
    border: 1px solid var(--line, rgba(0, 0, 0, 0.14));
    font-size: 0.76rem;
    color: var(--muted, #666);
    background: var(--surface-strong, #fff);
  }

  .ctl-strong {
    border-color: var(--accent, #4c8);
    color: var(--accent-strong, var(--accent, #4c8));
    font-weight: 600;
  }

  /* ---- add word ---- */
  .add-row {
    display: flex;
    gap: 0.5rem;
  }

  .add-field {
    flex: 1;
    display: flex;
    align-items: center;
    padding: 0.55rem 0.7rem;
    border-radius: 10px;
    border: 1px solid var(--accent, #4c8);
    background: var(--surface-strong, #fff);
    font-size: 0.9rem;
  }

  .photo-button {
    flex: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.4rem;
    border-radius: 10px;
    border: 1px solid var(--line-strong, rgba(0, 0, 0, 0.2));
    background: var(--surface-strong, #fff);
    color: var(--text, #111);
    cursor: pointer;
  }

  .sense-list {
    display: grid;
    gap: 0.35rem;
  }

  .sense-head {
    margin: 0;
    font-size: 0.64rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted, #666);
    font-weight: 700;
  }

  .sense-row {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.45rem 0.55rem;
    border-radius: 9px;
    border: 1px solid var(--line, rgba(0, 0, 0, 0.12));
    background: var(--surface-strong, #fff);
    font-size: 0.78rem;
    line-height: 1.45;
  }

  .sense-row input {
    margin-top: 0.15rem;
    accent-color: var(--accent, #4c8);
  }

  .pool-note {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.5rem 0.6rem;
    border-radius: 9px;
    background: var(--accent-soft, rgba(0, 0, 0, 0.05));
    font-size: 0.78rem;
  }

  .pool-dot {
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: var(--accent, #4c8);
    flex: none;
  }

  /* ---- verb switch ---- */
  .verb-switch {
    display: flex;
    gap: 0.4rem;
  }

  .verb-tab {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.05rem;
    position: relative;
    padding: 0.5rem 0.7rem;
    border-radius: 10px;
    border: 1px solid var(--line, rgba(0, 0, 0, 0.14));
    background: var(--surface-strong, #fff);
    color: var(--text, #111);
    font: inherit;
    text-align: left;
    cursor: pointer;
  }

  .verb-tab strong {
    font-size: 0.83rem;
  }

  .verb-tab small {
    font-size: 0.68rem;
    color: var(--muted, #666);
  }

  .verb-tab-on {
    border-color: var(--accent, #4c8);
    background: var(--accent-soft, rgba(0, 0, 0, 0.06));
  }

  .verb-tab-locked {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .tab-lock {
    position: absolute;
    top: 0.5rem;
    right: 0.55rem;
  }

  /* ---- tables ---- */
  .table-setup {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem;
  }

  .chip {
    padding: 0.25rem 0.6rem;
    border-radius: 999px;
    border: 1px solid var(--line, rgba(0, 0, 0, 0.14));
    background: var(--surface-strong, #fff);
    font-size: 0.74rem;
    color: var(--muted, #666);
  }

  .chip-on {
    border-color: var(--accent, #4c8);
    background: var(--accent, #4c8);
    color: var(--bg, #fff);
    font-weight: 600;
  }

  .setup-note {
    margin-left: auto;
    font-family: var(--mono, monospace);
    font-size: 0.72rem;
    color: var(--muted, #666);
  }

  .table-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
    gap: 0.3rem;
  }

  .grid-row {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .grid-pronoun {
    flex: none;
    width: 4.1rem;
    font-size: 0.74rem;
    color: var(--muted, #666);
    text-align: right;
  }

  .grid-cell {
    flex: 1;
    min-width: 0;
    padding: 0.34rem 0.5rem;
    border-radius: 7px;
    border: 1px solid var(--line, rgba(0, 0, 0, 0.14));
    background: var(--surface-strong, #fff);
    font-size: 0.79rem;
  }

  .cell-empty {
    border-style: dashed;
    min-height: 1.75rem;
  }

  .table-foot {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    flex-wrap: wrap;
  }

  .foot-note {
    font-size: 0.73rem;
    color: var(--muted, #666);
  }

  /* ---- footer ---- */
  .stage-foot {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    flex-wrap: wrap;
  }

  .complete-button {
    padding: 0.5rem 1rem;
    border-radius: 10px;
    border: 1px solid var(--accent, #4c8);
    background: var(--accent, #4c8);
    color: var(--bg, #fff);
    font: inherit;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s, transform 0.07s;
  }

  .complete-button:hover {
    background: var(--accent-strong, var(--accent, #4c8));
  }

  .complete-button:active {
    transform: scale(0.97);
  }

  .foot-hint,
  .foot-done {
    margin: 0;
    font-size: 0.74rem;
    color: var(--muted, #666);
  }

  @media (max-width: 560px) {
    .verb-switch {
      flex-direction: column;
    }

    .grid-pronoun {
      width: 3.4rem;
    }
  }
</style>
