import {
  parseAliases,
  parseDocuments,
  parseLoreStatus,
  parseOwnerSetup,
  parseProjectListItem,
  parseProjectShell,
  parseProjects,
  parseProviders,
  parseRevisions,
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
  parseReviewDetail,
  parseReviewJobResponse,
  parseReviews,
  parseUsage,
} from "@/app/apiWorkflowContract";
import { parseChapterBeat } from "@/app/beatContract";
import { browserTzOffsetMinutes } from "@/app/browserTimezone";
import { parseDiagnostics } from "@/app/diagnosticsContract";
import { type ExportsRequestOptions, projectExportsRequest } from "@/app/exportApiRequest";
import { downloadBlob, json, patchJson, postJson, putJson, request } from "@/app/httpClient";
import { type JobsRequestOptions, projectJobsRequest, retryJobRequest } from "@/app/jobApiRequest";
import { parseLoreExtractJob } from "@/app/loreExtractContract";
import { type ProjectsRequestOptions, projectCatalogRequest } from "@/app/projectApiRequest";
import { clearRetryAttemptSession, parseAndRecordRetrySession } from "@/app/retryAttemptRegistry";
import { type ReviewListOptions, reviewDetailPath, reviewsRequest } from "@/app/reviewApiRequest";
import { documentRevisionsRequest, type RevisionRequestOptions } from "@/app/revisionApiRequest";
import { parseRevisionDetail } from "@/app/revisionDetailContract";
import { parseSearch } from "@/app/searchContract";
import { parseWritingStats } from "@/app/statsContract";
import type { DocumentKind, ExportFormat, LoreStatus, ProjectUpdateBody } from "@/app/types/studio";

export { apiUrl, getCsrfToken, HttpError } from "@/app/httpClient";

export const api = {
  setupStatus: (init?: RequestInit) => request("/api/setup", init, parseSetupStatus),
  // The optional first-start setup token (DR-008) rides the x-setup-token
  // header, and only when the operator actually typed one: loopback setups
  // must keep the header absent rather than send an empty value.
  setupOwner: (username: string, password: string, setupToken?: string) => {
    const token = setupToken?.trim();
    return postJson(
      "/api/setup",
      { username, password },
      parseOwnerSetup,
      token ? { headers: { "x-setup-token": token } } : undefined,
    );
  },
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
  // DR-043: the read surface carries the chapter's candidate catalog and the
  // outline it came from, so the association control never needs typed recall.
  chapterBeat: (projectId: string, documentId: string, init?: RequestInit) =>
    request(`/api/projects/${projectId}/documents/${documentId}/beat`, init, parseChapterBeat),
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
      /** #DR-047: marks the editor's draft autosave for revision folding. */
      autosave?: boolean;
    },
  ) => putJson(`/api/projects/${projectId}/documents/${documentId}`, payload, parseStudioDocument),
  revisions: (projectId: string, documentId: string, options: RevisionRequestOptions = {}) =>
    request(...documentRevisionsRequest(projectId, documentId, options), parseRevisions),
  revision: (projectId: string, documentId: string, revisionId: string) =>
    request(
      `/api/projects/${projectId}/documents/${documentId}/revisions/${revisionId}`,
      undefined,
      parseRevisionDetail,
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
  /**
   * DR-029: one ranked search page. `offset` walks the remaining pages with
   * the server-issued `next_offset`; `signal` aborts an in-flight request.
   */
  search: (
    projectId: string,
    query: string,
    options: { offset?: number; signal?: AbortSignal } = {},
  ) => {
    const offset = options.offset ?? 0;
    const page = offset > 0 ? `&offset=${offset}` : "";
    return request(
      `/api/projects/${projectId}/search?q=${encodeURIComponent(query)}${page}`,
      { signal: options.signal },
      parseSearch,
    );
  },
  acceptProposal: (projectId: string, jobId: string) =>
    request(
      `/api/projects/${projectId}/ai-proposals/${jobId}/accept`,
      { method: "POST" },
      parseJob,
    ),
  reviews: (projectId: string, options: ReviewListOptions = {}) =>
    request(...reviewsRequest(projectId, options), parseReviews),
  reviewDetail: (projectId: string, reviewId: string, init?: RequestInit) =>
    request(reviewDetailPath(projectId, reviewId), init, parseReviewDetail),
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
  job: (projectId: string, jobId: string, init?: RequestInit) =>
    request(`/api/projects/${projectId}/jobs/${jobId}`, init, parseJob),
  usage: (projectId: string, init?: RequestInit) =>
    request(`/api/projects/${projectId}/usage`, init, parseUsage),
  writingStats: (projectId: string, init?: RequestInit) =>
    request(
      // DR-045: the aggregation buckets its day rows on the browser's own day
      // boundary, so a UTC+8 author's "today" is their local day.
      `/api/projects/${projectId}/stats?tz_offset_minutes=${browserTzOffsetMinutes()}`,
      init,
      parseWritingStats,
    ),
  extractLore: (projectId: string, segment: string, provider: string) =>
    postJson(
      `/api/projects/${projectId}/lore-extractions`,
      { segment, provider },
      parseLoreExtractJob,
    ),
  diagnostics: (projectId: string, init?: RequestInit) =>
    request(`/api/projects/${projectId}/diagnostics`, init, parseDiagnostics),
  retryJob: (projectId: string, jobId: string, idempotencyKey: string) => {
    const [path, init] = retryJobRequest(projectId, jobId, idempotencyKey);
    return request(path, init, parseJob);
  },
  download: (path: string, init?: RequestInit) => downloadBlob(path, init),
};
