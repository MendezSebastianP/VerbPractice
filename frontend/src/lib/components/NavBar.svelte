<script lang="ts">
  import { href, navigate } from '../router';
  import type { ThemeName, UserState } from '../types';

  export let routePath = '/dashboard';
  export let user: UserState;
  export let theme: ThemeName = 'light';
  export let onTheme: (theme: ThemeName) => Promise<void> | void;
  export let onLogout: () => Promise<void> | void;

  const links = [
    { path: '/training/words', label: 'Words' },
    { path: '/training/verbs', label: 'Verb Lab' },
    { path: '/chat', label: 'AI Tutor' },
    ...(user.is_admin ? [{ path: '/monitor', label: 'Monitor' }] : []),
  ];

  function isActive(path: string): boolean {
    if (path === '/training/verbs') {
      return routePath === '/training/conjugation' || routePath.startsWith('/training/verbs');
    }
    return routePath === path || routePath.startsWith(`${path}/`);
  }

  function isDashboardRoute(): boolean {
    return routePath === '/' || routePath === '/dashboard';
  }
</script>

<header class="topbar-shell">
  <div class="topbar-inner">
    <div class="brand-cluster">
      <button
        class:icon-button-on={isDashboardRoute()}
        class="home-button"
        type="button"
        aria-label="Open dashboard"
        title="Open dashboard"
        on:click={() => navigate('/dashboard')}
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 11.5 12 5l8 6.5" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8"></path>
          <path d="M6.5 10.5V19h11v-8.5" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8"></path>
          <path d="M10 19v-4.5h4V19" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8"></path>
        </svg>
      </button>

      <button class="brand-lockup" type="button" on:click={() => navigate('/dashboard')}>
        <span class="brand-mark">LexArena</span>
        <span class="brand-copy">Single-page adaptive language training</span>
      </button>
    </div>

    <nav class="nav-rail" aria-label="Primary navigation">
      {#each links as link}
        <a
          href={href(link.path)}
          class:active-link={isActive(link.path)}
          class="nav-link"
          aria-current={isActive(link.path) ? 'page' : undefined}
          on:click|preventDefault={() => navigate(link.path)}
        >
          {link.label}
        </a>
      {/each}
    </nav>

    <div class="nav-meta">
      <div class="theme-switcher" role="group" aria-label="Theme switcher">
        <button class:theme-on={theme === 'light'} type="button" aria-label="Sun mode" title="Sun mode" on:click={() => onTheme('light')}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="4.25" fill="none" stroke="currentColor" stroke-width="1.8"></circle>
            <path d="M12 2.75v2.5M12 18.75v2.5M21.25 12h-2.5M5.25 12h-2.5M18.55 5.45l-1.8 1.8M7.25 16.75l-1.8 1.8M18.55 18.55l-1.8-1.8M7.25 7.25l-1.8-1.8" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="1.8"></path>
          </svg>
        </button>
        <button class:theme-on={theme === 'dark'} type="button" aria-label="Moon mode" title="Moon mode" on:click={() => onTheme('dark')}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M15.8 3.8a7.9 7.9 0 1 0 4.4 14.6A8.8 8.8 0 0 1 15.8 3.8Z" fill="none" stroke="currentColor" stroke-linejoin="round" stroke-width="1.8"></path>
          </svg>
        </button>
        <button class:theme-on={theme === 'arcade'} type="button" aria-label="Arcade mode" title="Arcade mode" on:click={() => onTheme('arcade')}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="4.5" y="6" width="15" height="12" rx="3" fill="none" stroke="currentColor" stroke-width="1.8"></rect>
            <path d="M9 12h4M11 10v4" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="1.8"></path>
            <circle cx="16.5" cy="10.5" r="1" fill="currentColor"></circle>
            <circle cx="14.5" cy="13.5" r="1" fill="currentColor"></circle>
          </svg>
        </button>
      </div>

      <button class="user-chip user-chip-button" type="button" on:click={() => navigate('/dashboard')}>
        <span class="user-name">{user.username}</span>
        <span class="user-meta">Lv.{user.profile.level} · {user.profile.streak_days} day streak</span>
      </button>

      <button class="ghost-button" type="button" on:click={onLogout}>Logout</button>
    </div>
  </div>
</header>
