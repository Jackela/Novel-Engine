import {
  parseAliases,
  parseChapterBeat,
  parseDocuments,
  parseLoreStatus,
  parseOwnerSetup,
  parseProjectListItem,
  parseProjectShell,
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
import { type ExportsRequestOptions, projectExportsRequest } from "@/app/exportApiRequest";
import { downloadBlob, json, patchJson, postJson, putJson, request } from "@/app/httpClient";
import { type JobsRequestOptions, projectJobsRequest, retryJobRequest } from "@/app/jobApiRequest";
import { type ProjectsRequestOptions, projectCatalogRequest } from "@/app/projectApiRequest";
import { clearRetryAttemptSession, parseAndRecordRetrySession } from "@/app/retryAttemptRegistry";
import { documentRevisionsRequest, type RevisionRequestOptions } from "@/app/revisionApiRequest";
import type { DocumentKind, ExportFormat, LoreStatus, ProjectUpdateBody } from "@/app/types/studio";

export { apiUrl, getCsrfToken, HttpError, readHttpError } from "@/app/httpClient";

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
  projects: (options: ProjectsRequestOptions = {}) =>
    request(...projectCatalogRequest(options), parseProjects),
  project: (projectId: string, init?: RequestInit) =>
    request(`/api/projects/${projectId}`, init, parseProjectShell),
  createProject: (title: string, description: string) =>
    postJson("/api/projects", { title, description }, parseProjectShell),
  document: (projectId: string, documentId: string, init?: RequestInit) =>
    request(`/api/projects/${projectId}/documents/${documentId}`, init, parseStudioDocument),
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
  linkChapterBeat: (projectId: string, documentId: string, beat: string | null) =>
    putJson(`/api/projects/${projectId}/documents/${documentId}/beat`, { beat }, parseChapterBeat),
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
  exports: (projectId: string, options: ExportsRequestOptions = {}) => {
    const [path, init] = projectExportsRequest(projectId, options);
    return request(path, init, parseExports);
  },
  createExport: (projectId: string, format: ExportFormat, init?: RequestInit) =>
    request(
      `/api/projects/${projectId}/exports`,
      { ...init, method: "POST", body: json({ format }) },
      parseExportJobResponse,
    ),
  updateProject: (projectId: string, payload: ProjectUpdateBody, init?: RequestInit) =>
    patchJson(`/api/projects/${projectId}`, payload, parseProjectListItem, init),
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
