import { rmdir } from "node:fs/promises";

import { exportArtifactFilename } from "../application/export_artifact_identity.js";
import { cleanupOwnedFile, syncDirectory } from "./export_artifact_fs_support.js";
import type { ExportPublicationManifest } from "./export_artifact_publication.js";
import {
  assertCleanupIntentMatches,
  assertCleanupIntentMatchesManifest,
  type CleanupIntentRow,
  cleanupIntentManifest,
  cleanupIntentOwnership,
  type ExportPublicationCleanupJournal,
  type PublicationCleanupIntent,
} from "./export_publication_cleanup_journal.js";
import { readManifestEvidence } from "./export_publication_manifest_evidence.js";
import {
  readRecoveryStagingEntries,
  stageArtifactId,
} from "./export_publication_recovery_entries.js";
import {
  type ArtifactRow,
  type CleanupFileOwnership,
  type MutableRecoveryReport,
  matchingFileIdentity,
  ownedPublicationIdentity,
  preflightManifestRecovery,
  reconcileManifest,
  requireEvidence,
  restoreOrVerifyFinal,
} from "./export_publication_recovery_support.js";

export interface FinalQuarantine {
  readonly path: string;
  readonly finalName: string;
}

interface ReplayManifest {
  readonly record: ExportPublicationManifest;
  path?: string;
  identity?: { dev: bigint; ino: bigint };
  cleanupIntent?: CleanupIntentRow;
}

export async function removeOwnedFinalQuarantines(
  staging: string,
  projectDirectory: string,
  projectId: string,
  quarantines: readonly FinalQuarantine[],
  canonicalFiles: ReadonlySet<string>,
  intents: ReadonlyMap<string, CleanupIntentRow>,
  journal: ExportPublicationCleanupJournal,
  report: MutableRecoveryReport,
): Promise<void> {
  if (quarantines.length === 0) return;
  const entries = await readRecoveryStagingEntries(staging, projectId);
  const publications = replayManifests(entries.manifests, intents);
  const removals: Array<{
    path: string;
    identity: { dev: bigint; ino: bigint };
    intent: PublicationCleanupIntent;
  }> = [];
  for (const quarantine of quarantines) {
    if (canonicalFiles.has(quarantine.finalName)) {
      throw new Error(`Ambiguous export cleanup quarantine: ${quarantine.finalName}`);
    }
    const matching: Array<{
      identity: { dev: bigint; ino: bigint };
      intent: PublicationCleanupIntent;
    }> = [];
    for (const publication of publications.values()) {
      if (publication.cleanupIntent === undefined) continue;
      const { record } = publication;
      if (exportArtifactFilename(record.artifact_id, record.format) !== quarantine.finalName)
        continue;
      const stage = entries.stages.get(record.stage_file);
      if (stage === undefined) continue;
      const identity = await ownedPublicationIdentity(
        stage.path,
        quarantine.path,
        record.size_bytes,
        record.checksum_sha256,
      );
      if (identity === undefined) continue;
      const manifestIdentity =
        publication.identity ??
        (publication.cleanupIntent === undefined
          ? undefined
          : cleanupIntentOwnership(publication.cleanupIntent).manifest);
      if (manifestIdentity === undefined) continue;
      const intent = { manifest: record, stageIdentity: identity, manifestIdentity };
      if (publication.cleanupIntent !== undefined) {
        assertCleanupIntentMatches(publication.cleanupIntent, intent);
      }
      matching.push({ identity, intent });
    }
    if (matching.length !== 1 || matching[0] === undefined) {
      throw new Error(`Ambiguous export final quarantine: ${quarantine.finalName}`);
    }
    removals.push({ path: quarantine.path, ...matching[0] });
  }
  for (const removal of removals) await journal.begin(removal.intent);
  for (const removal of removals) {
    await cleanupOwnedFile(removal.path, removal.identity);
    report.orphanFilesRemoved += 1;
  }
  await syncDirectory(projectDirectory);
}

