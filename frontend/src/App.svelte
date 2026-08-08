<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import NavBar from './lib/components/NavBar.svelte';
  import AuthPage from './lib/pages/AuthPage.svelte';
  import ChatPage from './lib/pages/ChatPage.svelte';
  import AddWordPage from './lib/pages/AddWordPage.svelte';
  import CommunityPage from './lib/pages/CommunityPage.svelte';
  import GameFx from './lib/components/GameFx.svelte';
  import MonitorPage from './lib/pages/MonitorPage.svelte';
  import PlaygroundPage from './lib/pages/PlaygroundPage.svelte';
  import Playground2Page from './lib/pages/Playground2Page.svelte';
  import Playground3Page from './lib/pages/Playground3Page.svelte';
  import SetsPage from './lib/pages/SetsPage.svelte';
  import SettingsPage from './lib/pages/SettingsPage.svelte';
  import TranslationPage from './lib/pages/TranslationPage.svelte';
  import VerbLabPage from './lib/pages/VerbLabPage.svelte';
  import CoachTour from './lib/components/onboarding/CoachTour.svelte';
  import type { TourStep } from './lib/components/onboarding/CoachTour.svelte';
  import OnboardingChecklist from './lib/components/onboarding/OnboardingChecklist.svelte';
  import type { ChecklistStep } from './lib/components/onboarding/OnboardingChecklist.svelte';
  import {
    FEATURE_CHAIN,
    FEATURE_TOURS,
    INTRO_TOUR,
    chainComplete,
    fallbackRoute,
    featureById,
    featureForRoute,
    isComplete,
    isUnlocked,
  } from './lib/components/onboarding/onboarding';
  import type { FeatureId } from './lib/components/onboarding/onboarding';
  import {
    markTourDone,
    onboarding,
    setOnboarding,
    setOnboardingCsrf,
    setSkipped,
    lastLanded,
    tourSignal,
  } from './lib/onboardingStore';
  import { api, ApiError } from './lib/api';
  import { navigate, route } from './lib/router';
  import { setProfile } from './lib/profile';
  import type { BootPayload, ThemeName } from './lib/types';

  type ToastTone = 'info' | 'success' | 'error';

  interface Toast {
    id: number;
    message: string;
    tone: ToastTone;
  }

  let booting = true;
  let boot: BootPayload | null = null;
  let theme: ThemeName = 'arcade';
  let soundEnabled = false;
  let showShortcuts = true;
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
      showShortcuts = boot.preferences.show_shortcuts;
      setProfile(boot.user?.profile);
      setOnboardingCsrf(boot.csrf_token);
      setOnboarding(boot.onboarding);
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
    if (
      boot.authenticated
      && ($route === '/training/conjugation' || $route.startsWith('/training/verbs/conjugation'))
    ) {
      navigate('/training/verbs?mode=tables', { replace: true });
    }
    if (boot.authenticated && $route === '/monitor' && !boot.user?.is_admin) {
      navigate('/training/words', { replace: true });
    }
    if (boot.authenticated && $route === '/dashboard') {
      // Home was removed — its only unique content was settings, which now has
      // its own route. Kept as a redirect so the server's entry_path, the `/`
      // redirect in routers/pages.py, and old bookmarks all still land somewhere.
      navigate('/training/words', { replace: true });
    }
    if (boot.authenticated && $route === '/photo-word') {
      // Photo capture moved into Add Word (Experiment 05); keep old links alive.
      navigate('/add-word', { replace: true });
    }
    if (
      !boot.authenticated
      && !isAuthRoute($route)
      && $route !== '/playground'
      && $route !== '/playground2'
      && $route !== '/playground3'
    ) {
      navigate('/login', { replace: true });
    }
    if (boot.authenticated && (isAuthRoute($route) || $route === '/')) {
      navigate('/training/words', { replace: true });
    }
    // Onboarding gate: a locked drill reached by URL bounces to the one the
    // learner should be doing instead.
    if (boot.authenticated) {
      const wanted = featureForRoute($route, window.location.search);
      if (wanted && !isUnlocked($onboarding, wanted)) {
        notify(`${featureById(wanted).label} unlocks after ${featureById(wanted).requires}.`, 'info');
        navigate(fallbackRoute($onboarding), { replace: true });
      }
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
      showShortcuts = true;
      setProfile(null);
      setOnboarding(boot.onboarding);
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
      boot = { ...boot, preferences: { ...boot.preferences, sound_enabled: next } };
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to save sound preference', 'error');
    }
  }

  function setShortcutVisibility(next: boolean): void {
    showShortcuts = next;
    if (boot) {
      boot = { ...boot, preferences: { ...boot.preferences, show_shortcuts: next } };
    }
  }

  function handleAuthenticated(event: CustomEvent<BootPayload>): void {
    boot = event.detail;
    theme = boot.theme;
    soundEnabled = boot.preferences.sound_enabled;
    showShortcuts = boot.preferences.show_shortcuts;
    setProfile(boot.user?.profile);
    setOnboardingCsrf(boot.csrf_token);
    setOnboarding(boot.onboarding);
    window.localStorage.setItem('lexarena-theme', theme);
    navigate('/training/words', { replace: true });
    notify('Welcome to VerbPractice!', 'success');
  }

  // ------------------------------------------------------------------- tours
  let introTour: CoachTour;
  let featureTour: CoachTour;
  let featureTourSteps: TourStep[] = [];
  let pendingTourFor: FeatureId | null = null;
  let tourRunning = false;

  function onNavLocked(event: CustomEvent<{ id: FeatureId }>): void {
    const feature = featureById(event.detail.id);
    notify(`${feature.label} unlocks after ${feature.requires}.`, 'info');
  }

  async function runFeatureTour(id: FeatureId): Promise<void> {
    if (tourRunning || $onboarding.skipped || $onboarding.seenTours.includes(id)) {
      return;
    }
    pendingTourFor = id;
    featureTourSteps = FEATURE_TOURS[id];
    tourRunning = true;
    // Let the page paint so the tour can resolve its anchors.
    await new Promise((resolve) => window.setTimeout(resolve, 420));
    featureTour?.start();
  }

  function settleFeatureTour(): void {
    if (pendingTourFor) {
      markTourDone(pendingTourFor);
      pendingTourFor = null;
    }
    tourRunning = false;
  }

  // Trainers announce milestones without knowing a tour exists; forward each one
  // to whichever tour is up so its gate can open.
  let lastSignalSeq = 0;
  $: if ($tourSignal && $tourSignal.seq !== lastSignalSeq) {
    lastSignalSeq = $tourSignal.seq;
    featureTour?.fireSignal($tourSignal.name);
    introTour?.fireSignal($tourSignal.name);
  }

  // One-step pointer shown right after opting out, so "skip" never feels final.
  let resumeTour: CoachTour;
  const RESUME_TOUR: TourStep[] = [
    {
      id: 'resume',
      target: '[data-tour="resume-tutorial"]',
      title: 'You can come back to it',
      body: 'The tutorial lives here. Start it again whenever you like — your progress is kept.',
      placement: 'top',
    },
  ];

  async function runResumeTour(): Promise<void> {
    tourRunning = true;
    await new Promise((resolve) => window.setTimeout(resolve, 550));
    resumeTour?.start();
  }

  async function runIntro(): Promise<void> {
    if (tourRunning || $onboarding.skipped || $onboarding.seenTours.includes('intro')) {
      return;
    }
    tourRunning = true;
    await new Promise((resolve) => window.setTimeout(resolve, 450));
    introTour?.start();
  }

  function settleIntro(handOff: boolean): void {
    markTourDone('intro');
    tourRunning = false;
    if (handOff) {
      // The learner lands on Words, so its tour follows straight on.
      void runFeatureTour('words');
    }
  }

  // --------------------------------------------------------------- checklist
  // Lives on the Words landing screen — where a new account arrives — and hides
  // the moment a drill starts so it never sits behind a running game.
  let drillActive = false;

  $: checklistSteps = FEATURE_CHAIN.map(
    (feature): ChecklistStep => ({
      id: feature.id,
      label: feature.checklistLabel,
      hint: feature.checklistHint,
      cta: feature.cta,
      done: isComplete($onboarding, feature.id),
      href: feature.route,
    }),
  );

  // Follows the learner onto every screen (it is collapsed by default, so it
  // costs one line until they open it) and steps aside while a drill is running.
  $: showChecklist =
    Boolean(boot?.authenticated)
    && !isAuthRoute($route)
    && !drillActive
    && !chainComplete($onboarding);

  function onChecklistAction(event: CustomEvent<{ id: string }>): void {
    const feature = featureById(event.detail.id as FeatureId);
    if (!isUnlocked($onboarding, feature.id)) {
      notify(`${feature.label} unlocks after ${feature.requires}.`, 'info');
      return;
    }
    navigate(feature.route);
  }

  function onChecklistSkip(): void {
    setSkipped(true);
    // Opting out means opting out now — close anything mid-flight before the
    // resume pointer opens, or two tours end up on screen together.
    introTour?.close();
    featureTour?.close();
    pendingTourFor = null;
    tourRunning = false;
    // Hand them the way back before they need it: Settings is where the tutorial
    // restarts, so go there and point at the control.
    navigate('/settings');
    void runResumeTour();
  }

  function onChecklistUnskip(): void {
    setSkipped(false);
    notify('Guided order back on.', 'info');
  }

  // Fire the intro once the shell is up, then a drill's own tour whenever an
  // unlocked drill is opened for the first time.
  // Leaving the page takes every anchor with it, so shut any tour before the
  // new route paints rather than letting it hang over unrelated controls.
  let tourRouteGuard = '';
  $: if ($route !== tourRouteGuard) {
    tourRouteGuard = $route;
    introTour?.close();
    featureTour?.close();
    pendingTourFor = null;
    tourRunning = false;
  }

  let lastTouredRoute = '';
  $: if (!booting && boot?.authenticated && !$onboarding.skipped) {
    if (!$onboarding.seenTours.includes('intro')) {
      void runIntro();
    } else if ($route !== lastTouredRoute) {
      lastTouredRoute = $route;
      const here = featureForRoute($route, window.location.search);
      if (here && isUnlocked($onboarding, here) && !$onboarding.seenTours.includes(here)) {
        void runFeatureTour(here);
      }
    }
  }
