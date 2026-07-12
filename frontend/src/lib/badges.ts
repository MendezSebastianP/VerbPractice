// The backend stores badge/challenge icons as short slugs (see BADGE_CATALOG
// and WEEKLY_CHALLENGE_ROTATION in app/services/gamification.py). Map them to
// glyphs for display; anything unrecognized that already looks like an emoji
// passes through, otherwise fall back to a generic medal.
const ICON_EMOJI: Record<string, string> = {
  sprout: '🌱',
  flame: '🔥',
  star: '⭐',
  forge: '⚒️',
  grid: '🧩',
  flag: '🚩',
  bolt: '⚡',
  matrix: '🔢',
  spark: '✨',
};

export function iconEmoji(slug: string | null | undefined): string {
  if (!slug) {
    return '🏅';
  }
  const mapped = ICON_EMOJI[slug.toLowerCase()];
  if (mapped) {
    return mapped;
  }
  return /^[a-z0-9_-]+$/i.test(slug) ? '🏅' : slug;
}
