import type { TourStep } from './CoachTour.svelte';

/**
 * The scripted first Words round.
 *
 * Five curated prompts, each teaching one thing. The queue is fixed server-side
 * (see app/services/tutorial.py) so the script can say "type día" and be right.
 *
 *   1  the prompt, the field, and Enter
 *   2  the quick-shot: a perfect answer submits itself
 *   3  how the quick-shot is lost — branches on what happened in 2
 *   4  skipping costs nothing
 *   5  hints cost nothing either
 *
 * The quick-shot lesson gets prompts 2 and 3. If the learner has not landed one
 * by the end of 3 the script lets it go rather than eating the skip and hint
 * lessons, which are the last two prompts of a five-prompt round.
 */

export interface TutorialContext {
  /** 0-based position in the round. */
  index: number;
  /** The word being shown. */
  prompt: string;
  /** What the learner should type. */
  answer: string;
  /** Language they are answering in, e.g. "Spanish". */
  targetLanguage: string;
  /** True once the quick-shot has been spent on this prompt. */
  quickShotSpent: boolean;
  /** Whether the learner has landed a quick-shot yet this round. */
  quickShotLanded: boolean;
  /** Detail of the keystroke that spent it, when we caught it. */
  miss: { typed: string; expected: string } | null;
  /** The hint the trainer revealed, once it has been asked for. */
  hintText: string;
}

const SIGNALS = {
  typed: 'tutorial-answer-typed',
  submitted: 'tutorial-answer-submitted',
  quickShotFired: 'tutorial-quick-shot-fired',
  quickShotLost: 'tutorial-quick-shot-lost',
  skipped: 'tutorial-skipped',
  hinted: 'tutorial-hinted',
} as const;

export const TUTORIAL_SIGNALS = SIGNALS;

const PROMPT = '[data-tour="drill-prompt"]';
const FIELD = '[data-tour="drill-input"]';
// The quick-shot steps spotlight the icon itself — that is the thing being
// taught — but sit the card above the whole answer line so it never covers the
// input the learner is being asked to type into.
const QUICK_SHOT = '[data-tour="drill-quickshot"]';
// Steps that talk about what the learner just typed light the whole answer line
// as well as the icon — reading "you typed o where casa has a" is impossible if
// the field holding it is the one part left in the dark.
const ANSWER_LINE = '[data-tour="drill-answerline"]';
const SKIP = '[data-tour="drill-skip"]';
const HINT = '[data-tour="drill-hint"]';
// Where the revealed hint is printed. The follow-up card anchors here and sits
// below it — anchored to the hint button it covered the very text it explains.
const MESSAGE = '[data-tour="drill-message"]';

/** Where the two answers first diverge, for the "you typed X" message. */
export function firstDivergence(
  typed: string,
  expected: string,
): { typed: string; expected: string } | null {
  const a = typed.toLocaleLowerCase();
  const b = expected.toLocaleLowerCase();
  for (let i = 0; i < a.length; i += 1) {
    if (a[i] !== b[i]) {
      return { typed: a[i] ?? '', expected: b[i] ?? '' };
    }
  }
  return null;
}

function missLine(ctx: TutorialContext): string {
  if (ctx.miss && ctx.miss.typed && ctx.miss.expected) {
    return `You typed “${ctx.miss.typed}” where “${ctx.answer}” has “${ctx.miss.expected}”.`;
  }
  return `That was not “${ctx.answer}”.`;
}

