<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { fade } from 'svelte/transition';
  import { api, ApiError, streamChat } from '../api';
  import type { ChatPayload } from '../types';

  export let csrfToken = '';
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;

  let loading = true;
  let error = '';
  let state: ChatPayload | null = null;
  let message = '';
  let sending = false;
  let logRef: HTMLDivElement | null = null;

  async function load(): Promise<void> {
    loading = true;
    error = '';
    try {
      state = await api.chatState();
      await tick();
      scrollToBottom();
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to load chat';
    } finally {
      loading = false;
    }
  }

  onMount(load);

  async function sendMessage(): Promise<void> {
    if (!state || !message.trim() || sending) {
      return;
    }

    const content = message.trim();
    state = {
      ...state,
      messages: [
        ...state.messages,
        { id: Date.now(), role: 'user', content, created_at: new Date().toISOString() },
        { id: Date.now() + 1, role: 'assistant', content: '', created_at: new Date().toISOString() },
      ],
    };
    message = '';
    sending = true;
    await tick();
    scrollToBottom();

    try {
      await streamChat({ message: content, csrf_token: csrfToken }, (chunk) => {
        if (!state) {
          return;
        }
        const messages = [...state.messages];
        const last = messages[messages.length - 1];
        if (last && last.role === 'assistant') {
          last.content += chunk;
          state = { ...state, messages };
          void tick().then(scrollToBottom);
        }
      });
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Chat stream failed', 'error');
    } finally {
      sending = false;
    }
  }

  function scrollToBottom(): void {
    if (logRef) {
      logRef.scrollTop = logRef.scrollHeight;
    }
  }
</script>

<section class="trainer-shell">
  {#if loading && !state}
    <div class="glass-panel skeleton-card tall-skeleton"></div>
  {:else if error}
    <div class="glass-panel"><div class="feedback-banner error-banner">{error}</div></div>
  {:else if state}
    <div class="chat-shell" in:fade={{ duration: 180 }}>
      <header class="trainer-head glass-panel">
        <div>
          <p class="eyebrow">Learner-aware tutor</p>
          <h1>AI practice room</h1>
        </div>
        <span class={`pill-chip ${state.api_enabled ? 'ready-pill' : 'muted-pill'}`}>{state.api_enabled ? 'Live tutor enabled' : 'Fallback replies only'}</span>
      </header>

      <div class="tag-row">
        {#each state.focus_items.slice(0, 5) as item}
          <span class="mini-tag">{item.label} · {item.language_pair}</span>
        {:else}
          <span class="mini-tag muted-tag">Complete a few runs to surface focus items for the tutor.</span>
        {/each}
      </div>

      <div class="glass-panel strong-panel chat-card">
        <div class="chat-log" bind:this={logRef}>
          {#each state.messages as item}
            <article class={`bubble ${item.role}`}>
              <span>{item.role === 'user' ? 'You' : 'Tutor'}</span>
              <p>{item.content}</p>
            </article>
          {:else}
            <div class="empty-copy">No tutor history yet. Start with a focused prompt below.</div>
          {/each}
        </div>

        <div class="tag-row suggestion-row">
          {#each state.suggestions as suggestion}
            <button class="option-chip" type="button" on:click={() => (message = suggestion)}>{suggestion}</button>
          {/each}
        </div>

        <form class="chat-form" on:submit|preventDefault={sendMessage}>
          <textarea bind:value={message} rows="4" maxlength="1200" placeholder="Ask for a focused drill, a tense explanation, or a mini quiz."></textarea>
          <div class="chat-actions">
            <p class="section-copy">Streaming is handled inline, and the conversation is saved to the database.</p>
            <button class="primary-button" type="submit" disabled={sending}>{sending ? 'Streaming...' : 'Send prompt'}</button>
          </div>
        </form>
      </div>
    </div>
  {/if}
</section>
