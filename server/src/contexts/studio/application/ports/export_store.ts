import type { ExportArtifactFormat } from "../export_artifact_identity.js";
import type { JobRecord } from "./job_records.js";
import type { ProjectScope } from "./studio_store.js";

export type { ExportArtifactFormat } from "../export_artifact_identity.js";

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

/** The validated row budget of one bounded export catalog page. */
export type ExportPageLimit = number & { readonly __exportPageLimit: unique symbol };

/** Inclusive application/store boundary for one page of the catalog. */
export const MIN_EXPORT_PAGE_LIMIT = 1;
export const MAX_EXPORT_PAGE_LIMIT = 100;

/** Validate and narrow a transport/application number before persistence. */
export function exportPageLimit(value: number): ExportPageLimit {
  if (!Number.isInteger(value) || value < MIN_EXPORT_PAGE_LIMIT || value > MAX_EXPORT_PAGE_LIMIT) {
    throw new RangeError(
      `Export page limit must be an integer from ${MIN_EXPORT_PAGE_LIMIT} through ${MAX_EXPORT_PAGE_LIMIT}.`,
    );
  }
  return value as ExportPageLimit;
}

/** Persistence-neutral exclusive position in `(created_at DESC, id DESC)` order. */
export interface ExportPageCursor {
  readonly createdAtMs: number;
  readonly id: string;
}

/** One typed keyset request; the first page omits its exclusive cursor. */
export interface ExportPageInput {
  readonly limit: ExportPageLimit;
  readonly cursor?: ExportPageCursor | undefined;
}

/** One bounded catalog page and the exclusive position required to continue it. */
export interface ExportArtifactPage {
  readonly artifacts: ExportArtifactRecord[];
  readonly nextCursor: ExportPageCursor | null;
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
  listProjectArtifacts(
    scope: ProjectScope,
    projectId: string,
    input: ExportPageInput,
  ): ExportArtifactPage;
  findProjectArtifact(
    scope: ProjectScope,
    projectId: string,
    artifactId: string,
  ): ExportArtifactRecord;
}
