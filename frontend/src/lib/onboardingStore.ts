import { get, writable } from 'svelte/store';
import { api } from './api';
import {
  emptyState,
  markComplete,
  markTourSeen,
  normalizeState,
} from './components/onboarding/onboarding';
import type { FeatureId, OnboardingState } from './components/onboarding/onboarding';

/**
 * First-run progress, seeded from the boot payload and written back as the
 * learner moves through the chain.
 *
 * The server is the authority — it records drill completions where they
 * actually happen and re-derives from history for accounts older than the
 * feature. This store updates optimistically so locks lift immediately, then
 * reconciles with whatever the PATCH returns.
 */
export const onboarding = writable<OnboardingState>(emptyState());

/**
 * Signal bus for gated tour steps.
 *
 * A trainer announces that something happened ("session-started") without
 * knowing whether a tour is listening; the shell forwards it to the running
 * tour. This keeps the trainers free of tour logic and the tour free of
 * trainer internals.
 */
export const tourSignal = writable<{ name: string; seq: number } | null>(null);
let signalSeq = 0;

export function signalTour(name: string): void {
  signalSeq += 1;
  tourSignal.set({ name, seq: signalSeq });
}

let csrfToken = '';

export function setOnboardingCsrf(token: string): void {
  csrfToken = token;
}

export function setOnboarding(raw: unknown): void {
  onboarding.set(normalizeState(raw));
}

export function resetOnboardingLocal(): void {
  onboarding.set(emptyState());
}

async function push(payload: Parameters<typeof api.patchOnboarding>[0]): Promise<void> {
  if (!csrfToken) {
    return;
  }
  try {
    const next = await api.patchOnboarding(payload);
    onboarding.set(normalizeState(next));
  } catch {
    // A failed write is not worth interrupting a drill for: the optimistic
    // state stands, and the next bootstrap re-reads the server's version.
  }
}

/**
 * The drill that most recently landed, for the checklist's tick-over.
 *
 * It lives here rather than in the component because the checklist unmounts
 * while a drill is running — the completion happens precisely when the card is
 * off screen, so component-local detection would miss every one of them.
 */
export const lastLanded = writable<{ id: FeatureId; seq: number } | null>(null);
let landedSeq = 0;

export function completeFeature(id: FeatureId): void {
  const before = get(onboarding);
  if (before.completed.includes(id)) {
    return;
  }
  onboarding.set(markComplete(before, id));
  landedSeq += 1;
  lastLanded.set({ id, seq: landedSeq });
  void push({ completed: [id], csrf_token: csrfToken });
}

export function markTourDone(tourId: string): void {
  const before = get(onboarding);
  if (before.seenTours.includes(tourId)) {
    return;
  }
  onboarding.set(markTourSeen(before, tourId));
  void push({ seen_tours: [tourId], csrf_token: csrfToken });
}

export function setSkipped(skipped: boolean): void {
  onboarding.update((state) => ({ ...state, skipped }));
  void push({ skipped, csrf_token: csrfToken });
}

/**
 * Awaitable: the reset also closes any running drill server-side, and the
 * caller navigates to Words straight after. Navigating first showed the old
 * session's game screen, where the setup tour has nothing to point at.
 */
export async function restartOnboarding(): Promise<void> {
  onboarding.set(emptyState());
  await push({ reset: true, csrf_token: csrfToken });
}
