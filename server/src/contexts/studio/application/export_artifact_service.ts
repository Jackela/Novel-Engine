import { randomUUID } from "node:crypto";

import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { EXPORT_CAPACITY_LIMITS, ExportCapacityExceededError } from "../domain/exceptions.js";
import { ArtifactDownloadCapacity } from "./artifact_download_capacity.js";
import { ExportRendererGuard } from "./export_renderer_guard.js";
import type {
  ExportArtifactFormat,
  ExportArtifactPage,
  ExportArtifactRecord,
  ExportCompletionRecord,
  ExportOutcomeStore,
  ExportPageInput,
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
  readonly rendererGuard?: ExportRendererGuard | undefined;
  readonly downloadCapacity?: ArtifactDownloadCapacity | undefined;
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
  private readonly rendererGuard: ExportRendererGuard;
  private readonly downloadCapacity: ArtifactDownloadCapacity;

  constructor(
    private readonly exportStore: ExportOutcomeStore,
    private readonly artifactGateway: ExportArtifactGateway,
    options: SnapshotArtifactServiceOptions = {},
  ) {
    this.now = options.now ?? (() => new Date());
    this.newId = options.newId ?? randomUUID;
    this.rendererGuard = options.rendererGuard ?? new ExportRendererGuard();
    this.downloadCapacity = options.downloadCapacity ?? new ArtifactDownloadCapacity();
  }

  async recordCompletedExportJob(
    principal: Principal,
    projectId: string,
    format: ExportArtifactFormat,
    options: ArtifactOutcomeOptions = {},
  ): Promise<ExportCompletionRecord> {
    return this.withRendererPermit(projectId, () =>
      this.recordCompletedExportJobWithPermit(principal, projectId, format, options),
    );
  }

  private async recordCompletedExportJobWithPermit(
    principal: Principal,
    projectId: string,
    format: ExportArtifactFormat,
    options: ArtifactOutcomeOptions,
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

  async withRendererPermit<T>(projectId: string, work: () => Promise<T>): Promise<T> {
    const permit = this.rendererGuard.acquire(projectId);
    try {
      return await work();
    } finally {
      permit.release();
    }
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

  catalogProjectArtifacts(
    principal: Principal,
    projectId: string,
    input: ExportPageInput,
  ): ExportArtifactPage {
    return this.exportStore.listProjectArtifacts(scopeForPrincipal(principal), projectId, input);
  }

  async withArtifactDelivery<T>(
    principal: Principal,
    projectId: string,
    artifactId: string,
    consume: (artifact: { format: ExportArtifactFormat; bytes: Buffer }) => Promise<T>,
  ): Promise<T> {
    const artifact = this.scopedArtifact(principal, projectId, artifactId);
    const artifactLimit = EXPORT_CAPACITY_LIMITS.artifact_bytes;
    if (artifact.sizeBytes > artifactLimit) {
      throw new ExportCapacityExceededError("artifact_bytes", artifactLimit, artifact.sizeBytes);
    }
    const permit = this.downloadCapacity.acquire(projectId, artifact.sizeBytes);
    try {
      return await consume({
        format: artifact.format,
        bytes: await this.readArtifactBytesForRecord(artifact),
      });
    } finally {
      permit.release();
    }
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
