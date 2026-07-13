<script lang="ts">
  export let kind: 'words' | 'verbs' | 'conjugation';

  type Pair = { prompt: string; answer: string };
  type LanguageTable = {
    code: 'FR' | 'ES' | 'EN' | 'RU';
    language: string;
    verb: string;
    meaning: string;
    tense: string;
    forms: Pair[];
  };

  const wordNewest: Pair[] = [
    { prompt: 'azotea', answer: 'rooftop' },
    { prompt: 'anochecer', answer: 'nightfall' },
    { prompt: 'desvelo', answer: 'sleeplessness' },
    { prompt: 'madrugar', answer: 'to get up early' },
    { prompt: 'hallazgo', answer: 'discovery' },
    { prompt: 'brisa', answer: 'breeze' },
  ];
  const wordFocus: Pair[] = [
    { prompt: 'aunque', answer: 'although' },
    { prompt: 'lograr', answer: 'to achieve' },
    { prompt: 'ajeno', answer: "someone else's" },
    { prompt: 'apenas', answer: 'barely' },
    { prompt: 'rumbo', answer: 'direction' },
    { prompt: 'soler', answer: 'to tend to' },
  ];
  const verbNewest: Pair[] = [
    { prompt: 'desvelarse', answer: 'to stay up all night' },
    { prompt: 'aprovechar', answer: 'to make the most of' },
    { prompt: 'anhelar', answer: 'to long for' },
    { prompt: 'sostener', answer: 'to hold' },
    { prompt: 'hallar', answer: 'to find' },
    { prompt: 'atreverse', answer: 'to dare' },
  ];
  const verbFocus: Pair[] = [
    { prompt: 'caber', answer: 'to fit' },
    { prompt: 'yacer', answer: 'to lie' },
    { prompt: 'alcanzar', answer: 'to reach' },
    { prompt: 'suponer', answer: 'to suppose' },
    { prompt: 'conseguir', answer: 'to obtain' },
    { prompt: 'llevar', answer: 'to carry' },
  ];

  const languageTables: LanguageTable[] = [
    {
      code: 'FR', language: 'French', verb: 'aller', meaning: 'to go', tense: 'Présent',
      forms: [
        { prompt: 'je', answer: 'vais' }, { prompt: 'tu', answer: 'vas' },
        { prompt: 'il / elle / on', answer: 'va' }, { prompt: 'nous', answer: 'allons' },
        { prompt: 'vous', answer: 'allez' }, { prompt: 'ils / elles', answer: 'vont' },
      ],
    },
    {
      code: 'ES', language: 'Spanish', verb: 'ir', meaning: 'to go', tense: 'Presente',
      forms: [
        { prompt: 'yo', answer: 'voy' }, { prompt: 'tú', answer: 'vas' },
        { prompt: 'él / ella / usted', answer: 'va' }, { prompt: 'nosotros', answer: 'vamos' },
        { prompt: 'vosotros', answer: 'vais' }, { prompt: 'ellos / ustedes', answer: 'van' },
      ],
    },
    {
      code: 'EN', language: 'English', verb: 'go', meaning: 'aller / ir', tense: 'Present',
      forms: [
        { prompt: 'I', answer: 'go' }, { prompt: 'you', answer: 'go' },
        { prompt: 'he / she / it', answer: 'goes' }, { prompt: 'we', answer: 'go' },
        { prompt: 'you (plural)', answer: 'go' }, { prompt: 'they', answer: 'go' },
      ],
    },
    {
      code: 'RU', language: 'Russian', verb: 'идти', meaning: 'to go', tense: 'Настоящее время',
      forms: [
        { prompt: 'я', answer: 'иду' }, { prompt: 'ты', answer: 'идёшь' },
        { prompt: 'он / она / оно', answer: 'идёт' }, { prompt: 'мы', answer: 'идём' },
        { prompt: 'вы', answer: 'идёте' }, { prompt: 'они', answer: 'идут' },
      ],
    },
  ];
  const conjugationQueue = ['aller', 'venir', 'tenir', 'partir', 'prendre', 'voir', 'boire', 'devoir', 'croire', 'vivre', 'lire', 'écrire'];
  let activeCode: LanguageTable['code'] = 'FR';
  $: activeTable = languageTables.find((table) => table.code === activeCode) || languageTables[0];
  $: newest = kind === 'words' ? wordNewest : verbNewest;
  $: focus = kind === 'words' ? wordFocus : verbFocus;
</script>