export function buildTutorialSteps(ctx: TutorialContext): TourStep[] {
  switch (ctx.index) {
    // ---------------------------------------------------------------- 1 of 5
    case 0:
      return [
        {
          id: 't1-prompt',
          target: PROMPT,
          title: 'This is the word to translate',
          body: `“${ctx.prompt}”. One word at a time — that is the whole game.`,
          placement: 'bottom',
        },
        {
          id: 't1-type',
          target: FIELD,
          title: `Write it in ${ctx.targetLanguage}`,
          body: `Type “${ctx.answer}”. Accents and small typos are forgiven, so get close and you are fine.`,
          placement: 'top',
          gate: { kind: 'signal', name: SIGNALS.typed, nudge: `Type “${ctx.answer}”` },
          noSkip: true,
        },
        {
          id: 't1-enter',
          target: FIELD,
          title: 'Now press Enter',
          body: 'That submits your answer and brings up the next word.',
          placement: 'top',
          gate: { kind: 'signal', name: SIGNALS.submitted, nudge: 'Press Enter' },
          noSkip: true,
        },
      ];

    // ---------------------------------------------------------------- 2 of 5
    case 1:
      if (ctx.quickShotSpent) {
        return [
          {
            id: 't2-lost',
            target: QUICK_SHOT,
            extraTargets: [ANSWER_LINE],
            title: 'And there it goes',
            body: `${missLine(ctx)} One impossible letter spends the quick-shot, so this word now waits for Enter like any other. Press Enter to submit.`,
            placement: 'top',
            gate: { kind: 'signal', name: SIGNALS.submitted, nudge: 'Press Enter to submit' },
            noSkip: true,
          },
        ];
      }
      return [
        {
          id: 't2-quickshot',
          target: QUICK_SHOT,
          title: 'Watch this icon',
          body: `See the icon at the end of the line? While it is lit, a perfect answer submits itself — no Enter. Type “${ctx.answer}” straight through and watch.`,
          placement: 'top',
          gate: {
            kind: 'signal',
            name: SIGNALS.quickShotFired,
            nudge: `Type “${ctx.answer}” with no mistakes`,
          },
          noSkip: true,
        },
      ];

    // ---------------------------------------------------------------- 3 of 5
    case 2:
      if (ctx.quickShotLanded) {
        // They nailed it, so now show them how it is lost — on purpose. Both
        // steps live in one array so the gate advances in place; rebuilding the
        // script mid-step would race the advance and close the tour.
        return [
          {
            id: 't3-break-it',
            target: FIELD,
            title: 'Now break it on purpose',
            body: `Type “${ctx.answer}” but get one letter wrong. I want you to see what happens to the quick-shot.`,
            placement: 'top',
            gate: {
              kind: 'signal',
              name: SIGNALS.quickShotLost,
              nudge: 'Type a letter that cannot be right',
            },
            noSkip: true,
          },
          {
            id: 't3-lost-ok',
            target: QUICK_SHOT,
            extraTargets: [ANSWER_LINE],
            title: 'That is how you lose it',
            body: `${missLine(ctx)} The icon goes dark and the word waits for Enter — nothing is scored differently, you just gave up the shortcut. Now fix it to “${ctx.answer}” and press Enter.`,
            placement: 'top',
            gate: {
              kind: 'signal',
              name: SIGNALS.submitted,
              nudge: `Correct it to “${ctx.answer}”, then Enter`,
            },
            noSkip: true,
          },
        ];
      }

      // They missed it on prompt 2 — one more go.
      if (ctx.quickShotSpent) {
        return [
          {
            id: 't3-retry-lost',
            target: QUICK_SHOT,
            extraTargets: [ANSWER_LINE],
            title: 'Spent again — no harm done',
            body: `${missLine(ctx)} The quick-shot is only a shortcut; your score does not care. Press Enter and we will move on.`,
            placement: 'top',
            gate: { kind: 'signal', name: SIGNALS.submitted, nudge: 'Press Enter' },
            noSkip: true,
          },
        ];
      }
      return [
        {
          id: 't3-retry',
          target: QUICK_SHOT,
          title: 'One more try at the quick-shot',
          body: `Type “${ctx.answer}” straight through — every letter right, first time — and it fires by itself.`,
          placement: 'top',
          gate: {
            kind: 'signal',
            name: SIGNALS.quickShotFired,
            nudge: `Type “${ctx.answer}” with no mistakes`,
          },
          noSkip: true,
        },
      ];

    // ---------------------------------------------------------------- 4 of 5
    case 3:
      return [
        {
          id: 't4-skip',
          target: SKIP,
          title: 'Do not know it? Skip',
          body: 'Skip shows you the answer and moves on. It costs you nothing — the word just comes back sooner. Try it now.',
          placement: 'top',
          gate: { kind: 'signal', name: SIGNALS.skipped, nudge: 'Hit skip' },
          noSkip: true,
        },
      ];

    // ---------------------------------------------------------------- 5 of 5
    case 4: {
      const firstLetter = ctx.answer.trim().charAt(0);
      const revealed = ctx.hintText.trim();
      return [
        {
          id: 't5-hint',
          target: HINT,
          title: 'Half-remember it? Take a hint',
          body: 'A hint opens up the answer a letter at a time. Take one now.',
          placement: 'top',
          gate: { kind: 'signal', name: SIGNALS.hinted, nudge: 'Hit hint' },
          noSkip: true,
        },
        {
          id: 't5-hint-cost',
          target: MESSAGE,
          placement: 'bottom',
          title: 'There it is',
          // A one-letter hint is already the first letter, so quoting it twice
          // reads as a stutter: “a” — so you know it starts with “a”.
          body: `${
            revealed.length > 1
              ? `“${revealed}” — so it starts with “${firstLetter}”.`
              : `It starts with “${firstLetter || revealed}”.`
          } Hit hint again and again until you have enough, but each one takes a little more score off this word. Now finish the round however you like.`,
        },
      ];
    }

    default:
      return [];
  }
}
