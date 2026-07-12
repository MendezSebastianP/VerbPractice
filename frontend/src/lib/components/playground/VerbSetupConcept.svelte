<script lang="ts">
  import HelpTip from '../HelpTip.svelte';
  import { navigate } from '../../router';

  export let variant: 'staircase' | 'rail' | 'chapters';
  export let index = 'A1';
  export let kicker = '';
  export let title = '';
  export let description = '';

  type Level = 1 | 2 | 3 | 'custom';
  type FillDifficulty = 'hard' | 'medium' | 'easy';

  interface LanguageDemo {
    code: string;
    name: string;
    shortcut: string;
    tiers: [string[], string[], string[]];
  }

  const LANGUAGES: Record<string, LanguageDemo> = {
    EN: {
      code: 'EN',
      name: 'English',
      shortcut: 'E',
      tiers: [['Present'], ['Past'], ['Future']],
    },
    ES: {
      code: 'ES',
      name: 'Spanish',
      shortcut: 'S',
      tiers: [
        ['Presente', 'Futuro', 'Pretérito perfecto'],
        ['Imperfecto', 'Condicional', 'Imperativo', 'Futuro perfecto'],
        ['Subjuntivo', 'Pretérito simple', 'Pluscuamperfecto'],
      ],
    },
    FR: {
      code: 'FR',
      name: 'French',
      shortcut: 'F',
      tiers: [
        ['Présent', 'Futur', 'Passé composé'],
        ['Imparfait', 'Conditionnel', 'Impératif'],
        ['Subjonctif', 'Passé simple', 'Subjonctif imparfait'],
      ],
    },
    RU: {
      code: 'RU',
      name: 'Russian',
      shortcut: 'R',
      tiers: [['Настоящее'], ['Прошедшее'], ['Будущее']],
    },
  };

  const LANGUAGE_ORDER = ['EN', 'ES', 'FR', 'RU'];
  const TABLE_LENGTHS = [3, 5, 8];
  const FILL_DIFFICULTIES: Array<{ value: FillDifficulty; label: string; count: string; note: string }> = [
    { value: 'hard', label: 'Hard', count: '0 guides', note: 'Every valid cell is empty' },
    { value: 'medium', label: 'Medium', count: '1 guide', note: 'One random locked form per safe tense' },
    { value: 'easy', label: 'Easy', count: '~70%', note: 'Random locked forms, one answer always left' },
  ];
  const LEVEL_NAMES = ['Core', 'Expand', 'Master'];
  const LEVEL_NOTES = ['Start with the essential forms', 'Add everyday range', 'Open the complete corpus'];

  let previewCard: HTMLElement | null = null;
  let language = 'FR';
  let level: Level = variant === 'staircase' ? 1 : variant === 'rail' ? 2 : 3;
  let length = 5;
  let difficulty: FillDifficulty = 'medium';
  let customTenses = [...LANGUAGES.FR.tiers[0]];
  let launchReady = false;
  let showSpecialPolicy = false;
  let launchTimer: ReturnType<typeof setTimeout> | null = null;

  $: languageData = LANGUAGES[language];
  $: allTenses = languageData.tiers.flat();
  $: selectedTenses = level === 'custom'
    ? customTenses.filter((tense) => allTenses.includes(tense))
    : languageData.tiers.slice(0, level).flat();
  $: selectedDepth = level === 'custom'
    ? Math.max(1, ...selectedTenses.map((tense) => tierFor(tense)))
    : level;

  function clearLaunch(): void {
    launchReady = false;
  }

  function chooseLanguage(code: string): void {
    language = code;
    customTenses = [...LANGUAGES[code].tiers[0]];
    clearLaunch();
  }

  function chooseLevel(next: 1 | 2 | 3): void {
    level = next;
    clearLaunch();
  }

  function chooseCustom(): void {
    if (level !== 'custom') {
      customTenses = [...selectedTenses];
    }
    level = 'custom';
    clearLaunch();
  }

  function chooseDifficulty(next: FillDifficulty): void {
    difficulty = next;
    clearLaunch();
  }

  function toggleTense(tense: string): void {
    const base = level === 'custom' ? [...customTenses] : [...selectedTenses];
    customTenses = base.includes(tense)
      ? base.filter((item) => item !== tense)
      : [...base, tense];
    level = 'custom';
    clearLaunch();
  }

  function tierFor(tense: string): number {
    return languageData.tiers.findIndex((tier) => tier.includes(tense)) + 1;
  }

  function tierIsOn(tierIndex: number): boolean {
    return level === 'custom'
      ? languageData.tiers[tierIndex].some((tense) => selectedTenses.includes(tense))
      : level >= tierIndex + 1;
  }

  function openTranslation(): void {
    navigate('/training/verbs');
  }

  async function toggleFullscreen(): Promise<void> {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await previewCard?.requestFullscreen();
      }
    } catch {
      // Fullscreen can be denied by the browser; the prototype remains usable.
    }
  }

  function previewLaunch(): void {
    if (!selectedTenses.length) {
      return;
    }
    launchReady = true;
    if (launchTimer) {
      clearTimeout(launchTimer);
    }
    launchTimer = setTimeout(() => (launchReady = false), 1400);
  }

  function handleShortcut(event: KeyboardEvent): void {
    const key = event.key.toLowerCase();

    if (event.altKey && ['1', '2', '3', '4'].includes(event.key)) {
      event.preventDefault();
      if (event.key === '4') {
        chooseCustom();
      } else {
        chooseLevel(Number(event.key) as 1 | 2 | 3);
      }
      return;
    }

    if (event.shiftKey && !event.altKey && !event.ctrlKey && !event.metaKey && ['1', '2', '3'].includes(event.key)) {
      event.preventDefault();
      chooseDifficulty((['hard', 'medium', 'easy'] as FillDifficulty[])[Number(event.key) - 1]);
      return;
    }

    if (!event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
      const languageCode = LANGUAGE_ORDER.find((code) => LANGUAGES[code].shortcut.toLowerCase() === key);
      if (languageCode) {
        event.preventDefault();
        chooseLanguage(languageCode);
        return;
      }

      const lengthIndex = ['1', '2', '3'].indexOf(event.key);
      if (lengthIndex >= 0) {
        event.preventDefault();
        length = TABLE_LENGTHS[lengthIndex];
        clearLaunch();
        return;
      }

    }
  }

  function shortcutRegion(node: HTMLElement): { destroy: () => void } {
    const listener = (event: KeyboardEvent) => handleShortcut(event);
    node.addEventListener('keydown', listener);
    return { destroy: () => node.removeEventListener('keydown', listener) };
  }
