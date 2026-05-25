<script lang="ts">
  import { onMount } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import { navigate } from '../router';
  import type { DashboardPayload } from '../types';

  type ModeCard = DashboardPayload['mode_cards'][number];

  let loading = true;
  let error = '';
  let data: DashboardPayload | null = null;

  function mergedFocusItems(cards: ModeCard[]) {
    const byKey = new Map<string, ModeCard['focus_items'][number]>();

    for (const card of cards) {
      for (const item of card.focus_items) {
        const key = `${item.item_type}:${item.label}:${item.language_pair}`;
        const existing = byKey.get(key);
        if (!existing || item.probability > existing.probability) {
          byKey.set(key, item);
        }
      }
    }

    return [...byKey.values()].sort((left, right) => right.probability - left.probability).slice(0, 6);
  }

  function verbLabCards(cards: ModeCard[]): ModeCard[] {
    const verbCards = cards.filter((card) => card.mode === 'verb_translation' || card.mode === 'conjugation');
    if (!verbCards.length) {
      return cards;
    }

    const combined: ModeCard = {
      mode: 'verb_lab',
      title: 'Verb Lab',
      href: '/training/verbs',
      description: 'Move between verb translation drills and tense tables from one shared workspace.',
      pair_label: verbCards.map((card) => card.pair_label).find(Boolean) || 'Verb workspace',
      total: verbCards.reduce((sum, card) => sum + card.total, 0),
      unlocked: verbCards.reduce((sum, card) => sum + card.unlocked, 0),
      mastered: verbCards.reduce((sum, card) => sum + card.mastered, 0),
      practiced: verbCards.reduce((sum, card) => sum + card.practiced, 0),
      avg_probability: Math.round(
        verbCards.reduce((sum, card) => sum + card.avg_probability * Math.max(card.total, 1), 0)
          / verbCards.reduce((sum, card) => sum + Math.max(card.total, 1), 0),
      ),
      focus_items: mergedFocusItems(verbCards),
    };

    const output: ModeCard[] = [];
    let inserted = false;

    for (const card of cards) {
      if (card.mode === 'verb_translation' || card.mode === 'conjugation') {
        if (!inserted) {
          output.push(combined);
          inserted = true;
        }
        continue;
      }
      output.push(card);
    }

    return output;
  }

  function sessionLabel(mode: string): string {
    if (mode === 'word_translation') {
      return 'Words';
    }
    if (mode === 'verb_translation') {
      return 'Verb Lab · Translation';
    }
    if (mode === 'conjugation') {
      return 'Verb Lab · Tables';
    }
    return mode.replace('_', ' ');
  }

  $: cards = data ? verbLabCards(data.mode_cards) : [];
  $: verbLabRuns = (data?.mode_counts.verb_translation || 0) + (data?.mode_counts.conjugation || 0);

  async function load(): Promise<void> {
    loading = true;
    error = '';
    try {
      data = await api.dashboard();
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to load dashboard';
    } finally {
      loading = false;
    }
  }

  onMount(load);
</script>

<style>
  .dashboard-stack {
    max-width: 980px;
    margin-inline: auto;
    width: 100%;
  }
</style>

