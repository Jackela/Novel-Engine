import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type {
  DocumentMatchRecord,
  DocumentWithCurrent,
  RevisionRecord,
} from "./ports/studio_store.js";

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
    current_revision_id: revision.id,
    content_markdown: revision.contentMarkdown,
    metadata: safeLoadJson(revision.metadataJson),
    revision_source: revision.source,
    word_count: wordCount(revision.contentMarkdown),
    created_at: iso(document.createdAt),
    updated_at: iso(document.updatedAt),
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
