<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { api, ApiError } from '../api';
  import { navigate } from '../router';
  import type { BootPayload } from '../types';

  export let mode: 'login' | 'register' = 'login';
  export let csrfToken = '';

  const dispatch = createEventDispatcher<{ authenticated: BootPayload }>();

  let username = '';
  let password = '';
  let confirmPassword = '';
  let loading = false;
  let error = '';

  async function submit(): Promise<void> {
    loading = true;
    error = '';

    try {
      const payload =
        mode === 'login'
          ? await api.login({ username, password, csrf_token: csrfToken })
          : await api.register({
              username,
              password,
              confirm_password: confirmPassword,
              csrf_token: csrfToken,
            });
      dispatch('authenticated', payload);
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Authentication failed';
    } finally {
      loading = false;
    }
  }
</script>

<section class="auth-center-shell">
  <article class="auth-card glass-panel strong-panel">
    <p class="eyebrow">{mode === 'login' ? 'Sign in' : 'Create account'}</p>
    <h2>{mode === 'login' ? 'Keep your momentum.' : 'Start your first streak.'}</h2>
    <p class="subcopy">{mode === 'login' ? 'Jump back into the queue with one step.' : 'We will track XP, streaks, and your weak spots from the start.'}</p>

    {#if error}
      <div class="feedback-banner error-banner">{error}</div>
    {/if}

    <form class="auth-form" on:submit|preventDefault={submit}>
      <label>
        <span>Username</span>
        <input bind:value={username} autocomplete="username" placeholder="demo" required />
      </label>

      <label>
        <span>Password</span>
        <input bind:value={password} type="password" autocomplete={mode === 'login' ? 'current-password' : 'new-password'} required />
      </label>

      {#if mode === 'register'}
        <label>
          <span>Confirm password</span>
          <input bind:value={confirmPassword} type="password" autocomplete="new-password" required />
        </label>
      {/if}

      <button class="primary-button auth-submit" type="submit" disabled={loading}>
        {#if loading}
          Working...
        {:else if mode === 'login'}
          Enter VerbPractice
        {:else}
          Create profile
        {/if}
      </button>
    </form>

    {#if mode === 'login'}
      <div class="demo-chip">Demo: demo / demo12345</div>
    {/if}

    <button class="text-switch" type="button" on:click={() => navigate(mode === 'login' ? '/register' : '/login')}>
      {mode === 'login' ? 'Need an account? Create one.' : 'Already registered? Sign in.'}
    </button>
  </article>
</section>
