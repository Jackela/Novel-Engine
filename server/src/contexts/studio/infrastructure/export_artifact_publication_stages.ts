// Publication stages extracted from export_artifact_publication.ts. Together
// they implement the publishArtifact contract documented there: stage durable
// artifact and manifest bytes, hard-link the final file, and on any failure
// compensate exactly the side effects already performed (tracked on the shared
// PreparedArtifactPublication progress fields) so crash recovery stays
// anchored to the durable recovery manifest.
import { createHash, randomUUID } from "node:crypto";
import { constants } from "node:fs";
import { link, lstat, mkdir, open, realpath } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve, sep } from "node:path";

import type { ArtifactFileEvidence } from "../application/ports/artifact_gateway.js";
import { EXPORT_CAPACITY_LIMITS, ExportCapacityExceededError } from "../domain/exceptions.js";
import {
  cleanupOwnedFile,
  cleanupPublicationSidecars,
  errorCode,
  type FileIdentity,
  syncDirectory,
} from "./export_artifact_fs_support.js";
import type {
  ArtifactPublicationInput,
  ExportPublicationManifest,
} from "./export_artifact_publication.js";

import {
  cleanupFailedPublication,
  cleanupWithIntent,
} from "./export_artifact_publication_cleanup.js";
import { type OwnedArtifactProof, rollbackPublication } from "./export_artifact_rollback.js";
import type { PublicationCleanupIntent } from "./export_publication_cleanup_journal.js";

export const EXPORT_PUBLICATION_VERSION = 1;

// Fully resolved publication plan (readonly fields) plus the mutable progress
// trackers shared by the staging, evidence, and compensation steps below.
interface PreparedArtifactPublication {
  readonly artifactSizeBytes: number;
  readonly checksumSha256: string;
  readonly publicationRecord: ExportPublicationManifest;
  readonly manifestContents: Buffer;
  readonly stagingDirectory: string;
  readonly stage: string;
  readonly manifest: string;
  readonly manifestTemporary: string;
  finalLinked: boolean;
  stageIdentity: FileIdentity | undefined;
  manifestIdentity: FileIdentity | undefined;
  manifestTemporaryIdentity: FileIdentity | undefined;
  record: ExportPublicationManifest | undefined;
  cleanupIntentRecorded: boolean;
}

// Durable staging outputs needed to build the returned evidence and its
// acknowledge/rollback closures.
interface StagedPublicationFiles {
  readonly writtenIdentity: FileIdentity;
  readonly linkedManifestIdentity: FileIdentity;
  readonly cleanupIntent: PublicationCleanupIntent;
  readonly artifactProof: OwnedArtifactProof;
}

// Step 1: assemble the manifest record and resolve every staging path before
// any staging I/O starts; failures here need no compensation.
export async function preparePublication(
  input: ArtifactPublicationInput,
): Promise<PreparedArtifactPublication> {
  const artifactSizeBytes = input.contents.length;
  const checksumSha256 = createHash("sha256").update(input.contents).digest("hex");
  assertArtifactDescriptorSize(artifactSizeBytes, artifactSizeBytes);
  const nextId = input.newId ?? randomUUID;
  const publicationId = safeId(nextId());
  const stageFile = `${input.artifactId}.${publicationId}.stage`;
  const manifestFile = `${input.artifactId}.${publicationId}.manifest.json`;
  const publicationRecord: ExportPublicationManifest = {
    version: EXPORT_PUBLICATION_VERSION,
    publication_id: publicationId,
    artifact_id: input.artifactId,
    project_id: input.projectId,
    format: input.format,
    relative_path: input.relativePath,
    stage_file: stageFile,
    size_bytes: artifactSizeBytes,
    checksum_sha256: checksumSha256,
  };
  const manifestContents = encodeManifest(publicationRecord);
  const manifestTemporaryId = safeId(nextId());
  const stagingDirectory = await durableStagingDirectory(input.projectDirectory);
  await input.afterStagingReady?.();
  const stage = resolve(stagingDirectory, stageFile);
  const manifest = resolve(stagingDirectory, manifestFile);
  const manifestTemporary = resolve(
    stagingDirectory,
    `.${manifestFile}.${manifestTemporaryId}.tmp`,
  );
  return {
    artifactSizeBytes,
    checksumSha256,
    publicationRecord,
    manifestContents,
    stagingDirectory,
    stage,
    manifest,
    manifestTemporary,
    finalLinked: false,
    stageIdentity: undefined,
    manifestIdentity: undefined,
    manifestTemporaryIdentity: undefined,
    record: undefined,
    cleanupIntentRecorded: false,
  };
}

// Step 2: durable stage and manifest writes, cleanup-journal begin, final
// hard-link; trackers record progress for failure compensation.
export async function stagePublicationFiles(
  input: ArtifactPublicationInput,
  prepared: PreparedArtifactPublication,
): Promise<StagedPublicationFiles> {
  const writtenIdentity = await writeDurableFile(
    prepared.stage,
    input.contents,
    (identity) => {
      prepared.stageIdentity = identity;
    },
    input.afterStageWrite,
  );
  prepared.record = prepared.publicationRecord;
  const linkedManifestIdentity = await writeDurableManifest(
    prepared.manifestTemporary,
    prepared.manifest,
    prepared.manifestContents,
    (identity) => {
      prepared.manifestTemporaryIdentity = identity;
    },
    (identity) => {
      prepared.manifestIdentity = identity;
    },
  );
  const cleanupIntent: PublicationCleanupIntent = {
    manifest: prepared.publicationRecord,
    stageIdentity: writtenIdentity,
    manifestIdentity: linkedManifestIdentity,
  };
  const artifactProof: OwnedArtifactProof = {
    dev: writtenIdentity.dev,
    ino: writtenIdentity.ino,
    sizeBytes: prepared.publicationRecord.size_bytes,
    checksumSha256: prepared.checksumSha256,
  };
  if (input.cleanupJournal !== undefined) {
    await input.cleanupJournal.begin(cleanupIntent);
    prepared.cleanupIntentRecorded = true;
  }
  await link(prepared.stage, input.target);
  prepared.finalLinked = true;
  await syncDirectory(input.projectDirectory);
  return { writtenIdentity, linkedManifestIdentity, cleanupIntent, artifactProof };
}

