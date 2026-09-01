import { createHash, randomUUID } from "node:crypto";
import { constants } from "node:fs";
import { link, lstat, mkdir, open, realpath } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve, sep } from "node:path";

import type { ArtifactFileEvidence } from "../application/export_artifact_service.js";
import type { ExportArtifactFormat } from "../application/ports/export_store.js";
import {
  cleanupOwnedFile,
  cleanupPublicationSidecars,
  errorCode,
  type FileIdentity,
  syncDirectory,
} from "./export_artifact_fs_support.js";
import {
  cleanupFailedPublication,
  cleanupWithIntent,
} from "./export_artifact_publication_cleanup.js";
import { rollbackPublication } from "./export_artifact_rollback.js";
import type { ExportPublicationCleanupJournal } from "./export_publication_cleanup_journal.js";

export const EXPORT_PUBLICATION_VERSION = 1;

/** Durable recovery manifest retained until the outcome's file cleanup converges. */
export interface ExportPublicationManifest {
  readonly version: typeof EXPORT_PUBLICATION_VERSION;
  readonly publication_id: string;
  readonly artifact_id: string;
  readonly project_id: string;
  readonly format: ExportArtifactFormat;
  readonly relative_path: string;
  readonly stage_file: string;
  readonly size_bytes: number;
  readonly checksum_sha256: string;
}

export interface ArtifactPublicationInput {
  readonly projectDirectory: string;
  readonly target: string;
  readonly relativePath: string;
  readonly projectId: string;
  readonly artifactId: string;
  readonly format: ExportArtifactFormat;
  readonly contents: Buffer;
  readonly reportCleanupFailure?: ((failure: unknown) => void) | undefined;
  /** Deterministic publication/temporary ids used only by collision tests. */
  readonly newId?: (() => string) | undefined;
  /** Deterministic shared-staging race seam used only by filesystem tests. */
  readonly afterStagingReady?: (() => Promise<void>) | undefined;
  /** Deterministic race seam used only by filesystem rollback tests. */
  readonly afterRollbackQuarantine?:
    | ((quarantine: string, target: string) => Promise<void>)
    | undefined;
  readonly cleanupJournal?: ExportPublicationCleanupJournal | undefined;
}

/**
 * Publishes durable bytes plus a recovery manifest before database landing.
 * The stage hard-link remains until acknowledge(), making every crash window
 * recoverable from the database row as the commit marker.
 */
export async function publishArtifact(
  input: ArtifactPublicationInput,
): Promise<ArtifactFileEvidence> {
  const nextId = input.newId ?? randomUUID;
  const publicationId = safeId(nextId());
  const stagingDirectory = await durableStagingDirectory(input.projectDirectory);
  await input.afterStagingReady?.();
  const stageFile = `${input.artifactId}.${publicationId}.stage`;
  const manifestFile = `${input.artifactId}.${publicationId}.manifest.json`;
  const stage = resolve(stagingDirectory, stageFile);
  const manifest = resolve(stagingDirectory, manifestFile);
  const manifestTemporary = resolve(stagingDirectory, `.${manifestFile}.${safeId(nextId())}.tmp`);
  let finalLinked = false;
  let stageIdentity: FileIdentity | undefined;
  let manifestIdentity: FileIdentity | undefined;
  let manifestTemporaryIdentity: FileIdentity | undefined;
  let record: ExportPublicationManifest | undefined;
  let cleanupIntentRecorded = false;
  try {
    const writtenIdentity = await writeDurableFile(stage, input.contents, (identity) => {
      stageIdentity = identity;
    });
    const checksumSha256 = createHash("sha256").update(input.contents).digest("hex");
    const publicationRecord: ExportPublicationManifest = {
      version: EXPORT_PUBLICATION_VERSION,
      publication_id: publicationId,
      artifact_id: input.artifactId,
      project_id: input.projectId,
      format: input.format,
      relative_path: input.relativePath,
      stage_file: stageFile,
      size_bytes: input.contents.length,
      checksum_sha256: checksumSha256,
    };
    record = publicationRecord;
    const linkedManifestIdentity = await writeDurableManifest(
      manifestTemporary,
      manifest,
      publicationRecord,
      (identity) => {
        manifestTemporaryIdentity = identity;
      },
      (identity) => {
        manifestIdentity = identity;
      },
    );
    const cleanupIntent = {
      manifest: publicationRecord,
      stageIdentity: writtenIdentity,
      manifestIdentity: linkedManifestIdentity,
    };
    if (input.cleanupJournal !== undefined) {
      await input.cleanupJournal.begin(cleanupIntent);
      cleanupIntentRecorded = true;
    }
    await link(stage, input.target);
    finalLinked = true;
    await syncDirectory(input.projectDirectory);
    return {
      relativePath: input.relativePath,
      sizeBytes: input.contents.length,
      checksumSha256,
      acknowledge: () =>
        cleanupWithIntent(input.cleanupJournal, cleanupIntent, () =>
          cleanupPublicationSidecars(stage, manifest, stagingDirectory, {
            stage: writtenIdentity,
            manifest: linkedManifestIdentity,
          }),
        ),
      rollback: () =>
        cleanupWithIntent(input.cleanupJournal, cleanupIntent, () =>
          rollbackPublication(
            input.target,
            stage,
            manifest,
            stagingDirectory,
            input.contents,
            writtenIdentity.dev,
            writtenIdentity.ino,
            linkedManifestIdentity,
            input.afterRollbackQuarantine,
          ),
        ),
    };
  } catch (error) {
    await cleanupFailedPublication({
      target: input.target,
      projectDirectory: input.projectDirectory,
      stage,
      manifest,
      manifestTemporary,
      stagingDirectory,
      contents: input.contents,
      finalLinked,
      stageIdentity,
      manifestIdentity,
      manifestTemporaryIdentity,
      record,
      cleanupJournal: input.cleanupJournal,
      cleanupIntentRecorded,
      reportCleanupFailure: input.reportCleanupFailure,
      afterRollbackQuarantine: input.afterRollbackQuarantine,
    });
    throw error;
  }
}

