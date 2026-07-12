<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import { iconEmoji } from '../badges';
  import type { CommunityPayload } from '../types';

  export let csrfToken = '';
  export let username = '';
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;

  let loading = true;
  let error = '';
  let data: CommunityPayload | null = null;
  let friendName = '';
  let friendBusy = false;

  const MEDALS = ['🥇', '🥈', '🥉'];

  async function load(): Promise<void> {
    loading = true;
    error = '';
    try {
      data = await api.community();
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to load community';
    } finally {
      loading = false;
    }
  }

  onMount(load);

  async function addFriend(): Promise<void> {
    const name = friendName.trim();
    if (!name || friendBusy) {
      return;
    }
    friendBusy = true;
    try {
      const result = await api.addCircleFriend({ username: name, csrf_token: csrfToken });
      notify(`${result.friend.username} joined your circle.`, 'success');
      friendName = '';
      await load();
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to add friend', 'error');
    } finally {
      friendBusy = false;
    }
  }

  async function removeFriend(friendUserId: number, name: string): Promise<void> {
    if (friendBusy) {
      return;
    }
    friendBusy = true;
    try {
      await api.removeCircleFriend(friendUserId, csrfToken);
      notify(`${name} removed from your circle.`, 'info');
      await load();
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to remove friend', 'error');
    } finally {
      friendBusy = false;
    }
  }

  function challengePercent(): number {
    const challenge = data?.weekly_challenge;
    if (!challenge || !challenge.target_value) {
      return 0;
    }
    return Math.min(100, (challenge.progress / challenge.target_value) * 100);
  }

  function humanizeReason(reason: string): string {
    const cleaned = reason.replace(/_/g, ' ');
    return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
  }

  function rarityClass(rarity: string): string {
    const normalized = (rarity || 'common').toLowerCase();
    return ['common', 'rare', 'epic', 'legendary'].includes(normalized)
      ? `rarity-${normalized}`
      : 'rarity-common';
  }
</script>