export async function reconcileStaging(
  staging: string,
  projectDirectory: string,
  projectId: string,
  artifacts: Map<string, ArtifactRow>,
  intents: Map<string, CleanupIntentRow>,
  journal: ExportPublicationCleanupJournal,
  report: MutableRecoveryReport,
): Promise<void> {
  const entries = await readRecoveryStagingEntries(staging, projectId);
  const manifests = replayManifests(entries.manifests, intents);
  const temporaryByManifest = new Map<
    string,
    Array<{ path: string; identity: { dev: bigint; ino: bigint } }>
  >();
  for (const temporary of entries.temporary) {
    if (temporary.manifestName === undefined) unproven(temporary.path);
    const current = manifests.get(temporary.manifestName);
    if (current === undefined) {
      unproven(temporary.path);
    }
    if (current.path === undefined) {
      if (current.cleanupIntent === undefined) unproven(temporary.path);
      const cleanupIntent = current.cleanupIntent;
      const evidence = await readManifestEvidence(
        temporary.path,
        temporary.manifestName,
        projectId,
      );
      assertManifestEqual(current.record, evidence.record);
      assertManifestIdentity(cleanupIntent, evidence.identity);
      manifests.set(temporary.manifestName, {
        record: evidence.record,
        path: temporary.path,
        identity: evidence.identity,
        cleanupIntent,
      });
      continue;
    }
    const identity = await matchingFileIdentity(temporary.path, current.path);
    if (identity === undefined) unproven(temporary.path);
    assertManifestIdentity(current.cleanupIntent, identity);
    temporaryByManifest.set(temporary.manifestName, [
      ...(temporaryByManifest.get(temporary.manifestName) ?? []),
      { path: temporary.path, identity },
    ]);
  }
  const handledStages = new Set([...manifests.values()].map(({ record }) => record.stage_file));
  for (const [name, stage] of entries.stages) {
    if (handledStages.has(name)) continue;
    const artifact = artifacts.get(stageArtifactId(name) ?? "");
    if (artifact === undefined) unproven(name);
    await requireEvidence(stage.path, artifact);
  }
  for (const manifest of manifests.values()) {
    await preflightManifestRecovery(
      manifest.identity,
      cleanupOwnership(manifest.cleanupIntent),
      entries.stages.get(manifest.record.stage_file)?.path,
      projectDirectory,
      manifest.record,
      artifacts.get(manifest.record.artifact_id),
    );
  }
  for (const [manifestName, manifest] of manifests) {
    const artifact = artifacts.get(manifest.record.artifact_id);
    for (const temporary of temporaryByManifest.get(manifestName) ?? []) {
      await cleanupOwnedFile(temporary.path, temporary.identity);
      report.sidecarsRemoved += 1;
    }
    const cleanupIntentUsed = await reconcileManifest(
      manifest.path,
      manifest.identity,
      cleanupOwnership(manifest.cleanupIntent),
      entries.stages.get(manifest.record.stage_file)?.path,
      projectDirectory,
      manifest.record,
      artifact,
      report,
    );
    if (cleanupIntentUsed) await journal.complete(manifest.record.publication_id);
  }
  for (const [name, stage] of entries.stages) {
    if (handledStages.has(name)) continue;
    const artifact = artifacts.get(stageArtifactId(name) ?? "");
    if (artifact === undefined) throw new Error(`Missing committed export for stage: ${name}`);
    const identity = await restoreOrVerifyFinal(stage.path, projectDirectory, artifact, report);
    await cleanupOwnedFile(stage.path, identity);
    report.sidecarsRemoved += 1;
  }
  await syncDirectory(staging);
  await rmdir(staging);
  await syncDirectory(projectDirectory);
}

function replayManifests(
  parsed: Awaited<ReturnType<typeof readRecoveryStagingEntries>>["manifests"],
  intents: ReadonlyMap<string, CleanupIntentRow>,
): Map<string, ReplayManifest> {
  const result = new Map<string, ReplayManifest>();
  for (const [name, manifest] of parsed) {
    result.set(name, {
      record: manifest.evidence.record,
      path: manifest.path,
      identity: manifest.evidence.identity,
    });
  }
  for (const row of intents.values()) {
    const record = cleanupIntentManifest(row);
    const name = manifestFilename(record);
    const current = result.get(name);
    if (current === undefined) {
      result.set(name, { record, cleanupIntent: row });
    } else {
      assertCleanupIntentMatchesManifest(row, current.record);
      assertManifestIdentity(row, current.identity);
      current.cleanupIntent = row;
    }
  }
  return result;
}

function manifestFilename(manifest: ExportPublicationManifest): string {
  return `${manifest.artifact_id}.${manifest.publication_id}.manifest.json`;
}

function cleanupOwnership(row: CleanupIntentRow | undefined): CleanupFileOwnership | undefined {
  return row === undefined ? undefined : cleanupIntentOwnership(row);
}

function assertManifestIdentity(
  row: CleanupIntentRow | undefined,
  identity: { dev: bigint; ino: bigint } | undefined,
): void {
  if (row === undefined || identity === undefined) return;
  const expected = cleanupIntentOwnership(row).manifest;
  if (identity.dev !== expected.dev || identity.ino !== expected.ino) {
    throw new Error(`Export cleanup manifest identity was replaced: ${row.publicationId}`);
  }
}

function assertManifestEqual(
  expected: ExportPublicationManifest,
  actual: ExportPublicationManifest,
): void {
  if (JSON.stringify(expected) !== JSON.stringify(actual)) {
    throw new Error(`Export cleanup intent conflicts with manifest: ${actual.publication_id}`);
  }
}

function unproven(path: string): never {
  throw new Error(`Unproven export staging file requires operator recovery: ${path}`);
}
