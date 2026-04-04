import type {
  AdminConjugationRow,
  AdminContentSummaryPayload,
  AdminVerbRow,
  AdminWordRow,
  BootPayload,
  ChatPayload,
  CommunityPayload,
  ConjugationState,
  DashboardPayload,
  MonitorPayload,
  ThemeName,
  TranslationState,
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
  if (options.body && !headers.has('Content-Type')) {
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
  startWords: (payload: { length: number; direction: string; csrf_token: string }) =>
    request<TranslationState>('/api/training/words/start', { method: 'POST', body: JSON.stringify(payload) }),
  startVerbs: (payload: { length: number; direction: string; csrf_token: string }) =>
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
  conjugationState: () => request<ConjugationState>('/api/training/conjugation'),
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
  adminMonitor: () => request<MonitorPayload>('/api/admin/monitor'),
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
