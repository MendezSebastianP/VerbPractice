<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { api, ApiError } from '../api';
  import type { SemanticGradePayload, SemanticGradeResponse } from '../types';

  export let csrfToken = '';
  export let hasNavigation = false;

  type PresetTone = 'valid' | 'trap';

  interface RubricEntry {
    label: string;
  }

  interface AnswerPreset {
    label: string;
    tone: PresetTone;
    answer: string;
  }

  interface MeaningChallenge {
    id: SemanticGradePayload['challenge_id'];
    term: string;
    language: string;
    languageCode: string;
    context: string;
    prompt: string;
    note: string;
    acceptedLanguages: string[];
    reference: string;
    requiredConcepts: RubricEntry[];
    hardNegatives: RubricEntry[];
    presets: AnswerPreset[];
  }

  const challenges: MeaningChallenge[] = [
    {
      id: 'retrouvailles',
      term: 'retrouvailles',
      language: 'French',
      languageCode: 'FR',
      context: 'Après quinze ans sans se voir, leurs retrouvailles sur le quai furent pleines de rires et de larmes.',
      prompt: 'Explain what “retrouvailles” refers to here.',
      note: 'People who already know one another meet again after time apart.',
      acceptedLanguages: ['English', 'Français', 'Español', 'Русский'],
      reference: 'the meeting again of people who have been apart, often with strong emotion',
      requiredConcepts: [
        { label: 'Meeting one another again' },
        { label: 'After time apart' },
      ],
      hardNegatives: [
        { label: 'First introduction' },
        { label: 'Farewell' },
        { label: 'Finding a lost object' },
      ],
      presets: [
        {
          label: 'Valid paraphrase',
          tone: 'valid',
          answer: 'Es volver a verse después de haber pasado mucho tiempo separados.',
        },
        {
          label: 'Concise meaning',
          tone: 'valid',
          answer: 'Se revoir.',
        },
        {
          label: 'Related but wrong',
          tone: 'trap',
          answer: 'Deux inconnus qui font connaissance pour la première fois.',
        },
      ],
    },
    {
      id: 'esprit_escalier',
      term: 'l’esprit d’escalier',
      language: 'French',
      languageCode: 'FR',
      context: 'La réunion était finie depuis dix minutes quand Nora trouva enfin la réponse parfaite : encore un cas d’esprit d’escalier.',
      prompt: 'Explain the experience described by “l’esprit d’escalier”.',
      note: 'The fitting reply arrives only after the moment to say it has passed.',
      acceptedLanguages: ['English', 'Français', 'Español', 'Русский'],
      reference: 'the experience of thinking of the perfect reply only after the conversation has ended',
      requiredConcepts: [
        { label: 'Thinking of the fitting reply' },
        { label: 'Only after the opportunity has passed' },
      ],
      hardNegatives: [
        { label: 'Immediate wit' },
        { label: 'Never finding a reply' },
        { label: 'Literal staircase' },
      ],
      presets: [
        {
          label: 'Valid paraphrase',
          tone: 'valid',
          answer: 'La respuesta perfecta se te ocurre cuando la conversación ya ha terminado.',
        },
        {
          label: 'Concise meaning',
          tone: 'valid',
          answer: 'Trouver la bonne réponse trop tard.',
        },
        {
          label: 'Related but wrong',
          tone: 'trap',
          answer: 'Donner immédiatement la réplique parfaite pendant la conversation.',
        },
      ],
    },
    {
      id: 'madrugar',
      term: 'madrugar',
      language: 'Spanish',
      languageCode: 'ES',
      context: 'Para coger el primer tren, Inés tuvo que madrugar: salió de casa cuando todavía estaba oscuro.',
      prompt: 'Explain what “madrugar” means here.',
      note: 'It means getting out of bed and starting the day unusually early.',
      acceptedLanguages: ['English', 'Français', 'Español', 'Русский'],
      reference: 'to get up at dawn or very early in the morning',
      requiredConcepts: [
        { label: 'Getting out of bed' },
        { label: 'At a very early hour' },
      ],
      hardNegatives: [
        { label: 'Going to bed early' },
        { label: 'Staying awake until dawn' },
        { label: 'Sleeping late' },
      ],
      presets: [
        {
          label: 'Valid paraphrase',
          tone: 'valid',
          answer: 'Levantarse mucho antes de lo normal, cuando todavía está amaneciendo.',
        },
        {
          label: 'Concise meaning',
          tone: 'valid',
          answer: 'Levantarse muy temprano.',
        },
        {
          label: 'Related but wrong',
          tone: 'trap',
          answer: 'Quedarse despierto toda la noche hasta el amanecer.',
        },
      ],
    },
    {
      id: 'estrenar',
      term: 'estrenar',
      language: 'Spanish',
      languageCode: 'ES',
      context: 'Clara llevaba semanas guardando el abrigo nuevo y hoy, con el frío, por fin lo estrenó.',
      prompt: 'Explain what “estrenó” means here.',
      note: 'The coat moves from being merely new to being worn for the first time.',
      acceptedLanguages: ['English', 'Français', 'Español', 'Русский'],
      reference: 'to use or wear something for the first time',
      requiredConcepts: [
        { label: 'Using or wearing something' },
        { label: 'For the first time' },
      ],
      hardNegatives: [
        { label: 'Buying something' },
        { label: 'Using it again' },
        { label: 'Repairing it' },
        { label: 'Premiering a performance' },
      ],
      presets: [
        {
          label: 'Valid paraphrase',
          tone: 'valid',
          answer: 'Ponerse de verdad el abrigo por primera vez.',
        },
        {
          label: 'Concise meaning',
          tone: 'valid',
          answer: 'Usarlo por primera vez.',
        },
        {
          label: 'Related but wrong',
          tone: 'trap',
          answer: 'Volver a usar algo que ya se ha usado muchas veces.',
        },
      ],
    },
    {
      id: 'empalagar',
      term: 'empalagar',
      language: 'Spanish',
      languageCode: 'ES',
      context: 'El batido parecía rico, pero era tan dulce y espeso que después de dos sorbos me empalagó.',
      prompt: 'Explain what “me empalagó” means here.',
      note: 'Excessive sweetness turns enjoyment into weariness or aversion.',
      acceptedLanguages: ['English', 'Français', 'Español', 'Русский'],
      reference: 'for something sweet or rich to become cloying and cause weariness or dislike',
      requiredConcepts: [
        { label: 'Excessive sweetness or richness' },
        { label: 'Causing weariness or dislike' },
      ],
      hardNegatives: [
        { label: 'Pleasant sweetness' },
        { label: 'Spoiled or bitter food' },
        { label: 'Food allergy' },
      ],
      presets: [
        {
          label: 'Valid paraphrase',
          tone: 'valid',
          answer: 'Ser tan dulce que acaba cansando y quita las ganas de seguir tomándolo.',
        },
        {
          label: 'Concise meaning',
          tone: 'valid',
          answer: 'Demasiado dulce.',
        },
        {
          label: 'Related but wrong',
          tone: 'trap',
          answer: 'Ser agradablemente dulce y apetecible.',
        },
      ],
    },
  ];

  const verdictCopy = {
    correct: {
      eyebrow: 'Backend verdict · correct',
      title: 'Counted as correct.',
      body: 'The answer is close to a valid explanation, covers the essential idea, and stays clear of the known traps.',
    },
    partial: {
      eyebrow: 'Backend verdict · partial',
      title: 'Counted as partly correct.',
      body: 'The answer reaches the concept but does not clearly carry every required part of the meaning.',
    },
    incorrect: {
      eyebrow: 'Backend verdict · incorrect',
      title: 'Counted as incorrect.',
      body: 'Related vocabulary is present, but the explanation conflicts with the rubric or misses its core.',
    },
    uncertain: {
      eyebrow: 'Backend verdict · uncertain',
      title: 'Not counted right or wrong.',
      body: 'The backend abstained. A human decision is required before this answer can affect a score or training.',
    },
  } as const;

  const conciseCorrectCopy = {
    eyebrow: 'Backend verdict · correct',
    title: 'Correct — concise gloss.',
    body: 'This carries enough meaning to count as correct here. The component trace shows what was explicit, supplied by context, or optional.',
  } as const;

  let active = challenges[0];
  let answer = '';
  let result: SemanticGradeResponse | null = null;
  let busy = false;
  let error = '';
  let showRubric = false;
  let selfResolution: 'same' | 'different' | '' = '';
  let loadedPreset: AnswerPreset | null = null;
  let resultRegion: HTMLElement | null = null;

  onMount(() => {
    const root = document.documentElement;
    const previousTheme = root.getAttribute('data-theme');
    const previousPlayground = root.getAttribute('data-playground');
    const previousPlaygroundNav = root.getAttribute('data-playground-nav');
    root.setAttribute('data-theme', 'light');
    root.setAttribute('data-playground', 'meaning-lab');
    root.setAttribute('data-playground-nav', hasNavigation ? 'present' : 'absent');

    return () => {
      if (previousTheme) root.setAttribute('data-theme', previousTheme);
      else root.removeAttribute('data-theme');
      if (previousPlayground) root.setAttribute('data-playground', previousPlayground);
      else root.removeAttribute('data-playground');
      if (previousPlaygroundNav) root.setAttribute('data-playground-nav', previousPlaygroundNav);
      else root.removeAttribute('data-playground-nav');
    };
  });

  function chooseChallenge(challenge: MeaningChallenge): void {
    if (busy) return;
    active = challenge;
    answer = '';
    result = null;
    error = '';
    showRubric = false;
    selfResolution = '';
    loadedPreset = null;
  }

  function usePreset(preset: AnswerPreset): void {
    if (busy) return;
    answer = preset.answer;
    result = null;
    error = '';
    selfResolution = '';
    loadedPreset = preset;
  }

  function handleAnswerInput(): void {
    if (busy) return;
    result = null;
    error = '';
    selfResolution = '';
    loadedPreset = null;
  }

  async function gradeAnswer(): Promise<void> {
    const cleaned = answer.trim();
    if (!cleaned) {
      error = 'Write an explanation first, or load one of the test answers.';
      return;
    }
    if (!csrfToken) {
      error = 'The playground session is not ready yet. Refresh and try again.';
      return;
    }

    const requestChallengeId = active.id;
    const requestAnswer = cleaned;
    busy = true;
    error = '';
    result = null;
    selfResolution = '';
    try {
      const response = await api.gradeSemanticAnswer({
        csrf_token: csrfToken,
        challenge_id: requestChallengeId,
        answer: requestAnswer,
      });
      if (active.id === requestChallengeId && answer.trim() === requestAnswer) {
        result = response;
      }
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'The local grader could not check this answer.';
    } finally {
      busy = false;
    }
    if (result) {
      await tick();
      resultRegion?.focus({ preventScroll: true });
      resultRegion?.scrollIntoView({
        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
        block: 'start',
      });
    }
  }

  function handleAnswerKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void gradeAnswer();
    }
  }

  function resetRun(): void {
    if (busy) return;
    answer = '';
    result = null;
    error = '';
    selfResolution = '';
    loadedPreset = null;
  }

  function scoreText(value: number | null): string {
    return value === null ? '—' : value.toFixed(3);
  }

  function tracePosition(value: number | null): number {
    if (value === null) return 0;
    return Math.max(2, Math.min(98, ((value - 0.68) / 0.28) * 100));
  }

  function coveragePercent(value: number | null): number {
    if (value === null) return 0;
    return Math.max(0, Math.min(100, value * 100));
  }

  function probabilityPosition(value: number | null): number {
    if (value === null) return 0;
    return Math.max(2, Math.min(98, value * 100));
  }

  function conceptIsCovered(concept: SemanticGradeResponse['required_concepts'][number]): boolean {
    return concept.covered;
  }

  function conceptEvidenceLabel(
    concept: SemanticGradeResponse['required_concepts'][number],
  ): string {
    if (concept.evidence === 'explicit') return 'explicit';
    if (concept.evidence === 'context') return 'from context';
    if (concept.evidence === 'optional_omitted') return 'optional detail';
    if (concept.evidence === 'missing') return 'not clear';
    return scoreText(concept.score);
  }

  function conceptEvidenceIcon(
    concept: SemanticGradeResponse['required_concepts'][number],
  ): string {
    if (concept.evidence === 'context') return '↳';
    if (concept.evidence === 'optional_omitted') return '+';
    return concept.covered ? '✓' : '·';
  }

  function expectedVerdict(tone: PresetTone): SemanticGradeResponse['verdict'] {
    return tone === 'valid' ? 'correct' : 'incorrect';
  }

  function methodLabel(value: SemanticGradeResponse): string {
    if (value.answer_quality === 'concise') return 'curated concise gloss';
    if (value.exact_match) return 'exact normalized match';
    if (!value.model_available) return 'safe fallback only';
    if (value.verification.checked) return 'embedding + entailment';
    if (!value.verification.available) return 'embedding; verifier offline';
    return 'semantic rubric';
  }
