import type { TourStep } from './CoachTour.svelte';

/**
 * Onboarding model.
 *
 * Drills unlock in a strict chain — each opens only after the previous is
 * finished — with a single escape hatch that opens everything at once.
 */

export type FeatureId = 'words' | 'add-word' | 'verb-translate' | 'verb-tables';

export interface FeatureDef {
  id: FeatureId;
  /** Nav label. */
  label: string;
  /** Route this drill lives on. */
  route: string;
  /** Headline on the drill screen. */
  title: string;
  blurb: string;
  /** Checklist row. */
  checklistLabel: string;
  checklistHint: string;
  cta: string;
  /** Stands in for finishing the real drill on the bench. */
  completeLabel: string;
  /** Drill that must be finished first; null means open from the start. */
  unlockedBy: FeatureId | null;
  /** Plain-language prerequisite, shown on the lock. */
  requires: string;
}

export const FEATURE_CHAIN: FeatureDef[] = [
  {
    id: 'words',
    label: 'Words',
    route: '/training/words',
    title: 'Words',
    blurb: 'Translate single words both ways.',
    checklistLabel: 'Finish your first Words round',
    checklistHint: 'Ten prompts, about two minutes.',
    cta: 'Start',
    completeLabel: 'Finish this round',
    unlockedBy: null,
    requires: 'nothing — this is the starting point',
  },
  {
    id: 'add-word',
    label: 'Add Word',
    route: '/add-word',
    title: 'Add Word',
    blurb: 'Type a word or photograph a page.',
    checklistLabel: 'Add a word of your own',
    checklistHint: 'It lands straight in your pool.',
    cta: 'Add one',
    completeLabel: 'Save this word',
    unlockedBy: 'words',
    requires: 'your first Words round',
  },
  {
    id: 'verb-translate',
    label: 'Verb · Translate',
    route: '/training/verbs',
    title: 'Verb Lab · Translate',
    blurb: 'Same loop as Words, but every prompt is an infinitive.',
    checklistLabel: 'Translate your first verbs',
    checklistHint: 'Infinitive recall.',
    cta: 'Open',
    completeLabel: 'Finish this round',
    unlockedBy: 'add-word',
    requires: 'adding a word of your own',
  },
  {
    id: 'verb-tables',
    label: 'Verb · Tables',
    route: '/training/verbs?mode=tables',
    title: 'Verb Lab · Fill tables',
    blurb: 'Fill a whole tense at once, checked at the end.',
    checklistLabel: 'Fill a conjugation table',
    checklistHint: 'One tense, every pronoun.',
    cta: 'Open',
    completeLabel: 'Submit this table',
    unlockedBy: 'verb-translate',
    requires: 'a verb translation round',
  },
];

export function featureById(id: FeatureId): FeatureDef {
  const found = FEATURE_CHAIN.find((feature) => feature.id === id);
  if (!found) {
    throw new Error(`Unknown feature: ${id}`);
  }
  return found;
}

export interface OnboardingState {
  completed: FeatureId[];
  /** Tour ids already seen: 'intro' plus one per drill. */
  seenTours: string[];
  /** The escape hatch — opens every drill and stops tours firing. */
  skipped: boolean;
}

export function emptyState(): OnboardingState {
  return { completed: [], seenTours: [], skipped: false };
}

/** Coerce whatever the server sends into a usable state object. */
export function normalizeState(raw: unknown): OnboardingState {
  const value = (raw ?? {}) as Partial<OnboardingState>;
  const known = new Set<string>(FEATURE_CHAIN.map((feature) => feature.id));
  return {
    completed: Array.isArray(value.completed)
      ? (value.completed.filter((id) => known.has(id as string)) as FeatureId[])
      : [],
    seenTours: Array.isArray(value.seenTours) ? value.seenTours.filter((id) => typeof id === 'string') : [],
    skipped: value.skipped === true,
  };
}

export function isComplete(state: OnboardingState, id: FeatureId): boolean {
  return state.completed.includes(id);
}

