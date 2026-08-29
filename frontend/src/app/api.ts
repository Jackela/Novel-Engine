import { appConfig } from '@/app/config';
import {
  parseAliases,
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
  parseVolume,
  parseVolumes,
} from '@/app/apiContract';
import {
  parseExportJobResponse,
  parseExports,
  parseJob,
  parseJobs,
  parseReviewJobResponse,
  parseReviews,
  parseUsage,
} from '@/app/apiWorkflowContract';
import type { DocumentKind, ExportFormat } from '@/app/types/studio';

export class HttpError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail?: unknown,
    readonly code?: string,
  ) {
    super(message);
    Object.setPrototypeOf(this, HttpError.prototype);
  }
}

const url = (path: string) => (appConfig.apiBaseUrl ? `${appConfig.apiBaseUrl}${path}` : path);

/** Absolute-API-aware URL builder shared by the streaming client (#308). */
export const apiUrl = url;

export function getCsrfToken(): string | undefined {
  if (typeof document === 'undefined') {
    return undefined;
  }
  const engine = document.cookie.match(/(?:^|; )novel_engine_csrf=([^;]*)/);
  return engine?.[1];
}

type ResponseParser<T> = (value: unknown) => T;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Read an error response in the unified envelope shape
 * `{ error: { code, message, details } }`. Unknown bodies fall back to the
 * caller's status message.
 */
export async function readHttpError(
  response: Response,
  fallbackMessage: string,
): Promise<HttpError> {
  const payload = await response.json().catch(() => null);
  if (isRecord(payload) && isRecord(payload.error)) {
    const envelope = payload.error;
    const message = typeof envelope.message === 'string' ? envelope.message : fallbackMessage;
    const code = typeof envelope.code === 'string' ? envelope.code : undefined;
    return new HttpError(message, response.status, envelope.details, code);
  }
  return new HttpError(fallbackMessage, response.status, undefined, undefined);
}

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
        throw new Error('Novel Engine is unavailable. Check the local service and retry.');
      }
      throw error;
    }
    if (!response.ok) {
      throw await readHttpError(response, `Request failed with status ${response.status}`);
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
      throw await readHttpError(response, `Download failed with status ${response.status}`);
    }
    return await response.blob();
  } catch (error) {
    if (error instanceof HttpError) throw error;
    if ((error instanceof Error || error instanceof DOMException) && error.name === 'AbortError') {
      throw new Error('Download timed out. Please retry.');
    }
    if (error instanceof TypeError) {
      throw new Error('Novel Engine is unavailable. Check the local service and retry.');
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
  volumes: (projectId: string) =>
    request(`/api/projects/${projectId}/volumes`, undefined, parseVolumes),
  createVolume: (projectId: string, title: string) =>
    postJson(`/api/projects/${projectId}/volumes`, { title }, parseVolume),
  renameVolume: (projectId: string, volumeId: string, title: string) =>
    putJson(`/api/projects/${projectId}/volumes/${volumeId}`, { title }, parseVolume),
  deleteVolume: (projectId: string, volumeId: string) =>
    request(`/api/projects/${projectId}/volumes/${volumeId}`, { method: 'DELETE' }, parseVoid),
  reorderVolumes: (projectId: string, volumeIds: string[]) =>
    putJson(`/api/projects/${projectId}/volumes/reorder`, { volume_ids: volumeIds }, parseVolumes),
  moveChapterToVolume: (projectId: string, documentId: string, volumeId: string) =>
    putJson(
      `/api/projects/${projectId}/documents/${documentId}/volume`,
      { volume_id: volumeId },
      parseStudioDocument,
    ),
  documentAliases: (projectId: string, documentId: string) =>
    request(`/api/projects/${projectId}/documents/${documentId}/aliases`, undefined, parseAliases),
  saveDocumentAliases: (projectId: string, documentId: string, aliases: string[]) =>
    putJson(
      `/api/projects/${projectId}/documents/${documentId}/aliases`,
      { aliases },
      parseAliases,
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
    request(`/api/projects/${projectId}/reviews`, { method: 'POST' }, parseReviewJobResponse),
  exports: (projectId: string) =>
    request(`/api/projects/${projectId}/exports`, undefined, parseExports),
  createExport: (projectId: string, format: ExportFormat) =>
    postJson(`/api/projects/${projectId}/exports`, { format }, parseExportJobResponse),
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
  usage: (projectId: string) => request(`/api/projects/${projectId}/usage`, undefined, parseUsage),
  retryJob: (projectId: string, jobId: string) =>
    request(`/api/projects/${projectId}/jobs/${jobId}/retry`, { method: 'POST' }, parseJob),
  download: (path: string) => downloadBlob(path),
};
