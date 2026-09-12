/**
 * Export artifact orchestration contract: render one read-only export
 * source, write the artifact file through the artifact gateway, then
 * publish the discoverable outcome through the atomic export store.
 * Filesystem compensation stays in this layer because SQLite cannot
 * enlist the artifact file in its transaction.
 */

import { randomUUID } from "node:crypto";

import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { EXPORT_CAPACITY_LIMITS, ExportCapacityExceededError } from "../domain/exceptions.js";
import { ArtifactDownloadCapacity } from "./artifact_download_capacity.js";
import { ExportRendererGuard } from "./export_renderer_guard.js";
import type { ArtifactFileEvidence, ExportArtifactGateway } from "./ports/artifact_gateway.js";
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

  /**
   * Renders the current export source and lands it as a new completed export
   * job while holding the single app-wide renderer permit for the whole
   * attempt. Capacity failures are permanent: bounded rendering throws
   * ExportCapacityExceededError (HTTP 422) and a busy renderer throws
   * OperationCapacityExceededError (HTTP 503, retry-after). The store record
   * lands only after the artifact file is durable; a persistence failure rolls
   * the file back without masking the store error.
   */
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

  /**
   * Runs `work` while holding the one renderer permit shared per app
   * instance; the permit is always released, including when `work` rejects.
   * Throws OperationCapacityExceededError (HTTP 503, retry-after) when
   * another export render already owns the permit.
   */
  async withRendererPermit<T>(projectId: string, work: () => Promise<T>): Promise<T> {
    const permit = this.rendererGuard.acquire(projectId);
    try {
      return await work();
    } finally {
      permit.release();
    }
  }

  /**
   * Renders the current export source and completes one already-claimed retry
   * job with the published artifact. Failure semantics mirror
   * recordCompletedExportJob (permanent ExportCapacityExceededError 422, file
   * rollback without masking the store error) except no renderer permit is
   * taken; the caller serializes retries against the job lifecycle.
   */
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

  /**
   * Reads one scope-checked artifact and hands its verified bytes to
   * `consume` under a byte-weighted download permit. Rejects with
   * ExportCapacityExceededError (HTTP 422) above
   * EXPORT_CAPACITY_LIMITS.artifact_bytes, and with
   * OperationCapacityExceededError (HTTP 503) when the app-local download
   * pool cannot reserve the artifact's bytes. The permit is held until
   * `consume` settles and always released.
   */
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
