import type {
  AddWordResponse,
  AddedWordResult,
  AdminAiUsagePayload,
  TagEntry,
  WordSetDetail,
  WordSetSummary,
  AdminConjugationRow,
  AdminContentSummaryPayload,
  AdminVerbRow,
  AdminWordRow,
  BootPayload,
  ChatPayload,
  CommunityPayload,
  ConjugationState,
  ConjugationTenseReview,
  DashboardPayload,
  LanguageEntry,
  MonitorPayload,
  OcrResponse,
  PriorityQueueEntry,
  SenseSelectionResult,
  StudyPoolResponse,
  ThemeName,
  TranslationState,
  UserSettings,
  UserSettingsPatch,
  UserWordEntry,
  WordHistoryEntry,
} from './types';

export class ApiError extends Error {
  status: number;

  constructor(message: string, status = 500) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();

  if (!response.ok) {
    const detail = typeof payload === 'object' && payload && 'detail' in payload ? String(payload.detail) : response.statusText;
    throw new ApiError(detail || 'Request failed', response.status);
  }

  return payload as T;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  // FormData bodies must let the browser set the multipart boundary itself.
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(path, {
    credentials: 'same-origin',
    ...options,
    headers,
  });

  return parseResponse<T>(response);
}

export const api = {
  bootstrap: () => request<BootPayload>('/api/bootstrap'),
  login: (payload: { username: string; password: string; csrf_token: string }) =>
    request<BootPayload>('/api/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  register: (payload: { username: string; password: string; confirm_password: string; csrf_token: string }) =>
    request<BootPayload>('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  logout: (csrf_token: string) =>
    request<BootPayload>('/api/auth/logout', { method: 'POST', body: JSON.stringify({ csrf_token }) }),
  updateTheme: (theme: ThemeName, csrf_token: string) =>
    request<{ ok: boolean; theme: ThemeName }>('/api/preferences/theme', {
      method: 'POST',
      body: JSON.stringify({ theme, csrf_token }),
    }),
  updateSound: (sound_enabled: boolean, csrf_token: string) =>
    request<{ ok: boolean; sound_enabled: boolean }>('/api/preferences/sound', {
      method: 'POST',
      body: JSON.stringify({ sound_enabled, csrf_token }),
    }),
  dashboard: () => request<DashboardPayload>('/api/dashboard'),
  wordsState: () => request<TranslationState>('/api/training/words'),
  verbsState: () => request<TranslationState>('/api/training/verbs'),
  studyPool: (params: { mode: 'words' | 'verbs' | 'conjugation'; direction?: string; language?: string; tenses?: string[] }) => {
    const query = new URLSearchParams({ mode: params.mode });
    if (params.direction) query.set('direction', params.direction);
    if (params.language) query.set('language', params.language);
    if (params.tenses?.length) query.set('tenses', params.tenses.join(','));
    return request<StudyPoolResponse>(`/api/training/study-pool?${query.toString()}`, { cache: 'no-store' });
  },
  startWords: (payload: { length: number; direction: string; set_id?: number; csrf_token: string }) =>
    request<TranslationState>('/api/training/words/start', { method: 'POST', body: JSON.stringify(payload) }),
  startVerbs: (payload: { length: number; direction: string; set_id?: number; csrf_token: string }) =>
    request<TranslationState>('/api/training/verbs/start', { method: 'POST', body: JSON.stringify(payload) }),
  hintWords: (csrf_token: string) =>
    request<TranslationState>('/api/training/words/hint', { method: 'POST', body: JSON.stringify({ csrf_token }) }),
  hintVerbs: (csrf_token: string) =>
    request<TranslationState>('/api/training/verbs/hint', { method: 'POST', body: JSON.stringify({ csrf_token }) }),
  finishWords: (csrf_token: string) =>
    request<TranslationState>('/api/training/words/finish', { method: 'POST', body: JSON.stringify({ csrf_token }) }),
  finishVerbs: (csrf_token: string) =>
    request<TranslationState>('/api/training/verbs/finish', { method: 'POST', body: JSON.stringify({ csrf_token }) }),
  answerWords: (payload: { answer: string; csrf_token: string }) =>
    request<TranslationState>('/api/training/words/answer', { method: 'POST', body: JSON.stringify(payload) }),
  answerVerbs: (payload: { answer: string; csrf_token: string }) =>
    request<TranslationState>('/api/training/verbs/answer', { method: 'POST', body: JSON.stringify(payload) }),
  revealWords: (payload: { answer: string; csrf_token: string }) =>
    request<TranslationState>('/api/training/words/reveal', { method: 'POST', body: JSON.stringify(payload) }),
  revealVerbs: (payload: { answer: string; csrf_token: string }) =>
    request<TranslationState>('/api/training/verbs/reveal', { method: 'POST', body: JSON.stringify(payload) }),
  conjugationState: () => request<ConjugationState>('/api/training/conjugation', { cache: 'no-store' }),
  startConjugation: (payload: {
    language: string;
    level: string;
    fill_level: string;
    selected_tenses: string[];
    length: number;
    csrf_token: string;
  }) => request<ConjugationState>('/api/training/conjugation/start', { method: 'POST', body: JSON.stringify(payload) }),
  finishConjugation: (csrf_token: string) =>
    request<ConjugationState>('/api/training/conjugation/finish', { method: 'POST', body: JSON.stringify({ csrf_token }) }),
  submitConjugation: (payload: { answers: Record<string, Record<string, string>>; csrf_token: string }) =>
    request<ConjugationState>('/api/training/conjugation/submit', { method: 'POST', body: JSON.stringify(payload) }),
  checkConjugationTense: (payload: { tense: string; answers: Record<string, string>; csrf_token: string }) =>
    request<ConjugationTenseReview>('/api/training/conjugation/check-tense', { method: 'POST', body: JSON.stringify(payload) }),
  chatState: () => request<ChatPayload>('/api/chat'),
  community: () => request<CommunityPayload>('/api/community'),
  addCircleFriend: (payload: { username: string; csrf_token: string }) =>
    request<{ ok: boolean; friend: { user_id: number; username: string } }>('/api/community/friends', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  removeCircleFriend: (friend_user_id: number, csrf_token: string) =>
    request<{ ok: boolean }>(`/api/community/friends/${friend_user_id}`, {
      method: 'DELETE',
      body: JSON.stringify({ csrf_token }),
    }),
  getSettings: () => request<UserSettings>('/api/settings'),
  patchSettings: (payload: Partial<UserSettingsPatch> & { csrf_token: string }) =>
    request<UserSettings>('/api/settings', { method: 'PATCH', body: JSON.stringify(payload) }),
  listLanguages: () => request<{ languages: LanguageEntry[] }>('/api/languages'),
  addWord: (payload: {
    input_text: string;
    context?: string;
    question?: string;
    context_source?: 'manual' | 'photo';
    learning_lang_code?: string;
    mother_lang_code?: string;
    csrf_token: string;
  }) => request<AddWordResponse>('/api/words/add', { method: 'POST', body: JSON.stringify(payload) }),
  selectWordSense: (lookup_id: number, sense_id: number, csrf_token: string) =>
    request<SenseSelectionResult>(`/api/words/lookups/${lookup_id}/sense`, {
      method: 'POST',
      body: JSON.stringify({ sense_id, csrf_token }),
    }),
  ocrExtract: (image: Blob, lang_code: string, csrf_token: string) => {
    const form = new FormData();
    form.append('image', image, 'subtitle.jpg');
    form.append('lang_code', lang_code);
    form.append('csrf_token', csrf_token);
    return request<OcrResponse>('/api/words/ocr', { method: 'POST', body: form });
  },
  listTags: () => request<{ tags: TagEntry[] }>('/api/tags'),
  listWordSets: () => request<{ sets: WordSetSummary[] }>('/api/word-sets'),
  getWordSet: (id: number) => request<WordSetDetail>(`/api/word-sets/${id}`),
  createWordSet: (payload: {
    name: string;
    description?: string;
    icon?: string;
    kind: 'manual' | 'smart';
    filter_tag_slugs: string[];
    csrf_token: string;
  }) => request<WordSetSummary>('/api/word-sets', { method: 'POST', body: JSON.stringify(payload) }),
  updateWordSet: (
    id: number,
    payload: {
      name?: string;
      description?: string;
      icon?: string;
      filter_tag_slugs?: string[];
      csrf_token: string;
    },
  ) =>
    request<WordSetSummary>(`/api/word-sets/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteWordSet: (id: number, csrf_token: string) =>
    request<{ ok: boolean }>(`/api/word-sets/${id}`, {
      method: 'DELETE',
      body: JSON.stringify({ csrf_token }),
    }),
  addWordToSet: (set_id: number, word_id: number, csrf_token: string) =>
    request<{ ok: boolean }>(`/api/word-sets/${set_id}/words`, {
      method: 'POST',
      body: JSON.stringify({ word_id, csrf_token }),
    }),
  removeWordFromSet: (set_id: number, word_id: number, csrf_token: string) =>
    request<{ ok: boolean }>(`/api/word-sets/${set_id}/words/${word_id}`, {
      method: 'DELETE',
      body: JSON.stringify({ csrf_token }),
    }),
  expandWord: (word_id: number, csrf_token: string) =>
    request<{ extended_content: string }>(`/api/words/${word_id}/expand`, {
      method: 'POST',
      body: JSON.stringify({ csrf_token }),
    }),
  reportTranslation: (
    word_id: number,
    payload: { entry_type: 'lexical' | 'native'; entry_id: number; reason?: string; csrf_token: string },
  ) =>
    request<{ ok: boolean }>(`/api/words/${word_id}/report`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  priorityQueue: () => request<{ entries: PriorityQueueEntry[] }>('/api/words/priority-queue'),
  wordHistory: (limit = 20) =>
    request<{ entries: WordHistoryEntry[] }>(`/api/words/history?limit=${limit}`),
  listUserWords: (language_pair: string) =>
    request<{ entries: UserWordEntry[] }>(
      `/api/words/manage?language_pair=${encodeURIComponent(language_pair)}`,
    ),
  deleteUserWord: (word_id: number, language_pair: string, csrf_token: string) =>
    request<{ ok: boolean }>(`/api/words/manage/${word_id}/delete`, {
      method: 'POST',
      body: JSON.stringify({ language_pair, csrf_token }),
    }),
  addWordOffline: (payload: {
    learning_text: string;
    native_text: string;
    learning_lang_code: string;
    mother_lang_code: string;
    note?: string;
    csrf_token: string;
  }) =>
    request<{
      ok: boolean;
      word_id: number;
      text: string;
      translation: string;
      language_pair: string;
      force_unlocked: boolean;
    }>('/api/words/add-offline', { method: 'POST', body: JSON.stringify(payload) }),
  adminMonitor: () => request<MonitorPayload>('/api/admin/monitor'),
  adminAiUsage: (limit = 50) => request<AdminAiUsagePayload>(`/api/admin/ai/usage?limit=${limit}`),
  adminContentSummary: () => request<AdminContentSummaryPayload>('/api/admin/content/summary'),
  adminWords: (params: { search?: string; verified?: string; limit?: number } = {}) =>
    request<{ rows: AdminWordRow[] }>(
      `/api/admin/content/words?${new URLSearchParams(
        Object.entries(params)
          .filter(([, value]) => value !== undefined && value !== '')
          .map(([key, value]) => [key, String(value)]),
      ).toString()}`,
    ),
  createAdminWord: (payload: Record<string, unknown>) =>
    request<{ row: AdminWordRow }>('/api/admin/content/words', { method: 'POST', body: JSON.stringify(payload) }),
  updateAdminWord: (id: number, payload: Record<string, unknown>) =>
    request<{ row: AdminWordRow }>(`/api/admin/content/words/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteAdminWord: (id: number, csrf_token: string) =>
    request<{ ok: boolean }>(`/api/admin/content/words/${id}`, { method: 'DELETE', body: JSON.stringify({ csrf_token }) }),
  adminVerbs: (params: { search?: string; verified?: string; limit?: number } = {}) =>
    request<{ rows: AdminVerbRow[] }>(
      `/api/admin/content/verbs?${new URLSearchParams(
        Object.entries(params)
          .filter(([, value]) => value !== undefined && value !== '')
          .map(([key, value]) => [key, String(value)]),
      ).toString()}`,
    ),
  createAdminVerb: (payload: Record<string, unknown>) =>
    request<{ row: AdminVerbRow }>('/api/admin/content/verbs', { method: 'POST', body: JSON.stringify(payload) }),
  updateAdminVerb: (id: number, payload: Record<string, unknown>) =>
    request<{ row: AdminVerbRow }>(`/api/admin/content/verbs/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteAdminVerb: (id: number, csrf_token: string) =>
    request<{ ok: boolean }>(`/api/admin/content/verbs/${id}`, { method: 'DELETE', body: JSON.stringify({ csrf_token }) }),
  adminConjugations: (params: { search?: string; verified?: string; language_code?: string; limit?: number } = {}) =>
    request<{ rows: AdminConjugationRow[] }>(
      `/api/admin/content/conjugations?${new URLSearchParams(
        Object.entries(params)
          .filter(([, value]) => value !== undefined && value !== '')
          .map(([key, value]) => [key, String(value)]),
      ).toString()}`,
    ),
  createAdminConjugation: (payload: Record<string, unknown>) =>
    request<{ row: AdminConjugationRow }>('/api/admin/content/conjugations', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateAdminConjugation: (id: number, payload: Record<string, unknown>) =>
    request<{ row: AdminConjugationRow }>(`/api/admin/content/conjugations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deleteAdminConjugation: (id: number, csrf_token: string) =>
    request<{ ok: boolean }>(`/api/admin/content/conjugations/${id}`, {
      method: 'DELETE',
      body: JSON.stringify({ csrf_token }),
    }),
};

export async function streamChat(
  payload: { message: string; csrf_token: string },
  onChunk: (chunk: string) => void,
): Promise<void> {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok || !response.body) {
    await parseResponse(response);
    throw new ApiError('Chat stream failed', response.status);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      return;
    }

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop() || '';

    for (const block of events) {
      const lines = block.split('\n');
      for (const line of lines) {
        if (!line.startsWith('data: ')) {
          continue;
        }
        const payloadText = line.slice(6);
        if (payloadText === '[DONE]') {
          return;
        }
        try {
          const parsed = JSON.parse(payloadText) as { chunk?: string };
          if (parsed.chunk) {
            onChunk(parsed.chunk);
          }
        } catch {
          onChunk(payloadText);
        }
      }
    }
  }
}