</script>

<article class={`setup-preview variant-${variant}`}>
  <header class="concept-intro">
    <span class="concept-number">{index}</span>
    <div>
      <p class="eyebrow">{kicker}</p>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  </header>

  <div
    class="rush-setup-card"
    bind:this={previewCard}
    use:shortcutRegion
    role="group"
    aria-label={`${title} interactive setup prototype`}
    data-setup={variant}
    data-language={language}
    data-level={level}
    data-length={length}
    data-difficulty={difficulty}
    data-tense-count={selectedTenses.length}
  >
    <div class="setup-card-head">
      <div>
        <span class="stage-code">VERB LAB / TABLE SETUP</span>
        <h4>Build a table run</h4>
      </div>
      <div class="setup-tools">
        <button class="utility-button" type="button" aria-label="Preview fullscreen" title="Preview fullscreen" on:click={() => void toggleFullscreen()}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
            <path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"></path>
          </svg>
        </button>
        <HelpTip label="Table shortcuts">
          <h4>Table setup shortcuts</h4>
          <p>Click inside this prototype, then use the same visible keycaps as the trainer.</p>
          <ul>
            <li><kbd>E</kbd>/<kbd>S</kbd>/<kbd>F</kbd>/<kbd>R</kbd> choose the table language.</li>
            <li><kbd>Alt+1</kbd>/<kbd>Alt+2</kbd>/<kbd>Alt+3</kbd> choose tense depth; <kbd>Alt+4</kbd> opens Custom.</li>
            <li><kbd>Shift+1</kbd>/<kbd>Shift+2</kbd>/<kbd>Shift+3</kbd> choose Hard, Medium, or Easy guides.</li>
            <li><kbd>1</kbd>/<kbd>2</kbd>/<kbd>3</kbd> choose 3, 5, or 8 verbs.</li>
            <li><kbd>Enter</kbd> launches. During play it moves down, then submits the final cell.</li>
          </ul>
        </HelpTip>
      </div>
    </div>

    <div class="mode-gate" role="tablist" aria-label="Verb practice mode">
      <button class="mode-button mode-handoff" type="button" role="tab" aria-selected="false" on:click={openTranslation}>
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M5 7.5h8M5 12h6M5 16.5h8M15 7.5h4v4m0-4-6.5 7" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8"></path>
        </svg>
        <span><strong>Translate</strong><small>Exact same Verb Rush</small></span>
        <i>UNCHANGED ↗</i>
      </button>
      <button class="mode-button mode-on" type="button" role="tab" aria-selected="true">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect x="4.5" y="5.5" width="15" height="13" rx="2.5" fill="none" stroke="currentColor" stroke-width="1.8"></rect>
          <path d="M4.5 10h15M10 5.5v13M15 10v8.5" fill="none" stroke="currentColor" stroke-width="1.8"></path>
        </svg>
        <span><strong>Fill tables</strong><small>Design candidate</small></span>
        <i>ACTIVE</i>
      </button>
    </div>

    <section class="setup-block">
      <div class="block-title"><span>01</span><div><strong>Language</strong><small>One corpus per table run</small></div></div>
      <div class="language-strip" role="group" aria-label="Table language">
        {#each LANGUAGE_ORDER as code}
          <button class:language-on={language === code} type="button" aria-pressed={language === code} on:click={() => chooseLanguage(code)}>
            <span class="keycap">{LANGUAGES[code].shortcut}</span>
            <strong>{code}</strong>
            <small>{LANGUAGES[code].name}</small>
          </button>
        {/each}
      </div>
    </section>

    <section class="setup-block tense-block">
      <div class="block-title"><span>02</span><div><strong>Pick the tense depth</strong><small>{selectedTenses.length} {selectedTenses.length === 1 ? 'tense' : 'tenses'} in this run</small></div></div>

      {#if variant === 'staircase'}
        <div class="tense-staircase">
          {#each languageData.tiers as tier, tierIndex}
            <div class:stair-on={tierIsOn(tierIndex)} class="stair-step">
              <button class="stair-level" type="button" aria-label={`Choose level ${tierIndex + 1}`} on:click={() => chooseLevel((tierIndex + 1) as 1 | 2 | 3)}>
                <strong>L{tierIndex + 1}</strong><span class="keycap">Alt+{tierIndex + 1}</span>
              </button>
              <div class="stair-copy"><strong>{LEVEL_NAMES[tierIndex]}</strong><small>{LEVEL_NOTES[tierIndex]}</small></div>
              <div class="tense-chip-row">
                {#each tier as tense}
                  <button class:tense-on={selectedTenses.includes(tense)} type="button" on:click={() => toggleTense(tense)}>{tense}</button>
                {/each}
              </div>
            </div>
          {/each}
          <button class:custom-on={level === 'custom'} class="custom-route" type="button" on:click={chooseCustom}>
            <span class="custom-spark">✦</span><span><strong>Custom route</strong><small>Touch any tense to rewrite the staircase</small></span><span class="keycap">Alt+4</span>
          </button>
        </div>
      {:else if variant === 'rail'}
        <div class="mastery-rail">
          <div class="rail-track" style={`--rail-depth: ${selectedDepth}`}>
            <span class="rail-line" aria-hidden="true"><i></i></span>
            {#each languageData.tiers as tier, tierIndex}
              <button class:rail-stop-on={tierIsOn(tierIndex)} class="rail-stop" type="button" on:click={() => chooseLevel((tierIndex + 1) as 1 | 2 | 3)}>
                <span class="rail-node">{tierIndex + 1}</span>
                <span class="rail-stop-copy"><small>LEVEL {tierIndex + 1}</small><strong>{LEVEL_NAMES[tierIndex]}</strong><i>{tier.length} added</i></span>
                <span class="keycap">Alt+{tierIndex + 1}</span>
              </button>
            {/each}
            <button class:rail-stop-on={level === 'custom'} class="rail-stop rail-custom" type="button" on:click={chooseCustom}>
              <span class="rail-node">✦</span><span class="rail-stop-copy"><small>BRANCH</small><strong>Custom</strong><i>your route</i></span><span class="keycap">Alt+4</span>
            </button>
          </div>
          <div class="rail-manifest">
            <div class="manifest-head"><span>RUN MANIFEST</span><strong>{level === 'custom' ? 'Custom branch' : `Level ${level} · ${LEVEL_NAMES[level - 1]}`}</strong><small>Every lit ticket becomes one table column.</small></div>
            <div class="manifest-list">
              {#each allTenses as tense}
                <button class:manifest-on={selectedTenses.includes(tense)} type="button" on:click={() => toggleTense(tense)}>
                  <span>L{tierFor(tense)}</span><strong>{tense}</strong><i>{selectedTenses.includes(tense) ? 'IN RUN' : 'ADD'}</i>
                </button>
              {/each}
            </div>
          </div>
        </div>
      {:else}
        <div class="chapter-stack">
          {#each [1, 2, 3] as depth}
            <section class:chapter-on={level === depth} class="level-chapter">
              <button class="chapter-toggle" type="button" aria-expanded={level === depth} on:click={() => chooseLevel(depth as 1 | 2 | 3)}>
                <span class="chapter-index">0{depth}</span>
                <span><small>LEVEL {depth}</small><strong>{LEVEL_NAMES[depth - 1]}</strong></span>
                <span class="chapter-count">{languageData.tiers.slice(0, depth).flat().length} tenses</span>
                <span class="keycap">Alt+{depth}</span>
                <i>{level === depth ? '−' : '+'}</i>
              </button>
              {#if level === depth}
                <div class="chapter-body">
                  <p><strong>Everything below is included.</strong><span>{LEVEL_NOTES[depth - 1]}</span></p>
                  {#each languageData.tiers.slice(0, depth) as tier, tierIndex}
                    <div class="chapter-tier"><span>L{tierIndex + 1}</span><div>{#each tier as tense}<button type="button" on:click={() => toggleTense(tense)}>{tense}</button>{/each}</div></div>
                  {/each}
                </div>
              {/if}
            </section>
          {/each}
          <section class:chapter-on={level === 'custom'} class="level-chapter custom-chapter">
            <button class="chapter-toggle" type="button" aria-expanded={level === 'custom'} on:click={chooseCustom}>
              <span class="chapter-index">✦</span><span><small>LEVEL MY</small><strong>Custom route</strong></span><span class="chapter-count">{level === 'custom' ? selectedTenses.length : 'Pick'} tenses</span><span class="keycap">Alt+4</span><i>{level === 'custom' ? '−' : '+'}</i>
            </button>
            {#if level === 'custom'}
              <div class="chapter-body custom-library">
                <p><strong>Build your own chapter.</strong><span>Selected tenses stay in corpus order.</span></p>
                {#each languageData.tiers as tier, tierIndex}
                  <div class="chapter-tier"><span>L{tierIndex + 1}</span><div>{#each tier as tense}<button class:tense-on={selectedTenses.includes(tense)} type="button" on:click={() => toggleTense(tense)}>{tense}</button>{/each}</div></div>
                {/each}
              </div>
            {/if}
          </section>
        </div>
      {/if}
    </section>

    <section class="setup-block">
      <div class="block-title"><span>03</span><div><strong>Table difficulty</strong><small>Choose how many locked guides appear</small></div></div>
      <div class="difficulty-picker" role="group" aria-label="Table difficulty">
        {#each FILL_DIFFICULTIES as item, difficultyIndex}
          <button class:difficulty-on={difficulty === item.value} type="button" aria-pressed={difficulty === item.value} on:click={() => chooseDifficulty(item.value)}>
            <span class="difficulty-head"><strong>{item.label}</strong><span class="keycap">⇧{difficultyIndex + 1}</span></span>
            <span class="guide-dots" aria-hidden="true">
              {#each Array(6) as _, dotIndex}
                <i class:guide-dot-on={item.value === 'medium' ? dotIndex === 3 : item.value === 'easy' ? [1, 2, 4, 5].includes(dotIndex) : false}></i>
              {/each}
            </span>
            <span class="difficulty-count">{item.count}</span><small>{item.note}</small>
          </button>
        {/each}
      </div>

      <button class:special-policy-on={showSpecialPolicy} class="special-policy" type="button" aria-expanded={showSpecialPolicy} on:click={() => (showSpecialPolicy = !showSpecialPolicy)}>
        <span class="policy-shield" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 3 5.5 5.6v5.8c0 4.2 2.7 7.5 6.5 9.6 3.8-2.1 6.5-5.4 6.5-9.6V5.6L12 3Z"></path><path d="m9 12 2 2 4-4"></path></svg></span>
        <span><strong>Giveaway protection</strong><small>Special tense/verb columns automatically receive zero guides</small></span>
        <i>{showSpecialPolicy ? '−' : '+'}</i>
      </button>
      {#if showSpecialPolicy}
        <div class="special-policy-detail">
          <p><strong>PROPOSED EXACT-GIVEAWAY RULE</strong><span>If all valid answers are identical, or only one valid answer exists, do not reveal any cell.</span></p>
          <div><span>EN</span><strong>go · Past</strong><small>went × 6</small></div>
          <div><span>EN</span><strong>go · Future</strong><small>will go × 6</small></div>
          <div><span>RU</span><strong>быть · Present</strong><small>есть × 6</small></div>
          <div><span>FR</span><strong>falloir · Present</strong><small>only il faut is valid</small></div>
          <p class="policy-question"><strong>OPEN DECISION</strong><span>English Present is near-uniform (five base forms + one third-person form). Should it also receive zero guides?</span></p>
        </div>
      {/if}
    </section>

    <section class="setup-block">
      <div class="block-title"><span>04</span><div><strong>Number of verbs</strong><small>Same three-key rhythm as Verb Rush</small></div></div>
      <div class="run-lengths" role="group" aria-label="Number of verbs">
        {#each TABLE_LENGTHS as option, optionIndex}
          <button class:length-on={length === option} type="button" aria-pressed={length === option} on:click={() => { length = option; clearLaunch(); }}>
            <span class="keycap">{optionIndex + 1}</span><strong>{option}</strong><small>verbs</small>
          </button>
        {/each}
      </div>
    </section>

    <div class:launch-ready={launchReady} class="launch-ticket">
      <div><span>{languageData.name.toUpperCase()} · {level === 'custom' ? 'CUSTOM' : `LEVEL ${level}`} · {difficulty.toUpperCase()}</span><strong>{selectedTenses.length} {selectedTenses.length === 1 ? 'tense' : 'tenses'} × {length} verbs</strong><small>Tense-first table order · no data is sent here</small></div>
      <button type="button" disabled={!selectedTenses.length} on:click={previewLaunch}>
        {launchReady ? 'READY ✓' : 'PLAY'} <span class="keycap">Enter</span>
      </button>
    </div>

    <div class="shortcut-footer" aria-label="Setup shortcuts">
      <span><span class="keycap">E</span><span class="keycap">S</span><span class="keycap">F</span><span class="keycap">R</span> language</span>
      <span><span class="keycap">Alt+1…4</span> tense depth</span>
      <span><span class="keycap">Shift+1…3</span> difficulty</span>
      <span><span class="keycap">1</span><span class="keycap">2</span><span class="keycap">3</span> verbs</span>
      <span><span class="keycap">Enter</span> launch</span>
    </div>
  </div>
</article>

<style>
  .setup-preview {
    width: min(100%, 720px);
    margin-inline: auto;
  }

  .concept-intro {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.85rem;
    align-items: flex-start;
    margin-bottom: 0.8rem;
    padding-inline: 0.25rem;
  }

  .concept-number {
    display: grid;
    width: 2.45rem;
    height: 2.45rem;
    place-items: center;
    border: 1px solid var(--line-strong);
    border-radius: 13px;
    color: var(--accent-strong);
    background: var(--accent-soft);
    font: 800 0.7rem/1 var(--mono);
  }

  .concept-intro h3 {
    margin: 0.15rem 0 0.25rem;
    color: var(--text);
    font: 780 clamp(1.05rem, 3vw, 1.35rem)/1.15 var(--display);
    letter-spacing: -0.03em;
  }

  .concept-intro p:last-child {
    max-width: 650px;
    margin: 0;
    color: var(--muted);
    font-size: 0.72rem;
  }

  .rush-setup-card {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1.2rem;
    border: 1px solid color-mix(in srgb, var(--accent) 22%, var(--line));
    border-radius: 24px;
    outline: none;
    color: var(--text);
    background:
      radial-gradient(circle at 90% 0%, color-mix(in srgb, var(--accent) 13%, transparent), transparent 29%),
      color-mix(in srgb, var(--surface-strong) 94%, transparent);
    box-shadow: 0 22px 55px color-mix(in srgb, var(--text) 9%, transparent);
    transition: border-color 160ms ease, box-shadow 160ms ease;
  }

  .rush-setup-card:focus-within {
    border-color: color-mix(in srgb, var(--accent) 52%, var(--line));
    box-shadow: 0 24px 60px color-mix(in srgb, var(--accent) 13%, transparent);
  }

  .rush-setup-card:fullscreen {
    width: min(760px, calc(100% - 2rem));
    max-height: calc(100vh - 2rem);
    margin: auto;
    overflow: auto;
  }

  .setup-card-head,
  .setup-tools,
  .mode-button,
  .block-title,
  .stair-step,
  .custom-route,
  .rail-stop,
  .chapter-toggle,
  .launch-ticket,
  .shortcut-footer {
    display: flex;
    align-items: center;
  }

  .setup-card-head {
    justify-content: space-between;
    gap: 1rem;
  }

  .stage-code,
  .manifest-head > span {
    color: var(--accent-strong);
    font: 750 0.55rem/1 var(--mono);
    letter-spacing: 0.14em;
  }

  .setup-card-head h4 {
    margin: 0.3rem 0 0;
    color: var(--text);
    font: 800 clamp(1.3rem, 4vw, 1.8rem)/1 var(--display);
    letter-spacing: -0.04em;
  }

  .setup-tools {
    gap: 0.4rem;
  }

  .utility-button {
    display: grid;
    width: 2rem;
    height: 2rem;
    padding: 0;
    place-items: center;
    border: 1px solid var(--line);
    border-radius: 50%;
    color: var(--muted);
    background: color-mix(in srgb, var(--surface-strong) 84%, transparent);
  }

  .utility-button:hover {
    border-color: var(--accent);
    color: var(--accent-strong);
  }

  .utility-button svg {
    width: 1rem;
    height: 1rem;
  }

  .setup-tools :global(.help-button) {
    width: 2rem;
    height: 2rem;
  }

  .mode-gate {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.4rem;
    padding: 0.35rem;
    border: 1px solid var(--line);
    border-radius: 17px;
    background: color-mix(in srgb, var(--text) 5%, transparent);
  }

  .mode-button {
    position: relative;
    min-width: 0;
    gap: 0.7rem;
    padding: 0.8rem;
    border: 1px solid transparent;
    border-radius: 13px;
    color: var(--muted);
    text-align: left;
    background: transparent;
  }

  .mode-button svg {
    flex: 0 0 auto;
    width: 1.2rem;
    height: 1.2rem;
    color: var(--accent-strong);
  }

  .mode-button > span {
    display: grid;
    min-width: 0;
    gap: 0.1rem;
  }

  .mode-button strong {
    color: var(--text);
    font-size: 0.78rem;
  }

  .mode-button small {
    font-size: 0.58rem;
  }

  .mode-button > i {
    margin-left: auto;
    color: var(--muted);
    font: 700 0.48rem/1 var(--mono);
    letter-spacing: 0.08em;
  }

  .mode-button.mode-on {
    border-color: color-mix(in srgb, var(--accent) 62%, var(--line));
    color: var(--accent-strong);
    background: var(--accent-soft);
    box-shadow: inset 0 -2px 0 color-mix(in srgb, var(--accent) 62%, transparent);
  }

  .mode-handoff:hover {
    border-color: var(--line-strong);
    background: color-mix(in srgb, var(--surface-strong) 78%, transparent);
  }

  .setup-block {
    display: grid;
    gap: 0.75rem;
    padding-top: 1rem;
    border-top: 1px solid var(--line);
  }

  .block-title {
    gap: 0.65rem;
  }

  .block-title > span {
    display: grid;
    width: 1.8rem;
    height: 1.8rem;
    place-items: center;
    border: 1px solid color-mix(in srgb, var(--accent) 60%, var(--line));
    border-radius: 9px;
    color: var(--accent-strong);
    background: var(--accent-soft);
    font: 750 0.55rem/1 var(--mono);
  }

  .block-title > div {
    display: grid;
    gap: 0.1rem;
  }

  .block-title strong {
    font-size: 0.76rem;
  }

  .block-title small {
    color: var(--muted);
    font-size: 0.57rem;
  }

  .language-strip,
  .run-lengths {
    display: grid;
    gap: 0.45rem;
  }

  .language-strip {
    grid-template-columns: repeat(4, 1fr);
  }

  .language-strip button,
  .run-lengths button {
    position: relative;
    display: grid;
    gap: 0.13rem;
    min-width: 0;
    place-items: center;
    padding: 0.7rem 0.45rem;
    border: 1px solid var(--line);
    border-radius: 13px;
    color: var(--text);
    background: color-mix(in srgb, var(--surface-strong) 72%, transparent);
  }

  .language-strip button:hover,
  .run-lengths button:hover {
    border-color: color-mix(in srgb, var(--accent) 52%, var(--line));
  }

  .language-strip button.language-on,
  .run-lengths button.length-on {
    border-color: var(--accent);
    background: var(--accent-soft);
    box-shadow: inset 0 -2px 0 color-mix(in srgb, var(--accent) 55%, transparent);
  }

  .language-strip strong {
    font: 780 0.7rem/1 var(--display);
  }

  .language-strip small,
  .run-lengths small {
    color: var(--muted);
    font-size: 0.52rem;
  }

  .keycap {
    display: inline-flex;
    min-width: 1.2rem;
    min-height: 1rem;
    align-items: center;
    justify-content: center;
    padding: 0.12rem 0.28rem;
    border: 1px solid color-mix(in srgb, var(--line-strong) 80%, transparent);
    border-bottom-width: 2px;
    border-radius: 5px;
    color: var(--muted);
    background: color-mix(in srgb, var(--surface-strong) 78%, transparent);
    font: 700 0.48rem/1 var(--mono);
    white-space: nowrap;
  }

  .language-strip .keycap {
    position: absolute;
    top: 0.35rem;
    right: 0.35rem;
  }

  .tense-staircase {
    position: relative;
    display: grid;
    gap: 0.45rem;
    padding-left: 0.2rem;
  }

  .tense-staircase::before {
    position: absolute;
    top: 1.4rem;
    bottom: 2.8rem;
    left: 1.55rem;
    width: 1px;
    content: '';
    background: linear-gradient(var(--accent), color-mix(in srgb, var(--accent) 12%, var(--line)));
  }

  .stair-step {
    position: relative;
    display: grid;
    grid-template-columns: auto 6rem 1fr;
    gap: 0.7rem;
    min-height: 3.4rem;
    padding: 0.55rem;
    border: 1px solid var(--line);
    border-radius: 15px;
    background: color-mix(in srgb, var(--surface-strong) 64%, transparent);
  }

  .stair-step.stair-on {
    border-color: color-mix(in srgb, var(--accent) 62%, var(--line));
    background: color-mix(in srgb, var(--accent-soft) 64%, transparent);
  }

  .stair-level {
    z-index: 1;
    display: grid;
    width: 2.3rem;
    gap: 0.2rem;
    place-items: center;
    padding: 0.3rem;
    border: 1px solid var(--line-strong);
    border-radius: 11px;
    color: var(--muted);
    background: var(--surface-strong);
  }

  .stair-on .stair-level {
    border-color: var(--accent);
    color: var(--accent-strong);
    box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 10%, transparent);
  }

  .stair-level strong {
    font: 800 0.6rem/1 var(--mono);
  }

  .stair-level .keycap {
    border: 0;
    min-width: 0;
    min-height: 0;
    padding: 0;
    font-size: 0.37rem;
    background: transparent;
  }

  .stair-copy {
    display: grid;
    align-content: center;
    gap: 0.15rem;
  }

  .stair-copy strong {
    font-size: 0.76rem;
  }

  .stair-copy small {
    color: var(--muted);
    font-size: 0.51rem;
  }

  .tense-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
    align-content: center;
  }

  .tense-chip-row button,
  .chapter-tier button {
    padding: 0.4rem 0.55rem;
    border: 1px solid var(--line);
    border-radius: 8px;
    color: var(--muted);
    background: color-mix(in srgb, var(--surface-strong) 74%, transparent);
    font-size: 0.54rem;
  }

  .tense-chip-row button.tense-on,
  .chapter-tier button.tense-on {
    border-color: color-mix(in srgb, var(--accent) 68%, var(--line));
    color: var(--text);
    background: var(--accent-soft);
  }

  .custom-route {
    gap: 0.65rem;
    margin-left: 0.7rem;
    padding: 0.65rem 0.8rem;
    border: 1px dashed var(--line-strong);
    border-radius: 14px;
    color: var(--muted);
    text-align: left;
    background: transparent;
  }

  .custom-route.custom-on {
    border-style: solid;
    border-color: var(--accent);
    color: var(--text);
    background: var(--accent-soft);
  }

  .custom-route > span:nth-child(2) {
    display: grid;
    flex: 1;
    gap: 0.12rem;
  }

  .custom-route strong {
    font-size: 0.72rem;
  }

  .custom-route small {
    font-size: 0.51rem;
  }

  .custom-spark {
    color: var(--accent-strong);
  }

  .mastery-rail {
    display: grid;
    grid-template-columns: minmax(11rem, 0.75fr) minmax(0, 1.25fr);
    gap: 0.7rem;
    padding: 0.75rem;
    border: 1px solid var(--line);
    border-radius: 18px;
    background: color-mix(in srgb, var(--text) 4%, transparent);
  }

  .rail-track {
    position: relative;
    display: grid;
    gap: 0.35rem;
  }

  .rail-line {
    position: absolute;
    top: 1.4rem;
    bottom: 1.4rem;
    left: 1.05rem;
    width: 2px;
    overflow: hidden;
    background: var(--line);
  }

  .rail-line i {
    display: block;
    width: 100%;
    height: calc((var(--rail-depth) - 1) * 33.333% + 8%);
    background: linear-gradient(var(--accent), var(--accent-2));
    transition: height 220ms ease;
  }

  .rail-stop {
    position: relative;
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 0.55rem;
    min-width: 0;
    padding: 0.55rem 0.45rem;
    border: 1px solid transparent;
    border-radius: 12px;
    color: var(--muted);
    text-align: left;
    background: transparent;
  }

  .rail-stop:hover,
  .rail-stop.rail-stop-on {
    border-color: var(--line);
    color: var(--text);
    background: color-mix(in srgb, var(--surface-strong) 76%, transparent);
  }

  .rail-node {
    z-index: 1;
    display: grid;
    width: 1.3rem;
    height: 1.3rem;
    place-items: center;
    border: 2px solid var(--line-strong);
    border-radius: 50%;
    background: var(--surface-strong);
    font: 750 0.48rem/1 var(--mono);
  }

  .rail-stop-on .rail-node {
    border-color: var(--accent);
    color: var(--accent-strong);
    box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 13%, transparent);
  }

  .rail-stop-copy {
    display: grid;
    gap: 0.08rem;
  }

  .rail-stop-copy small,
  .rail-stop-copy i {
    font: 650 0.43rem/1 var(--mono);
  }

  .rail-stop-copy small {
    color: var(--accent-strong);
    letter-spacing: 0.08em;
  }

  .rail-stop-copy strong {
    font-size: 0.67rem;
  }

  .rail-stop-copy i {
    color: var(--muted);
    font-style: normal;
  }

  .rail-stop .keycap {
    font-size: 0.38rem;
  }

  .rail-custom {
    margin-top: 0.25rem;
    border-top-color: var(--line);
  }

  .rail-manifest {
    display: grid;
    align-content: start;
    gap: 0.6rem;
    padding: 0.75rem;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: color-mix(in srgb, var(--surface-strong) 78%, transparent);
  }

  .manifest-head {
    display: grid;
    gap: 0.15rem;
    padding-bottom: 0.55rem;
    border-bottom: 1px solid var(--line);
  }

  .manifest-head strong {
    font-size: 0.8rem;
  }

  .manifest-head small {
    color: var(--muted);
    font-size: 0.5rem;
  }

  .manifest-list {
    display: grid;
    gap: 0.3rem;
    padding-right: 0.15rem;
  }

  .manifest-list button {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 0.45rem;
    align-items: center;
    padding: 0.45rem 0.5rem;
    border: 1px solid var(--line);
    border-radius: 9px;
    color: var(--muted);
    text-align: left;
    background: transparent;
  }

  .manifest-list button.manifest-on {
    border-color: color-mix(in srgb, var(--accent) 62%, var(--line));
    color: var(--text);
    background: var(--accent-soft);
  }

  .manifest-list button > span,
  .manifest-list button > i {
    font: 700 0.43rem/1 var(--mono);
  }

  .manifest-list button > span {
    color: var(--accent-strong);
  }

  .manifest-list button > strong {
    font-size: 0.58rem;
  }

  .manifest-list button > i {
    color: var(--muted);
    font-style: normal;
  }

  .chapter-stack {
    display: grid;
    gap: 0.4rem;
  }

  .level-chapter {
    overflow: hidden;
    border: 1px solid var(--line);
    border-radius: 15px;
    background: color-mix(in srgb, var(--surface-strong) 66%, transparent);
  }

  .level-chapter.chapter-on {
    border-color: color-mix(in srgb, var(--accent) 65%, var(--line));
    box-shadow: 0 8px 24px color-mix(in srgb, var(--accent) 8%, transparent);
  }

  .chapter-toggle {
    display: grid;
    width: 100%;
    grid-template-columns: auto 1fr auto auto auto;
    gap: 0.65rem;
    padding: 0.7rem;
    border: 0;
    color: var(--text);
    text-align: left;
    background: transparent;
  }

  .chapter-on .chapter-toggle {
    background: var(--accent-soft);
  }

  .chapter-index {
    display: grid;
    width: 2rem;
    height: 2rem;
    place-items: center;
    border-radius: 9px;
    color: var(--accent-strong);
    background: color-mix(in srgb, var(--accent) 13%, var(--surface-strong));
    font: 800 0.56rem/1 var(--mono);
  }

  .chapter-toggle > span:nth-child(2) {
    display: grid;
    gap: 0.08rem;
  }

  .chapter-toggle small {
    color: var(--accent-strong);
    font: 700 0.43rem/1 var(--mono);
    letter-spacing: 0.08em;
  }

  .chapter-toggle strong {
    font-size: 0.72rem;
  }

  .chapter-count {
    color: var(--muted);
    font-size: 0.55rem;
  }

  .chapter-toggle > i {
    color: var(--accent-strong);
    font-style: normal;
    font-weight: 800;
  }

  .chapter-body {
    display: grid;
    gap: 0.55rem;
    padding: 0.7rem;
    border-top: 1px solid var(--line);
    background: color-mix(in srgb, var(--surface-strong) 80%, transparent);
  }

  .chapter-body > p {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    margin: 0;
    font-size: 0.58rem;
  }

  .chapter-body > p span {
    color: var(--muted);
  }

  .chapter-tier {
    display: grid;
    grid-template-columns: 1.5rem 1fr;
    gap: 0.45rem;
    align-items: start;
  }

  .chapter-tier > span {
    padding-top: 0.45rem;
    color: var(--accent-strong);
    font: 700 0.45rem/1 var(--mono);
  }

  .chapter-tier > div {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
  }

  .chapter-body:not(.custom-library) .chapter-tier button {
    color: var(--text);
    background: var(--accent-soft);
  }

  .custom-chapter {
    border-style: dashed;
  }

  .difficulty-picker {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.45rem;
  }

  .difficulty-picker > button {
    display: grid;
    min-width: 0;
    gap: 0.4rem;
    padding: 0.65rem;
    border: 1px solid var(--line);
    border-radius: 14px;
    color: var(--text);
    text-align: left;
    background: color-mix(in srgb, var(--surface-strong) 70%, transparent);
  }

  .difficulty-picker > button:hover,
  .difficulty-picker > button.difficulty-on {
    border-color: color-mix(in srgb, var(--accent) 68%, var(--line));
  }

  .difficulty-picker > button.difficulty-on {
    background: var(--accent-soft);
    box-shadow: inset 0 -2px 0 color-mix(in srgb, var(--accent) 55%, transparent);
  }

  .difficulty-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .difficulty-head strong {
    font-size: 0.7rem;
  }

  .guide-dots {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 0.18rem;
  }

  .guide-dots i {
    height: 0.7rem;
    border: 1px solid var(--line-strong);
    border-radius: 4px;
    background: color-mix(in srgb, var(--surface-strong) 72%, transparent);
  }

  .guide-dots i.guide-dot-on {
    border-color: color-mix(in srgb, #e6a83b 68%, var(--line));
    background: color-mix(in srgb, #e6a83b 28%, var(--surface-strong));
    box-shadow: inset 0 -1px 0 color-mix(in srgb, #e6a83b 55%, transparent);
  }

  .difficulty-count {
    color: var(--accent-strong);
    font: 750 0.55rem/1 var(--mono);
  }

  .difficulty-picker small {
    min-height: 1.5rem;
    color: var(--muted);
    font-size: 0.5rem;
    line-height: 1.35;
  }

  .special-policy {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 0.65rem;
    align-items: center;
    padding: 0.65rem 0.75rem;
    border: 1px dashed color-mix(in srgb, #e6a83b 50%, var(--line));
    border-radius: 13px;
    color: var(--text);
    text-align: left;
    background: color-mix(in srgb, #e6a83b 7%, transparent);
  }

  .special-policy.special-policy-on {
    border-style: solid;
    border-color: #e6a83b;
  }

  .policy-shield {
    display: grid;
    width: 1.8rem;
    height: 1.8rem;
    place-items: center;
    border-radius: 9px;
    color: #b7780e;
    background: color-mix(in srgb, #e6a83b 18%, var(--surface-strong));
  }

  .policy-shield svg {
    width: 1.05rem;
    height: 1.05rem;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.7;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .special-policy > span:nth-child(2) {
    display: grid;
    gap: 0.12rem;
  }

  .special-policy strong {
    font-size: 0.66rem;
  }

  .special-policy small {
    color: var(--muted);
    font-size: 0.51rem;
  }

  .special-policy > i {
    color: #b7780e;
    font-style: normal;
    font-weight: 800;
  }

  .special-policy-detail {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.35rem;
    padding: 0.65rem;
    border: 1px solid color-mix(in srgb, #e6a83b 38%, var(--line));
    border-radius: 13px;
    background: color-mix(in srgb, #e6a83b 6%, var(--surface-strong));
  }

  .special-policy-detail > p {
    display: grid;
    grid-column: 1 / -1;
    gap: 0.18rem;
    margin: 0 0 0.2rem;
    padding: 0.25rem;
    color: var(--muted);
    font-size: 0.52rem;
  }

  .special-policy-detail > p strong {
    color: #b7780e;
    font: 750 0.48rem/1 var(--mono);
    letter-spacing: 0.08em;
  }

  .special-policy-detail > div {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.12rem 0.4rem;
    padding: 0.5rem;
    border: 1px solid var(--line);
    border-radius: 9px;
    background: color-mix(in srgb, var(--surface-strong) 74%, transparent);
  }

  .special-policy-detail > div > span {
    grid-row: 1 / 3;
    color: var(--accent-strong);
    font: 750 0.48rem/1 var(--mono);
  }

  .special-policy-detail > div > strong {
    font-size: 0.56rem;
  }

  .special-policy-detail > div > small {
    color: var(--muted);
    font-size: 0.48rem;
  }

  .special-policy-detail > p.policy-question {
    margin: 0.25rem 0 0;
    padding-top: 0.5rem;
    border-top: 1px solid color-mix(in srgb, #e6a83b 30%, var(--line));
  }

  .run-lengths {
    grid-template-columns: repeat(3, 1fr);
  }

  .run-lengths button {
    grid-template-columns: auto auto;
    grid-template-rows: auto auto;
  }

  .run-lengths .keycap {
    grid-row: 1 / 3;
  }

  .run-lengths strong {
    font: 800 1rem/1 var(--display);
  }

  .launch-ticket {
    justify-content: space-between;
    gap: 1rem;
    padding: 0.75rem;
    border: 1px solid color-mix(in srgb, var(--accent) 70%, var(--line));
    border-radius: 15px;
    background: color-mix(in srgb, var(--accent-soft) 52%, transparent);
    transition: 180ms ease;
  }

  .launch-ticket.launch-ready {
    border-color: #31c980;
    background: color-mix(in srgb, #31c980 12%, transparent);
    box-shadow: 0 0 0 4px color-mix(in srgb, #31c980 10%, transparent);
  }

  .launch-ticket > div {
    display: grid;
    gap: 0.13rem;
  }

  .launch-ticket > div > span {
    color: var(--accent-strong);
    font: 750 0.5rem/1 var(--mono);
    letter-spacing: 0.08em;
  }

  .launch-ticket strong {
    font-size: 0.72rem;
  }

  .launch-ticket small {
    color: var(--muted);
    font-size: 0.52rem;
  }

  .launch-ticket > button {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    padding: 0.65rem 0.75rem;
    border: 1px solid var(--accent);
    border-radius: 11px;
    color: var(--accent-strong);
    background: var(--accent-soft);
    font: 750 0.62rem/1 var(--mono);
  }

  .launch-ticket > button:disabled {
    cursor: not-allowed;
    opacity: 0.45;
  }

  .shortcut-footer {
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.5rem 0.8rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--line);
    color: var(--muted);
    font-size: 0.5rem;
  }

  .shortcut-footer > span {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
  }

  button:not(:disabled) {
    cursor: pointer;
  }

  :global(html[data-theme='arcade']) .setup-card-head h4,
  :global(html[data-theme='arcade']) .concept-intro h3,
  :global(html[data-theme='arcade']) .run-lengths strong {
    line-height: 1.5;
    letter-spacing: 0;
  }

  :global(html[data-theme='arcade']) .rush-setup-card {
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--accent) 45%, transparent), 0 0 32px color-mix(in srgb, var(--accent) 14%, transparent);
  }

  @media (max-width: 620px) {
    .rush-setup-card {
      padding: 0.9rem;
      border-radius: 20px;
    }

    .mode-gate {
      grid-template-columns: 1fr;
    }

    .mode-button > i {
      display: none;
    }

    .language-strip {
      grid-template-columns: 1fr 1fr;
    }

    .stair-step {
      grid-template-columns: auto 1fr;
    }

    .tense-chip-row {
      grid-column: 2;
    }

    .mastery-rail {
      grid-template-columns: 1fr;
    }

    .chapter-toggle {
      grid-template-columns: auto 1fr auto auto;
    }

    .chapter-count {
      display: none;
    }

    .chapter-body > p {
      display: grid;
      gap: 0.15rem;
    }

    .difficulty-picker,
    .special-policy-detail {
      grid-template-columns: 1fr;
    }

    .special-policy-detail > p {
      grid-column: 1;
    }

    .launch-ticket {
      align-items: stretch;
      flex-direction: column;
    }

    .launch-ticket > button {
      justify-content: space-between;
    }
  }

  @media (max-width: 420px) {
    .setup-card-head h4 {
      font-size: 1.15rem;
    }

    .setup-tools {
      align-self: flex-start;
    }

    .mode-button {
      padding: 0.65rem;
    }

    .rail-stop-copy i {
      display: none;
    }

    .chapter-toggle {
      gap: 0.4rem;
    }

    .chapter-toggle .keycap {
      display: none;
    }

    .run-lengths button {
      grid-template-columns: 1fr;
      grid-template-rows: auto auto auto;
    }

    .run-lengths .keycap {
      grid-row: auto;
    }
  }
</style>
