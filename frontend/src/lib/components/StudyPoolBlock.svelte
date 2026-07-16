<script lang="ts">
  import type { StudyConjugationEntry, StudyPoolResponse, StudyTranslationEntry } from '../types';

  export let mode: 'words' | 'verbs' | 'conjugation';
  export let expanded = false;
  export let loading = false;
  export let error = '';
  export let entries: StudyPoolResponse['entries'] = [];
  export let onToggle: () => void = () => {};

  let activeVerbId: number | null = null;
  $: conjugationEntries = entries.filter(isConjugation);
  $: if (conjugationEntries.length && !conjugationEntries.some((entry) => entry.item_id === activeVerbId)) {
    activeVerbId = conjugationEntries[0].item_id;
  }
  $: activeVerb = conjugationEntries.find((entry) => entry.item_id === activeVerbId) || conjugationEntries[0];

  function isConjugation(entry: StudyTranslationEntry | StudyConjugationEntry): entry is StudyConjugationEntry {
    return 'tenses' in entry;
  }

  function translationEntries(): StudyTranslationEntry[] {
    return entries.filter((entry): entry is StudyTranslationEntry => !isConjugation(entry));
  }

  function groupEntries(group: 'newest' | 'focus'): StudyTranslationEntry[] {
    return translationEntries().filter((entry) => entry.group === group);
  }

  function verbGroup(group: 'newest' | 'focus'): StudyConjugationEntry[] {
    return conjugationEntries.filter((entry) => entry.group === group);
  }
</script>

