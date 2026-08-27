import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type {
  DocumentMatchRecord,
  DocumentWithCurrent,
  JobRecord,
  RevisionRecord,
} from "./ports/studio_store.js";
import type { VolumeRecord } from "./ports/volume_store.js";

/** Mirror of the Python authority's \b[\w'-]+\b word counter (UNICODE-aware). */
export function wordCount(markdown: string): number {
  return markdown.match(/[\p{L}\p{N}_'-]+/gu)?.length ?? 0;
}

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
): Record<string, unknown> {
  const payload: Record<string, unknown> = {
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

export function documentPayload(document: DocumentWithCurrent): Record<string, unknown> {
  const revision = document.currentRevision;
  if (revision === null) {
    throw new InvalidOperationError("Document has no current revision.");
  }
  return {
    id: document.id,
    project_id: document.projectId,
    kind: document.kind,
    title: document.title,
    position: document.position,
    volume_id: document.volumeId,
    beat_ref: document.beatRef,
    current_revision_id: revision.id,
    content_markdown: revision.contentMarkdown,
    metadata: safeLoadJson(revision.metadataJson),
    revision_source: revision.source,
    word_count: wordCount(revision.contentMarkdown),
    created_at: iso(document.createdAt),
    updated_at: iso(document.updatedAt),
  };
}

/** The ordered list-level volume shape handed to every HTTP surface. */
export function volumePayload(volume: VolumeRecord): Record<string, unknown> {
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
export function documentMatchPayload(match: DocumentMatchRecord): Record<string, unknown> {
  return {
    document_id: match.documentId,
    title: match.title,
    excerpt: match.excerpt,
  };
}

export function revisionPayload(revision: RevisionRecord): Record<string, unknown> {
  return {
    id: revision.id,
    document_id: revision.documentId,
    parent_revision_id: revision.parentRevisionId,
    revision_number: revision.revisionNumber,
    content_markdown: revision.contentMarkdown,
    metadata: safeLoadJson(revision.metadataJson),
    source: revision.source,
    word_count: wordCount(revision.contentMarkdown),
    created_at: iso(revision.createdAt),
  };
}

export function jobPayload(job: JobRecord): Record<string, unknown> {
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
