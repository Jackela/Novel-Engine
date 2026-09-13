// Publication stages extracted from export_artifact_publication.ts. Together
// they implement the publishArtifact contract documented there: stage durable
// artifact and manifest bytes, hard-link the final file, and on any failure
// compensate exactly the side effects already performed (tracked on the shared
// PreparedArtifactPublication progress fields) so crash recovery stays
// anchored to the durable recovery manifest.
import { createHash, randomUUID } from "node:crypto";
import { link } from "node:fs/promises";
import { resolve } from "node:path";

import type { ArtifactFileEvidence } from "../application/ports/artifact_gateway.js";
import {
  assertArtifactDescriptorSize,
  durableStagingDirectory,
  encodeManifest,
  safeId,
  writeDurableFile,
  writeDurableManifest,
} from "./export_artifact_durable_files.js";
import {
  cleanupPublicationSidecars,
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
