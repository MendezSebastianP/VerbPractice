<script lang="ts">
  import { createEventDispatcher, onMount, tick } from 'svelte';
  import { href, navigate } from '../router';
  import { profile } from '../profile';
  import { onboarding } from '../onboardingStore';
  import { featureById, isUnlocked } from './onboarding/onboarding';
  import type { FeatureId, OnboardingState } from './onboarding/onboarding';

  export let routePath = '/training/words';

  const dispatch = createEventDispatcher<{ locked: { id: FeatureId } }>();

  // Sets, Community, AI Tutor and Monitor are parked until they earn a slot —
  // eight links overflowed the desktop rail. The routes stay reachable by URL.
  // `feature` ties a link into the onboarding chain; links without one never
  // lock. Verb Lab opens with its Translate half — Tables gates inside the page.
  const links: Array<{ path: string; label: string; feature?: FeatureId }> = [
    { path: '/training/words', label: 'Words', feature: 'words' },
    { path: '/training/verbs', label: 'Verb Lab', feature: 'verb-translate' },
    { path: '/add-word', label: 'Add Word', feature: 'add-word' },
    { path: '/settings', label: 'Settings' },
  ];

  function lockedFor(link: { feature?: FeatureId }, state: OnboardingState): boolean {
    return Boolean(link.feature) && !isUnlocked(state, link.feature as FeatureId);
  }

  function openLink(link: { path: string; feature?: FeatureId }): void {
    if (lockedFor(link, $onboarding)) {
      dispatch('locked', { id: link.feature as FeatureId });
      return;
    }
    navigate(link.path);
  }

  // Flame grows with streak length (report.md §9.6): 5+ and 14+ days step it up.
  function flameTier(days: number): string {
    if (days >= 14) return 'flame-3';
    if (days >= 5) return 'flame-2';
    if (days >= 1) return 'flame-1';
    return 'flame-0';
  }

  function isActive(path: string): boolean {
    if (path === '/training/words') {
      // Words is the landing route, so it also owns `/` and the retired
      // `/dashboard` while their redirects are still in flight.
      return routePath === '/' || routePath === '/dashboard' || routePath === '/training/words';
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
    <button class="brand-button" type="button" aria-label="Go to training" on:click={() => navigate('/training/words')}>
      <span class="vp-badge" aria-hidden="true">
        <span class="vp-v">V</span><span class="vp-p">P</span>
        <span class="vp-notch"></span>
      </span>
      <span class="brand-word">Verb Practice</span>
    </button>

    <nav class="nav-rail" aria-label="Primary navigation" bind:this={railEl} data-tour="rail">
      <span class="nav-pill-indicator" style={pillStyle} aria-hidden="true"></span>
      {#each links as link (link.path)}
        {@const locked = lockedFor(link, $onboarding)}
        <a
          href={href(link.path)}
          class:active-link={isActive(link.path)}
          class:locked-link={locked}
          class="nav-link"
          aria-current={isActive(link.path) ? 'page' : undefined}
          aria-disabled={locked ? 'true' : undefined}
          title={locked ? `Unlocks after ${featureById(link.feature as FeatureId).requires}` : undefined}
          on:click|preventDefault={() => openLink(link)}
          bind:this={linkEls[link.path]}
        >
          {#if locked}
            <svg class="nav-lock" viewBox="0 0 16 16" width="10" height="10" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="3.2" y="7" width="9.6" height="6.4" rx="1.6" />
              <path d="M5.6 7V5.2a2.4 2.4 0 0 1 4.8 0V7" />
            </svg>
          {/if}
          {link.label}
        </a>
      {/each}
    </nav>

    {#if $profile}
      <div class="profile-cluster" role="status" aria-label={`Streak ${$profile.streak_days} days, level ${$profile.level}`}>
        <span
          class={`streak-flame ${flameTier($profile.streak_days)}`}
          title={$profile.streak_days > 0 ? `${$profile.streak_days}-day streak` : 'No streak yet — practice today!'}
        >
          <span class="flame-icon" aria-hidden="true">🔥</span>{$profile.streak_days}
        </span>
        <span class="level-chip" title={`Level ${$profile.level}`}>Lv.{$profile.level}</span>
      </div>
    {/if}
  </div>
</header>
