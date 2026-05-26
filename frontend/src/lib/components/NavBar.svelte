<script lang="ts">
  import { href, navigate } from '../router';
  import type { UserState } from '../types';

  export let routePath = '/dashboard';
  export let user: UserState;
  export let onLogout: () => Promise<void> | void;

  const links = [
    { path: '/training/words', label: 'Words' },
    { path: '/training/verbs', label: 'Verb Lab' },
    { path: '/add-word', label: 'Add Word' },
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
    <button
      class:icon-button-on={isDashboardRoute()}
      class="home-button"
      type="button"
      aria-label="Open home"
      title="Home"
      on:click={() => navigate('/dashboard')}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 11.5 12 5l8 6.5" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8"></path>
        <path d="M6.5 10.5V19h11v-8.5" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8"></path>
        <path d="M10 19v-4.5h4V19" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8"></path>
      </svg>
    </button>

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

    <button class="ghost-button logout-button" type="button" on:click={onLogout}>Logout</button>
  </div>
</header>
