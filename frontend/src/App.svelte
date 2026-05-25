<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import NavBar from './lib/components/NavBar.svelte';
  import AuthPage from './lib/pages/AuthPage.svelte';
  import ChatPage from './lib/pages/ChatPage.svelte';
  import AddWordPage from './lib/pages/AddWordPage.svelte';
  import DashboardPage from './lib/pages/DashboardPage.svelte';
  import MonitorPage from './lib/pages/MonitorPage.svelte';
  import SetsPage from './lib/pages/SetsPage.svelte';
  import SettingsPage from './lib/pages/SettingsPage.svelte';
  import TranslationPage from './lib/pages/TranslationPage.svelte';
  import VerbLabPage from './lib/pages/VerbLabPage.svelte';
  import { api, ApiError } from './lib/api';
  import { navigate, route } from './lib/router';
  import type { BootPayload, ThemeName } from './lib/types';

  type ToastTone = 'info' | 'success' | 'error';

  interface Toast {
    id: number;
    message: string;
    tone: ToastTone;
  }

  let booting = true;
  let boot: BootPayload | null = null;
  let theme: ThemeName = 'light';
  let soundEnabled = false;
  let toasts: Toast[] = [];

  function notify(message: string, tone: ToastTone = 'info'): void {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    toasts = [...toasts, { id, message, tone }];
    window.setTimeout(() => {
      toasts = toasts.filter((toast) => toast.id !== id);
    }, 2800);
  }

  function isAuthRoute(path: string): boolean {
    return path === '/login' || path === '/register';
  }

  async function loadBootstrap(): Promise<void> {
    booting = true;
    try {
      boot = await api.bootstrap();
      theme = boot.theme;
      soundEnabled = boot.preferences.sound_enabled;
      const savedTheme = window.localStorage.getItem('lexarena-theme') as ThemeName | null;
      if (!boot.authenticated && savedTheme) {
        theme = savedTheme;
      }
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to start the app shell', 'error');
    } finally {
      booting = false;
    }
  }

  onMount(loadBootstrap);

  $: document.documentElement.setAttribute('data-theme', theme);
  $: if (!booting && boot) {
    if (boot.authenticated && $route === '/training/conjugation') {
      navigate('/training/verbs/conjugation', { replace: true });
    }
    if (boot.authenticated && $route === '/monitor' && !boot.user?.is_admin) {
      navigate('/dashboard', { replace: true });
    }
    if (!boot.authenticated && !isAuthRoute($route)) {
      navigate('/login', { replace: true });
    }
    if (boot.authenticated && (isAuthRoute($route) || $route === '/')) {
      navigate('/dashboard', { replace: true });
    }
  }

  async function setTheme(nextTheme: ThemeName): Promise<void> {
    theme = nextTheme;
    window.localStorage.setItem('lexarena-theme', nextTheme);
    if (boot?.authenticated) {
      try {
        await api.updateTheme(nextTheme, boot.csrf_token);
      } catch (err) {
        notify(err instanceof ApiError ? err.message : 'Unable to save theme preference', 'error');
      }
    }
  }

  async function handleLogout(): Promise<void> {
    if (!boot) {
      return;
    }
    try {
      boot = await api.logout(boot.csrf_token);
      soundEnabled = false;
      navigate('/login', { replace: true });
      notify('Session closed.', 'info');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to log out', 'error');
    }
  }

  async function setSound(next: boolean): Promise<void> {
    soundEnabled = next;
    if (!boot?.authenticated) {
      return;
    }
    try {
      await api.updateSound(next, boot.csrf_token);
      boot = { ...boot, preferences: { sound_enabled: next } };
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to save sound preference', 'error');
    }
  }

  function handleAuthenticated(event: CustomEvent<BootPayload>): void {
    boot = event.detail;
    theme = boot.theme;
    soundEnabled = boot.preferences.sound_enabled;
    window.localStorage.setItem('lexarena-theme', theme);
    navigate('/dashboard', { replace: true });
    notify('Welcome to the new SPA flow.', 'success');
  }
</script>

{#if booting}
  <main class="boot-shell">
    <div class="boot-card glass-panel strong-panel" in:fade={{ duration: 120 }}>
      <p class="eyebrow">LexArena</p>
      <h1>Loading your training cockpit...</h1>
    </div>
  </main>
{:else}
  <div class="app-shell">
    <a class="skip-link" href="#main-content">Skip to content</a>
    {#if boot?.authenticated && boot.user && !isAuthRoute($route)}
      <NavBar routePath={$route} user={boot.user} {theme} onTheme={setTheme} onLogout={handleLogout} />
    {/if}

    <main class="workspace-shell" id="main-content">
      <div class="toast-stack" aria-atomic="true" aria-live="polite" role="status">
        {#each toasts as toast (toast.id)}
          <div class={`toast-card ${toast.tone}`}>{toast.message}</div>
        {/each}
      </div>

      {#key $route + String(boot?.authenticated)}
        <div class="page-shell" in:fade={{ duration: 140 }}>
          {#if !boot?.authenticated && $route === '/register'}
            <AuthPage mode="register" csrfToken={boot?.csrf_token || ''} on:authenticated={handleAuthenticated} />
          {:else if !boot?.authenticated}
            <AuthPage mode="login" csrfToken={boot?.csrf_token || ''} on:authenticated={handleAuthenticated} />
          {:else if $route === '/dashboard'}
            <DashboardPage />
          {:else if $route === '/training/words'}
            <TranslationPage mode="words" csrfToken={boot.csrf_token} soundEnabled={soundEnabled} {notify} />
          {:else if $route.startsWith('/training/verbs') || $route === '/training/conjugation'}
            <VerbLabPage routePath={$route} csrfToken={boot.csrf_token} soundEnabled={soundEnabled} {notify} />
          {:else if $route === '/chat'}
            <ChatPage csrfToken={boot.csrf_token} {notify} />
          {:else if $route === '/add-word'}
            <AddWordPage csrfToken={boot.csrf_token} {notify} />
          {:else if $route === '/sets'}
            <SetsPage csrfToken={boot.csrf_token} {notify} />
          {:else if $route === '/settings'}
            <SettingsPage csrfToken={boot.csrf_token} {notify} />
          {:else if $route === '/monitor'}
            <MonitorPage csrfToken={boot.csrf_token} {notify} />
          {:else}
            <section class="glass-panel strong-panel not-found-card">
              <p class="eyebrow">Route not found</p>
              <h1>This page is not in the SPA map yet.</h1>
              <button class="primary-button" type="button" on:click={() => navigate('/dashboard')}>Back to dashboard</button>
            </section>
          {/if}
        </div>
      {/key}
    </main>
  </div>
{/if}
