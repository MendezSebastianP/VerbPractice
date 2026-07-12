<script lang="ts">
  // The direction block from the Words trainer, shared so Add Word (and any
  // future surface) renders the exact same tiles: language dropdowns with
  // key-cap shortcut chips and the round swap button with its Ctrl+Space chip.
  // Keyboard handling stays in the host page — this component only draws and
  // exposes popSwap()/closeMenus() for shortcut feedback.
  import { popEl } from '../fx';
  import type { LanguageEntry } from '../types';

  export let languages: LanguageEntry[] = [];
  export let sourceCode = '';
  export let targetCode = '';
  export let sourceLabel = 'Prompt language';
  export let targetLabel = 'Answer language';

  const LANG_SHORTCUT: Record<string, string> = { EN: 'E', ES: 'S', RU: 'R', FR: 'F' };

  let sourceOpen = false;
  let targetOpen = false;
  let swapButtonEl: HTMLButtonElement | null = null;

  function languageByCode(code: string): LanguageEntry | undefined {
    return languages.find((l) => l.code === code.toUpperCase());
  }

  function swap(): void {
    const t = sourceCode;
    sourceCode = targetCode;
    targetCode = t;
  }

  export function popSwap(): void {
    popEl(swapButtonEl);
  }

  export function closeMenus(): void {
    sourceOpen = false;
    targetOpen = false;
  }
</script>

{#if sourceOpen || targetOpen}
  <button class="dd-backdrop" type="button" aria-label="Close language menu" on:click={closeMenus}></button>
{/if}

<div class="lang-grid">
  <div>
    <p class="toggle-label">{sourceLabel}</p>
    <div class="lang-select">
      <button
        class="lang-button"
        type="button"
        aria-expanded={sourceOpen}
        on:click={() => { sourceOpen = !sourceOpen; targetOpen = false; }}
      >
        <span class="lang-name">
          {languageByCode(sourceCode)?.name || sourceCode || '—'}
          {#if LANG_SHORTCUT[sourceCode]}<span class="kbd-chip">{LANG_SHORTCUT[sourceCode]}</span>{/if}
        </span>
        <span class="lang-chev" style={`transform: rotate(${sourceOpen ? 180 : 0}deg);`}>▼</span>
      </button>
      {#if sourceOpen}
        <div class="lang-menu">
          {#each languages as lang}
            <button
              class="lang-option"
              type="button"
              on:click={() => { sourceCode = lang.code; sourceOpen = false; }}
              disabled={lang.code === targetCode}
            >
              <span>{lang.name}</span>
              <span class="kbd-chip">{LANG_SHORTCUT[lang.code] ?? ''}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  </div>

  <div class="swap-cluster">
    <button
      bind:this={swapButtonEl}
      class="swap-round-button"
      type="button"
      aria-label="Swap direction"
      title="Swap"
      on:click={() => { swap(); popEl(swapButtonEl); }}
    >
      ⇄
    </button>
    <span class="kbd-chip">Ctrl+Space</span>
  </div>

  <div>
    <p class="toggle-label">{targetLabel}</p>
    <div class="lang-select">
      <button
        class="lang-button"
        type="button"
        aria-expanded={targetOpen}
        on:click={() => { targetOpen = !targetOpen; sourceOpen = false; }}
      >
        <span class="lang-name">
          {languageByCode(targetCode)?.name || targetCode || '—'}
          {#if LANG_SHORTCUT[targetCode]}<span class="kbd-chip">⇧{LANG_SHORTCUT[targetCode]}</span>{/if}
        </span>
        <span class="lang-chev" style={`transform: rotate(${targetOpen ? 180 : 0}deg);`}>▼</span>
      </button>
      {#if targetOpen}
        <div class="lang-menu">
          {#each languages as lang}
            <button
              class="lang-option"
              type="button"
              on:click={() => { targetCode = lang.code; targetOpen = false; }}
              disabled={lang.code === sourceCode}
            >
              <span>{lang.name}</span>
              <span class="kbd-chip">⇧{LANG_SHORTCUT[lang.code] ?? ''}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .dd-backdrop {
    position: fixed;
    inset: 0;
    z-index: 25;
    background: transparent;
    border: 0;
    cursor: default;
  }

  .lang-grid {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 16px;
    align-items: end;
  }

  .lang-select {
    position: relative;
    margin-top: 0.5rem;
  }

  .lang-button {
    cursor: pointer;
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: color-mix(in srgb, var(--surface-strong) 85%, transparent);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 12px 14px;
    color: var(--text);
    font-size: 1rem;
    transition: border-color 0.25s, box-shadow 0.25s;
  }

  .lang-button:hover {
    border-color: color-mix(in srgb, var(--accent) 55%, transparent);
    box-shadow: 0 4px 14px -6px color-mix(in srgb, var(--accent) 40%, transparent);
  }

  .lang-name {
    display: flex;
    align-items: center;
    gap: 9px;
    min-width: 0;
  }

  .lang-chev {
    color: var(--accent);
    font-size: 11px;
    transition: transform 0.25s;
    flex-shrink: 0;
  }

  .lang-menu {
    position: absolute;
    left: 0;
    right: 0;
    top: calc(100% + 6px);
    z-index: 30;
    background: var(--surface-strong);
    border: 1px solid var(--line-strong);
    border-radius: 12px;
    box-shadow: var(--shadow);
    max-height: 180px;
    overflow-y: auto;
    animation: dd-open 0.18s ease-out;
    backdrop-filter: blur(14px);
  }

  @keyframes dd-open {
    0% { opacity: 0; transform: translateY(-8px); }
    100% { opacity: 1; transform: translateY(0); }
  }

  .lang-option {
    cursor: pointer;
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: transparent;
    border: 0;
    padding: 11px 14px;
    color: var(--text);
    font-size: 0.95rem;
  }

  .lang-option:hover:not(:disabled) {
    background: var(--accent-soft);
  }

  .lang-option:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .swap-cluster {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    padding-bottom: 2px;
  }

  .swap-round-button {
    cursor: pointer;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    border: 1px solid var(--line);
    background: color-mix(in srgb, var(--surface-strong) 85%, transparent);
    color: var(--accent);
    font-size: 17px;
    transition: background 0.3s, color 0.3s, transform 0.4s;
  }

  .swap-round-button:hover {
    background: var(--accent);
    color: white;
    transform: rotate(180deg);
  }

  button:active:not(:disabled) {
    transform: scale(0.96);
    transition: transform 0.07s ease-out;
  }

  @media (max-width: 560px) {
    .lang-grid {
      grid-template-columns: 1fr;
      gap: 10px;
    }

    .swap-cluster {
      flex-direction: row;
      justify-content: center;
    }
  }
</style>
