import { writable } from 'svelte/store';
import type { RewardState } from './types';

export interface BadgeReveal {
  code: string;
  title: string;
  description: string;
  icon: string;
  rarity: string;
}

export type FxOverlay =
  | { id: number; kind: 'level'; level: number }
  | { id: number; kind: 'badges'; badges: BadgeReveal[] };

// Transient reward effects rendered by the global <GameFx /> layer.
// Pages push events here instead of owning overlay markup themselves.
export const fxQueue = writable<FxOverlay[]>([]);
export const missFlash = writable(0);

let nextId = 1;

export function flashMiss(): void {
  missFlash.update((n) => n + 1);
}

// Restartable "pop" feedback for buttons triggered via keyboard shortcuts
// (the .btn-pop animation lives in app.css).
export function popEl(el: HTMLElement | null): void {
  if (!el) return;
  el.classList.remove('btn-pop');
  void el.offsetWidth; // reflow to restart animation
  el.classList.add('btn-pop');
  el.addEventListener('animationend', () => el.classList.remove('btn-pop'), { once: true });
}

export function dismissOverlay(id: number): void {
  fxQueue.update((queue) => queue.filter((overlay) => overlay.id !== id));
}

// One call per graded reward. Level-ups are NOT shown immediately: a mid-game
// popup steals the Enter keystroke (which then grades a half-typed answer), so
// the level is buffered here and released as a short toast once the session
// ends. (The nav-bar level chip still updates live via the profile store.)
let pendingLevel: number | null = null;

export function celebrateReward(reward: RewardState | null | undefined): void {
  if (!reward) {
    return;
  }
  if (reward.leveled_up) {
    pendingLevel = reward.new_level;
  }
  // Badge unlock overlays are suspended for now — they popped mid-game and
  // distracted play. Badges still unlock silently (profile store updates);
  // re-enable by buffering them like pendingLevel above.
}

// Called by trainers when a session finishes (completed or ended early).
export function releaseCelebrations(): void {
  if (pendingLevel === null) {
    return;
  }
  const level = pendingLevel;
  pendingLevel = null;
  fxQueue.update((queue) => [...queue, { id: nextId++, kind: 'level', level }]);
}
