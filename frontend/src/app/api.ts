import { appConfig } from '@/app/config';
import type {
  DocumentKind,
  ExportFormat,
  Project,
  Review,
  Revision,
  Session,
  SetupStatus,
  StudioDocument,
  StudioExport,
  StudioJob,
} from '@/app/types/studio';

export class HttpError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail?: unknown,
  ) {
    super(message);
    Object.setPrototypeOf(this, HttpError.prototype);
  }
}

const url = (path: string) => (appConfig.apiBaseUrl ? `${appConfig.apiBaseUrl}${path}` : path);

export function getCsrfToken(): string | undefined {
  if (typeof document === 'undefined') {
    return undefined;
  }
  const match = document.cookie.match(/(?:^|; )novel_studio_csrf=([^;]*)/);
  return match?.[1];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const externalSignal = init?.signal;
  let timedOut = false;
  const abortFromExternal = () => controller.abort(externalSignal?.reason);
  if (externalSignal?.aborted) {
    abortFromExternal();
  } else {
    externalSignal?.addEventListener('abort', abortFromExternal, { once: true });
  }
  const timeout = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, appConfig.apiTimeoutMs);
  try {
    let response: Response;
    try {
      const method = init?.method?.toUpperCase();
      const csrfToken =
        method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method) ? getCsrfToken() : undefined;
      response = await fetch(url(path), {
        credentials: 'include',
        ...init,
        headers: {
          ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
          ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
          ...(init?.headers ?? {}),
        },
        signal: controller.signal,
      });
    } catch (error) {
      if (
        (error instanceof Error || error instanceof DOMException) &&
        error.name === 'AbortError'
      ) {
        throw new Error(timedOut ? 'Request timed out. Please retry.' : 'Request cancelled.');
      }
      if (error instanceof TypeError) {
        throw new Error('Novel Studio is unavailable. Check the local service and retry.');
      }
      throw error;
    }
    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as { detail?: unknown } | null;
      const detail = payload?.detail;
      const message =
        typeof detail === 'string'
          ? detail
          : typeof detail === 'object' && detail && 'message' in detail
            ? String((detail as { message: unknown }).message)
            : `Request failed with status ${response.status}`;
      throw new HttpError(message, response.status, detail);
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  } finally {
    window.clearTimeout(timeout);
    externalSignal?.removeEventListener('abort', abortFromExternal);
  }
}

const json = (value: unknown) => JSON.stringify(value);

export const api = {
  setupStatus: () => request<SetupStatus>('/api/setup'),
  setupOwner: (username: string, password: string) =>
    request<{ id: string; username: string }>('/api/setup', {
      method: 'POST',
      body: json({ username, password }),
    }),
  login: (username: string, password: string) =>
    request<Session>('/api/session/login', {
      method: 'POST',
      body: json({ username, password }),
    }),
  guest: () => request<Session>('/api/session/guest', { method: 'POST' }),
  session: () => request<Session>('/api/session'),
  logout: () => request<void>('/api/session', { method: 'DELETE' }),
  projects: (init?: RequestInit) => request<{ projects: Project[] }>('/api/projects', init),
  project: (projectId: string) => request<Project>(`/api/projects/${projectId}`),
  createProject: (title: string, description: string) =>
    request<Project>('/api/projects', {
      method: 'POST',
      body: json({ title, description }),
    }),
  createDocument: (
    projectId: string,
    payload: {
      kind: DocumentKind;
      title: string;
      content_markdown?: string;
    },
  ) =>
    request<StudioDocument>(`/api/projects/${projectId}/documents`, {
      method: 'POST',
      body: json(payload),
    }),
  reorderDocuments: (projectId: string, documentIds: string[]) =>
    request<{ documents: StudioDocument[] }>(`/api/projects/${projectId}/documents/reorder`, {
      method: 'PUT',
      body: json({ document_ids: documentIds }),
    }),
  saveDocument: (
    projectId: string,
    documentId: string,
    payload: {
      content_markdown: string;
      base_revision_id: string;
      title?: string;
      metadata?: Record<string, unknown>;
    },
  ) =>
    request<StudioDocument>(`/api/projects/${projectId}/documents/${documentId}`, {
      method: 'PUT',
      body: json(payload),
    }),
  revisions: (projectId: string, documentId: string) =>
    request<{ revisions: Revision[] }>(
      `/api/projects/${projectId}/documents/${documentId}/revisions`,
    ),
  restoreRevision: (
    projectId: string,
    documentId: string,
    revisionId: string,
    baseRevisionId: string,
  ) =>
    request<StudioDocument>(
      `/api/projects/${projectId}/documents/${documentId}/revisions/${revisionId}/restore`,
      { method: 'POST', body: json({ base_revision_id: baseRevisionId }) },
    ),
  search: (projectId: string, query: string) =>
    request<{ results: Array<{ document_id: string; title: string; excerpt: string }> }>(
      `/api/projects/${projectId}/search?q=${encodeURIComponent(query)}`,
    ),
  proposal: (
    projectId: string,
    documentId: string,
    operation: 'continue' | 'rewrite' | 'generate',
    instruction: string,
    provider: string,
  ) =>
    request<StudioJob>(`/api/projects/${projectId}/documents/${documentId}/ai-proposals`, {
      method: 'POST',
      body: json({ operation, instruction, provider }),
    }),
  acceptProposal: (projectId: string, jobId: string) =>
    request<StudioJob>(`/api/projects/${projectId}/ai-proposals/${jobId}/accept`, {
      method: 'POST',
    }),
  reviews: (projectId: string) =>
    request<{ reviews: Review[] }>(`/api/projects/${projectId}/reviews`),
  createReview: (projectId: string) =>
    request<Review>(`/api/projects/${projectId}/reviews`, { method: 'POST' }),
  exports: (projectId: string) =>
    request<{ exports: StudioExport[] }>(`/api/projects/${projectId}/exports`),
  createExport: (projectId: string, format: ExportFormat) =>
    request<StudioExport>(`/api/projects/${projectId}/exports`, {
      method: 'POST',
      body: json({ format }),
    }),
  updateProject: (
    projectId: string,
    payload: {
      title?: string;
      description?: string;
      settings?: Record<string, unknown>;
    },
  ) =>
    request<Project>(`/api/projects/${projectId}`, {
      method: 'PATCH',
      body: json(payload),
    }),
  jobs: (projectId: string) => request<{ jobs: StudioJob[] }>(`/api/projects/${projectId}/jobs`),
  retryJob: (projectId: string, jobId: string) =>
    request<StudioJob>(`/api/projects/${projectId}/jobs/${jobId}/retry`, {
      method: 'POST',
    }),
};
