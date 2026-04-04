<script lang="ts">
  import { onMount } from 'svelte';
  import { fade, fly } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import { navigate } from '../router';
  import type { DashboardPayload } from '../types';

  export let csrfToken = '';
  export let soundEnabled = false;
  export let onSoundToggle: (enabled: boolean) => Promise<void> | void;
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;

  type ModeCard = DashboardPayload['mode_cards'][number];

  let loading = true;
  let error = '';
  let data: DashboardPayload | null = null;
  let friendUsername = '';

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

  async function toggleSound(): Promise<void> {
    const next = !soundEnabled;
    try {
      await onSoundToggle(next);
      if (data) {
        data = {
          ...data,
          preferences: { sound_enabled: next },
          gamification: { ...data.gamification, sound_enabled: next },
        };
      }
      notify(next ? 'Sound cues enabled.' : 'Sound cues muted.', 'info');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to update sound setting', 'error');
    }
  }

  async function addFriend(): Promise<void> {
    if (!friendUsername.trim()) {
      return;
    }
    try {
      await api.addCircleFriend({ username: friendUsername.trim(), csrf_token: csrfToken });
      friendUsername = '';
      await load();
      notify('Circle updated.', 'success');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to add friend', 'error');
    }
  }

  async function removeFriend(friendUserId: number): Promise<void> {
    try {
      await api.removeCircleFriend(friendUserId, csrfToken);
      await load();
      notify('Removed from circle.', 'info');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to remove friend', 'error');
    }
  }

  onMount(load);