export function isUnlocked(state: OnboardingState, id: FeatureId): boolean {
  if (state.skipped) {
    return true;
  }
  const feature = featureById(id);
  return feature.unlockedBy === null || isComplete(state, feature.unlockedBy);
}

/** The drill the learner should do next, or null once the chain is finished. */
export function currentFeature(state: OnboardingState): FeatureDef | null {
  return FEATURE_CHAIN.find((feature) => !isComplete(state, feature.id)) ?? null;
}

export function chainComplete(state: OnboardingState): boolean {
  return currentFeature(state) === null;
}

/** Drill unlocked by finishing `id`, used for the "just unlocked" toast. */
export function unlockedByCompleting(id: FeatureId): FeatureDef | null {
  return FEATURE_CHAIN.find((feature) => feature.unlockedBy === id) ?? null;
}

export function markComplete(state: OnboardingState, id: FeatureId): OnboardingState {
  if (isComplete(state, id)) {
    return state;
  }
  return { ...state, completed: [...state.completed, id] };
}

export function markTourSeen(state: OnboardingState, tourId: string): OnboardingState {
  if (state.seenTours.includes(tourId)) {
    return state;
  }
  return { ...state, seenTours: [...state.seenTours, tourId] };
}

/** Route a locked drill should be bounced to. */
export function fallbackRoute(state: OnboardingState): string {
  return (currentFeature(state) ?? FEATURE_CHAIN[0]).route;
}

/** Which drill a route belongs to, if any. */
export function featureForRoute(path: string, search = ''): FeatureId | null {
  if (path === '/training/words') return 'words';
  if (path === '/add-word') return 'add-word';
  if (path.startsWith('/training/verbs') || path === '/training/conjugation') {
    const mode = new URLSearchParams(search).get('mode');
    return mode === 'tables' || path.includes('conjugation') ? 'verb-tables' : 'verb-translate';
  }
  return null;
}

// ---------------------------------------------------------------------- tours

/**
 * The first-run pass: say hello, show the rail, point at the checklist.
 * Anything drill-specific belongs in a drill tour.
 */
export const INTRO_TOUR: TourStep[] = [
  {
    id: 'welcome',
    target: null,
    title: 'Welcome to VerbPractice',
    body: 'Three quick things and you are training.',
  },
  {
    id: 'rail',
    target: '[data-tour="rail"]',
    title: 'Everything lives up here',
    body: 'Four drills. They open one at a time, so there is only ever one next thing.',
    placement: 'bottom',
  },
  {
    id: 'checklist',
    target: '[data-tour="checklist"]',
    title: 'This is your map',
    body: 'It tracks what opens next — and lets you unlock everything at once if you would rather explore.',
    placement: 'bottom',
  },
];

/**
 * One tour per drill, fired the first time it is opened. They taper as they go:
 * by the fourth the interface is familiar and only the new rule needs saying.
 */
