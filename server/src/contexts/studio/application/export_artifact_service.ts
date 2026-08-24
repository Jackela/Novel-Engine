import { randomUUID } from "node:crypto";

import type { Principal } from "../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type {
  ExportArtifactFormat,
  ExportArtifactRecord,
  ExportStore,
} from "./ports/export_store.js";
import { type ProjectRecord, type ProjectScope, scopeForPrincipal } from "./ports/studio_store.js";

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
  /** Removes this publication after a later persistence failure, best-effort. */
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
  writeSnapshotArtifact(request: ArtifactWriteRequest): Promise<ArtifactFileEvidence>;
  readArtifactBytes(request: ArtifactReadRequest): Promise<Buffer>;
}

/** The existing project port supplies only the title needed by renderers. */
export interface ProjectTitleLookup {
  findProject(scope: ProjectScope, projectId: string): Pick<ProjectRecord, "title">;
}

export interface SnapshotArtifactServiceOptions {
  readonly now?: (() => Date) | undefined;
  readonly newId?: (() => string) | undefined;
}

/**
 * Turns immutable export snapshots into files. Snapshot reuse and artifact
 * records remain owned by ExportStore; this service never creates jobs.
 */
export class SnapshotArtifactService {
  private readonly now: () => Date;
  private readonly newId: () => string;

  constructor(
    private readonly exportStore: ExportStore,
    private readonly projectTitles: ProjectTitleLookup,
    private readonly artifactGateway: ExportArtifactGateway,
    options: SnapshotArtifactServiceOptions = {},
  ) {
    this.now = options.now ?? (() => new Date());
    this.newId = options.newId ?? randomUUID;
  }

  async materializeSnapshotArtifact(
    principal: Principal,
    projectId: string,
    format: ExportArtifactFormat,
  ): Promise<ExportArtifactRecord> {
    const scope = scopeForPrincipal(principal);
    const project = this.projectTitles.findProject(scope, projectId);
    const createdAt = this.now();
    const snapshot = this.exportStore.materializeArtifactSnapshot(scope, projectId, createdAt);
    const chapters = snapshot.documents
      .filter((document) => document.kind === "chapter")
      .map((document) => ({ title: document.title, contentMarkdown: document.contentMarkdown }));
    if (chapters.length === 0) {
      throw new InvalidOperationError("A project needs at least one chapter before export.");
    }
    const id = this.newId();
    const file = await this.artifactGateway.writeSnapshotArtifact({
      projectId,
      artifactId: id,
      format,
      projectTitle: project.title,
      chapters,
    });
    try {
      return this.exportStore.appendArtifact(scope, projectId, {
        id,
        snapshotId: snapshot.snapshotId,
        format,
        relativePath: file.relativePath,
        sizeBytes: file.sizeBytes,
        checksumSha256: file.checksumSha256,
        createdAt,
      });
    } catch (error) {
      await rollbackWithoutMasking(file);
      throw error;
    }
  }

  catalogProjectArtifacts(principal: Principal, projectId: string): ExportArtifactRecord[] {
    return this.exportStore.listProjectArtifacts(scopeForPrincipal(principal), projectId);
  }

  async readArtifactBytes(
    principal: Principal,
    projectId: string,
    artifactId: string,
  ): Promise<Buffer> {
    const artifact = this.exportStore.findProjectArtifact(
      scopeForPrincipal(principal),
      projectId,
      artifactId,
    );
    return this.artifactGateway.readArtifactBytes({
      projectId,
      artifactId,
      format: artifact.format,
      relativePath: artifact.relativePath,
      sizeBytes: artifact.sizeBytes,
      checksumSha256: artifact.checksumSha256,
    });
  }
}

async function rollbackWithoutMasking(file: ArtifactFileEvidence): Promise<void> {
  try {
    await file.rollback();
  } catch {
    return;
  }
}
