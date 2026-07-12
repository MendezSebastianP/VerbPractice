<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { href, navigate } from '../router';
  import { profile } from '../profile';

  export let routePath = '/dashboard';

  // Sets, Community, AI Tutor and Monitor are parked until they earn a slot —
  // eight links overflowed the desktop rail. The routes stay reachable by URL.
  const links = [
    { path: '/dashboard', label: 'Home' },
    { path: '/training/words', label: 'Words' },
    { path: '/training/verbs', label: 'Verb Lab' },
    { path: '/add-word', label: 'Add Word' },
  ];

  // Flame grows with streak length (report.md §9.6): 5+ and 14+ days step it up.
  function flameTier(days: number): string {
    if (days >= 14) return 'flame-3';
    if (days >= 5) return 'flame-2';
    if (days >= 1) return 'flame-1';
    return 'flame-0';
  }

  function isActive(path: string): boolean {
    if (path === '/dashboard') {
      return routePath === '/' || routePath === '/dashboard';
    }
    if (path === '/training/verbs') {
      return routePath === '/training/conjugation' || routePath.startsWith('/training/verbs');
    }
    return routePath === path || routePath.startsWith(`${path}/`);
  }

  let railEl: HTMLElement | undefined;
  let linkEls: Record<string, HTMLAnchorElement> = {};
  let pillStyle = 'opacity: 0;';

  function updatePill(): void {
    const active = links.find((link) => isActive(link.path));
    const el = active ? linkEls[active.path] : undefined;
    if (!railEl || !el) {
      pillStyle = 'opacity: 0;';
      return;
    }
    const railRect = railEl.getBoundingClientRect();
    const linkRect = el.getBoundingClientRect();
    const left = linkRect.left - railRect.left + railEl.scrollLeft;
    pillStyle = `width: ${linkRect.width}px; transform: translateX(${left}px); opacity: 1;`;
  }

  onMount(() => {
    updatePill();
    const onResize = () => updatePill();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  });

  $: if (routePath) {
    tick().then(updatePill);
  }
</script>

<header class="topbar-shell">
  <div class="topbar-inner">
    <button class="brand-button" type="button" aria-label="Go to dashboard" on:click={() => navigate('/dashboard')}>
      <span class="vp-badge" aria-hidden="true">
        <span class="vp-v">V</span><span class="vp-p">P</span>
        <span class="vp-notch"></span>
      </span>
      <span class="brand-word">Verb Practice</span>
    </button>

    <nav class="nav-rail" aria-label="Primary navigation" bind:this={railEl}>
      <span class="nav-pill-indicator" style={pillStyle} aria-hidden="true"></span>
      {#each links as link (link.path)}
        <a
          href={href(link.path)}
          class:active-link={isActive(link.path)}
          class="nav-link"
          aria-current={isActive(link.path) ? 'page' : undefined}
          on:click|preventDefault={() => navigate(link.path)}
          bind:this={linkEls[link.path]}
        >
          {link.label}
        </a>
      {/each}
    </nav>

    {#if $profile}
      <div class="profile-cluster" role="status" aria-label={`Streak ${$profile.streak_days} days, level ${$profile.level}, ${$profile.xp} XP`}>
        <span
          class={`streak-flame ${flameTier($profile.streak_days)}`}
          title={$profile.streak_days > 0 ? `${$profile.streak_days}-day streak` : 'No streak yet — practice today!'}
        >
          <span class="flame-icon" aria-hidden="true">🔥</span>{$profile.streak_days}
        </span>
        <span class="level-chip" title={`Level ${$profile.level}`}>Lv.{$profile.level}</span>
        {#key $profile.xp}
          <span class="xp-chip" title="Total XP">{$profile.xp.toLocaleString()} XP</span>
        {/key}
      </div>
    {/if}
  </div>
</header>