export const FEATURE_TOURS: Record<FeatureId, TourStep[]> = {
  // The setup pass. Every step is gated: being shown a control teaches less
  // than using it once, so the learner picks the length, swaps the direction and
  // starts the round themselves. The first run is pinned to 5 words — short
  // enough that finishing it is never in doubt.
  words: [
    {
      id: 'words-length',
      target: '[data-tour="words-length"]',
      title: 'Pick how long',
      body: 'Five, ten or twenty prompts. Start with five — you can go longer once you know the loop.',
      placement: 'bottom',
      gate: { kind: 'click', selector: '[data-tour-tile="5"]', nudge: 'Tap “5 words” to carry on' },
      noSkip: true,
    },
    {
      // One step, not two: an extra "now press swap twice" beat between picking
      // and confirming taught a button nobody had asked about yet, and left
      // people unsure which direction they had ended up with.
      id: 'words-confirm',
      target: '[data-tour="words-direction"]',
      extraTargets: ['.lang-menu'],
      title: 'Now set your languages',
      body: 'Left is what you are shown, right is what you answer in. Open either list and pick your pair — you can change it again any time.',
      placement: 'bottom',
    },
    {
      id: 'words-play',
      target: '[data-tour="words-play"]',
      title: 'Now start the round',
      body: 'Press Enter, or click the grid. I will stay with you for the first few words.',
      placement: 'top',
      gate: { kind: 'signal', name: 'session-started', nudge: 'Press Enter to start' },
      noSkip: true,
    },
  ],
  // Scripted, like the first Words round: the learner sets the pair, types the
  // seeded example, and runs a real lookup. The example word is one of the
  // curated tutorial words, so the translation is already in the inventory and
  // the result comes back the same way every time.
  'add-word': [
    {
      id: 'add-pair',
      // No gate: a click-gate advanced the moment one dropdown closed, which
      // rushed people past the second language. They set both, then say when.
      target: '[data-tour="add-picker"]',
      extraTargets: ['.lang-menu'],
      title: 'First, set the pair',
      body: 'What you type on the left, what you want back on the right. Set both the way you want them, then hit Next.',
      placement: 'bottom',
    },
    {
      id: 'add-input',
      target: '[data-tour="add-input"]',
      title: 'An example is already in',
      body: 'We dropped in a word for the language you picked, so you can see the whole flow. Any word works here — swap it for one of your own whenever you like.',
      placement: 'bottom',
    },
    {
      id: 'add-go',
      target: '[data-tour="add-translate"]',
      title: 'Run the lookup',
      body: 'Hit this and we fetch the meaning. It is saved to your words at the same time.',
      placement: 'top',
      gate: { kind: 'signal', name: 'add-word-result', nudge: 'Hit translate' },
      noSkip: true,
    },
    {
      id: 'add-result',
      target: '[data-tour="add-result"]',
      title: 'And there it is',
      body: 'The translation, a definition in your language, and example sentences. This word is in your Words rotation from now on.',
      placement: 'top',
    },
    {
      // Centred and unanchored on purpose: spotlighting the camera made it read
      // as another thing they had to do. It is an option, not a step.
      id: 'add-done',
      target: null,
      title: 'That is Add Word',
      body: 'One last thing worth knowing: you can photograph a page instead of typing, and tap the word you want. Try it whenever you like.',
    },
  ],
  // Same loop as Words, so this one only covers what is different: the two verb
  // drills, and choosing a pair for verbs specifically. Length is pre-set to
  // five so there is one less decision.
  'verb-translate': [
    {
      id: 'verb-switch',
      target: '[data-tour="verb-switch"]',
      title: 'Two verb drills',
      body: 'Translate is infinitive recall. Fill tables opens once you have done a round here.',
      placement: 'bottom',
    },
    {
      id: 'verb-direction',
      target: '[data-tour="words-direction"]',
      title: 'Pick your languages again',
      body: 'Verbs get their own pair — you might want a different direction here than you use for words. Set it, then hit Next.',
      placement: 'bottom',
    },
    {
      id: 'verb-play',
      target: '[data-tour="words-play"]',
      title: 'Five verbs to start',
      body: 'Already set to five. Start when you are ready — everything else works exactly like Words.',
      placement: 'top',
      gate: { kind: 'signal', name: 'session-started', nudge: 'Press Enter to start' },
      noSkip: true,
    },
  ],
  // The last drill, and the shortest script. By now the learner knows the
  // prompt/answer loop, the quick-shot and the free hint — the only genuinely
  // new thing is that a whole tense is graded in one go. Two gated steps: start
  // a run, then see the grid.
  'verb-tables': [
    {
      id: 'tables-setup',
      target: '[data-tour="tables-setup"]',
      title: 'One tense at a time',
      body: 'Pick a verb count and a tense, then start. Everything else works the way Words did.',
      placement: 'top',
      gate: { kind: 'signal', name: 'tables-started', nudge: 'Start a run when you are ready' },
      noSkip: true,
    },
    {
      id: 'tables-grid',
      target: '[data-tour="tables-grid"]',
      title: 'Fill every pronoun, then submit',
      body: 'Nothing is marked until you submit the tense, so you can go back and fix a cell first. That is the only new rule here.',
      placement: 'top',
    },
  ],
};