</script>

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
        <p class="eyebrow">Daily cockpit</p>
        <h1>Level {data.user.profile.level} progress for {data.user.username}</h1>
        <p class="hero-copy">
          The whole flow now runs as one client app. Your queue, verb lab, tutor context, and session history stay
          connected while you move between drills.
        </p>

        <div class="hero-actions">
          <button class="primary-button" type="button" on:click={() => navigate('/training/words')}>Resume vocabulary</button>
          <button class="secondary-button" type="button" on:click={() => navigate('/training/verbs')}>Open verb lab</button>
        </div>
      </div>

      <div class="hero-stats">
        <div class="stat-card compact-stat">
          <span>Total XP</span>
          <strong>{data.user.profile.xp}</strong>
        </div>
        <div class="stat-card compact-stat">
          <span>Current streak</span>
          <strong>{data.user.profile.streak_days} days</strong>
        </div>
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

    <section class="dashboard-grid">
      <article class="glass-panel">
        <div class="section-head">
          <div>
            <p class="eyebrow">Weekly challenge</p>
            <h2>{data.gamification.weekly_challenge.title}</h2>
          </div>
          <span class="pill-chip reward-pill">+{data.gamification.weekly_challenge.reward_xp} XP</span>
        </div>
        <p class="section-copy">{data.gamification.weekly_challenge.description}</p>
        <div class="progress-shell">
          <div class="progress-top">
            <span>Progress</span>
            <strong>{data.gamification.weekly_challenge.progress}/{data.gamification.weekly_challenge.target_value}</strong>
          </div>
          <div class="progress-track">
            <span
              class="progress-bar"
              style={`width: ${Math.min(100, (data.gamification.weekly_challenge.progress / Math.max(data.gamification.weekly_challenge.target_value, 1)) * 100)}%`}
            ></span>
          </div>
        </div>
        <div class="tag-row">
          <span class={`mini-tag ${data.gamification.weekly_challenge.completed ? 'reward-badge' : ''}`}>
            {data.gamification.weekly_challenge.completed ? 'Completed this week' : 'In progress'}
          </span>
          <span class="mini-tag">{data.gamification.weekly_challenge.metric_key.replace('_', ' ')}</span>
          <span class="mini-tag">Ends {new Date(data.gamification.weekly_challenge.ends_at).toLocaleDateString()}</span>
        </div>
      </article>

      <article class="glass-panel">
        <div class="section-head">
          <div>
            <p class="eyebrow">Arcade controls</p>
            <h2>Reward layer</h2>
          </div>
          <button class="secondary-button" type="button" on:click={toggleSound}>
            {soundEnabled ? 'Mute cues' : 'Enable cues'}
          </button>
        </div>
        <p class="section-copy">
          Sound cues are optional. Keep them on for the arcade feel, or mute them and keep the reward layer visual-only.
        </p>
        <div class="tag-row">
          {#each data.gamification.badges.slice(0, 6) as badge}
            <span class="mini-tag reward-badge">{badge.title}</span>
          {:else}
            <span class="mini-tag muted-tag">Badges unlock as you build streaks, perfect runs, and mastery.</span>
          {/each}
        </div>
        <div class="list-stack">
          {#each data.gamification.recent_xp.slice(0, 4) as event}
            <div class="list-row">
              <div>
                <strong>+{event.amount} XP</strong>
                <p>{event.reason.replace(/_/g, ' ')}</p>
              </div>
              <div class="row-metrics">
                <span>{event.created_at ? new Date(event.created_at).toLocaleString() : '-'}</span>
              </div>
            </div>
          {/each}
        </div>
      </article>
    </section>

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

    <section class="dashboard-grid">
      <article class="glass-panel">
        <div class="section-head">
          <div>
            <p class="eyebrow">Focus queue</p>
            <h2>Items asking for another pass</h2>
          </div>
        </div>
        <div class="list-stack">
          {#each data.overall.focus_items as item}
            <div class="list-row">
              <div>
                <strong>{item.label}</strong>
                <p>{item.item_type.replace('_', ' ')} · {item.language_pair}</p>
              </div>
              <div class="row-metrics">
                <span>Weight {item.probability}</span>
                <span>{item.accuracy === null ? 'New item' : `${item.accuracy}% accuracy`}</span>
              </div>
            </div>
          {:else}
            <p class="empty-copy">Your focus queue will populate once you complete a few runs.</p>
          {/each}
        </div>
      </article>

      <article class="glass-panel">
        <div class="section-head">
          <div>
            <p class="eyebrow">Tutor memory</p>
            <h2>Recent AI context</h2>
          </div>
          <button class="text-button" type="button" on:click={() => navigate('/chat')}>Open chat</button>
        </div>
        <div class="list-stack">
          {#each data.recent_messages as message}
            <div class={`message-card ${message.role}`}>
              <span>{message.role}</span>
              <p>{message.content}</p>
            </div>
          {:else}
            <p class="empty-copy">No tutor history yet.</p>
          {/each}
        </div>
      </article>
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

    <section class="dashboard-grid bottom-grid">
      <article class="glass-panel">
        <div class="section-head">
          <div>
            <p class="eyebrow">Leaderboards</p>
            <h2>Global and weekly pace</h2>
          </div>
        </div>
        <div class="dashboard-grid compact-dual">
          <div class="table-scroll">
            <table class="data-table">
              <thead><tr><th>Global</th><th>Level</th><th>XP</th><th>Streak</th></tr></thead>
              <tbody>
                {#each data.gamification.global_leaderboard as row}
                  <tr><td>{row.username}</td><td>{row.level}</td><td>{row.xp}</td><td>{row.streak_days}</td></tr>
                {/each}
              </tbody>
            </table>
          </div>
          <div class="table-scroll">
            <table class="data-table">
              <thead><tr><th>Weekly</th><th>XP</th></tr></thead>
              <tbody>
                {#each data.gamification.weekly_leaderboard as row}
                  <tr><td>{row.username}</td><td>{row.weekly_xp}</td></tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      </article>

      <article class="glass-panel">
        <div class="section-head">
          <div>
            <p class="eyebrow">Circle</p>
            <h2>Friends and private ranking</h2>
          </div>
        </div>
        <form class="answer-form" on:submit|preventDefault={addFriend}>
          <div class="answer-row">
            <input bind:value={friendUsername} class="answer-input" type="text" placeholder="Add user by username" />
            <button class="secondary-button" type="submit">Add</button>
          </div>
        </form>
        <div class="tag-row">
          {#each data.gamification.circle.friends as friend}
            <button class="option-chip" type="button" on:click={() => removeFriend(friend.user_id)}>{friend.username} ×</button>
          {:else}
            <span class="mini-tag muted-tag">Build a small study circle for a private leaderboard.</span>
          {/each}
        </div>
        <div class="table-scroll">
          <table class="data-table">
            <thead><tr><th>User</th><th>Level</th><th>XP</th></tr></thead>
            <tbody>
              {#each data.gamification.circle.leaderboard as row}
                <tr><td>{row.username}</td><td>{row.level}</td><td>{row.xp}</td></tr>
              {/each}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  </section>
{/if}
