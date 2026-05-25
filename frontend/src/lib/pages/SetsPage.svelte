<script lang="ts">
  import { onMount } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import { navigate } from '../router';
  import type { TagEntry, WordSetDetail, WordSetSummary } from '../types';

  export let csrfToken = '';
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;

  let loading = true;
  let error = '';
  let sets: WordSetSummary[] = [];
  let tags: TagEntry[] = [];

  let creating = false;
  let showCreate = false;
  let createName = '';
  let createDescription = '';
  let createKind: 'manual' | 'smart' = 'smart';
  let createTagSlugs = new Set<string>();

  let detail: WordSetDetail | null = null;
  let detailLoading = false;

  async function load(): Promise<void> {
    loading = true;
    error = '';
    try {
      const [listResp, tagResp] = await Promise.all([api.listWordSets(), api.listTags()]);
      sets = listResp.sets;
      tags = tagResp.tags;
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to load sets';
    } finally {
      loading = false;
    }
  }

  async function submitCreate(): Promise<void> {
    if (!createName.trim()) {
      return;
    }
    if (createKind === 'smart' && createTagSlugs.size === 0) {
      notify('Pick at least one tag for a smart set.', 'error');
      return;
    }
    creating = true;
    try {
      const summary = await api.createWordSet({
        name: createName.trim(),
        description: createDescription.trim() || undefined,
        kind: createKind,
        filter_tag_slugs: Array.from(createTagSlugs),
        csrf_token: csrfToken,
      });
      sets = [summary, ...sets];
      showCreate = false;
      createName = '';
      createDescription = '';
      createKind = 'smart';
      createTagSlugs = new Set();
      notify('Set created.', 'success');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to create set', 'error');
    } finally {
      creating = false;
    }
  }

  function toggleCreateTag(slug: string): void {
    const next = new Set(createTagSlugs);
    if (next.has(slug)) {
      next.delete(slug);
    } else {
      next.add(slug);
    }
    createTagSlugs = next;
  }

  async function openDetail(setId: number): Promise<void> {
    detailLoading = true;
    try {
      detail = await api.getWordSet(setId);
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to load set', 'error');
    } finally {
      detailLoading = false;
    }
  }

  async function removeWord(wordId: number): Promise<void> {
    if (!detail) {
      return;
    }
    try {
      await api.removeWordFromSet(detail.id, wordId, csrfToken);
      detail = {
        ...detail,
        words: detail.words.filter((w) => w.word_id !== wordId),
        word_count: detail.word_count - 1,
      };
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to remove', 'error');
    }
  }

  async function destroySet(setId: number): Promise<void> {
    if (!confirm('Delete this set?')) {
      return;
    }
    try {
      await api.deleteWordSet(setId, csrfToken);
      sets = sets.filter((s) => s.id !== setId);
      if (detail?.id === setId) {
        detail = null;
      }
      notify('Set deleted.', 'info');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to delete', 'error');
    }
  }

  function practiceSet(setId: number): void {
    navigate(`/training/words?set=${setId}`);
  }

  function tagLabel(slug: string): string {
    return tags.find((t) => t.slug === slug)?.display_name ?? slug;
  }

  function groupedTags(): { kind: string; tags: TagEntry[] }[] {
    const groups = new Map<string, TagEntry[]>();
    const visibleTags = tags.filter(
      (tag) => !tag.applies_to.length || tag.applies_to.includes('word'),
    );
    for (const t of visibleTags) {
      const arr = groups.get(t.kind) || [];
      arr.push(t);
      groups.set(t.kind, arr);
    }
    return Array.from(groups.entries()).map(([kind, tags]) => ({ kind, tags }));
  }

  onMount(load);
</script>