<section class="community-shell">
  {#if loading && !data}
    <div class="glass-panel skeleton-card tall-skeleton"></div>
  {:else if error}
    <div class="glass-panel">
      <div class="feedback-banner error-banner">{error}</div>
    </div>
  {:else if data}
    <div class="community-stack" in:fade={{ duration: 180 }}>
      <header class="glass-panel strong-panel">
        <p class="eyebrow">Community</p>
        <h1 class="community-title">Leaderboards &amp; circle</h1>
        {#if data.weekly_challenge}
          <div class="challenge-block">
            <div class="section-head">
              <div>
                <p class="eyebrow">Weekly challenge</p>
                <h2>{iconEmoji(data.weekly_challenge.icon)} {data.weekly_challenge.title}</h2>
              </div>
              <span class="pill-chip reward-pill">+{data.weekly_challenge.reward_xp} XP</span>
            </div>
            <p class="section-copy">{data.weekly_challenge.description}</p>
            <div class="progress-shell">
              <div class="progress-top">
                <span>{data.weekly_challenge.completed ? 'Completed!' : 'Progress'}</span>
                <strong>{data.weekly_challenge.progress}/{data.weekly_challenge.target_value}</strong>
              </div>
              <div class="progress-track">
                <span class="progress-bar" style={`width: ${challengePercent()}%`}></span>
              </div>
            </div>
          </div>
        {/if}
      </header>

      <div class="board-grid">
        <article class="glass-panel">
          <div class="section-head">
            <div>
              <p class="eyebrow">All time</p>
              <h2>Global leaderboard</h2>
            </div>
          </div>
          {#if data.global_leaderboard.length}
            <ol class="board-list">
              {#each data.global_leaderboard as row, i}
                <li class="board-row" class:is-you={row.username === username}>
                  <span class="board-rank">{MEDALS[i] ?? i + 1}</span>
                  <span class="board-name">{row.username}{row.username === username ? ' (you)' : ''}</span>
                  <span class="level-chip">Lv.{row.level}</span>
                  {#if row.streak_days > 0}
                    <span class="board-streak" title={`${row.streak_days}-day streak`}>🔥{row.streak_days}</span>
                  {/if}
                  <span class="board-xp">{row.xp.toLocaleString()} XP</span>
                </li>
              {/each}
            </ol>
          {:else}
            <p class="empty-copy">No ranked players yet — earn some XP!</p>
          {/if}
        </article>

        <article class="glass-panel">
          <div class="section-head">
            <div>
              <p class="eyebrow">This week</p>
              <h2>Weekly leaderboard</h2>
            </div>
          </div>
          {#if data.weekly_leaderboard.length}
            <ol class="board-list">
              {#each data.weekly_leaderboard as row, i}
                <li class="board-row" class:is-you={row.username === username}>
                  <span class="board-rank">{MEDALS[i] ?? i + 1}</span>
                  <span class="board-name">{row.username}{row.username === username ? ' (you)' : ''}</span>
                  <span class="board-xp">{row.weekly_xp.toLocaleString()} XP</span>
                </li>
              {/each}
            </ol>
          {:else}
            <p class="empty-copy">Nobody has earned XP this week yet. First mover advantage!</p>
          {/if}
        </article>
      </div>

      <article class="glass-panel">
        <div class="section-head">
          <div>
            <p class="eyebrow">Your circle</p>
            <h2>Friends leaderboard</h2>
          </div>
        </div>

        <form class="friend-form" on:submit|preventDefault={addFriend}>
          <input
            class="answer-input"
            bind:value={friendName}
            placeholder="Add a friend by username"
            autocomplete="off"
            disabled={friendBusy}
          />
          <button class="secondary-button" type="submit" disabled={friendBusy || !friendName.trim()}>
            Add friend
          </button>
        </form>

        {#if data.circle.friends.length}
          <div class="tag-row">
            {#each data.circle.friends as friend (friend.user_id)}
              <span class="pill-chip friend-chip">
                {friend.username}
                <button
                  class="friend-remove"
                  type="button"
                  title={`Remove ${friend.username}`}
                  aria-label={`Remove ${friend.username} from circle`}
                  on:click={() => removeFriend(friend.user_id, friend.username)}
                  disabled={friendBusy}
                >
                  ×
                </button>
              </span>
            {/each}
          </div>
        {/if}

        {#if data.circle.leaderboard.length > 1}
          <ol class="board-list">
            {#each data.circle.leaderboard as row, i (row.user_id)}
              <li class="board-row" class:is-you={row.username === username}>
                <span class="board-rank">{MEDALS[i] ?? i + 1}</span>
                <span class="board-name">{row.username}{row.username === username ? ' (you)' : ''}</span>
                <span class="level-chip">Lv.{row.level}</span>
                <span class="board-xp">{row.xp.toLocaleString()} XP</span>
              </li>
            {/each}
          </ol>
        {:else}
          <p class="empty-copy">Your circle is just you so far. Add friends to race them on XP.</p>
        {/if}
      </article>

      <div class="board-grid">
        <article class="glass-panel">
          <div class="section-head">
            <div>
              <p class="eyebrow">Trophy shelf</p>
              <h2>Badges</h2>
            </div>
          </div>
          {#if data.badges.length}
            <div class="badge-wall">
              {#each data.badges as badge (badge.code)}
                <div class={`badge-tile ${rarityClass(badge.rarity)}`}>
                  <span class="badge-tile-icon">{iconEmoji(badge.icon)}</span>
                  <strong>{badge.title}</strong>
                  <span class="badge-tile-copy">{badge.description}</span>
                  <span class="badge-tile-rarity">{badge.rarity}</span>
                </div>
              {/each}
            </div>
          {:else}
            <p class="empty-copy">No badges yet — complete sessions to start unlocking them.</p>
          {/if}
        </article>

        <article class="glass-panel">
          <div class="section-head">
            <div>
              <p class="eyebrow">Ledger</p>
              <h2>Recent XP</h2>
            </div>
          </div>
          {#if data.recent_xp.length}
            <div class="list-stack">
              {#each data.recent_xp as event}
                <div class="list-row xp-event-row">
                  <span class="xp-event-amount">+{event.amount} XP</span>
                  <span class="xp-event-reason">{humanizeReason(event.reason)}</span>
                  <span class="xp-event-date">
                    {event.created_at ? new Date(event.created_at).toLocaleString() : ''}
                  </span>
                </div>
              {/each}
            </div>
          {:else}
            <p class="empty-copy">No XP earned yet. Every correct answer lands here.</p>
          {/if}
        </article>
      </div>
    </div>
  {/if}
</section>

<style>
  .community-shell {
    max-width: 720px;
    margin-inline: auto;
    width: 100%;
  }

  .community-stack {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .community-title {
    font-family: var(--display);
    font-weight: 600;
    letter-spacing: -0.04em;
    font-size: 1.6rem;
    margin: 0.2rem 0 0;
  }

  .challenge-block {
    margin-top: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .board-grid {
    display: grid;
    gap: 1.25rem;
    grid-template-columns: 1fr;
  }

  .board-list {
    list-style: none;
    margin: 1rem 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .board-row {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.55rem 0.75rem;
    border-radius: 12px;
    border: 1px solid transparent;
  }

  .board-row.is-you {
    border-color: color-mix(in srgb, var(--accent) 40%, transparent);
    background: var(--accent-soft);
  }

  .board-rank {
    width: 2rem;
    flex-shrink: 0;
    text-align: center;
    font-family: var(--mono);
    font-weight: 700;
    color: var(--muted);
  }

  .board-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 600;
  }

  .board-streak {
    font-family: var(--mono);
    font-size: 0.8rem;
    flex-shrink: 0;
  }

  .board-xp {
    font-family: var(--mono);
    font-weight: 700;
    color: var(--xp);
    flex-shrink: 0;
    font-size: 0.85rem;
  }

  .friend-form {
    display: flex;
    gap: 0.75rem;
    margin: 1rem 0;
    flex-wrap: wrap;
  }

  .friend-form .answer-input {
    flex: 1;
    min-width: 220px;
  }

  .friend-chip {
    gap: 0.4rem;
    text-transform: none;
    letter-spacing: normal;
    font-family: var(--ui);
    font-size: 0.85rem;
    color: var(--text);
  }

  .friend-remove {
    border: 0;
    background: transparent;
    color: var(--muted);
    font-size: 1rem;
    line-height: 1;
    padding: 0 0.1rem;
    cursor: pointer;
  }

  .friend-remove:hover {
    color: var(--danger);
  }

  .badge-wall {
    margin-top: 1rem;
    display: grid;
    gap: 0.75rem;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }

  .badge-tile {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    padding: 0.85rem;
    border-radius: 14px;
    border: 2px solid var(--line);
    background: color-mix(in srgb, var(--surface-strong) 84%, transparent);
    text-align: left;
  }

  .badge-tile-icon {
    font-size: 1.5rem;
  }

  .badge-tile strong {
    font-family: var(--display);
    font-size: 0.9rem;
  }

  .badge-tile-copy {
    font-size: 0.75rem;
    color: var(--muted);
    line-height: 1.35;
  }

  .badge-tile-rarity {
    margin-top: 0.2rem;
    font-family: var(--mono);
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    color: var(--muted);
  }

  .badge-tile.rarity-rare {
    border-color: color-mix(in srgb, var(--accent) 55%, transparent);
  }

  .badge-tile.rarity-rare .badge-tile-rarity {
    color: var(--accent-strong);
  }

  .badge-tile.rarity-epic {
    border-color: color-mix(in srgb, var(--accent-2) 60%, transparent);
  }

  .badge-tile.rarity-epic .badge-tile-rarity {
    color: var(--accent-2);
  }

  .badge-tile.rarity-legendary {
    border-color: color-mix(in srgb, var(--xp) 70%, transparent);
    box-shadow: 0 0 14px color-mix(in srgb, var(--xp) 22%, transparent);
  }

  .badge-tile.rarity-legendary .badge-tile-rarity {
    color: var(--xp);
  }

  .xp-event-row {
    align-items: baseline;
  }

  .xp-event-amount {
    font-family: var(--mono);
    font-weight: 700;
    color: var(--xp);
    flex-shrink: 0;
  }

  .xp-event-reason {
    flex: 1;
    min-width: 0;
  }

  .xp-event-date {
    font-size: 0.75rem;
    color: var(--muted);
    flex-shrink: 0;
  }
</style>