// Step 3: evidence whose acknowledge/rollback closures clean up the staged
// files and final link under the recorded cleanup intent.
export function buildPublicationEvidence(
  input: ArtifactPublicationInput,
  prepared: PreparedArtifactPublication,
  staged: StagedPublicationFiles,
): ArtifactFileEvidence {
  const { writtenIdentity, linkedManifestIdentity, cleanupIntent, artifactProof } = staged;
  return {
    relativePath: input.relativePath,
    sizeBytes: prepared.artifactSizeBytes,
    checksumSha256: prepared.checksumSha256,
    acknowledge: () =>
      cleanupWithIntent(input.cleanupJournal, cleanupIntent, () =>
        cleanupPublicationSidecars(prepared.stage, prepared.manifest, prepared.stagingDirectory, {
          stage: writtenIdentity,
          manifest: linkedManifestIdentity,
        }),
      ),
    rollback: () =>
      cleanupWithIntent(input.cleanupJournal, cleanupIntent, () =>
        rollbackPublication(
          input.target,
          prepared.stage,
          prepared.manifest,
          prepared.stagingDirectory,
          artifactProof,
          linkedManifestIdentity,
          input.afterRollbackQuarantine,
        ),
      ),
  };
}

// Step 4: failure compensation payload assembled from the progress trackers;
// the caller rethrows the original publication error afterwards.
export async function compensateFailedPublication(
  input: ArtifactPublicationInput,
  prepared: PreparedArtifactPublication,
): Promise<void> {
  await cleanupFailedPublication({
    target: input.target,
    projectDirectory: input.projectDirectory,
    stage: prepared.stage,
    manifest: prepared.manifest,
    manifestTemporary: prepared.manifestTemporary,
    stagingDirectory: prepared.stagingDirectory,
    artifactProof:
      prepared.stageIdentity === undefined
        ? {
            dev: 0n,
            ino: 0n,
            sizeBytes: prepared.artifactSizeBytes,
            checksumSha256: prepared.checksumSha256,
          }
        : {
            dev: prepared.stageIdentity.dev,
            ino: prepared.stageIdentity.ino,
            sizeBytes: prepared.artifactSizeBytes,
            checksumSha256: prepared.checksumSha256,
          },
    finalLinked: prepared.finalLinked,
    stageIdentity: prepared.stageIdentity,
    manifestIdentity: prepared.manifestIdentity,
    manifestTemporaryIdentity: prepared.manifestTemporaryIdentity,
    record: prepared.record,
    cleanupJournal: input.cleanupJournal,
    cleanupIntentRecorded: prepared.cleanupIntentRecorded,
    reportCleanupFailure: input.reportCleanupFailure,
    afterRollbackQuarantine: input.afterRollbackQuarantine,
  });
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
  afterWrite?: (path: string) => Promise<void>,
): Promise<FileIdentity> {
  const handle = await open(path, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL);
  try {
    const details = await handle.stat({ bigint: true });
    const identity = { dev: details.dev, ino: details.ino };
    onCreated?.(identity);
    await handle.writeFile(contents);
    await afterWrite?.(path);
    const written = await handle.stat();
    if (!written.isFile()) throw new Error("Export stage is not a regular file.");
    assertArtifactDescriptorSize(written.size, contents.length);
    await handle.sync();
    return identity;
  } finally {
    await handle.close();
  }
}

function assertArtifactDescriptorSize(observed: number, expected: number): void {
  const limit = EXPORT_CAPACITY_LIMITS.artifact_bytes;
  if (observed > limit) {
    throw new ExportCapacityExceededError("artifact_bytes", limit, observed);
  }
  if (observed !== expected) throw new Error("Export stage size changed during publication.");
}

async function writeDurableManifest(
  temporary: string,
  target: string,
  contents: Buffer,
  onTemporaryCreated: (identity: FileIdentity) => void,
  onManifestLinked: (identity: FileIdentity) => void,
): Promise<FileIdentity> {
  const identity = await writeDurableFile(temporary, contents, onTemporaryCreated);
  await link(temporary, target);
  onManifestLinked(identity);
  await syncDirectory(dirname(target));
  await cleanupOwnedFile(temporary, identity);
  await syncDirectory(dirname(target));
  return identity;
}

function encodeManifest(manifest: ExportPublicationManifest): Buffer {
  const contents = Buffer.from(`${JSON.stringify(manifest)}\n`, "utf8");
  const limit = EXPORT_CAPACITY_LIMITS.manifest_bytes;
  if (contents.length > limit) {
    throw new ExportCapacityExceededError("manifest_bytes", limit, contents.length);
  }
  return contents;
}

function safeId(value: string): string {
  if (!/^[A-Za-z0-9_-]+$/.test(value)) throw new Error("Unsafe export publication id.");
  return value;
}

function isDescendant(root: string, candidate: string): boolean {
  const offset = relative(root, candidate);
  return offset !== "" && offset !== ".." && !offset.startsWith(`..${sep}`) && !isAbsolute(offset);
}
