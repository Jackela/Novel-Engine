import type { ProjectScope } from "./studio_store.js";

export type ExportArtifactFormat = "markdown" | "docx" | "epub";

/** One immutable document/revision pair read from an export snapshot. */
export interface ExportSnapshotDocument {
  snapshotDocumentId: string;
  documentId: string;
  revisionId: string;
  kind: string;
  title: string;
  contentMarkdown: string;
  metadataJson: string;
  position: number;
}

/** The immutable document set from which a later artifact will be rendered. */
export interface ExportSnapshotMaterialization {
  snapshotId: string;
  documents: readonly ExportSnapshotDocument[];
}

/** A persisted artifact whose file is managed by a later application service. */
export interface ExportArtifactRecord {
  id: string;
  projectId: string;
  snapshotId: string;
  format: ExportArtifactFormat;
  relativePath: string;
  sizeBytes: number;
  checksumSha256: string;
  createdAt: Date;
}

/** The service supplies the generated artifact id and post-write integrity evidence. */
export interface AppendArtifactInput {
  id: string;
  snapshotId: string;
  format: ExportArtifactFormat;
  relativePath: string;
  sizeBytes: number;
  checksumSha256: string;
  createdAt: Date;
}

/** Persistence boundary for immutable export snapshots and artifact records. */
export interface ExportStore {
  materializeArtifactSnapshot(
    scope: ProjectScope,
    projectId: string,
    now: Date,
  ): ExportSnapshotMaterialization;
  appendArtifact(
    scope: ProjectScope,
    projectId: string,
    input: AppendArtifactInput,
  ): ExportArtifactRecord;
  listProjectArtifacts(scope: ProjectScope, projectId: string): ExportArtifactRecord[];
  findProjectArtifact(
    scope: ProjectScope,
    projectId: string,
    artifactId: string,
  ): ExportArtifactRecord;
}
