import {
  parseAliases,
  parseDocuments,
  parseLoreStatus,
  parseOwnerSetup,
  parseProject,
  parseProjects,
  parseProviders,
  parseRevisions,
  parseSearch,
  parseSetupStatus,
  parseStudioDocument,
  parseVoid,
  parseVolume,
  parseVolumes,
} from "@/app/apiContract";
import {
  parseExportJobResponse,
  parseExports,
  parseJob,
  parseJobs,
  parseReviewJobResponse,
  parseReviews,
  parseUsage,
} from "@/app/apiWorkflowContract";
import { appConfig } from "@/app/config";
import { type JobsRequestOptions, projectJobsRequest, retryJobRequest } from "@/app/jobApiRequest";
import { localServiceUnavailable } from "@/app/networkError";
import { createRequestAbortScope } from "@/app/requestAbortScope";
import { clearRetryAttemptSession, parseAndRecordRetrySession } from "@/app/retryAttemptRegistry";
import { documentRevisionsRequest, type RevisionRequestOptions } from "@/app/revisionApiRequest";
import type { DocumentKind, ExportFormat, LoreStatus } from "@/app/types/studio";

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
  if (typeof document === "undefined") {
    return undefined;
  }
  const engine = document.cookie.match(/(?:^|; )novel_engine_csrf=([^;]*)/);
  return engine?.[1];
}

type ResponseParser<T> = (value: unknown) => T;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
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
    const message = typeof envelope.message === "string" ? envelope.message : fallbackMessage;
    const code = typeof envelope.code === "string" ? envelope.code : undefined;
    return new HttpError(message, response.status, envelope.details, code);
  }
  return new HttpError(fallbackMessage, response.status, undefined, undefined);
}

async function request<T>(
  path: string,
  init: RequestInit | undefined,
  parse: ResponseParser<T>,
): Promise<T> {
  const abortScope = createRequestAbortScope(init?.signal);
  try {
    let response: Response;
    try {
      const method = init?.method?.toUpperCase();
      const csrfToken =
        method && ["POST", "PUT", "PATCH", "DELETE"].includes(method) ? getCsrfToken() : undefined;
      response = await fetch(url(path), {
        credentials: "include",
        ...init,
        headers: {
          ...(init?.body ? { "Content-Type": "application/json" } : {}),
          ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
          ...(init?.headers ?? {}),
        },
        signal: abortScope.signal,
      });
    } catch (error) {
      if (
        (error instanceof Error || error instanceof DOMException) &&
        error.name === "AbortError"
      ) {
        throw new Error(
          abortScope.timedOut() ? "Request timed out. Please retry." : "Request cancelled.",
          { cause: error },
        );
      }
      if (error instanceof TypeError) {
        throw localServiceUnavailable(error);
      }
      throw error;
    }
    if (!response.ok) {
      throw await readHttpError(response, `Request failed with status ${response.status}`);
    }
    if (response.status === 204) return parse(undefined);
    return parse(await response.json());
  } finally {
    abortScope.dispose();
  }
}

const json = (value: unknown) => JSON.stringify(value);

const postJson = <T>(path: string, value: unknown, parse: ResponseParser<T>) =>
  request(path, { method: "POST", body: json(value) }, parse);
const putJson = <T>(path: string, value: unknown, parse: ResponseParser<T>) =>
  request(path, { method: "PUT", body: json(value) }, parse);
const patchJson = <T>(path: string, value: unknown, parse: ResponseParser<T>) =>
  request(path, { method: "PATCH", body: json(value) }, parse);

async function downloadBlob(path: string, init?: RequestInit): Promise<Blob> {
  const abortScope = createRequestAbortScope(init?.signal);
  try {
    const response = await fetch(url(path), {
      credentials: "include",
      ...init,
      signal: abortScope.signal,
    });
    if (!response.ok) {
      throw await readHttpError(response, `Download failed with status ${response.status}`);
    }
    return await response.blob();
  } catch (error) {
    if (error instanceof HttpError) throw error;
    if ((error instanceof Error || error instanceof DOMException) && error.name === "AbortError") {
      throw new Error(
        abortScope.timedOut() ? "Download timed out. Please retry." : "Request cancelled.",
        { cause: error },
      );
    }
    if (error instanceof TypeError) {
      throw localServiceUnavailable(error);
    }
    throw error;
  } finally {
    abortScope.dispose();
  }
}

