import { createHash } from "node:crypto";
import { mkdir, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { exportArtifactExtension } from "../../src/contexts/studio/application/export_artifact_identity.js";
import type { ArtifactFileEvidence } from "../../src/contexts/studio/application/export_artifact_service.js";
import type { ExportArtifactFormat } from "../../src/contexts/studio/application/ports/export_store.js";
import {
  exports as exportArtifacts,
  projectSnapshots,
  projects,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { publishArtifact } from "../../src/contexts/studio/infrastructure/export_artifact_publication.js";
import { DatabaseExportPublicationCleanupJournal } from "../../src/contexts/studio/infrastructure/export_publication_cleanup_journal.js";
import { owners } from "../../src/shared/infrastructure/db/schema.js";
import {
  openStudioDatabase,
  type StudioDatabase,
} from "../../src/shared/infrastructure/db/startup.js";

export interface RecoveryHarness {
  directory: string;
  studio: StudioDatabase;
  projectId: string;
  snapshotId: string;
}

const harnesses: RecoveryHarness[] = [];
export const RECOVERY_NOW = new Date("2026-08-31T16:00:00.000Z");

export async function cleanupRecoveryHarnesses(): Promise<void> {
  for (const harness of harnesses.splice(0)) {
    harness.studio.close();
    await rm(harness.directory, { recursive: true });
  }
}

export async function openRecoveryHarness(): Promise<RecoveryHarness> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-export-recovery-"));
  const studio = await openStudioDatabase(directory);
  const projectId = "project-main";
  const snapshotId = "snapshot-main";
  studio.db
    .insert(owners)
    .values({
      id: "owner-main",
      username: "recovery-owner",
      password_hash: "test-only",
      created_at: RECOVERY_NOW,
    })
    .run();
  studio.db
    .insert(projects)
    .values({
      id: projectId,
      ownerId: "owner-main",
      title: "Recovery",
      description: "",
      settingsJson: "{}",
      importHash: null,
      createdAt: RECOVERY_NOW,
      updatedAt: RECOVERY_NOW,
    })
    .run();
  studio.db
    .insert(projectSnapshots)
    .values({ id: snapshotId, projectId, reason: "export", createdAt: RECOVERY_NOW })
    .run();
  const value = { directory, studio, projectId, snapshotId };
  harnesses.push(value);
  return value;
}

export function projectDirectory(value: RecoveryHarness): string {
  return join(value.directory, "exports", value.projectId);
}

export function finalPath(
  value: RecoveryHarness,
  artifactId: string,
  format: ExportArtifactFormat = "markdown",
): string {
  return join(projectDirectory(value), `${artifactId}.${exportArtifactExtension(format)}`);
}

export async function preparePublication(
  value: RecoveryHarness,
  artifactId: string,
  contents: Buffer,
  format: ExportArtifactFormat = "markdown",
  recordCleanupIntent = true,
): Promise<ArtifactFileEvidence> {
  const directory = projectDirectory(value);
  await mkdir(directory, { recursive: true });
  return publishArtifact({
    projectDirectory: directory,
    target: finalPath(value, artifactId, format),
    relativePath: `exports/${value.projectId}/${artifactId}.${exportArtifactExtension(format)}`,
    projectId: value.projectId,
    artifactId,
    format,
    contents,
    cleanupJournal: recordCleanupIntent
      ? new DatabaseExportPublicationCleanupJournal(value.studio.db)
      : undefined,
  });
}

export function addArtifact(
  value: RecoveryHarness,
  artifactId: string,
  evidence: Pick<ArtifactFileEvidence, "relativePath" | "sizeBytes" | "checksumSha256">,
  format: ExportArtifactFormat = "markdown",
): void {
  value.studio.db
    .insert(exportArtifacts)
    .values({
      id: artifactId,
      projectId: value.projectId,
      snapshotId: value.snapshotId,
      format,
      relativePath: evidence.relativePath,
      sizeBytes: evidence.sizeBytes,
      checksumSha256: evidence.checksumSha256,
      createdAt: RECOVERY_NOW,
    })
    .run();
}

export function directEvidence(value: RecoveryHarness, artifactId: string, bytes: Buffer) {
  return {
    relativePath: `exports/${value.projectId}/${artifactId}.md`,
    sizeBytes: bytes.length,
    checksumSha256: createHash("sha256").update(bytes).digest("hex"),
  };
}