{#if loading}
  <section class="dashboard-grid loading-grid">
    <div class="glass-panel skeleton-card"></div>
  </section>
{:else if error}
  <section class="glass-panel">
    <div class="feedback-banner error-banner">{error}</div>
  </section>
{:else}
  <section class="dashboard-stack" in:fade={{ duration: 180 }}>
    <article class="glass-panel strong-panel">
      <div class="section-head">
        <div>
          <p class="eyebrow">Vocabulary</p>
          <h1>Word sets</h1>
        </div>
        <button class="primary-button" type="button" on:click={() => (showCreate = !showCreate)}>
          {showCreate ? 'Cancel' : '+ New set'}
        </button>
      </div>
      <p class="section-copy">
        Group words into themed sets to practice them together. <strong>Manual sets</strong> are explicit
        lists you curate. <strong>Smart sets</strong> auto-collect any word tagged with the filters you pick.
      </p>

      {#if showCreate}
        <div class="glass-panel" style="margin-top: 1rem; padding: 1rem;" in:fly={{ y: -10, duration: 160 }}>
          <p class="eyebrow">New set</p>

          <input
            class="answer-input"
            type="text"
            placeholder="Name (e.g. 'Trip to Lisbon')"
            bind:value={createName}
            style="margin-top: 0.5rem;"
          />
          <input
            class="answer-input"
            type="text"
            placeholder="Optional description"
            bind:value={createDescription}
            style="margin-top: 0.5rem;"
          />

          <div style="margin-top: 0.75rem;">
            <p class="eyebrow">Kind</p>
            <div class="option-row">
              <button
                class="option-chip"
                class:option-on={createKind === 'smart'}
                type="button"
                on:click={() => (createKind = 'smart')}
              >
                Smart (auto-collect by tags)
              </button>
              <button
                class="option-chip"
                class:option-on={createKind === 'manual'}
                type="button"
                on:click={() => (createKind = 'manual')}
              >
                Manual (curated list)
              </button>
            </div>
          </div>

          {#if createKind === 'smart'}
            <div style="margin-top: 0.75rem;">
              <p class="eyebrow">Filter tags (word must have ALL selected)</p>
              {#each groupedTags() as group}
                <p style="margin: 0.5rem 0 0.25rem; font-size: 0.8rem; opacity: 0.7;">
                  {group.kind}
                </p>
                <div class="tag-row">
                  {#each group.tags as t}
                    <button
                      class="option-chip"
                      class:option-on={createTagSlugs.has(t.slug)}
                      type="button"
                      on:click={() => toggleCreateTag(t.slug)}
                    >
                      {t.display_name}
                    </button>
                  {/each}
                </div>
              {/each}
            </div>
          {:else}
            <p class="section-copy" style="margin-top: 0.5rem; font-size: 0.85rem;">
              You'll add words to this set one at a time from the Add Word page or from the set detail view.
            </p>
          {/if}

          <div class="hero-actions" style="margin-top: 1rem;">
            <button class="primary-button" type="button" on:click={submitCreate} disabled={creating}>
              {creating ? 'Creating…' : 'Create set'}
            </button>
            <button class="ghost-button" type="button" on:click={() => (showCreate = false)}>Cancel</button>
          </div>
        </div>
      {/if}
    </article>

    <section class="mode-card-grid">
      {#each sets as set (set.id)}
        <article class="mode-card glass-panel" in:fly={{ y: 12, duration: 160 }}>
          <div class="mode-card-top">
            <div>
              <p class="eyebrow">{set.kind}{set.owner_user_id === null ? ' · system' : ''}</p>
              <h2>{set.name}</h2>
            </div>
            <span class="pill-chip">{set.word_count} words</span>
          </div>
          {#if set.description}
            <p class="mode-description">{set.description}</p>
          {/if}
          {#if set.filter_tag_slugs.length}
            <div class="tag-row">
              {#each set.filter_tag_slugs as slug}
                <span class="mini-tag">{tagLabel(slug)}</span>
              {/each}
            </div>
          {/if}
          <div class="trainer-actions" style="margin-top: 0.75rem;">
            <button class="primary-button" type="button" on:click={() => practiceSet(set.id)} disabled={set.word_count === 0}>
              Practice
            </button>
            <button class="secondary-button" type="button" on:click={() => openDetail(set.id)}>
              View
            </button>
            {#if set.owner_user_id !== null}
              <button class="ghost-button" type="button" on:click={() => destroySet(set.id)}>
                Delete
              </button>
            {/if}
          </div>
        </article>
      {:else}
        <article class="glass-panel">
          <p class="empty-copy">No sets yet. Click "+ New set" to create one.</p>
        </article>
      {/each}
    </section>

    {#if detail}
      <article class="glass-panel" in:fly={{ y: 12, duration: 160 }}>
        <div class="section-head">
          <div>
            <p class="eyebrow">{detail.kind} set</p>
            <h2>{detail.name}</h2>
          </div>
          <button class="ghost-button" type="button" on:click={() => (detail = null)}>Close</button>
        </div>
        {#if detail.description}
          <p class="section-copy">{detail.description}</p>
        {/if}
        {#if detail.filter_tag_slugs.length}
          <div class="tag-row">
            {#each detail.filter_tag_slugs as slug}
              <span class="mini-tag">{tagLabel(slug)}</span>
            {/each}
          </div>
        {/if}

        <p class="eyebrow" style="margin-top: 1rem;">Words ({detail.words.length})</p>
        {#if detail.words.length === 0}
          <p class="empty-copy">No matching words yet.</p>
        {:else}
          <div class="list-stack">
            {#each detail.words as w}
              <div class="list-row">
                <div>
                  <strong>{w.text}</strong>
                  <p>{w.language_code}</p>
                </div>
                <div class="row-metrics">
                  {#if detail.kind === 'manual'}
                    <button
                      class="ghost-button"
                      type="button"
                      on:click={() => removeWord(w.word_id)}
                      style="font-size: 0.8rem;"
                    >
                      remove
                    </button>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </article>
    {:else if detailLoading}
      <article class="glass-panel">
        <p>Loading set…</p>
      </article>
    {/if}
  </section>
{/if}
