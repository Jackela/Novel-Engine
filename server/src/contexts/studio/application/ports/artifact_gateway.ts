import type { ExportArtifactFormat } from "./export_store.js";

/**
 * Filesystem boundary port for export artifacts. Implementations render
 * bounded snapshot chapters into durable files and read persisted bytes back
 * only for scope-checked records carrying integrity evidence; the write side
 * owns the acknowledge/rollback compensation protocol so callers never touch
 * artifact files directly.
 */

/** One frozen chapter handed to the file-format adapter in snapshot order. */
export interface ArtifactChapter {
  readonly title: string;
  readonly contentMarkdown: string;
}

/** Inputs for one atomic project-scoped artifact write. */
export interface ArtifactWriteRequest {
  readonly projectId: string;
  readonly artifactId: string;
  readonly format: ExportArtifactFormat;
  readonly projectTitle: string;
  readonly chapters: readonly ArtifactChapter[];
}

/** Integrity evidence returned only after the final file has been written. */
export interface ArtifactFileEvidence {
  readonly relativePath: string;
  readonly sizeBytes: number;
  readonly checksumSha256: string;
  /** Removes durable recovery sidecars after the database commit marker exists. */
  acknowledge(): Promise<void>;
  /** Removes this publication after a later persistence failure. */
  rollback(): Promise<void>;
}

/** The complete persisted evidence required for a safe artifact read. */
export interface ArtifactReadRequest {
  readonly projectId: string;
  readonly artifactId: string;
  readonly format: ExportArtifactFormat;
  readonly relativePath: string;
  readonly sizeBytes: number;
  readonly checksumSha256: string;
}

/** Filesystem boundary for rendering and safe retrieval of export artifacts. */
export interface ExportArtifactGateway {
  writeSnapshotArtifact(
    request: ArtifactWriteRequest,
    reportCleanupFailure?: (failure: unknown) => void,
  ): Promise<ArtifactFileEvidence>;
  readArtifactBytes(request: ArtifactReadRequest): Promise<Buffer>;
}
