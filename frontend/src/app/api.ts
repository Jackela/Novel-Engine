import { appConfig } from '@/app/config';
import {
  parseDocuments,
  parseOwnerSetup,
  parseProject,
  parseProjects,
  parseProviders,
  parseRevisions,
  parseSearch,
  parseSession,
  parseSetupStatus,
  parseStudioDocument,
  parseVoid,
} from '@/app/apiContract';
import {
  parseExport,
  parseExports,
  parseJob,
  parseJobs,
  parseReview,
  parseReviews,
} from '@/app/apiWorkflowContract';
import type { DocumentKind, ExportFormat } from '@/app/types/studio';

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

type ResponseParser<T> = (value: unknown) => T;

async function request<T>(
  path: string,
  init: RequestInit | undefined,
  parse: ResponseParser<T>,
): Promise<T> {
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
    if (response.status === 204) return parse(undefined);
    return parse(await response.json());
  } finally {
    window.clearTimeout(timeout);
    externalSignal?.removeEventListener('abort', abortFromExternal);
  }
}

const json = (value: unknown) => JSON.stringify(value);

const postJson = <T>(path: string, value: unknown, parse: ResponseParser<T>) =>
  request(path, { method: 'POST', body: json(value) }, parse);
const putJson = <T>(path: string, value: unknown, parse: ResponseParser<T>) =>
  request(path, { method: 'PUT', body: json(value) }, parse);
const patchJson = <T>(path: string, value: unknown, parse: ResponseParser<T>) =>
  request(path, { method: 'PATCH', body: json(value) }, parse);

async function downloadBlob(path: string): Promise<Blob> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), appConfig.apiTimeoutMs);
  try {
    const response = await fetch(url(path), { credentials: 'include', signal: controller.signal });
    if (!response.ok) {
      throw new HttpError(`Download failed with status ${response.status}`, response.status);
    }
    return await response.blob();
  } catch (error) {
    if (error instanceof HttpError) throw error;
    if ((error instanceof Error || error instanceof DOMException) && error.name === 'AbortError') {
      throw new Error('Download timed out. Please retry.');
    }
    if (error instanceof TypeError) {
      throw new Error('Novel Studio is unavailable. Check the local service and retry.');
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

export const api = {
  setupStatus: () => request('/api/setup', undefined, parseSetupStatus),
  setupOwner: (username: string, password: string) =>
    postJson('/api/setup', { username, password }, parseOwnerSetup),
  login: (username: string, password: string) =>
    postJson('/api/session/login', { username, password }, parseSession),
  guest: () => request('/api/session/guest', { method: 'POST' }, parseSession),
  session: () => request('/api/session', undefined, parseSession),
  logout: () => request('/api/session', { method: 'DELETE' }, parseVoid),
  providers: () => request('/api/providers', undefined, parseProviders),
  projects: (init?: RequestInit) => request('/api/projects', init, parseProjects),
  project: (projectId: string) => request(`/api/projects/${projectId}`, undefined, parseProject),
  createProject: (title: string, description: string) =>
    postJson('/api/projects', { title, description }, parseProject),
  createDocument: (
    projectId: string,
    payload: {
      kind: DocumentKind;
      title: string;
      content_markdown?: string;
    },
  ) => postJson(`/api/projects/${projectId}/documents`, payload, parseStudioDocument),
  reorderDocuments: (projectId: string, documentIds: string[]) =>
    putJson(
      `/api/projects/${projectId}/documents/reorder`,
      { document_ids: documentIds },
      parseDocuments,
    ),
  saveDocument: (
    projectId: string,
    documentId: string,
    payload: {
      content_markdown: string;
      base_revision_id: string;
      title?: string;
      metadata?: Record<string, unknown>;
    },
  ) => putJson(`/api/projects/${projectId}/documents/${documentId}`, payload, parseStudioDocument),
  revisions: (projectId: string, documentId: string) =>
    request(
      `/api/projects/${projectId}/documents/${documentId}/revisions`,
      undefined,
      parseRevisions,
    ),
  restoreRevision: (
    projectId: string,
    documentId: string,
    revisionId: string,
    baseRevisionId: string,
  ) =>
    postJson(
      `/api/projects/${projectId}/documents/${documentId}/revisions/${revisionId}/restore`,
      { base_revision_id: baseRevisionId },
      parseStudioDocument,
    ),
  search: (projectId: string, query: string) =>
    request(
      `/api/projects/${projectId}/search?q=${encodeURIComponent(query)}`,
      undefined,
      parseSearch,
    ),
  proposal: (
    projectId: string,
    documentId: string,
    operation: 'continue' | 'rewrite' | 'generate',
    instruction: string,
    provider: string,
  ) =>
    postJson(
      `/api/projects/${projectId}/documents/${documentId}/ai-proposals`,
      { operation, instruction, provider },
      parseJob,
    ),
  acceptProposal: (projectId: string, jobId: string) =>
    request(
      `/api/projects/${projectId}/ai-proposals/${jobId}/accept`,
      { method: 'POST' },
      parseJob,
    ),
  reviews: (projectId: string) =>
    request(`/api/projects/${projectId}/reviews`, undefined, parseReviews),
  createReview: (projectId: string) =>
    request(`/api/projects/${projectId}/reviews`, { method: 'POST' }, parseReview),
  exports: (projectId: string) =>
    request(`/api/projects/${projectId}/exports`, undefined, parseExports),
  createExport: (projectId: string, format: ExportFormat) =>
    postJson(`/api/projects/${projectId}/exports`, { format }, parseExport),
  updateProject: (
    projectId: string,
    payload: {
      title?: string;
      description?: string;
      settings?: Record<string, unknown>;
    },
  ) => patchJson(`/api/projects/${projectId}`, payload, parseProject),
  deleteProject: (projectId: string) =>
    request(`/api/projects/${projectId}`, { method: 'DELETE' }, parseVoid),
  deleteDocument: (projectId: string, documentId: string) =>
    request(`/api/projects/${projectId}/documents/${documentId}`, { method: 'DELETE' }, parseVoid),
  jobs: (projectId: string) => request(`/api/projects/${projectId}/jobs`, undefined, parseJobs),
  retryJob: (projectId: string, jobId: string) =>
    request(`/api/projects/${projectId}/jobs/${jobId}/retry`, { method: 'POST' }, parseJob),
  download: (path: string) => downloadBlob(path),
};