async function durableStagingDirectory(projectDirectory: string): Promise<string> {
  const projectDetails = await lstat(projectDirectory);
  if (projectDetails.isSymbolicLink() || !projectDetails.isDirectory()) {
    throw new Error("Export project directory is not a real directory.");
  }
  const realProjectDirectory = await realpath(projectDirectory);
  const candidate = resolve(realProjectDirectory, ".staging");
  if (!isDescendant(realProjectDirectory, candidate)) {
    throw new Error("Export staging directory is outside the project root.");
  }
  let details: Awaited<ReturnType<typeof lstat>>;
  try {
    details = await lstat(candidate);
  } catch (error) {
    if (errorCode(error) !== "ENOENT") throw error;
    try {
      await mkdir(candidate);
    } catch (mkdirError) {
      if (errorCode(mkdirError) !== "EEXIST") throw mkdirError;
    }
    details = await lstat(candidate);
  }
  if (details.isSymbolicLink() || !details.isDirectory()) {
    throw new Error("Export staging path is not a real directory.");
  }
  const actual = await realpath(candidate);
  if (!isDescendant(realProjectDirectory, actual)) {
    throw new Error("Export staging directory escapes the project root.");
  }
  await syncDirectory(realProjectDirectory);
  return actual;
}

async function writeDurableFile(
  path: string,
  contents: Buffer,
  onCreated?: (identity: FileIdentity) => void,
): Promise<FileIdentity> {
  const handle = await open(path, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL);
  try {
    const details = await handle.stat({ bigint: true });
    const identity = { dev: details.dev, ino: details.ino };
    onCreated?.(identity);
    await handle.writeFile(contents);
    await handle.sync();
    return identity;
  } finally {
    await handle.close();
  }
}

async function writeDurableManifest(
  temporary: string,
  target: string,
  manifest: ExportPublicationManifest,
  onTemporaryCreated: (identity: FileIdentity) => void,
  onManifestLinked: (identity: FileIdentity) => void,
): Promise<FileIdentity> {
  const identity = await writeDurableFile(
    temporary,
    Buffer.from(`${JSON.stringify(manifest)}\n`, "utf8"),
    onTemporaryCreated,
  );
  await link(temporary, target);
  onManifestLinked(identity);
  await syncDirectory(dirname(target));
  await cleanupOwnedFile(temporary, identity);
  await syncDirectory(dirname(target));
  return identity;
}

function safeId(value: string): string {
  if (!/^[A-Za-z0-9_-]+$/.test(value)) throw new Error("Unsafe export publication id.");
  return value;
}

function isDescendant(root: string, candidate: string): boolean {
  const offset = relative(root, candidate);
  return offset !== "" && offset !== ".." && !offset.startsWith(`..${sep}`) && !isAbsolute(offset);
}
