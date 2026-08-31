import type { JobRecord } from "./job_records.js";
import type { ProjectScope } from "./studio_store.js";

export type ExportArtifactFormat = "markdown" | "docx" | "epub";

/** One ordered document/revision payload captured without durable writes. */
export interface ExportSourceDocument {
  readonly documentId: string;
  readonly revisionId: string;
  readonly kind: string;
  readonly title: string;
  readonly contentMarkdown: string;
  readonly metadataJson: string;
  readonly position: number;
}

/** The exact point-in-time projection rendered by one export attempt. */
export interface ExportSource {
  readonly projectId: string;
  readonly projectTitle: string;
  readonly capturedAt: Date;
  readonly reuseSnapshotId: string | null;
  readonly documents: readonly ExportSourceDocument[];
}

/** A persisted artifact whose file is managed by the application layer. */
export interface ExportArtifactRecord {
  readonly id: string;
  readonly projectId: string;
  readonly snapshotId: string;
  readonly format: ExportArtifactFormat;
  readonly relativePath: string;
  readonly sizeBytes: number;
  readonly checksumSha256: string;
  readonly createdAt: Date;
}

/** File evidence plus the captured source needed for one database landing. */
export interface PreparedExportArtifact {
  readonly source: ExportSource;
  readonly id: string;
  readonly format: ExportArtifactFormat;
  readonly relativePath: string;
  readonly sizeBytes: number;
  readonly checksumSha256: string;
  readonly createdAt: Date;
}

/** One completed export outcome returned from its atomic database command. */
export interface ExportCompletionRecord {
  readonly artifact: ExportArtifactRecord;
  readonly job: JobRecord;
}

/**
 * Deep persistence interface for read-only export capture and atomic evidence
 * landing. Rendering stays outside SQLite; all discoverable evidence does not.
 */
export interface ExportOutcomeStore {
  readExportSource(scope: ProjectScope, projectId: string, capturedAt: Date): ExportSource;
  recordCompletedExportJob(
    scope: ProjectScope,
    input: PreparedExportArtifact,
  ): ExportCompletionRecord;
  completeExportRetryJob(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    input: PreparedExportArtifact,
  ): ExportCompletionRecord;
  listProjectArtifacts(scope: ProjectScope, projectId: string): ExportArtifactRecord[];
  findProjectArtifact(
    scope: ProjectScope,
    projectId: string,
    artifactId: string,
  ): ExportArtifactRecord;
}
