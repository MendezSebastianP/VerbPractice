<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { api, ApiError } from '../api';
  import type {
    AdminAiUsagePayload,
    AdminConjugationRow,
    AdminContentSummaryPayload,
    AdminVerbRow,
    AdminWordRow,
    MonitorPayload,
  } from '../types';

  export let csrfToken = '';
  export let notify: (message: string, tone?: 'info' | 'success' | 'error') => void;

  let loading = true;
  let error = '';
  let tab: 'runtime' | 'financials' | 'words' | 'verbs' | 'conjugations' = 'runtime';
  let data: MonitorPayload | null = null;
  let summary: AdminContentSummaryPayload | null = null;
  let aiUsage: AdminAiUsagePayload | null = null;
  let timer: number | undefined;

  let wordRows: AdminWordRow[] = [];
  let verbRows: AdminVerbRow[] = [];
  let conjugationRows: AdminConjugationRow[] = [];

  let wordSearch = '';
  let verbSearch = '';
  let conjugationSearch = '';
  let verifiedFilter = 'all';

  let newWord = {
    text: '',
    language_code: 'ES',
    translation: '',
    target_language_code: 'FR',
    synonyms: '',
    verified: false,
    source: 'admin_manual',
  };
  let newVerb = {
    infinitive: '',
    language_code: 'FR',
    translation: '',
    target_language_code: 'ES',
    synonyms: '',
    verified: false,
    source: 'admin_manual',
  };
  let newConjugation = {
    infinitive: '',
    language_code: 'FR',
    mood: 'Indicatif',
    tense: '',
    pronoun: '',
    conjugated_form: '',
    verified: false,
    source: 'admin_manual',
  };

  async function loadRuntime(): Promise<void> {
    data = await api.adminMonitor();
  }

  async function loadSummary(): Promise<void> {
    summary = await api.adminContentSummary();
  }

  async function loadFinancials(): Promise<void> {
    aiUsage = await api.adminAiUsage(80);
  }

  async function loadWords(): Promise<void> {
    wordRows = (await api.adminWords({ search: wordSearch, verified: verifiedFilter === 'all' ? '' : verifiedFilter })).rows;
  }

  async function loadVerbs(): Promise<void> {
    verbRows = (await api.adminVerbs({ search: verbSearch, verified: verifiedFilter === 'all' ? '' : verifiedFilter })).rows;
  }

  async function loadConjugations(): Promise<void> {
    conjugationRows = (
      await api.adminConjugations({ search: conjugationSearch, verified: verifiedFilter === 'all' ? '' : verifiedFilter })
    ).rows;
  }

  async function loadTabData(activeTab = tab): Promise<void> {
    if (activeTab === 'runtime') {
      await loadRuntime();
      return;
    }
    if (activeTab === 'financials') {
      await loadSummary();
      await loadFinancials();
      return;
    }
    await loadSummary();
    if (activeTab === 'words') {
      await loadWords();
    } else if (activeTab === 'verbs') {
      await loadVerbs();
    } else if (activeTab === 'conjugations') {
      await loadConjugations();
    }
  }

  async function load(): Promise<void> {
    loading = true;
    try {
      await loadSummary();
      await loadTabData();
      error = '';
    } catch (err) {
      error = err instanceof ApiError ? err.message : 'Unable to load admin workbench';
    } finally {
      loading = false;
    }
  }

  function setTab(nextTab: typeof tab): void {
    tab = nextTab;
    void load();
  }

  function money(value: number, digits = 4): string {
    return `$${value.toFixed(digits)}`;
  }

  function formatNumber(value: number): string {
    return value.toLocaleString();
  }

  async function createWord(): Promise<void> {
    try {
      await api.createAdminWord({ ...newWord, csrf_token: csrfToken, synonyms: newWord.synonyms });
      newWord = { text: '', language_code: 'ES', translation: '', target_language_code: 'FR', synonyms: '', verified: false, source: 'admin_manual' };
      await load();
      notify('Word row created.', 'success');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to create word row', 'error');
    }
  }

  async function saveWord(row: AdminWordRow): Promise<void> {
    try {
      await api.updateAdminWord(row.id, {
        csrf_token: csrfToken,
        text: row.text,
        language_code: row.language_code,
        translation: row.translation,
        target_language_code: row.target_language_code,
        synonyms: row.synonyms,
        verified: row.verified,
        source: row.source,
      });
      await loadSummary();
      notify('Word row updated.', 'success');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to save word row', 'error');
    }
  }

  async function deleteWord(id: number): Promise<void> {
    try {
      await api.deleteAdminWord(id, csrfToken);
      await load();
      notify('Word row deleted.', 'info');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to delete word row', 'error');
    }
  }

  async function createVerb(): Promise<void> {
    try {
      await api.createAdminVerb({ ...newVerb, csrf_token: csrfToken, synonyms: newVerb.synonyms });
      newVerb = { infinitive: '', language_code: 'FR', translation: '', target_language_code: 'ES', synonyms: '', verified: false, source: 'admin_manual' };
      await load();
      notify('Verb row created.', 'success');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to create verb row', 'error');
    }
  }

  async function saveVerb(row: AdminVerbRow): Promise<void> {
    try {
      await api.updateAdminVerb(row.id, {
        csrf_token: csrfToken,
        infinitive: row.infinitive,
        language_code: row.language_code,
        translation: row.translation,
        target_language_code: row.target_language_code,
        synonyms: row.synonyms,
        verified: row.verified,
        source: row.source,
      });
      await loadSummary();
      notify('Verb row updated.', 'success');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to save verb row', 'error');
    }
  }

  async function deleteVerb(id: number): Promise<void> {
    try {
      await api.deleteAdminVerb(id, csrfToken);
      await load();
      notify('Verb row deleted.', 'info');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to delete verb row', 'error');
    }
  }

  async function createConjugation(): Promise<void> {
    try {
      await api.createAdminConjugation({ ...newConjugation, csrf_token: csrfToken });
      newConjugation = {
        infinitive: '',
        language_code: 'FR',
        mood: 'Indicatif',
        tense: '',
        pronoun: '',
        conjugated_form: '',
        verified: false,
        source: 'admin_manual',
      };
      await load();
      notify('Conjugation row created.', 'success');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to create conjugation row', 'error');
    }
  }

  async function saveConjugation(row: AdminConjugationRow): Promise<void> {
    try {
      await api.updateAdminConjugation(row.id, {
        csrf_token: csrfToken,
        infinitive: row.infinitive,
        language_code: row.language_code,
        mood: row.mood,
        tense: row.tense,
        pronoun: row.pronoun,
        conjugated_form: row.conjugated_form,
        verified: row.verified,
        source: row.source,
      });
      await loadSummary();
      notify('Conjugation row updated.', 'success');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to save conjugation row', 'error');
    }
  }

  async function deleteConjugation(id: number): Promise<void> {
    try {
      await api.deleteAdminConjugation(id, csrfToken);
      await load();
      notify('Conjugation row deleted.', 'info');
    } catch (err) {
      notify(err instanceof ApiError ? err.message : 'Unable to delete conjugation row', 'error');
    }
  }

  onMount(() => {
    void load();
    timer = window.setInterval(() => {
      if (tab === 'runtime') {
        void loadRuntime();
      }
    }, 4000);
  });

  onDestroy(() => {
    if (timer) {
      window.clearInterval(timer);
    }
  });