</script>

<svelte:head>
  <title>Meaning Lab · VerbPractice Playground</title>
  <meta
    name="description"
    content="Test a fully local semantic answer grader against multilingual explanations, partial answers, and meaning traps."
  />
</svelte:head>

<section class="meaning-lab">
  <header class="lab-hero">
    <div class="hero-copy">
      <div class="lab-kicker">
        <span class="live-dot" aria-hidden="true"></span>
        Playground / local experiment
      </div>
      <h1>Does the answer carry<br /><em>the same idea?</em></h1>
      <p>
        Test explanations that cannot be graded word-for-word. The model runs on this machine,
        shows its evidence, and can choose not to decide.
      </p>
    </div>

    <aside class="local-note" aria-label="Experiment boundaries">
      <div class="model-mark" aria-hidden="true">
        <span>e5+nli</span>
        <i></i>
      </div>
      <div>
        <strong>Local meaning model</strong>
        <span>No paid API · no progress changes</span>
      </div>
      <p>
        This is a prototype, not the live trainer. Its job is to expose where lightweight
        grading feels trustworthy—and where it does not.
      </p>
    </aside>
  </header>

  <nav class="challenge-strip" aria-label="Meaning challenges">
    {#each challenges as challenge, index (challenge.id)}
      <button
        type="button"
        class:active={active.id === challenge.id}
        aria-pressed={active.id === challenge.id}
        on:click={() => chooseChallenge(challenge)}
        disabled={busy}
      >
        <span>{String(index + 1).padStart(2, '0')} · {challenge.languageCode}</span>
        <strong>{challenge.term}</strong>
        <small>{challenge.note}</small>
      </button>
    {/each}
  </nav>

  <div class="workbench">
    <section class="answer-bench" aria-labelledby="active-term">
      <header class="word-card">
        <div class="word-meta">
          <span>{active.language} · sense test</span>
          <button type="button" on:click={() => (showRubric = !showRubric)} disabled={busy}>
            {showRubric ? 'Hide rubric' : 'Inspect rubric'}
          </button>
        </div>
        <h2 id="active-term">{active.term}</h2>
        <blockquote lang={active.languageCode.toLowerCase()}>{active.context}</blockquote>
        <p>{active.prompt}</p>
      </header>

      {#if showRubric}
        <aside class="rubric-sheet">
          <div class="rubric-heading">
            <span>What “right” means</span>
            <p>The model is not inventing a definition; it compares against this small human-written rubric.</p>
          </div>
          <div class="rubric-columns">
            <div>
              <strong>Essential ideas</strong>
              <ul>
                {#each active.requiredConcepts as concept}
                  <li><i aria-hidden="true"></i>{concept.label}</li>
                {/each}
              </ul>
            </div>
            <div>
              <strong>Nearby traps</strong>
              <ul class="trap-list">
                {#each active.hardNegatives as negative}
                  <li><i aria-hidden="true"></i>{negative.label}</li>
                {/each}
              </ul>
            </div>
          </div>
        </aside>
      {/if}

      <form class="answer-form" on:submit|preventDefault={gradeAnswer}>
        <div class="answer-heading">
          <label for="semantic-answer">Explain it in your own words</label>
          <span>Any of these languages can carry the meaning</span>
        </div>
        <div class="language-row" aria-label="Accepted answer languages">
          {#each active.acceptedLanguages as language}
            <span>{language}</span>
          {/each}
        </div>
        <textarea
          id="semantic-answer"
          bind:value={answer}
          on:input={handleAnswerInput}
          on:keydown={handleAnswerKeydown}
          maxlength="600"
          rows="5"
          placeholder="A phrase or short explanation…"
          aria-describedby="answer-help"
          disabled={busy}
        ></textarea>
        <div class="answer-foot">
          <span id="answer-help"><kbd>Ctrl</kbd> <b>+</b> <kbd>Enter</kbd> to check</span>
          <span>{answer.length} / 600</span>
        </div>

        <div class="preset-group">
          <span>Load a stress test</span>
          <div>
            {#each active.presets as preset}
              <button
                type="button"
                class={`preset-${preset.tone}`}
                on:click={() => usePreset(preset)}
                disabled={busy}
              >
                <i aria-hidden="true"></i>{preset.label}
              </button>
            {/each}
          </div>
        </div>

        {#if error}
          <p class="form-error" role="alert">{error}</p>
        {/if}

        <div class="form-actions">
          <button class="grade-button" type="submit" disabled={busy || !answer.trim()}>
            {#if busy}
              <span class="button-spinner" aria-hidden="true"></span>
              Reading the meaning…
            {:else}
              Check the meaning
              <span aria-hidden="true">→</span>
            {/if}
          </button>
          <button class="reset-button" type="button" on:click={resetRun} disabled={busy}>
            Clear
          </button>
        </div>
      </form>
    </section>

    <section class="evidence-bench" class:has-result={Boolean(result)} aria-busy={busy}>
      <div class="trace-header">
        <div>
          <span>Semantic trace</span>
          <strong>{result ? 'Run complete' : busy ? 'Reading answer' : 'Waiting for an answer'}</strong>
        </div>
        <small>Similarity is evidence, not probability.</small>
      </div>

      {#if busy}
        <div class="reading-state" aria-live="polite">
          <div class="scan-field" aria-hidden="true">
            <i></i>
            <span></span>
            <b></b>
          </div>
          <strong>Comparing ideas across languages</strong>
          <p>One answer, several valid explanations, essential concepts, and known traps.</p>
        </div>
      {:else if result}
        {@const copy = result.answer_quality === 'concise' ? conciseCorrectCopy : verdictCopy[result.verdict]}
        <div
          class={`result-sheet verdict-${result.verdict}`}
          bind:this={resultRegion}
          tabindex="-1"
          aria-live="polite"
        >
          <header class="verdict-head">
            <div class="verdict-symbol" aria-hidden="true">
              {result.verdict === 'correct' ? '✓' : result.verdict === 'partial' ? '≈' : result.verdict === 'incorrect' ? '×' : '?'}
            </div>
            <div>
              <span>{copy.eyebrow}</span>
              <h3>{copy.title}</h3>
              <p>{copy.body}</p>
            </div>
          </header>

          {#if loadedPreset}
            {@const expected = expectedVerdict(loadedPreset.tone)}
            <div class:matched={result.verdict === expected} class="fixture-check">
              <span>Test fixture</span>
              <p>
                <strong>Expected {expected}</strong>
                <i aria-hidden="true">→</i>
                <strong>Observed {result.verdict}</strong>
              </p>
              <small>
                {result.verdict === expected
                  ? 'The grader agrees with this human-labelled example.'
                  : 'Useful disagreement: this case should stay visible during calibration.'}
              </small>
            </div>
          {/if}

          <div class="meaning-traces">
            <article>
              <div class="trace-label">
                <span>Nearest valid explanation</span>
                <strong>{scoreText(result.positive_score)}</strong>
              </div>
              <div class="score-track positive-track" aria-hidden="true">
                <i style={`left:${tracePosition(result.positive_score)}%`}></i>
              </div>
              <small>Higher means more related; it does not prove correctness.</small>
            </article>

            <article>
              <div class="trace-label">
                <span>{result.answer_quality === 'concise' ? 'Minimum meaning carried' : 'Meaning-component evidence'}</span>
                <strong>{result.answer_quality === 'concise' ? 'Yes' : `${Math.round(coveragePercent(result.concept_coverage))}%`}</strong>
              </div>
              <div class="coverage-track" aria-hidden="true">
                <i style={`width:${result.answer_quality === 'concise' ? 100 : coveragePercent(result.concept_coverage)}%`}></i>
              </div>
              <small>
                {result.answer_quality === 'concise'
                  ? `${result.required_concepts.filter(conceptIsCovered).length} of ${result.required_concepts.length} meaning signals are explicit or supplied by context. This answer meets the curated minimum; omitted detail stays optional.`
                  : `${result.required_concepts.filter(conceptIsCovered).length} of ${result.required_concepts.length} components cleared the current checks.`}
              </small>
            </article>

            <article>
              <div class="trace-label">
                <span>Nearest known trap</span>
                <strong>{scoreText(result.negative_score)}</strong>
              </div>
              <div class="score-track negative-track" aria-hidden="true">
                <i style={`left:${tracePosition(result.negative_score)}%`}></i>
              </div>
              <small>Lower is safer. The valid-vs-trap margin is {result.margin === null ? '—' : result.margin.toFixed(3)}.</small>
            </article>

            <article>
              <div class="trace-label">
                <span>Entailment verifier</span>
                <strong>{result.verification.checked ? scoreText(result.verification.entailment_score) : '—'}</strong>
              </div>
              <div class="score-track verifier-track" aria-hidden="true">
                <i style={`left:${probabilityPosition(result.verification.entailment_score)}%`}></i>
              </div>
              <small>
                {result.verification.checked
                  ? `Contradiction ${scoreText(result.verification.contradiction_score)} · valid-over-trap lead ${scoreText(result.verification.entailment_margin)}.`
                  : result.verification.available
                    ? 'Runs only after the embedding rubric clears every safety gate.'
                    : 'Not installed; semantic similarity cannot auto-accept a paraphrase.'}
              </small>
            </article>
          </div>

          <div class="concept-audit">
            <span>Meaning components</span>
            <div>
              {#each result.required_concepts as concept}
                <article
                  class:covered={concept.covered}
                  class:optional={concept.evidence === 'optional_omitted'}
                >
                  <i aria-hidden="true">{conceptEvidenceIcon(concept)}</i>
                  <p><strong>{concept.label}</strong><small>{conceptEvidenceLabel(concept)}</small></p>
                </article>
              {/each}
            </div>
          </div>

          {#if result.reasons.length}
            <div class="reason-note">
              <span>Why this verdict</span>
              <ul>
                {#each result.reasons as reason}
                  <li>{reason}</li>
                {/each}
              </ul>
            </div>
          {/if}

          <details class="reference-detail">
            <summary>Closest accepted explanation</summary>
            <p>{result.matched_reference.text}</p>
            <span>Similarity {scoreText(result.matched_reference.score)}</span>
          </details>

          {#if result.verdict === 'uncertain'}
            <div class="human-call">
              <span>The reference says</span>
              <p>{active.reference}</p>
              {#if !selfResolution}
                <strong>Choose a demo-only outcome</strong>
                <div>
                  <button type="button" on:click={() => (selfResolution = 'same')}>Treat as correct</button>
                  <button type="button" on:click={() => (selfResolution = 'different')}>Treat as incorrect</button>
                </div>
              {:else}
                <div class={`self-resolution ${selfResolution}`}>
                  <i aria-hidden="true">{selfResolution === 'same' ? '✓' : '↺'}</i>
                  <p>
                    <strong>{selfResolution === 'same' ? 'Demo override: correct.' : 'Demo override: incorrect.'}</strong>
                    <span>The backend verdict remains uncertain; no training score was changed.</span>
                  </p>
                </div>
              {/if}
            </div>
          {/if}

          <footer class="run-meta">
            <span>
              <i class:offline={!result.model_available}></i>
              {result.model_available ? result.model_name : 'Model unavailable'}
            </span>
            <span>{methodLabel(result)}</span>
            <span>{Math.round(result.latency_ms)} ms</span>
          </footer>
        </div>
      {:else}
        <div class="empty-trace">
          <div class="trace-map" aria-hidden="true">
            <span class="map-answer">your answer</span>
            <i class="map-line line-one"></i>
            <i class="map-line line-two"></i>
            <i class="map-line line-three"></i>
            <span class="map-node node-one"><b>A</b> valid explanations</span>
            <span class="map-node node-two"><b>B</b> essential ideas</span>
            <span class="map-node node-three"><b>C</b> nearby traps</span>
          </div>
          <div class="empty-copy">
            <strong>One score is not enough.</strong>
            <p>
              The lab looks for resemblance, completeness, and contradictions separately,
              then returns correct, partial, incorrect, or uncertain.
            </p>
          </div>
        </div>
      {/if}
    </section>
  </div>

  <footer class="lab-footer">
    <span>Prototype boundary</span>
    <p>
      Answers stay in this request. The demo does not save them, change spaced-repetition
      scores, or call a paid model.
    </p>
    <a href="#main-content">Back to top ↑</a>
  </footer>
</section>

<style>
  :global(html[data-playground='meaning-lab']) {
    --lab-paper: #edf2ff;
    --lab-paper-deep: #dce5fa;
    --lab-sheet: #f9fbff;
    --lab-ink: #172033;
    --lab-muted: #4f5c75;
    --lab-line: #c8d3ea;
    --lab-cobalt: #3656d4;
    --lab-cobalt-soft: #dfe6ff;
    --lab-jade: #176c59;
    --lab-jade-soft: #ddf3eb;
    --lab-coral: #b64038;
    --lab-coral-soft: #ffe4df;
    --lab-amber: #8c4d0b;
    --lab-amber-soft: #fff0d6;
    color-scheme: light;
  }

  :global(html[data-playground='meaning-lab'] body) {
    color: var(--lab-ink);
    background:
      linear-gradient(rgba(54, 86, 212, 0.055) 1px, transparent 1px),
      linear-gradient(90deg, rgba(54, 86, 212, 0.055) 1px, transparent 1px),
      radial-gradient(circle at 8% 4%, rgba(89, 124, 238, 0.18), transparent 28rem),
      radial-gradient(circle at 94% 24%, rgba(35, 128, 105, 0.11), transparent 30rem),
      var(--lab-paper);
    background-size: 28px 28px, 28px 28px, auto, auto, auto;
    background-attachment: fixed;
  }

  :global(html[data-playground='meaning-lab'] body::before),
  :global(html[data-playground='meaning-lab'] body::after) {
    display: none;
  }

  :global(html[data-playground='meaning-lab'] .page-floor) {
    border-color: rgba(54, 86, 212, 0.14);
    background: linear-gradient(180deg, transparent, rgba(54, 86, 212, 0.08));
  }

  :global(html[data-playground='meaning-lab'][data-playground-nav='absent'] .workspace-shell) {
    padding-top: 2rem;
  }

  .meaning-lab {
    width: min(100%, 1180px);
    margin-inline: auto;
    color: var(--lab-ink);
    font-family: "Figtree", sans-serif;
  }

  button,
  textarea {
    font: inherit;
  }

  button:disabled,
  textarea:disabled {
    cursor: not-allowed;
    opacity: 0.58;
  }

  button:focus-visible,
  textarea:focus-visible,
  .result-sheet:focus-visible,
  a:focus-visible {
    outline: 3px solid color-mix(in srgb, var(--lab-cobalt) 65%, white);
    outline-offset: 3px;
  }

  .lab-hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(280px, 380px);
    gap: clamp(2rem, 7vw, 6rem);
    align-items: end;
    padding: clamp(1rem, 4vw, 3.2rem) 0 clamp(2.3rem, 5vw, 4.2rem);
    border-bottom: 1px solid var(--lab-line);
  }

  .hero-copy {
    max-width: 770px;
  }

  .lab-kicker,
  .word-meta,
  .trace-header span,
  .rubric-heading > span,
  .preset-group > span,
  .concept-audit > span,
  .reason-note > span,
  .human-call > span,
  .lab-footer > span {
    font: 600 0.7rem/1.2 "IBM Plex Mono", monospace;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  .lab-kicker {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    color: var(--lab-cobalt);
  }

  .live-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--lab-jade);
    box-shadow: 0 0 0 5px rgba(35, 128, 105, 0.12);
  }

  .hero-copy h1 {
    margin: 1.3rem 0 1.15rem;
    color: var(--lab-ink);
    font: 700 clamp(3.2rem, 7.4vw, 7.3rem)/0.86 "Space Grotesk", sans-serif;
    letter-spacing: -0.078em;
  }

  .hero-copy h1 em {
    color: var(--lab-cobalt);
    font-style: normal;
  }

  .hero-copy > p {
    max-width: 660px;
    margin: 0;
    color: var(--lab-muted);
    font-size: clamp(1rem, 1.7vw, 1.2rem);
    line-height: 1.55;
  }

  .local-note {
    position: relative;
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.8rem 0.9rem;
    padding: 1.15rem;
    border: 1px solid var(--lab-line);
    border-radius: 4px 22px 4px 4px;
    background: rgba(249, 251, 255, 0.82);
    box-shadow: 12px 12px 0 rgba(54, 86, 212, 0.08);
  }

  .model-mark {
    position: relative;
    display: grid;
    width: 46px;
    height: 46px;
    place-items: center;
    overflow: hidden;
    border: 1px solid var(--lab-cobalt);
    border-radius: 50%;
    color: var(--lab-cobalt);
    background: var(--lab-cobalt-soft);
    font: 700 0.57rem/1 "IBM Plex Mono", monospace;
  }

  .model-mark i {
    position: absolute;
    width: 52px;
    height: 1px;
    background: var(--lab-cobalt);
    transform: rotate(-34deg);
  }

  .local-note > div:nth-child(2) {
    display: grid;
    align-content: center;
    gap: 0.18rem;
  }

  .local-note strong {
    font: 700 0.92rem/1.2 "Space Grotesk", sans-serif;
  }

  .local-note span {
    color: var(--lab-jade);
    font: 600 0.66rem/1.3 "IBM Plex Mono", monospace;
  }

  .local-note p {
    grid-column: 1 / -1;
    margin: 0.25rem 0 0;
    color: var(--lab-muted);
    font-size: 0.8rem;
    line-height: 1.5;
  }

  .challenge-strip {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 1px;
    margin: 1.35rem 0;
    padding: 1px;
    background: var(--lab-line);
  }

  .challenge-strip button {
    position: relative;
    display: grid;
    min-height: 142px;
    gap: 0.4rem;
    align-content: start;
    padding: 1rem;
    border: 0;
    color: var(--lab-ink);
    background: rgba(249, 251, 255, 0.84);
    text-align: left;
    transition: background 160ms ease, transform 160ms ease;
  }

  .challenge-strip button::after {
    position: absolute;
    right: 1rem;
    bottom: 0.85rem;
    width: 9px;
    height: 9px;
    border: 1px solid var(--lab-line);
    border-radius: 50%;
    content: '';
  }

  .challenge-strip button.active {
    z-index: 1;
    background: var(--lab-cobalt-soft);
    box-shadow: inset 0 -4px 0 var(--lab-cobalt);
  }

  .challenge-strip button.active::after {
    border-color: var(--lab-cobalt);
    background: var(--lab-cobalt);
    box-shadow: 0 0 0 4px rgba(54, 86, 212, 0.12);
  }

  .challenge-strip button:hover:not(:disabled) {
    background: color-mix(in srgb, var(--lab-cobalt-soft) 60%, white);
  }

  .challenge-strip span {
    color: var(--lab-cobalt);
    font: 650 0.66rem/1 "IBM Plex Mono", monospace;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .challenge-strip strong {
    font: 700 1.35rem/1.1 "Space Grotesk", sans-serif;
    letter-spacing: -0.035em;
  }

  .challenge-strip small {
    max-width: 31ch;
    color: var(--lab-muted);
    font-size: 0.74rem;
    line-height: 1.4;
  }

  .workbench {
    display: grid;
    grid-template-columns: minmax(0, 1.05fr) minmax(390px, 0.95fr);
    border: 1px solid var(--lab-line);
    background: var(--lab-sheet);
    box-shadow: 0 24px 60px -42px rgba(23, 32, 51, 0.45);
  }

  .answer-bench,
  .evidence-bench {
    min-width: 0;
    padding: clamp(1.2rem, 3vw, 2.2rem);
  }

  .answer-bench {
    border-right: 1px solid var(--lab-line);
  }

  .word-card {
    padding-bottom: 1.4rem;
    border-bottom: 1px solid var(--lab-line);
  }

  .word-meta {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
    color: var(--lab-cobalt);
  }

  .word-meta button {
    min-height: 38px;
    padding: 0.45rem 0.7rem;
    border: 1px solid var(--lab-line);
    border-radius: 999px;
    color: var(--lab-cobalt);
    background: transparent;
    font: 600 0.66rem/1 "Figtree", sans-serif;
  }

  .word-card h2 {
    margin: 1.2rem 0 0.7rem;
    color: var(--lab-ink);
    font: 700 clamp(3rem, 7vw, 5.7rem)/0.86 "Space Grotesk", sans-serif;
    letter-spacing: -0.075em;
  }

  .word-card blockquote {
    margin: 0;
    padding-left: 0.85rem;
    border-left: 3px solid var(--lab-cobalt);
    color: var(--lab-muted);
    font-size: 0.86rem;
    font-style: italic;
    line-height: 1.45;
  }

  .word-card > p {
    margin: 1rem 0 0;
    font: 650 1rem/1.35 "Space Grotesk", sans-serif;
  }

  .rubric-sheet {
    margin-top: 1rem;
    padding: 1rem;
    border: 1px dashed color-mix(in srgb, var(--lab-cobalt) 45%, var(--lab-line));
    background: color-mix(in srgb, var(--lab-cobalt-soft) 42%, white);
    animation: sheet-open 180ms ease-out both;
  }

  @keyframes sheet-open {
    from { opacity: 0; transform: translateY(-5px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .rubric-heading {
    display: grid;
    gap: 0.35rem;
  }

  .rubric-heading > span {
    color: var(--lab-cobalt);
  }

  .rubric-heading p {
    margin: 0;
    color: var(--lab-muted);
    font-size: 0.76rem;
    line-height: 1.45;
  }

  .rubric-columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-top: 0.9rem;
  }

  .rubric-columns strong {
    font-size: 0.75rem;
  }

  .rubric-columns ul {
    display: grid;
    gap: 0.35rem;
    margin: 0.5rem 0 0;
    padding: 0;
    list-style: none;
  }

  .rubric-columns li {
    display: flex;
    gap: 0.45rem;
    color: var(--lab-muted);
    font-size: 0.72rem;
    line-height: 1.35;
  }

  .rubric-columns li i {
    flex: 0 0 auto;
    width: 7px;
    height: 7px;
    margin-top: 0.25rem;
    border-radius: 50%;
    background: var(--lab-jade);
  }

  .rubric-columns .trap-list i {
    background: var(--lab-coral);
  }

  .answer-form {
    display: grid;
    gap: 0.85rem;
    padding-top: 1.4rem;
  }

  .answer-heading {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: end;
  }

  .answer-heading label {
    color: var(--lab-ink);
    font: 700 0.94rem/1.2 "Space Grotesk", sans-serif;
  }

  .answer-heading span {
    max-width: 190px;
    color: var(--lab-muted);
    font-size: 0.68rem;
    line-height: 1.35;
    text-align: right;
  }

  .language-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }

  .language-row span {
    padding: 0.3rem 0.48rem;
    border: 1px solid var(--lab-line);
    border-radius: 999px;
    color: var(--lab-muted);
    background: var(--lab-paper);
    font: 600 0.62rem/1 "IBM Plex Mono", monospace;
  }

  textarea {
    width: 100%;
    min-height: 140px;
    box-sizing: border-box;
    padding: 1rem;
    border: 1px solid var(--lab-line);
    border-radius: 3px 16px 3px 3px;
    outline: 0;
    color: var(--lab-ink);
    background:
      linear-gradient(transparent 31px, rgba(54, 86, 212, 0.08) 32px),
      white;
    background-size: 100% 32px;
    font-size: 1rem;
    line-height: 2;
    resize: vertical;
    transition: border-color 160ms ease, box-shadow 160ms ease;
  }

  textarea:focus {
    border-color: var(--lab-cobalt);
    box-shadow: 0 0 0 4px rgba(54, 86, 212, 0.09);
  }

  textarea::placeholder {
    color: #929db2;
  }

  textarea:disabled {
    background-color: #f2f5fb;
  }

  .answer-foot {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    color: var(--lab-muted);
    font-size: 0.64rem;
  }

  .answer-foot kbd {
    padding: 0.14rem 0.3rem;
    border: 1px solid var(--lab-line);
    border-bottom-width: 2px;
    border-radius: 3px;
    background: white;
    font: 600 0.58rem/1 "IBM Plex Mono", monospace;
  }

  .answer-foot b {
    font-weight: 500;
  }

  .preset-group {
    display: grid;
    gap: 0.55rem;
    padding-top: 0.35rem;
  }

  .preset-group > span {
    color: var(--lab-muted);
  }

  .preset-group > div {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
  }

  .preset-group button {
    display: flex;
    min-height: 40px;
    gap: 0.4rem;
    align-items: center;
    padding: 0.5rem 0.7rem;
    border: 1px solid var(--lab-line);
    border-radius: 999px;
    color: var(--lab-ink);
    background: white;
    font-size: 0.68rem;
  }

  .preset-group button i {
    width: 7px;
    height: 7px;
    border-radius: 50%;
  }

  .preset-valid i { background: var(--lab-jade); }
  .preset-partial i { background: var(--lab-amber); }
  .preset-trap i { background: var(--lab-coral); }

  .preset-group button:hover:not(:disabled) {
    border-color: var(--lab-cobalt);
    background: var(--lab-cobalt-soft);
  }

  .form-error {
    margin: 0;
    padding: 0.7rem 0.8rem;
    border-left: 3px solid var(--lab-coral);
    color: #8d302c;
    background: var(--lab-coral-soft);
    font-size: 0.76rem;
    line-height: 1.4;
  }

  .form-actions {
    display: flex;
    gap: 0.6rem;
    margin-top: 0.25rem;
  }

  .grade-button,
  .reset-button {
    min-height: 50px;
    border-radius: 3px;
    font-weight: 700;
  }

  .grade-button {
    display: flex;
    flex: 1;
    gap: 0.7rem;
    align-items: center;
    justify-content: space-between;
    padding: 0.7rem 1rem;
    border: 1px solid var(--lab-cobalt);
    color: white;
    background: var(--lab-cobalt);
    box-shadow: 5px 5px 0 #b9c6f6;
  }

  .grade-button:hover:not(:disabled) {
    transform: translate(-1px, -1px);
    box-shadow: 7px 7px 0 #b9c6f6;
  }

  .grade-button:disabled,
  .reset-button:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }

  .reset-button {
    padding: 0.7rem 1rem;
    border: 1px solid var(--lab-line);
    color: var(--lab-muted);
    background: transparent;
  }

  .button-spinner {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.4);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 700ms linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .evidence-bench {
    display: flex;
    min-height: 690px;
    flex-direction: column;
    background:
      linear-gradient(rgba(54, 86, 212, 0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(54, 86, 212, 0.04) 1px, transparent 1px),
      #f4f7ff;
    background-size: 22px 22px;
  }

  .trace-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: start;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--lab-line);
  }

  .trace-header > div {
    display: grid;
    gap: 0.3rem;
  }

  .trace-header span {
    color: var(--lab-cobalt);
  }

  .trace-header strong {
    font: 700 0.9rem/1.2 "Space Grotesk", sans-serif;
  }

  .trace-header small {
    max-width: 150px;
    color: var(--lab-muted);
    font-size: 0.62rem;
    line-height: 1.35;
    text-align: right;
  }

  .empty-trace,
  .reading-state {
    display: grid;
    flex: 1;
    place-content: center;
    gap: 2rem;
  }

  .trace-map {
    position: relative;
    width: min(100%, 390px);
    height: 295px;
    margin-inline: auto;
  }

  .map-answer {
    position: absolute;
    z-index: 2;
    left: 50%;
    top: 50%;
    display: grid;
    width: 90px;
    height: 90px;
    place-items: center;
    border: 1px solid var(--lab-cobalt);
    border-radius: 50%;
    color: var(--lab-cobalt);
    background: var(--lab-cobalt-soft);
    font: 650 0.67rem/1.2 "IBM Plex Mono", monospace;
    text-align: center;
    transform: translate(-50%, -50%);
    box-shadow: 0 0 0 12px rgba(54, 86, 212, 0.06);
  }

  .map-node {
    position: absolute;
    z-index: 2;
    display: flex;
    width: 132px;
    gap: 0.45rem;
    align-items: center;
    color: var(--lab-muted);
    font-size: 0.68rem;
    line-height: 1.25;
  }

  .map-node b {
    display: grid;
    flex: 0 0 auto;
    width: 27px;
    height: 27px;
    place-items: center;
    border: 1px solid currentColor;
    border-radius: 50%;
    color: var(--lab-cobalt);
    background: var(--lab-sheet);
    font: 700 0.62rem/1 "IBM Plex Mono", monospace;
  }

  .node-one { left: 0; top: 22px; }
  .node-two { right: 0; top: 24px; }
  .node-three { left: 50%; bottom: 0; transform: translateX(-50%); }
  .node-three b { color: var(--lab-coral); }

  .map-line {
    position: absolute;
    left: 50%;
    top: 50%;
    width: 150px;
    height: 1px;
    transform-origin: left center;
    background: repeating-linear-gradient(90deg, var(--lab-line) 0 5px, transparent 5px 9px);
  }

  .line-one { transform: rotate(-145deg); }
  .line-two { transform: rotate(-35deg); }
  .line-three { transform: rotate(90deg); }

  .empty-copy {
    max-width: 400px;
    margin-inline: auto;
    text-align: center;
  }

  .empty-copy strong {
    font: 700 1.2rem/1.2 "Space Grotesk", sans-serif;
  }

  .empty-copy p,
  .reading-state p {
    margin: 0.55rem 0 0;
    color: var(--lab-muted);
    font-size: 0.78rem;
    line-height: 1.5;
  }

  .reading-state {
    justify-items: center;
    gap: 0.7rem;
    text-align: center;
  }

  .scan-field {
    position: relative;
    width: 180px;
    height: 180px;
    overflow: hidden;
    border: 1px solid var(--lab-line);
    border-radius: 50%;
    background:
      linear-gradient(var(--lab-line), var(--lab-line)) center/1px 100% no-repeat,
      linear-gradient(90deg, var(--lab-line), var(--lab-line)) center/100% 1px no-repeat,
      var(--lab-cobalt-soft);
  }

  .scan-field::after {
    position: absolute;
    inset: 18px;
    border: 1px solid rgba(54, 86, 212, 0.25);
    border-radius: 50%;
    content: '';
  }

  .scan-field i {
    position: absolute;
    left: 50%;
    top: 50%;
    width: 50%;
    height: 1px;
    transform-origin: left;
    background: var(--lab-cobalt);
    animation: scan 1.4s linear infinite;
  }

  .scan-field span,
  .scan-field b {
    position: absolute;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--lab-jade);
  }

  .scan-field span { left: 38px; top: 52px; }
  .scan-field b { right: 34px; bottom: 46px; background: var(--lab-coral); }

  @keyframes scan {
    to { transform: rotate(360deg); }
  }

  .reading-state strong {
    margin-top: 0.5rem;
    font: 700 1.05rem/1.2 "Space Grotesk", sans-serif;
  }

  .reading-state p {
    max-width: 350px;
  }

  .result-sheet {
    padding-top: 1.2rem;
    scroll-margin-top: 1rem;
    outline: 0;
    animation: result-in 240ms ease-out both;
  }

  @keyframes result-in {
    from { opacity: 0; transform: translateY(7px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .verdict-head {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.9rem;
    align-items: start;
    padding-bottom: 1.1rem;
  }

  .verdict-symbol {
    display: grid;
    width: 47px;
    height: 47px;
    place-items: center;
    border: 1px solid currentColor;
    border-radius: 50%;
    font: 700 1.25rem/1 "IBM Plex Mono", monospace;
  }

  .verdict-head > div:last-child {
    display: grid;
    gap: 0.25rem;
  }

  .verdict-head span {
    font: 650 0.65rem/1 "IBM Plex Mono", monospace;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .verdict-head h3 {
    margin: 0;
    font: 700 clamp(1.45rem, 3vw, 2rem)/1.05 "Space Grotesk", sans-serif;
    letter-spacing: -0.045em;
  }

  .verdict-head p {
    margin: 0.25rem 0 0;
    color: var(--lab-muted);
    font-size: 0.74rem;
    line-height: 1.45;
  }

  .verdict-correct .verdict-head { color: var(--lab-jade); }
  .verdict-partial .verdict-head { color: var(--lab-amber); }
  .verdict-incorrect .verdict-head { color: var(--lab-coral); }
  .verdict-uncertain .verdict-head { color: var(--lab-cobalt); }
  .verdict-head h3,
  .verdict-head p { color: var(--lab-ink); }
  .verdict-head p { color: var(--lab-muted); }

  .fixture-check {
    display: grid;
    gap: 0.35rem;
    margin-bottom: 0.9rem;
    padding: 0.75rem 0.8rem;
    border: 1px solid color-mix(in srgb, var(--lab-coral) 42%, var(--lab-line));
    background: var(--lab-coral-soft);
  }

  .fixture-check.matched {
    border-color: color-mix(in srgb, var(--lab-jade) 42%, var(--lab-line));
    background: var(--lab-jade-soft);
  }

  .fixture-check > span {
    color: var(--lab-muted);
    font: 600 0.66rem/1 "IBM Plex Mono", monospace;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .fixture-check p {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    align-items: center;
    margin: 0;
    color: var(--lab-coral);
    font: 650 0.7rem/1.2 "IBM Plex Mono", monospace;
  }

  .fixture-check.matched p {
    color: var(--lab-jade);
  }

  .fixture-check p i {
    color: var(--lab-muted);
    font-style: normal;
  }

  .fixture-check small {
    color: var(--lab-muted);
    font-size: 0.68rem;
    line-height: 1.35;
  }

  .meaning-traces {
    display: grid;
    gap: 0.9rem;
    padding: 1rem 0;
    border-block: 1px solid var(--lab-line);
  }

  .meaning-traces article {
    display: grid;
    gap: 0.38rem;
  }

  .trace-label {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
  }

  .trace-label span {
    color: var(--lab-muted);
    font-size: 0.7rem;
  }

  .trace-label strong {
    font: 700 0.75rem/1 "IBM Plex Mono", monospace;
  }

  .score-track,
  .coverage-track {
    position: relative;
    height: 9px;
    border: 1px solid var(--lab-line);
    background:
      linear-gradient(90deg, transparent 24%, var(--lab-line) 25%, transparent 26%, transparent 49%, var(--lab-line) 50%, transparent 51%, transparent 74%, var(--lab-line) 75%, transparent 76%),
      white;
  }

  .score-track::before,
  .score-track::after {
    position: absolute;
    top: 14px;
    color: var(--lab-muted);
    font: 500 0.62rem/1 "IBM Plex Mono", monospace;
  }

  .score-track::before { left: 0; content: '.68'; }
  .score-track::after { right: 0; content: '.96'; }

  .score-track {
    margin-bottom: 0.72rem;
  }

  .score-track i {
    position: absolute;
    z-index: 2;
    top: 50%;
    width: 13px;
    height: 13px;
    border: 3px solid white;
    border-radius: 50%;
    background: var(--lab-jade);
    box-shadow: 0 0 0 1px var(--lab-jade);
    transform: translate(-50%, -50%);
  }

  .negative-track i {
    background: var(--lab-coral);
    box-shadow: 0 0 0 1px var(--lab-coral);
  }

  .verifier-track::before { content: '0'; }
  .verifier-track::after { content: '1'; }

  .verifier-track i {
    background: var(--lab-cobalt);
    box-shadow: 0 0 0 1px var(--lab-cobalt);
  }

  .coverage-track i {
    display: block;
    height: 100%;
    background: var(--lab-cobalt);
    transition: width 420ms ease;
  }

  .meaning-traces article > small {
    color: var(--lab-muted);
    font-size: 0.68rem;
    line-height: 1.35;
  }

  .concept-audit {
    display: grid;
    gap: 0.65rem;
    padding: 1rem 0;
  }

  .concept-audit > span {
    color: var(--lab-muted);
  }

  .concept-audit > div {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.45rem;
  }

  .concept-audit article {
    display: flex;
    min-width: 0;
    gap: 0.5rem;
    align-items: center;
    padding: 0.6rem;
    border: 1px solid var(--lab-line);
    color: var(--lab-coral);
    background: rgba(255, 255, 255, 0.7);
  }

  .concept-audit article.covered {
    color: var(--lab-jade);
    background: var(--lab-jade-soft);
  }

  .concept-audit article.optional {
    color: var(--lab-amber);
    background: var(--lab-amber-soft);
  }

  .concept-audit article > i {
    display: grid;
    flex: 0 0 auto;
    width: 22px;
    height: 22px;
    place-items: center;
    border: 1px solid currentColor;
    border-radius: 50%;
    font: 700 0.66rem/1 "IBM Plex Mono", monospace;
    font-style: normal;
  }

  .concept-audit p {
    display: grid;
    min-width: 0;
    gap: 0.15rem;
    margin: 0;
  }

  .concept-audit strong {
    overflow: hidden;
    color: var(--lab-ink);
    font-size: 0.65rem;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .concept-audit small {
    color: currentColor;
    font: 600 0.65rem/1 "IBM Plex Mono", monospace;
  }

  .reason-note,
  .human-call,
  .reference-detail {
    padding: 0.85rem;
    border: 1px solid var(--lab-line);
    background: rgba(255, 255, 255, 0.72);
  }

  .reason-note > span,
  .human-call > span {
    color: var(--lab-cobalt);
  }

  .reason-note ul {
    display: grid;
    gap: 0.28rem;
    margin: 0.55rem 0 0;
    padding-left: 1rem;
    color: var(--lab-muted);
    font-size: 0.68rem;
    line-height: 1.4;
  }

  .reference-detail {
    margin-top: 0.55rem;
  }

  .reference-detail summary {
    color: var(--lab-cobalt);
    cursor: pointer;
    font: 650 0.66rem/1.2 "Space Grotesk", sans-serif;
  }

  .reference-detail p {
    margin: 0.65rem 0 0.35rem;
    color: var(--lab-ink);
    font-size: 0.7rem;
    font-style: italic;
    line-height: 1.45;
  }

  .reference-detail span {
    color: var(--lab-muted);
    font: 550 0.65rem/1 "IBM Plex Mono", monospace;
  }

  .human-call {
    display: grid;
    gap: 0.6rem;
    margin-top: 0.7rem;
    border-color: color-mix(in srgb, var(--lab-cobalt) 38%, var(--lab-line));
    background: var(--lab-cobalt-soft);
  }

  .human-call > p {
    margin: 0;
    color: var(--lab-ink);
    font-size: 0.76rem;
    font-style: italic;
    line-height: 1.45;
  }

  .human-call > strong {
    font-size: 0.72rem;
  }

  .human-call > div:not(.self-resolution) {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
  }

  .human-call button {
    min-height: 40px;
    padding: 0.5rem 0.7rem;
    border: 1px solid var(--lab-cobalt);
    border-radius: 3px;
    color: var(--lab-cobalt);
    background: white;
    font-size: 0.66rem;
    font-weight: 700;
  }

  .self-resolution {
    display: flex;
    gap: 0.55rem;
    align-items: center;
    padding-top: 0.35rem;
    border-top: 1px solid rgba(54, 86, 212, 0.2);
  }

  .self-resolution > i {
    display: grid;
    width: 30px;
    height: 30px;
    place-items: center;
    border-radius: 50%;
    color: white;
    background: var(--lab-jade);
    font-style: normal;
  }

  .self-resolution.different > i {
    background: var(--lab-coral);
  }

  .self-resolution p {
    display: grid;
    gap: 0.12rem;
    margin: 0;
  }

  .self-resolution strong {
    font-size: 0.68rem;
  }

  .self-resolution span {
    color: var(--lab-muted);
    font-size: 0.68rem;
  }

  .run-meta {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 0.5rem;
    margin-top: 0.8rem;
    padding-top: 0.7rem;
    border-top: 1px solid var(--lab-line);
    color: var(--lab-muted);
    font: 550 0.65rem/1.25 "IBM Plex Mono", monospace;
  }

  .run-meta span:first-child {
    display: flex;
    gap: 0.35rem;
    align-items: center;
  }

  .run-meta i {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--lab-jade);
  }

  .run-meta i.offline {
    background: var(--lab-coral);
  }

  .lab-footer {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 1.2rem;
    align-items: center;
    margin-top: 1.35rem;
    padding: 1.15rem 0 0.25rem;
    border-top: 1px solid var(--lab-line);
  }

  .lab-footer > span {
    color: var(--lab-cobalt);
  }

  .lab-footer p {
    max-width: 660px;
    margin: 0;
    color: var(--lab-muted);
    font-size: 0.7rem;
    line-height: 1.45;
  }

  .lab-footer a {
    color: var(--lab-cobalt);
    font: 650 0.68rem/1 "IBM Plex Mono", monospace;
    text-decoration: none;
  }

  @media (max-width: 1050px) {
    .challenge-strip {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }

  @media (max-width: 900px) {
    .lab-hero {
      grid-template-columns: 1fr;
      gap: 2rem;
    }

    .local-note {
      width: min(100%, 440px);
      box-sizing: border-box;
    }

    .workbench {
      grid-template-columns: 1fr;
    }

    .answer-bench {
      border-right: 0;
      border-bottom: 1px solid var(--lab-line);
    }

    .evidence-bench {
      min-height: 580px;
    }
  }

  @media (max-width: 650px) {
    .hero-copy h1 {
      font-size: clamp(3rem, 15vw, 5rem);
    }

    .challenge-strip {
      grid-template-columns: none;
      grid-auto-columns: minmax(250px, 82vw);
      grid-auto-flow: column;
      gap: 0.55rem;
      overflow-x: auto;
      padding: 1px 1px 0.7rem;
      background: transparent;
      overscroll-behavior-inline: contain;
      scroll-snap-type: inline proximity;
      scrollbar-color: var(--lab-cobalt) var(--lab-paper-deep);
    }

    .challenge-strip button {
      min-height: 112px;
      border: 1px solid var(--lab-line);
      scroll-snap-align: start;
    }

    .rubric-columns,
    .concept-audit > div {
      grid-template-columns: 1fr;
    }

    .answer-heading,
    .trace-header {
      align-items: start;
      flex-direction: column;
    }

    .answer-heading {
      display: grid;
    }

    .answer-heading span,
    .trace-header small {
      max-width: none;
      text-align: left;
    }

    .form-actions {
      flex-direction: column;
    }

    .reset-button {
      width: 100%;
    }

    .trace-map {
      transform: scale(0.84);
    }

    .lab-footer {
      grid-template-columns: 1fr;
      gap: 0.55rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
      scroll-behavior: auto !important;
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
    }
  }
</style>