{#if loading}
  <section class="dashboard-grid loading-grid">
    <div class="glass-panel skeleton-card"></div>
    <div class="glass-panel skeleton-card"></div>
    <div class="glass-panel skeleton-card"></div>
  </section>
{:else if error}
  <section class="glass-panel">
    <div class="feedback-banner error-banner">{error}</div>
  </section>
{:else if data}
  <section class="dashboard-stack" in:fade={{ duration: 180 }}>
    <article class="hero-grid glass-panel strong-panel">
      <div class="hero-copy-block">
        <h1>Welcome back, {data.user.username}</h1>
        <p class="hero-copy">
          Pick a mode below to resume practice. Your progress is tracked per language pair.
        </p>

        <div class="hero-actions">
          <button class="primary-button" type="button" on:click={() => navigate('/training/words')}>Resume vocabulary</button>
          <button class="secondary-button" type="button" on:click={() => navigate('/training/verbs')}>Open verb lab</button>
        </div>
      </div>

      <div class="hero-stats">
        <div class="stat-card compact-stat">
          <span>Tracked items</span>
          <strong>{data.overall.total}</strong>
        </div>
        <div class="stat-card compact-stat">
          <span>Mastered items</span>
          <strong>{data.overall.mastered}</strong>
        </div>
      </div>
    </article>

    <section class="mode-card-grid">
      {#each cards as card, index}
        <button class="mode-card glass-panel" type="button" on:click={() => navigate(card.href)} in:fly={{ y: 20, duration: 180, delay: index * 40 }}>
          <div class="mode-card-top">
            <div>
              <p class="eyebrow">{card.pair_label}</p>
              <h2>{card.title}</h2>
            </div>
            <span class="pill-chip">{card.practiced} practiced</span>
          </div>
          <p class="mode-description">{card.description}</p>
          <div class="metric-grid tight-grid">
            <div class="stat-card compact-stat">
              <span>Unlocked</span>
              <strong>{card.unlocked}</strong>
            </div>
            <div class="stat-card compact-stat">
              <span>Mastered</span>
              <strong>{card.mastered}</strong>
            </div>
            <div class="stat-card compact-stat">
              <span>Pressure</span>
              <strong>{card.avg_probability}</strong>
            </div>
          </div>
          <div class="tag-row">
            {#each card.focus_items.slice(0, 3) as item}
              <span class="mini-tag">{item.label}</span>
            {:else}
              <span class="mini-tag muted-tag">Start a session to surface focus items.</span>
            {/each}
          </div>
        </button>
      {/each}
    </section>

    <section class="dashboard-grid bottom-grid">
      <article class="glass-panel">
        <div class="section-head">
          <div>
            <p class="eyebrow">Momentum</p>
            <h2>Today at a glance</h2>
          </div>
        </div>
        <div class="metric-grid glance-grid">
          <div class="stat-card compact-stat"><span>Completed sessions</span><strong>{data.completed_sessions}</strong></div>
          <div class="stat-card compact-stat"><span>Finished today</span><strong>{data.today_sessions}</strong></div>
          <div class="stat-card compact-stat"><span>Word runs</span><strong>{data.mode_counts.word_translation || 0}</strong></div>
          <div class="stat-card compact-stat"><span>Verb lab runs</span><strong>{verbLabRuns}</strong></div>
        </div>

        {#if data.active_sessions.length}
          <div class="resume-strip">
            <p class="eyebrow">Resume sessions</p>
            <div class="resume-grid">
              {#each data.active_sessions as session}
                <button class="resume-card" type="button" on:click={() => navigate(session.href)}>
                  <strong>{session.title}</strong>
                  <span>{session.language_pair}</span>
                  <span>{session.progress_current}/{session.progress_total}</span>
                </button>
              {/each}
            </div>
          </div>
        {/if}
      </article>

      <article class="glass-panel">
        <div class="section-head">
          <div>
            <p class="eyebrow">History</p>
            <h2>Recent completed sessions</h2>
          </div>
        </div>
        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>Mode</th>
                <th>Pair</th>
                <th>Score</th>
                <th>Completed</th>
              </tr>
            </thead>
            <tbody>
              {#each data.recent_sessions as session}
                <tr>
                  <td>{sessionLabel(session.mode)}</td>
                  <td>{session.language_pair}</td>
                  <td>{session.score === null ? '-' : `${session.score.toFixed(1)}%`}</td>
                  <td>{session.completed_at ? new Date(session.completed_at).toLocaleString() : '-'}</td>
                </tr>
              {:else}
                <tr><td colspan="4">No completed sessions yet.</td></tr>
              {/each}
            </tbody>
          </table>
        </div>
      </article>
    </section>

  </section>
{/if}
