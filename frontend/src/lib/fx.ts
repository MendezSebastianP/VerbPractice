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

// One call per graded reward: level-up and badge overlays queued so they
// never fight for the screen. (The nav-bar XP counter ticks separately via
// the profile store — no floating XP text in the play area.)
export function celebrateReward(reward: RewardState | null | undefined): void {
  if (!reward) {
    return;
  }
  const overlays: FxOverlay[] = [];
  if (reward.leveled_up) {
    overlays.push({ id: nextId++, kind: 'level', level: reward.new_level });
  }
  // Badge unlock overlays are suspended for now — they popped mid-game and
  // distracted play. Badges still unlock silently (nav XP/profile updates);
  // re-enable by restoring the push below.
  // if (reward.unlocked_badges?.length) {
  //   overlays.push({ id: nextId++, kind: 'badges', badges: reward.unlocked_badges });
  // }
  if (overlays.length) {
    fxQueue.update((queue) => [...queue, ...overlays]);
  }
}