<article class="study-concept" class:conjugation-concept={kind === 'conjugation'}>
  <header class="concept-head">
    <div>
      <span class="mode-kicker">{kind === 'words' ? 'WORD STUDY' : kind === 'verbs' ? 'VERB TRANSLATION STUDY' : 'VERB TABLE STUDY'}</span>
      <h3>{kind === 'words' ? 'Words and translations' : kind === 'verbs' ? 'Infinitives and translations' : `${activeTable.language} · ${activeTable.verb}`}</h3>
      <p>{kind === 'conjugation' ? `${activeTable.meaning} · ${activeTable.tense}` : 'Six newest first, then six items that need more practice. Duplicates are removed before display.'}</p>
    </div>
    <span class="twelve-badge">12 items</span>
  </header>

  {#if kind === 'conjugation'}
    <div class="language-switch" role="tablist" aria-label="Conjugation language preview">
      {#each languageTables as table}
        <button type="button" class:active={activeCode === table.code} on:click={() => (activeCode = table.code)}>{table.code}<small>{table.language}</small></button>
      {/each}
    </div>
    <div class="verb-queue" aria-label="Six newest verbs and six verbs that need more practice">
      {#each conjugationQueue as verb, index}
        <span class:focus-verb={index >= 6}>{verb}<i>{index < 6 ? 'new' : 'practice'}</i></span>
      {/each}
    </div>
    <div class="two-col-table language-table" data-language={activeTable.code}>
      <div class="table-row table-header"><span>Pronoun</span><span>Form</span></div>
      {#each activeTable.forms as form}
        <div class="table-row"><strong>{form.prompt}</strong><span>{form.answer}</span></div>
      {/each}
    </div>
  {:else}
    <div class="two-col-table">
      <div class="table-row table-header"><span>{kind === 'words' ? 'Word' : 'Infinitive'}</span><span>Translation</span></div>
      <div class="group-label"><span>Newest 6</span><small>Recently added</small></div>
      {#each newest as item}
        <div class="table-row"><strong>{item.prompt}</strong><span>{item.answer}</span></div>
      {/each}
      <div class="group-label focus-label"><span>Needs more practice</span><small>Items you find harder</small></div>
      {#each focus as item}
        <div class="table-row"><strong>{item.prompt}</strong><span>{item.answer}</span></div>
      {/each}
    </div>
  {/if}
</article>

<style>
  .study-concept {
    --study-violet: #7065e8;
    --study-violet-soft: color-mix(in srgb, #7065e8 12%, transparent);
    --study-coral: #e56f52;
    --study-coral-soft: color-mix(in srgb, #e56f52 11%, transparent);
    display: grid;
    gap: 1rem;
    padding: clamp(1rem, 3vw, 1.5rem);
    border: 1px solid color-mix(in srgb, var(--line) 82%, #7065e8);
    border-radius: 20px;
    background: linear-gradient(145deg, color-mix(in srgb, var(--surface-strong) 94%, #7065e8 6%), var(--surface-strong));
    box-shadow: 0 18px 42px color-mix(in srgb, #141326 10%, transparent);
  }
  .concept-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; }
  .mode-kicker { color: var(--study-violet); font: 750 0.65rem/1 var(--mono); letter-spacing: 0.14em; }
  h3 { margin: 0.38rem 0 0.28rem; color: var(--text); font: 800 clamp(1.3rem, 3vw, 1.8rem)/1.05 var(--display); letter-spacing: -0.045em; }
  .concept-head p { max-width: 640px; margin: 0; color: var(--muted); font-size: 0.82rem; line-height: 1.45; }
  .twelve-badge { flex: 0 0 auto; padding: 0.38rem 0.58rem; border: 1px solid color-mix(in srgb, var(--study-violet) 32%, var(--line)); border-radius: 999px; color: var(--study-violet); background: var(--study-violet-soft); font: 750 0.66rem/1 var(--mono); }
  .two-col-table { overflow: hidden; border: 1px solid var(--line); border-radius: 14px; background: color-mix(in srgb, var(--surface) 80%, transparent); }
  .table-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); border-bottom: 1px solid var(--line); }
  .table-row:last-child { border-bottom: 0; }
  .table-row > * { min-width: 0; padding: 0.58rem 0.72rem; overflow-wrap: anywhere; }
  .table-row > * + * { border-left: 1px solid var(--line); }
  .table-row strong { color: var(--text); font-size: 0.83rem; }
  .table-row > span { color: var(--muted); font-size: 0.81rem; }
  .table-header { color: var(--text); background: color-mix(in srgb, var(--study-violet) 10%, var(--surface-strong)); font: 750 0.65rem/1.2 var(--mono); letter-spacing: 0.1em; text-transform: uppercase; }
  .table-header span { color: inherit; font-size: inherit; }
  .group-label { display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; padding: 0.42rem 0.72rem; border-bottom: 1px solid var(--line); color: var(--study-violet); background: var(--study-violet-soft); font-size: 0.72rem; font-weight: 750; }
  .group-label small { color: var(--muted); font-weight: 600; }
  .focus-label { color: var(--study-coral); background: var(--study-coral-soft); }
  .language-switch { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.45rem; }
  .language-switch button { display: grid; gap: 0.15rem; padding: 0.58rem; border: 1px solid var(--line); border-radius: 10px; color: var(--muted); background: color-mix(in srgb, var(--surface) 68%, transparent); font: 800 0.8rem/1 var(--mono); }
  .language-switch button small { font: 600 0.65rem/1.2 var(--body); }
  .language-switch button.active { border-color: color-mix(in srgb, var(--study-violet) 58%, var(--line)); color: var(--study-violet); background: var(--study-violet-soft); }
  .verb-queue { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.35rem; }
  .verb-queue span { display: flex; align-items: center; justify-content: space-between; gap: 0.25rem; min-width: 0; padding: 0.4rem 0.48rem; border: 1px solid var(--line); border-radius: 8px; color: var(--text); font-size: 0.72rem; }
  .verb-queue span i { color: var(--study-violet); font: 700 0.5rem/1 var(--mono); font-style: normal; text-transform: uppercase; }
  .verb-queue span.focus-verb i { color: var(--study-coral); }
  .language-table[data-language='ES'] { border-color: color-mix(in srgb, var(--study-coral) 38%, var(--line)); }
  .language-table[data-language='EN'] { border-color: color-mix(in srgb, #4f7fe6 38%, var(--line)); }
  .language-table[data-language='RU'] { border-color: color-mix(in srgb, #c58a36 42%, var(--line)); }
  @media (max-width: 620px) {
    .concept-head { flex-direction: column; }
    .language-switch, .verb-queue { grid-template-columns: 1fr; }
  }
</style>
