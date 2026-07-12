import { writable } from 'svelte/store';
import type { RewardState, UserProfileState } from './types';

export interface ProfileSnapshot {
  xp: number;
  level: number;
  streak_days: number;
}

// Live gamification readout for the nav bar. Seeded from the boot payload,
// bumped optimistically as rewards land, and re-synced whenever a page
// receives fresh server truth (e.g. the dashboard payload).
export const profile = writable<ProfileSnapshot | null>(null);

export function setProfile(next: UserProfileState | null | undefined): void {
  profile.set(next ? { xp: next.xp, level: next.level, streak_days: next.streak_days } : null);
}

export function applyReward(reward: RewardState | null | undefined): void {
  if (!reward) {
    return;
  }
  profile.update((current) => {
    if (!current) {
      return current;
    }
    return {
      ...current,
      xp: current.xp + (reward.gained_xp || 0),
      level: Math.max(current.level, reward.new_level || 0),
    };
  });
}
