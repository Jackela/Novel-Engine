import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type { DocumentKind, LoreStatus, RevisionSource } from "../domain/kinds.js";
import { assertStoredRevisionWordCount } from "../domain/revision_word_count.js";
import { asLoreStatus, isLoreEntryKind } from "./lorebook.js";
import type { ChapterBeatPayload } from "./payload_schemas/beat.js";
import type { DocumentPayload, MatchResultPayload } from "./payload_schemas/document.js";
import type { ExportArtifactPayload } from "./payload_schemas/export.js";
import {
  JOB_SUMMARY_KINDS,
  JOB_SUMMARY_OPERATIONS,
  JOB_SUMMARY_STATUSES,
  type JobPayload,
  type JobSummaryPayload,
} from "./payload_schemas/job.js";
import type { LoreAliasPayload, LoreStatusPayload } from "./payload_schemas/lore.js";
import type { ProjectPayload } from "./payload_schemas/project.js";
import type { ReviewPayload, ReviewSeverity } from "./payload_schemas/review.js";
import type { RevisionPayload } from "./payload_schemas/revision.js";
import type { VolumePayload } from "./payload_schemas/volume.js";
import type { ExportArtifactRecord } from "./ports/export_store.js";
import type { JobSummaryRecord } from "./ports/job_records.js";
import type {
  DocumentMatchRecord,
  DocumentWithCurrent,
  JobRecord,
  RevisionRecord,
} from "./ports/studio_store.js";
import type { VolumeRecord } from "./ports/volume_store.js";
import type { EditorialAssessment } from "./review_service.js";

/**
 * Payload builders for the studio HTTP surfaces. Return types are `Static`
 * projections of the TypeBox payload SSOT (`payload_schemas/`), which the
 * interface layer declares verbatim as its response schemas — builder and
 * schema are one shape by construction (#433, #440).
 */

export { revisionWordCount as wordCount } from "../domain/revision_word_count.js";