</script>

{#if booting}
  <main class="boot-shell">
    <div class="boot-card glass-panel strong-panel" in:fade={{ duration: 120 }}>
      <p class="eyebrow">VerbPractice</p>
      <h1>Loading your training cockpit...</h1>
    </div>
  </main>
{:else}
  <div class:shortcuts-hidden={!showShortcuts} class="app-shell">
    <a class="skip-link" href="#main-content">Skip to content</a>
    <GameFx />
    {#if boot?.authenticated && boot.user && !isAuthRoute($route)}
      <NavBar routePath={$route} on:locked={onNavLocked} />
    {/if}

    <main class="workspace-shell" id="main-content">
      <div class="toast-stack" aria-atomic="true" aria-live="polite" role="status">
        {#each toasts as toast (toast.id)}
          <div class={`toast-card ${toast.tone}`}>{toast.message}</div>
        {/each}
      </div>

      <!-- Outside the {#key} on purpose: remounting per route would reset the
           collapse state and swallow the "step landed" flash. -->
      {#if showChecklist}
        <div class="onboarding-slot" data-tour="checklist">
          <OnboardingChecklist
            steps={checklistSteps}
            variant="card"
            dismissible={false}
            skipped={$onboarding.skipped}
            landed={$lastLanded}
            on:action={onChecklistAction}
            on:skip={onChecklistSkip}
            on:unskip={onChecklistUnskip}
          />
        </div>
      {/if}

      {#key $route + String(boot?.authenticated)}
        <div class="page-shell" in:fade={{ duration: 140 }}>
          {#if $route === '/playground'}
            <!-- Public mobile experiment bench, reachable with or without a session. -->
            <PlaygroundPage
              csrfToken={boot?.csrf_token || ''}
              hasNavigation={Boolean(boot?.authenticated)}
            />
          {:else if $route === '/playground2'}
            <!-- Independent English verb-table design bench. -->
            <Playground2Page />
          {:else if $route === '/playground3'}
            <!-- First-run onboarding bench: checklist, guided tour, feature gating. -->
            <Playground3Page />
          {:else if !boot?.authenticated && $route === '/register'}
            <AuthPage mode="register" csrfToken={boot?.csrf_token || ''} on:authenticated={handleAuthenticated} />
          {:else if !boot?.authenticated}
            <AuthPage mode="login" csrfToken={boot?.csrf_token || ''} on:authenticated={handleAuthenticated} />
          {:else if $route === '/settings'}
            <SettingsPage csrfToken={boot.csrf_token} {theme} onTheme={setTheme} onShowShortcuts={setShortcutVisibility} onLogout={handleLogout} {notify} />
          {:else if $route === '/training/words'}
            <TranslationPage
              mode="words"
              csrfToken={boot.csrf_token}
              soundEnabled={soundEnabled}
              {theme}
              {notify}
              onSessionActiveChange={(active) => (drillActive = active)}
            />
          {:else if $route.startsWith('/training/verbs') || $route === '/training/conjugation'}
            <VerbLabPage
              routePath={$route}
              csrfToken={boot.csrf_token}
              soundEnabled={soundEnabled}
              {theme}
              {notify}
              onSessionActiveChange={(active) => (drillActive = active)}
            />
          {:else if $route === '/chat'}
            <ChatPage csrfToken={boot.csrf_token} {notify} />
          {:else if $route === '/add-word'}
            <AddWordPage csrfToken={boot.csrf_token} {theme} {notify} />
          {:else if $route === '/sets'}
            <SetsPage csrfToken={boot.csrf_token} {notify} />
          {:else if $route === '/community'}
            <CommunityPage csrfToken={boot.csrf_token} username={boot.user?.username || ''} {notify} />
          {:else if $route === '/monitor'}
            <MonitorPage csrfToken={boot.csrf_token} {notify} />
          {:else}
            <section class="glass-panel strong-panel not-found-card">
              <p class="eyebrow">Route not found</p>
              <h1>This page is not in the SPA map yet.</h1>
              <button class="primary-button" type="button" on:click={() => navigate('/training/words')}>Back to training</button>
            </section>
          {/if}
        </div>
      {/key}
    </main>

    <div class="page-floor" aria-hidden="true"><div class="page-floor-grid"></div></div>

    <CoachTour
      bind:this={introTour}
      steps={INTRO_TOUR}
      tone="intro"
      finishLabel="Show me Words"
      on:finish={() => settleIntro(true)}
      on:skip={() => settleIntro(false)}
    />

    <CoachTour
      bind:this={featureTour}
      steps={featureTourSteps}
      tone="feature"
      on:finish={settleFeatureTour}
      on:skip={settleFeatureTour}
    />

    <CoachTour
      bind:this={resumeTour}
      steps={RESUME_TOUR}
      tone="feature"
      finishLabel="Got it"
      on:finish={() => (tourRunning = false)}
      on:skip={() => (tourRunning = false)}
    />
  </div>
{/if}

<style>
  /* Onboarding checklist sits above the Words trainer on the landing screen.
     The shell centres its children, so without width:100% the card collapses to
     its own content and reads as a different column from the trainer below. */
  .onboarding-slot {
    width: 100%;
    max-width: 45rem; /* matches .setup-card so the two share an edge */
    margin: 0 auto 1rem;
  }
</style>
