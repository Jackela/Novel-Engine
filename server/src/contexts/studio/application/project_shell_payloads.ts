import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type { DocumentKind } from "../domain/kinds.js";
import { assertStoredRevisionSource } from "../domain/revision_source.js";
import { assertStoredRevisionWordCount } from "../domain/revision_word_count.js";
import { asLoreStatus, isLoreEntryKind } from "./lorebook.js";
import type { DocumentSummaryPayload } from "./payload_schemas/document.js";
import type { ProjectShellPayload } from "./payload_schemas/project.js";
import { iso, type ProjectPayloadInput, projectPayload, volumePayload } from "./payloads.js";
import type { DocumentSummaryRecord, DocumentWithCurrent } from "./ports/studio_store.js";
import type { VolumeRecord } from "./ports/volume_store.js";

export function projectShellPayload(
  project: ProjectPayloadInput,
  documents: DocumentSummaryRecord[],
  volumes: VolumeRecord[],
): ProjectShellPayload {
  return {
    ...projectPayload(project),
    documents: documents.map(documentSummaryPayload),
    volumes: volumes.map(volumePayload),
  };
}

/** Reduce a complete accepted Document to the structural shell authority. */
export function summarizeDocument(document: DocumentWithCurrent): DocumentSummaryRecord {
  const revision = document.currentRevision;
  if (revision === null) {
    throw new InvalidOperationError("Document has no current revision.");
  }
  return {
    id: document.id,
    projectId: document.projectId,
    kind: document.kind,
    title: document.title,
    position: document.position,
    volumeId: document.volumeId,
    beatRef: document.beatRef,
    loreStatus: document.loreStatus,
    currentRevisionId: revision.id,
    revisionSource: assertStoredRevisionSource(revision.source),
    wordCount: assertStoredRevisionWordCount(revision.wordCount),
    createdAt: document.createdAt,
    updatedAt: document.updatedAt,
  };
}

export function documentSummaryPayload(document: DocumentSummaryRecord): DocumentSummaryPayload {
  return {
    id: document.id,
    project_id: document.projectId,
    kind: document.kind as DocumentKind,
    title: document.title,
    position: document.position,
    volume_id: document.volumeId,
    beat_ref: document.beatRef,
    lore_status: isLoreEntryKind(document.kind) ? asLoreStatus(document.loreStatus) : null,
    current_revision_id: document.currentRevisionId,
    revision_source: document.revisionSource,
    word_count: assertStoredRevisionWordCount(document.wordCount),
    created_at: iso(document.createdAt),
    updated_at: iso(document.updatedAt),
  };
}