export const api = {
  setupStatus: (init?: RequestInit) => request("/api/setup", init, parseSetupStatus),
  setupOwner: (username: string, password: string) =>
    postJson("/api/setup", { username, password }, parseOwnerSetup),
  login: (username: string, password: string) =>
    postJson("/api/session/login", { username, password }, parseAndRecordRetrySession),
  session: (init?: RequestInit) => request("/api/session", init, parseAndRecordRetrySession),
  logout: () => {
    clearRetryAttemptSession();
    return request("/api/session", { method: "DELETE" }, parseVoid);
  },
  providers: () => request("/api/providers", undefined, parseProviders),
  projects: (init?: RequestInit) => request("/api/projects", init, parseProjects),
  project: (projectId: string, init?: RequestInit) =>
    request(`/api/projects/${projectId}`, init, parseProject),
  createProject: (title: string, description: string) =>
    postJson("/api/projects", { title, description }, parseProject),
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
    request(`/api/projects/${projectId}/volumes/${volumeId}`, { method: "DELETE" }, parseVoid),
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
  saveLoreStatus: (projectId: string, documentId: string, lore_status: LoreStatus) =>
    putJson(
      `/api/projects/${projectId}/documents/${documentId}/lore-status`,
      { lore_status },
      parseLoreStatus,
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
  revisions: (projectId: string, documentId: string, options: RevisionRequestOptions = {}) =>
    request(...documentRevisionsRequest(projectId, documentId, options), parseRevisions),
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
  search: (projectId: string, query: string, init?: RequestInit) =>
    request(`/api/projects/${projectId}/search?q=${encodeURIComponent(query)}`, init, parseSearch),
  proposal: (
    projectId: string,
    documentId: string,
    operation: "continue" | "rewrite" | "generate",
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
      { method: "POST" },
      parseJob,
    ),
  reviews: (projectId: string, init?: RequestInit) =>
    request(`/api/projects/${projectId}/reviews`, init, parseReviews),
  createReview: (projectId: string) =>
    request(`/api/projects/${projectId}/reviews`, { method: "POST" }, parseReviewJobResponse),
  exports: (projectId: string, init?: RequestInit) =>
    request(`/api/projects/${projectId}/exports`, init, parseExports),
  createExport: (projectId: string, format: ExportFormat, init?: RequestInit) =>
    request(
      `/api/projects/${projectId}/exports`,
      { ...init, method: "POST", body: json({ format }) },
      parseExportJobResponse,
    ),
  updateProject: (
    projectId: string,
    payload: {
      title?: string;
      description?: string;
      settings?: Record<string, unknown>;
    },
  ) => patchJson(`/api/projects/${projectId}`, payload, parseProject),
  deleteProject: (projectId: string) =>
    request(`/api/projects/${projectId}`, { method: "DELETE" }, parseVoid),
  deleteDocument: (projectId: string, documentId: string) =>
    request(`/api/projects/${projectId}/documents/${documentId}`, { method: "DELETE" }, parseVoid),
  jobs: (projectId: string, options: JobsRequestOptions = {}) => {
    const [path, init] = projectJobsRequest(projectId, options);
    return request(path, init, parseJobs);
  },
  usage: (projectId: string, init?: RequestInit) =>
    request(`/api/projects/${projectId}/usage`, init, parseUsage),
  retryJob: (projectId: string, jobId: string, idempotencyKey: string) => {
    const [path, init] = retryJobRequest(projectId, jobId, idempotencyKey);
    return request(path, init, parseJob);
  },
  download: (path: string, init?: RequestInit) => downloadBlob(path, init),
};
