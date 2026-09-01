import { randomUUID } from "node:crypto";

import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type {
  ExportArtifactFormat,
  ExportArtifactRecord,
  ExportCompletionRecord,
  ExportOutcomeStore,
  PreparedExportArtifact,
} from "./ports/export_store.js";
import { scopeForPrincipal } from "./ports/studio_store.js";

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

export interface SnapshotArtifactServiceOptions {
  readonly now?: (() => Date) | undefined;
  readonly newId?: (() => string) | undefined;
}

export interface ArtifactOutcomeOptions {
  readonly reportCleanupFailure?: ((failure: unknown) => void) | undefined;
}

interface PreparedPublication {
  readonly input: PreparedExportArtifact;
  readonly file: ArtifactFileEvidence;
}

/**
 * Renders one read-only export source, then delegates discoverable outcome
 * publication to the atomic export store. Filesystem compensation remains
 * here because SQLite cannot enlist the artifact file in its transaction.
 */
export class SnapshotArtifactService {
  private readonly now: () => Date;
  private readonly newId: () => string;

  constructor(
    private readonly exportStore: ExportOutcomeStore,
    private readonly artifactGateway: ExportArtifactGateway,
    options: SnapshotArtifactServiceOptions = {},
  ) {
    this.now = options.now ?? (() => new Date());
    this.newId = options.newId ?? randomUUID;
  }

  async recordCompletedExportJob(
    principal: Principal,
    projectId: string,
    format: ExportArtifactFormat,
    options: ArtifactOutcomeOptions = {},
  ): Promise<ExportCompletionRecord> {
    const scope = scopeForPrincipal(principal);
    const publication = await this.preparePublication(
      principal,
      projectId,
      format,
      options.reportCleanupFailure,
    );
    return this.landPublication(
      publication,
      (input) => this.exportStore.recordCompletedExportJob(scope, input),
      options.reportCleanupFailure,
    );
  }

  async completeExportRetryJob(
    principal: Principal,
    projectId: string,
    jobId: string,
    format: ExportArtifactFormat,
    options: ArtifactOutcomeOptions = {},
  ): Promise<ExportCompletionRecord> {
    const scope = scopeForPrincipal(principal);
    const publication = await this.preparePublication(
      principal,
      projectId,
      format,
      options.reportCleanupFailure,
    );
    return this.landPublication(
      publication,
      (input) => this.exportStore.completeExportRetryJob(scope, projectId, jobId, input),
      options.reportCleanupFailure,
    );
  }

  private async preparePublication(
    principal: Principal,
    projectId: string,
    format: ExportArtifactFormat,
    reportCleanupFailure?: (failure: unknown) => void,
  ): Promise<PreparedPublication> {
    const source = this.exportStore.readExportSource(
      scopeForPrincipal(principal),
      projectId,
      this.now(),
    );
    const chapters = source.documents
      .filter((document) => document.kind === "chapter")
      .map((document) => ({ title: document.title, contentMarkdown: document.contentMarkdown }));
    if (chapters.length === 0) {
      throw new InvalidOperationError("A project needs at least one chapter before export.");
    }
    const id = this.newId();
    const file = await this.artifactGateway.writeSnapshotArtifact(
      {
        projectId,
        artifactId: id,
        format,
        projectTitle: source.projectTitle,
        chapters,
      },
      reportCleanupFailure,
    );
    const createdAt = this.now();
    return {
      file,
      input: {
        source,
        id,
        format,
        relativePath: file.relativePath,
        sizeBytes: file.sizeBytes,
        checksumSha256: file.checksumSha256,
        createdAt,
      },
    };
  }

  catalogProjectArtifacts(principal: Principal, projectId: string): ExportArtifactRecord[] {
    return this.exportStore.listProjectArtifacts(scopeForPrincipal(principal), projectId);
  }

  async readArtifactForDelivery(
    principal: Principal,
    projectId: string,
    artifactId: string,
  ): Promise<{ format: ExportArtifactFormat; bytes: Buffer }> {
    const artifact = this.scopedArtifact(principal, projectId, artifactId);
    return {
      format: artifact.format,
      bytes: await this.readArtifactBytesForRecord(artifact),
    };
  }

  /** Compatibility-only internal buffer seam; HTTP delivery uses the typed result above. */
  async readArtifactBytes(
    principal: Principal,
    projectId: string,
    artifactId: string,
  ): Promise<Buffer> {
    return this.readArtifactBytesForRecord(this.scopedArtifact(principal, projectId, artifactId));
  }

  private scopedArtifact(
    principal: Principal,
    projectId: string,
    artifactId: string,
  ): ExportArtifactRecord {
    return this.exportStore.findProjectArtifact(
      scopeForPrincipal(principal),
      projectId,
      artifactId,
    );
  }

  private async landPublication<T>(
    publication: PreparedPublication,
    land: (input: PreparedExportArtifact) => T,
    reportCleanupFailure?: (failure: unknown) => void,
  ): Promise<T> {
    let result: T;
    try {
      result = land(publication.input);
    } catch (error) {
      await rollbackWithoutMasking(publication.file, reportCleanupFailure);
      throw error;
    }
    await acknowledgeWithoutMasking(publication.file, reportCleanupFailure);
    return result;
  }

  private readArtifactBytesForRecord(artifact: ExportArtifactRecord): Promise<Buffer> {
    return this.artifactGateway.readArtifactBytes({
      projectId: artifact.projectId,
      artifactId: artifact.id,
      format: artifact.format,
      relativePath: artifact.relativePath,
      sizeBytes: artifact.sizeBytes,
      checksumSha256: artifact.checksumSha256,
    });
  }
}

async function rollbackWithoutMasking(
  file: ArtifactFileEvidence,
  reportCleanupFailure?: (failure: unknown) => void,
): Promise<void> {
  try {
    await file.rollback();
  } catch (failure) {
    try {
      reportCleanupFailure?.(failure);
    } catch {
      // Cleanup reporting is secondary evidence and cannot replace the
      // transaction error that triggered compensation.
    }
  }
}

async function acknowledgeWithoutMasking(
  file: ArtifactFileEvidence,
  reportCleanupFailure?: (failure: unknown) => void,
): Promise<void> {
  try {
    await file.acknowledge();
  } catch (failure) {
    try {
      reportCleanupFailure?.(failure);
    } catch {
      // The database already committed. Sidecar cleanup is recoverable startup
      // work and must not turn a completed outcome into a failed response.
    }
  }
}