</script>

<section class="trainer-shell">
  {#if loading && !summary && !data}
    <div class="glass-panel skeleton-card tall-skeleton"></div>
  {:else if error}
    <div class="glass-panel"><div class="feedback-banner error-banner">{error}</div></div>
  {:else}
    <div class="monitor-stack" in:fade={{ duration: 180 }}>
      <header class="trainer-head glass-panel">
        <div>
          <p class="eyebrow">Admin workbench</p>
          <h1>Runtime visibility and content management</h1>
        </div>
        <div class="pill-row">
          <button class:option-on={tab === 'runtime'} class="option-chip" type="button" role="tab" aria-selected={tab === 'runtime'} on:click={() => setTab('runtime')}>Runtime</button>
          <button class:option-on={tab === 'financials'} class="option-chip" type="button" role="tab" aria-selected={tab === 'financials'} on:click={() => setTab('financials')}>Financials</button>
          <button class:option-on={tab === 'words'} class="option-chip" type="button" role="tab" aria-selected={tab === 'words'} on:click={() => setTab('words')}>Words</button>
          <button class:option-on={tab === 'verbs'} class="option-chip" type="button" role="tab" aria-selected={tab === 'verbs'} on:click={() => setTab('verbs')}>Verbs</button>
          <button class:option-on={tab === 'conjugations'} class="option-chip" type="button" role="tab" aria-selected={tab === 'conjugations'} on:click={() => setTab('conjugations')}>Conjugations</button>
        </div>
      </header>

      {#if summary}
        <section class="metric-grid monitor-cards">
          <article class="stat-card compact-stat"><span>Word rows</span><strong>{summary.summary.words.total}</strong></article>
          <article class="stat-card compact-stat"><span>Word review</span><strong>{summary.summary.words.needs_review}</strong></article>
          <article class="stat-card compact-stat"><span>Verb rows</span><strong>{summary.summary.verbs.total}</strong></article>
          <article class="stat-card compact-stat"><span>Verb review</span><strong>{summary.summary.verbs.needs_review}</strong></article>
          <article class="stat-card compact-stat"><span>Conjugations</span><strong>{summary.summary.conjugations.total}</strong></article>
          <article class="stat-card compact-stat"><span>Conj review</span><strong>{summary.summary.conjugations.needs_review}</strong></article>
          <article class="stat-card compact-stat"><span>Curated approved</span><strong>{summary.summary.curated.approved_pct}%</strong></article>
          <article class="stat-card compact-stat"><span>Ready batches</span><strong>{summary.summary.curated.batches_import_ready}/{summary.summary.curated.batches_total}</strong></article>
          <article class="stat-card compact-stat"><span>Authored batches</span><strong>{summary.summary.curated.batches_with_authored}</strong></article>
        </section>
      {/if}

      {#if tab === 'runtime' && data}
        <section class="dashboard-grid">
          <article class="glass-panel">
            <div class="section-head"><div><p class="eyebrow">Accounts</p><h2>User state</h2></div></div>
            <div class="table-scroll">
              <table class="data-table">
                <thead><tr><th>User</th><th>Level</th><th>Streak</th><th>Theme</th></tr></thead>
                <tbody>
                  {#each data.users as user}
                    <tr><td>{user.username}</td><td>{user.level}</td><td>{user.streak_days}</td><td>{user.theme}</td></tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </article>

          <article class="glass-panel">
            <div class="section-head"><div><p class="eyebrow">Runtime</p><h2>Active sessions</h2></div></div>
            <div class="table-scroll">
              <table class="data-table">
                <thead><tr><th>ID</th><th>User</th><th>Mode</th><th>Pair</th><th>Started</th></tr></thead>
                <tbody>
                  {#each data.active_sessions as session}
                    <tr>
                      <td>{String(session.id ?? '-')}</td>
                      <td>{String(session.user_id ?? '-')}</td>
                      <td>{String(session.mode ?? '-')}</td>
                      <td>{String(session.language_pair ?? '-')}</td>
                      <td>{String(session.started_at ?? '-')}</td>
                    </tr>
                  {:else}
                    <tr><td colspan="5">No active sessions</td></tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </article>

          {#if summary}
            <article class="glass-panel">
              <div class="section-head">
                <div>
                  <p class="eyebrow">Curated trust</p>
                  <h2>Manual conjugation pipeline</h2>
                </div>
                <div class="pill-row">
                  <span class="pill-chip">Inventory {summary.summary.curated.inventory_links}</span>
                  <span class="pill-chip">Approved {summary.summary.curated.approved_slots}/{summary.summary.curated.required_slots}</span>
                </div>
              </div>
              <div class="table-scroll">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Batch</th>
                      <th>Required</th>
                      <th>Authored</th>
                      <th>Reviewed</th>
                      <th>Approved</th>
                      <th>Ready</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each summary.summary.curated.batches as batch}
                      <tr>
                        <td>{batch.batch}</td>
                        <td>{batch.required_slots}</td>
                        <td>{batch.authored_slots} ({batch.authored_pct}%)</td>
                        <td>{batch.reviewed_slots} ({batch.reviewed_pct}%)</td>
                        <td>{batch.approved_slots} ({batch.approved_pct}%)</td>
                        <td>{batch.import_ready ? 'Yes' : 'No'}</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            </article>
          {/if}
        </section>
      {:else if tab === 'financials'}
        {#if aiUsage}
          <section class="monitor-stack">
            <section class="metric-grid monitor-cards">
              <article class="stat-card compact-stat"><span>Total AI cost</span><strong>{money(aiUsage.financials.total_cost_usd, 2)}</strong></article>
              <article class="stat-card compact-stat"><span>Translation cost</span><strong>{money(aiUsage.financials.translation_cost_usd, 2)}</strong></article>
              <article class="stat-card compact-stat"><span>Avg/translation</span><strong>{money(aiUsage.financials.average_translation_cost_usd, 5)}</strong></article>
              <article class="stat-card compact-stat"><span>AI calls</span><strong>{formatNumber(aiUsage.financials.total_calls)}</strong></article>
              <article class="stat-card compact-stat"><span>Tokens</span><strong>{formatNumber(aiUsage.financials.total_tokens)}</strong></article>
              <article class="stat-card compact-stat"><span>Translations</span><strong>{formatNumber(aiUsage.financials.translation_calls)}</strong></article>
            </section>

            <section class="dashboard-grid">
              <article class="glass-panel">
                <div class="section-head">
                  <div>
                    <p class="eyebrow">AI spend</p>
                    <h2>Usage by feature</h2>
                  </div>
                  <button class="secondary-button" type="button" on:click={loadFinancials}>Refresh</button>
                </div>
                <div class="table-scroll" style="margin-top: 1rem;">
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>Feature</th>
                        <th>Calls</th>
                        <th>Cost</th>
                        <th>Avg cost</th>
                        <th>Input</th>
                        <th>Output</th>
                      </tr>
                    </thead>
                    <tbody>
                      {#each aiUsage.by_feature as row}
                        <tr>
                          <td>{row.label}</td>
                          <td>{formatNumber(row.calls)}</td>
                          <td>{money(row.cost_usd, 5)}</td>
                          <td>{money(row.average_cost_usd, 5)}</td>
                          <td>{formatNumber(row.prompt_tokens)}</td>
                          <td>{formatNumber(row.completion_tokens)}</td>
                        </tr>
                      {:else}
                        <tr><td colspan="6">No AI usage recorded yet</td></tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              </article>

              <article class="glass-panel">
                <div class="section-head">
                  <div>
                    <p class="eyebrow">Pricing</p>
                    <h2>Model rates and users</h2>
                  </div>
                </div>
                <div class="table-scroll" style="margin-top: 1rem;">
                  <table class="data-table">
                    <thead><tr><th>Model</th><th>Calls</th><th>Cost</th><th>Tokens</th><th>Input / 1M</th><th>Output / 1M</th></tr></thead>
                    <tbody>
                      {#each aiUsage.by_model as row}
                        <tr>
                          <td>{row.model}</td>
                          <td>{formatNumber(row.calls)}</td>
                          <td>{money(row.cost_usd, 5)}</td>
                          <td>{formatNumber(row.total_tokens)}</td>
                          <td>{money(row.input_cost_per_million, 2)}</td>
                          <td>{money(row.output_cost_per_million, 2)}</td>
                        </tr>
                      {:else}
                        <tr><td colspan="6">No model usage yet</td></tr>
                      {/each}
                    </tbody>
                  </table>
                </div>

                <div class="table-scroll" style="margin-top: 1rem;">
                  <table class="data-table">
                    <thead><tr><th>User</th><th>Calls</th><th>Total cost</th></tr></thead>
                    <tbody>
                      {#each aiUsage.top_users as user}
                        <tr><td>{user.username}</td><td>{formatNumber(user.calls)}</td><td>{money(user.total_cost_usd, 5)}</td></tr>
                      {:else}
                        <tr><td colspan="3">No user usage yet</td></tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              </article>
            </section>

            <article class="glass-panel">
              <div class="section-head">
                <div>
                  <p class="eyebrow">Recent calls</p>
                  <h2>Per-translation AI costs</h2>
                </div>
              </div>
              <div class="table-scroll" style="margin-top: 1rem;">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>When</th>
                      <th>User</th>
                      <th>Feature</th>
                      <th>Request</th>
                      <th>Model</th>
                      <th>Tokens</th>
                      <th>Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each aiUsage.recent as row}
                      <tr>
                        <td>{row.created_at ? new Date(row.created_at).toLocaleString() : '-'}</td>
                        <td>{row.user ?? '-'}</td>
                        <td>{row.label}</td>
                        <td>{row.request_label ?? '-'}</td>
                        <td>{row.model}</td>
                        <td>{formatNumber(row.total_tokens)}</td>
                        <td>{money(row.cost_usd, 6)}</td>
                      </tr>
                    {:else}
                      <tr><td colspan="7">No AI calls yet</td></tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            </article>
          </section>
        {:else}
          <div class="glass-panel skeleton-card"></div>
        {/if}
      {:else if tab === 'words'}
        <article class="glass-panel admin-workbench">
          <div class="section-head">
            <div>
              <p class="eyebrow">Word review</p>
              <h2>Edit vocabulary and provenance</h2>
            </div>
            <div class="pill-row">
              <input bind:value={wordSearch} class="answer-input admin-search" type="text" placeholder="Search words or translations" />
              <select bind:value={verifiedFilter} class="answer-input admin-select">
                <option value="all">All</option>
                <option value="true">Verified</option>
                <option value="false">Needs review</option>
              </select>
              <button class="secondary-button" type="button" on:click={loadWords}>Refresh</button>
            </div>
          </div>

          <div class="admin-create-grid">
            <input bind:value={newWord.text} class="answer-input" type="text" placeholder="Source word" />
            <input bind:value={newWord.translation} class="answer-input" type="text" placeholder="Translation" />
            <input bind:value={newWord.synonyms} class="answer-input" type="text" placeholder="Synonyms, comma separated" />
            <input bind:value={newWord.source} class="answer-input" type="text" placeholder="Source/provenance" />
            <button class="primary-button" type="button" on:click={createWord}>Create row</button>
          </div>

          <div class="list-stack">
            {#each wordRows as row}
              <article class="glass-panel strong-panel admin-edit-card">
                <div class="admin-edit-grid">
                  <input bind:value={row.text} class="answer-input" type="text" aria-label="Word text" />
                  <input bind:value={row.translation} class="answer-input" type="text" aria-label="Word translation" />
                  <input bind:value={row.source} class="answer-input" type="text" aria-label="Word source" />
                  <input class="answer-input" type="text" value={row.synonyms.join(', ')} aria-label="Word synonyms" on:input={(event) => (row.synonyms = (event.currentTarget as HTMLInputElement).value.split(',').map((item) => item.trim()).filter(Boolean))} />
                  <label class="admin-check"><input bind:checked={row.verified} type="checkbox" /> Verified</label>
                </div>
                <div class="trainer-actions">
                  <span class="mini-tag">{row.language_code} → {row.target_language_code}</span>
                  <button class="secondary-button" type="button" on:click={() => saveWord(row)}>Save</button>
                  <button class="ghost-button" type="button" on:click={() => deleteWord(row.id)}>Delete</button>
                </div>
              </article>
            {/each}
          </div>
        </article>
      {:else if tab === 'verbs'}
        <article class="glass-panel admin-workbench">
          <div class="section-head">
            <div>
              <p class="eyebrow">Verb review</p>
              <h2>Edit infinitives and translations</h2>
            </div>
            <div class="pill-row">
              <input bind:value={verbSearch} class="answer-input admin-search" type="text" placeholder="Search verbs or translations" />
              <select bind:value={verifiedFilter} class="answer-input admin-select">
                <option value="all">All</option>
                <option value="true">Verified</option>
                <option value="false">Needs review</option>
              </select>
              <button class="secondary-button" type="button" on:click={loadVerbs}>Refresh</button>
            </div>
          </div>

          <div class="admin-create-grid">
            <input bind:value={newVerb.infinitive} class="answer-input" type="text" placeholder="Infinitive" />
            <input bind:value={newVerb.translation} class="answer-input" type="text" placeholder="Translation" />
            <input bind:value={newVerb.synonyms} class="answer-input" type="text" placeholder="Synonyms, comma separated" />
            <input bind:value={newVerb.source} class="answer-input" type="text" placeholder="Source/provenance" />
            <button class="primary-button" type="button" on:click={createVerb}>Create row</button>
          </div>

          <div class="list-stack">
            {#each verbRows as row}
              <article class="glass-panel strong-panel admin-edit-card">
                <div class="admin-edit-grid">
                  <input bind:value={row.infinitive} class="answer-input" type="text" aria-label="Verb infinitive" />
                  <input bind:value={row.translation} class="answer-input" type="text" aria-label="Verb translation" />
                  <input bind:value={row.source} class="answer-input" type="text" aria-label="Verb source" />
                  <input class="answer-input" type="text" value={row.synonyms.join(', ')} aria-label="Verb synonyms" on:input={(event) => (row.synonyms = (event.currentTarget as HTMLInputElement).value.split(',').map((item) => item.trim()).filter(Boolean))} />
                  <label class="admin-check"><input bind:checked={row.verified} type="checkbox" /> Verified</label>
                </div>
                <div class="trainer-actions">
                  <span class="mini-tag">{row.language_code} → {row.target_language_code}</span>
                  <button class="secondary-button" type="button" on:click={() => saveVerb(row)}>Save</button>
                  <button class="ghost-button" type="button" on:click={() => deleteVerb(row.id)}>Delete</button>
                </div>
              </article>
            {/each}
          </div>
        </article>
      {:else}
        <article class="glass-panel admin-workbench">
          <div class="section-head">
            <div>
              <p class="eyebrow">Conjugation review</p>
              <h2>Fix tense slots and verification state</h2>
            </div>
            <div class="pill-row">
              <input bind:value={conjugationSearch} class="answer-input admin-search" type="text" placeholder="Search verbs, tense, or form" />
              <select bind:value={verifiedFilter} class="answer-input admin-select">
                <option value="all">All</option>
                <option value="true">Verified</option>
                <option value="false">Needs review</option>
              </select>
              <button class="secondary-button" type="button" on:click={loadConjugations}>Refresh</button>
            </div>
          </div>

          <div class="admin-create-grid admin-conj-grid">
            <input bind:value={newConjugation.infinitive} class="answer-input" type="text" placeholder="Infinitive" />
            <input bind:value={newConjugation.tense} class="answer-input" type="text" placeholder="Tense" />
            <input bind:value={newConjugation.pronoun} class="answer-input" type="text" placeholder="Pronoun" />
            <input bind:value={newConjugation.conjugated_form} class="answer-input" type="text" placeholder="Conjugated form" />
            <input bind:value={newConjugation.source} class="answer-input" type="text" placeholder="Source/provenance" />
            <button class="primary-button" type="button" on:click={createConjugation}>Create row</button>
          </div>

          <div class="list-stack">
            {#each conjugationRows as row}
              <article class="glass-panel strong-panel admin-edit-card">
                <div class="admin-edit-grid admin-conj-grid">
                  <input bind:value={row.infinitive} class="answer-input" type="text" aria-label="Conjugation infinitive" />
                  <input bind:value={row.tense} class="answer-input" type="text" aria-label="Conjugation tense" />
                  <input bind:value={row.pronoun} class="answer-input" type="text" aria-label="Conjugation pronoun" />
                  <input bind:value={row.conjugated_form} class="answer-input" type="text" aria-label="Conjugated form" />
                  <input bind:value={row.source} class="answer-input" type="text" aria-label="Conjugation source" />
                  <label class="admin-check"><input bind:checked={row.verified} type="checkbox" /> Verified</label>
                </div>
                <div class="trainer-actions">
                  <span class="mini-tag">{row.language_code} · {row.mood}</span>
                  <button class="secondary-button" type="button" on:click={() => saveConjugation(row)}>Save</button>
                  <button class="ghost-button" type="button" on:click={() => deleteConjugation(row.id)}>Delete</button>
                </div>
              </article>
            {/each}
          </div>
        </article>
      {/if}
    </div>
  {/if}
</section>