<section class="study-pool-block" class:study-open={expanded}>
  <button class="study-pool-trigger" type="button" aria-expanded={expanded} on:click={onToggle}>
    <span class="study-pool-icon" aria-hidden="true">◫</span>
    <span class="study-pool-trigger-copy">
      <strong>Study before you play</strong>
      <small>6 newest + 6 that need more practice · no duplicates</small>
    </span>
    <span class="study-pool-action">{expanded ? 'Close' : 'Open'} <i aria-hidden="true">{expanded ? '↑' : '↓'}</i></span>
  </button>

  {#if expanded}
    <div class="study-pool-content">
      {#if loading}
        <p class="study-pool-state">Loading your study pool…</p>
      {:else if error}
        <p class="study-pool-state study-pool-error">{error}</p>
      {:else if entries.length === 0}
        <p class="study-pool-state">No study items are available for this selection yet.</p>
      {:else if mode === 'conjugation' && activeVerb}
        <div class="study-verb-layout">
          <div class="study-verb-picker">
            {#each ['newest', 'focus'] as group}
              {@const groupItems = verbGroup(group as 'newest' | 'focus')}
              {#if groupItems.length}
                <p class:focus-heading={group === 'focus'}>{group === 'newest' ? 'Newest 6' : 'Needs more practice'}</p>
                <div class="study-verb-buttons">
                  {#each groupItems as entry}
                    <button type="button" class:active={entry.item_id === activeVerb.item_id} on:click={() => (activeVerbId = entry.item_id)}>
                      <strong>{entry.prompt}</strong>
                    </button>
                  {/each}
                </div>
              {/if}
            {/each}
          </div>
          <div class="study-verb-detail">
            <header><div><span>{activeVerb.language} · conjugation</span><h3>{activeVerb.prompt}</h3></div></header>
            {#each activeVerb.tenses as tense}
              <div class="study-tense">
                <h4>{tense.tense}</h4>
                <div class="study-table">
                  <div class="study-row study-header"><span>Pronoun</span><span>Form</span></div>
                  {#each tense.forms as form}
                    <div class="study-row"><strong>{form.pronoun}</strong><span>{form.form}</span></div>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        </div>
      {:else}
        <div class="study-table">
          <div class="study-row study-header"><span>{mode === 'words' ? 'Word' : 'Infinitive'}</span><span>Translation</span></div>
          {#each ['newest', 'focus'] as group}
            {@const groupItems = groupEntries(group as 'newest' | 'focus')}
            {#if groupItems.length}
              <div class:focus-group={group === 'focus'} class="study-group"><strong>{group === 'newest' ? 'Newest 6' : 'Needs more practice'}</strong><small>{group === 'newest' ? 'Recently added' : 'Items you find harder'}</small></div>
              {#each groupItems as entry}
                <div class="study-row"><strong>{entry.prompt}</strong><span>{entry.answer}</span></div>
              {/each}
            {/if}
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</section>

<style>
  .study-pool-block { --study-violet: #7065e8; --study-coral: #e56f52; display: grid; overflow: hidden; border: 1px solid color-mix(in srgb, var(--study-violet) 36%, var(--line)); border-radius: 14px; background: color-mix(in srgb, var(--surface-strong) 88%, var(--study-violet) 4%); }
  :global(html[data-theme='light']) .study-pool-block { --study-violet: var(--accent); --study-coral: var(--accent-2); border-radius: 9px; }
  .study-pool-trigger { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 0.8rem; align-items: center; width: 100%; min-height: 4.5rem; padding: 0.8rem 1rem; border: 0; color: var(--text); text-align: left; background: linear-gradient(90deg, color-mix(in srgb, var(--study-violet) 10%, var(--surface)), color-mix(in srgb, var(--study-coral) 5%, var(--surface))); }
  .study-pool-trigger:hover { background: linear-gradient(90deg, color-mix(in srgb, var(--study-violet) 15%, var(--surface)), color-mix(in srgb, var(--study-coral) 8%, var(--surface))); }
  .study-pool-icon { display: grid; width: 2.5rem; height: 2.5rem; place-items: center; border-radius: 10px; color: var(--study-violet); background: color-mix(in srgb, var(--study-violet) 13%, transparent); font-size: 1.25rem; }
  .study-pool-trigger-copy { display: grid; gap: 0.25rem; }
  .study-pool-trigger-copy strong { font-size: 1.05rem; line-height: 1.15; }
  .study-pool-trigger-copy small { color: var(--muted); font-size: 0.9rem; line-height: 1.3; }
  .study-pool-action { color: var(--study-violet); font-size: 0.92rem; font-weight: 750; } .study-pool-action i { font-style: normal; }
  .study-pool-content { padding: 1rem; border-top: 1px solid var(--line); }
  .study-pool-state { margin: 0; padding: 1rem; color: var(--muted); font-size: 1rem; text-align: center; } .study-pool-error { color: var(--danger); }
  .study-table { overflow: hidden; border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }
  .study-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); border-bottom: 1px solid var(--line); }
  .study-row:last-child { border-bottom: 0; }
  .study-row > * { min-width: 0; padding: 0.75rem 0.9rem; overflow-wrap: anywhere; font-size: 1rem; line-height: 1.35; }
  .study-row > * + * { border-left: 1px solid var(--line); }
  .study-row strong { color: var(--text); } .study-row > span { color: var(--muted); }
  .study-header { color: var(--study-violet); background: color-mix(in srgb, var(--study-violet) 9%, var(--surface)); font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; }
  .study-header span { color: inherit; font-size: 0.82rem; }
  .study-group { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; padding: 0.6rem 0.9rem; border-bottom: 1px solid var(--line); color: var(--study-violet); background: color-mix(in srgb, var(--study-violet) 9%, transparent); }
  .study-group strong { font-size: 0.92rem; } .study-group small { color: var(--muted); font-size: 0.85rem; }
  .study-group.focus-group { color: var(--study-coral); background: color-mix(in srgb, var(--study-coral) 8%, transparent); }
  .study-verb-layout { display: grid; grid-template-columns: minmax(15rem, 0.75fr) minmax(0, 1.4fr); gap: 1rem; align-items: start; }
  .study-verb-picker { display: grid; gap: 0.55rem; }
  .study-verb-picker > p { margin: 0.2rem 0 0; color: var(--study-violet); font-size: 0.92rem; font-weight: 800; } .study-verb-picker > p.focus-heading { color: var(--study-coral); }
  .study-verb-buttons { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.45rem; }
  .study-verb-buttons button { display: flex; align-items: center; gap: 0.45rem; min-height: 3rem; padding: 0.65rem 0.75rem; border: 1px solid var(--line); border-radius: 9px; color: var(--text); background: var(--surface); text-align: left; }
  .study-verb-buttons button:hover, .study-verb-buttons button.active { border-color: color-mix(in srgb, var(--study-violet) 55%, var(--line)); background: color-mix(in srgb, var(--study-violet) 10%, var(--surface)); }
  .study-verb-buttons strong { min-width: 0; overflow: hidden; text-overflow: ellipsis; font-size: 0.95rem; }
  .study-verb-detail { display: grid; gap: 1rem; }
  .study-verb-detail > header { display: flex; align-items: flex-start; gap: 0.75rem; }
  .study-verb-detail > header span { color: var(--study-violet); font-size: 0.82rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; }
  .study-verb-detail h3 { margin: 0.25rem 0 0; color: var(--text); font-size: 1.65rem; line-height: 1; }
  .study-tense { display: grid; gap: 0.5rem; } .study-tense h4 { margin: 0; color: var(--text); font-size: 1.05rem; }
  @media (max-width: 760px) { .study-verb-layout { grid-template-columns: 1fr; } }
  @media (max-width: 520px) { .study-pool-trigger { grid-template-columns: auto 1fr; } .study-pool-action { grid-column: 2; } .study-verb-buttons { grid-template-columns: 1fr; } .study-row > * { padding: 0.68rem; font-size: 0.94rem; } }
</style>