/** Parse stored JSON defensively: unreadable payloads collapse to `{}`. */
export function safeLoadJson(value: string): Record<string, unknown> {
  try {
    const parsed: unknown = JSON.parse(value);
    if (parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    // Stored settings/metadata are advisory payloads; a malformed value must
    // not take down reads.
  }
  return {};
}

export function dumpJson(value: Record<string, unknown>): string {
  return JSON.stringify(value);
}

export function iso(value: Date): string {
  return value.toISOString();
}

export interface ProjectPayloadInput {
  id: string;
  title: string;
  description: string;
  settingsJson: string;
  importHash: string | null;
  createdAt: Date;
  updatedAt: Date;
}

export function projectPayload(
  project: ProjectPayloadInput,
  documents?: DocumentWithCurrent[],
  volumes?: VolumeRecord[],
): ProjectPayload {
  const payload: ProjectPayload = {
    id: project.id,
    title: project.title,
    description: project.description,
    settings: safeLoadJson(project.settingsJson),
    import_hash: project.importHash,
    created_at: iso(project.createdAt),
    updated_at: iso(project.updatedAt),
  };
  if (documents !== undefined) {
    payload.documents = documents.map((document) => documentPayload(document));
  }
  if (volumes !== undefined) {
    payload.volumes = volumes.map((volume) => volumePayload(volume));
  }
  return payload;
}

export function documentPayload(document: DocumentWithCurrent): DocumentPayload {
  const revision = document.currentRevision;
  if (revision === null) {
    throw new InvalidOperationError("Document has no current revision.");
  }
  return {
    id: document.id,
    project_id: document.projectId,
    // Store rows carry write-validated enum values; the payload narrows to
    // the closed sets declared in `domain/kinds.ts`.
    kind: document.kind as DocumentKind,
    title: document.title,
    position: document.position,
    volume_id: document.volumeId,
    beat_ref: document.beatRef,
    // Lore lifecycle status (#444): lore kinds narrow to the closed enum,
    // every other kind stays null so the semantics never leak beyond lore.
    lore_status: isLoreEntryKind(document.kind) ? asLoreStatus(document.loreStatus) : null,
    current_revision_id: revision.id,
    content_markdown: revision.contentMarkdown,
    metadata: safeLoadJson(revision.metadataJson),
    revision_source: revision.source as RevisionSource,
    word_count: assertStoredRevisionWordCount(revision.wordCount),
    created_at: iso(document.createdAt),
    updated_at: iso(document.updatedAt),
  };
}

/** The ordered list-level volume shape handed to every HTTP surface. */
export function volumePayload(volume: VolumeRecord): VolumePayload {
  return {
    id: volume.id,
    project_id: volume.projectId,
    title: volume.title,
    position: volume.position,
    created_at: iso(volume.createdAt),
    updated_at: iso(volume.updatedAt),
  };
}

/** One full-text hit: identifier, title, and a plain-text excerpt. */
export function documentMatchPayload(match: DocumentMatchRecord): MatchResultPayload {
  return {
    document_id: match.documentId,
    title: match.title,
    excerpt: match.excerpt,
  };
}

export function revisionPayload(revision: RevisionRecord): RevisionPayload {
  return {
    id: revision.id,
    document_id: revision.documentId,
    parent_revision_id: revision.parentRevisionId,
    revision_number: revision.revisionNumber,
    content_markdown: revision.contentMarkdown,
    metadata: safeLoadJson(revision.metadataJson),
    source: revision.source as RevisionSource,
    word_count: assertStoredRevisionWordCount(revision.wordCount),
    created_at: iso(revision.createdAt),
  };
}

export function jobPayload(job: JobRecord): JobPayload {
  return {
    id: job.id,
    project_id: job.projectId,
    document_id: job.documentId,
    kind: job.kind,
    operation: job.operation,
    status: job.status,
    provider: job.provider,
    model: job.model,
    request: safeLoadJson(job.requestJson),
    result: safeLoadJson(job.resultJson),
    error: job.error,
    retry_of_job_id: job.retryOfJobId,
    created_at: iso(job.createdAt),
    updated_at: iso(job.updatedAt),
    events: job.events.map((event) => ({
      id: event.id,
      status: event.status,
      details: safeLoadJson(event.detailsJson),
      created_at: iso(event.createdAt),
    })),
  };
}

function isJobSummaryKind(value: string): value is JobSummaryPayload["kind"] {
  return JOB_SUMMARY_KINDS.some((candidate) => candidate === value);
}

function isJobSummaryOperation(value: string): value is JobSummaryPayload["operation"] {
  return JOB_SUMMARY_OPERATIONS.some((candidate) => candidate === value);
}

function isJobSummaryStatus(value: string): value is JobSummaryPayload["status"] {
  return JOB_SUMMARY_STATUSES.some((candidate) => candidate === value);
}

/** Serialize one lightweight history row without touching stored JSON bodies. */
export function jobSummaryPayload(job: JobSummaryRecord): JobSummaryPayload {
  if (!isJobSummaryKind(job.kind)) throw new Error("Stored Job has an unsupported kind.");
  if (!isJobSummaryOperation(job.operation)) {
    throw new Error("Stored Job has an unsupported operation.");
  }
  if (!isJobSummaryStatus(job.status)) throw new Error("Stored Job has an unsupported status.");
  return {
    id: job.id,
    project_id: job.projectId,
    document_id: job.documentId,
    kind: job.kind,
    operation: job.operation,
    status: job.status,
    provider: job.provider,
    model: job.model,
    error: job.error,
    retry_of_job_id: job.retryOfJobId,
    created_at: iso(job.createdAt),
    updated_at: iso(job.updatedAt),
  };
}

/** The review-job result payload shared by the bridge and the retry path. */
export function reviewJobResultJson(assessment: {
  id: string;
  snapshotId: string;
  summary: string;
}): string {
  return dumpJson({
    review_id: assessment.id,
    snapshot_id: assessment.snapshotId,
    summary: assessment.summary,
  });
}

/** The export-job result payload shared by the bridge and the retry path. */
export function exportJobResultJson(
  projectId: string,
  artifact: { id: string; snapshotId: string; format: string },
): string {
  return dumpJson({
    export_id: artifact.id,
    snapshot_id: artifact.snapshotId,
    format: artifact.format,
    download_url:
      `/api/projects/${encodeURIComponent(projectId)}/exports/` +
      `${encodeURIComponent(artifact.id)}/download`,
  });
}

/** The lorebook alias envelope served by both alias surface verbs (#315). */
export function loreAliasPayload(aliases: readonly string[]): LoreAliasPayload {
  return { aliases: [...aliases] };
}

/** The lifecycle-status envelope answered by the lore-status write (#444). */
export function loreStatusPayload(status: LoreStatus): LoreStatusPayload {
  return { lore_status: status };
}

/**
 * One stored editorial assessment for the review LIST surface; identical to
 * the shape the review bridge lands in the job `result` JSON.
 */
export function reviewPayload(assessment: EditorialAssessment): ReviewPayload {
  return {
    id: assessment.id,
    project_id: assessment.projectId,
    snapshot_id: assessment.snapshotId,
    provider: assessment.provider,
    model: assessment.model,
    summary: assessment.summary,
    created_at: assessment.createdAt.toISOString(),
    issues: assessment.issues.map((issue) => ({
      id: issue.id,
      document_id: issue.documentId,
      // Store rows carry write-coerced severities; the payload declares the
      // closed read-compatible set from the review SSOT.
      severity: issue.severity as ReviewSeverity,
      code: issue.code,
      message: issue.message,
      suggestion: issue.suggestion,
      evidence: { ...issue.evidence },
    })),
  };
}

/** One immutable export artifact for the export catalog surface. */
export function exportArtifactPayload(
  artifact: ExportArtifactRecord,
  projectId: string,
): ExportArtifactPayload {
  return {
    id: artifact.id,
    project_id: artifact.projectId,
    snapshot_id: artifact.snapshotId,
    format: artifact.format,
    size_bytes: artifact.sizeBytes,
    checksum_sha256: artifact.checksumSha256,
    created_at: artifact.createdAt.toISOString(),
    download_url:
      `/api/projects/${encodeURIComponent(projectId)}/exports/` +
      `${encodeURIComponent(artifact.id)}/download`,
  };
}

/** The resolved beat association view shared by both chapter beat verbs. */
export function chapterBeatPayload(
  resolved: { title: string; content: string } | null,
): ChapterBeatPayload {
  return { beat: resolved === null ? null : { title: resolved.title, content: resolved.content } };
}
