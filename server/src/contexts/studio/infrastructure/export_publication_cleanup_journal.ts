import { eq } from "drizzle-orm";

import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import {
  exportArtifactNames,
  isExportArtifactFormat,
} from "../application/export_artifact_identity.js";
import { exportPublicationCleanupIntents } from "./db/schema.js";
import type { FileIdentity } from "./export_artifact_fs_support.js";
import {
  EXPORT_PUBLICATION_VERSION,
  type ExportPublicationManifest,
} from "./export_artifact_publication.js";

export type CleanupIntentRow = typeof exportPublicationCleanupIntents.$inferSelect;

export interface PublicationCleanupIntent {
  readonly manifest: ExportPublicationManifest;
  readonly stageIdentity: FileIdentity;
  readonly manifestIdentity: FileIdentity;
}

export interface ExportPublicationCleanupJournal {
  begin(intent: PublicationCleanupIntent): Promise<void>;
  complete(publicationId: string): Promise<void>;
}

export class DatabaseExportPublicationCleanupJournal implements ExportPublicationCleanupJournal {
  constructor(private readonly db: StudioSqliteDatabase) {}

  async begin(intent: PublicationCleanupIntent): Promise<void> {
    const { manifest } = intent;
    const existing = this.db
      .select()
      .from(exportPublicationCleanupIntents)
      .where(eq(exportPublicationCleanupIntents.publicationId, manifest.publication_id))
      .get();
    if (existing !== undefined) {
      assertCleanupIntentMatches(existing, intent);
      return;
    }
    this.db
      .insert(exportPublicationCleanupIntents)
      .values({
        publicationId: manifest.publication_id,
        artifactId: manifest.artifact_id,
        projectId: manifest.project_id,
        version: manifest.version,
        format: manifest.format,
        relativePath: manifest.relative_path,
        stageFile: manifest.stage_file,
        stageDevice: intent.stageIdentity.dev.toString(),
        stageInode: intent.stageIdentity.ino.toString(),
        manifestDevice: intent.manifestIdentity.dev.toString(),
        manifestInode: intent.manifestIdentity.ino.toString(),
        sizeBytes: manifest.size_bytes,
        checksumSha256: manifest.checksum_sha256,
        createdAt: new Date(),
      })
      .run();
  }

  async complete(publicationId: string): Promise<void> {
    this.db
      .delete(exportPublicationCleanupIntents)
      .where(eq(exportPublicationCleanupIntents.publicationId, publicationId))
      .run();
  }
}

export function loadCleanupIntents(db: StudioSqliteDatabase): CleanupIntentRow[] {
  const rows = db.select().from(exportPublicationCleanupIntents).all();
  for (const row of rows) cleanupIntentManifest(row);
  return rows;
}

export function cleanupIntentManifest(row: CleanupIntentRow): ExportPublicationManifest {
  if (
    row.version !== EXPORT_PUBLICATION_VERSION ||
    !safeId(row.publicationId) ||
    !safeId(row.artifactId) ||
    !safeId(row.projectId) ||
    !isExportArtifactFormat(row.format) ||
    row.relativePath !==
      exportArtifactNames(row.projectId, row.artifactId, row.format).relativePath ||
    row.stageFile !== `${row.artifactId}.${row.publicationId}.stage` ||
    !validBigint(row.stageDevice) ||
    !validBigint(row.stageInode) ||
    !validBigint(row.manifestDevice) ||
    !validBigint(row.manifestInode) ||
    !Number.isSafeInteger(row.sizeBytes) ||
    row.sizeBytes < 0 ||
    !/^[a-f0-9]{64}$/.test(row.checksumSha256)
  ) {
    throw new Error(`Invalid export publication cleanup intent: ${row.publicationId}`);
  }
  return {
    version: EXPORT_PUBLICATION_VERSION,
    publication_id: row.publicationId,
    artifact_id: row.artifactId,
    project_id: row.projectId,
    format: row.format,
    relative_path: row.relativePath,
    stage_file: row.stageFile,
    size_bytes: row.sizeBytes,
    checksum_sha256: row.checksumSha256,
  };
}

export function cleanupIntentOwnership(row: CleanupIntentRow): {
  readonly stage: FileIdentity;
  readonly manifest: FileIdentity;
} {
  cleanupIntentManifest(row);
  return {
    stage: { dev: BigInt(row.stageDevice), ino: BigInt(row.stageInode) },
    manifest: { dev: BigInt(row.manifestDevice), ino: BigInt(row.manifestInode) },
  };
}

export function assertCleanupIntentMatchesManifest(
  row: CleanupIntentRow,
  manifest: ExportPublicationManifest,
): void {
  const recorded = cleanupIntentManifest(row);
  if (
    recorded.version !== manifest.version ||
    recorded.publication_id !== manifest.publication_id ||
    recorded.artifact_id !== manifest.artifact_id ||
    recorded.project_id !== manifest.project_id ||
    recorded.format !== manifest.format ||
    recorded.relative_path !== manifest.relative_path ||
    recorded.stage_file !== manifest.stage_file ||
    recorded.size_bytes !== manifest.size_bytes ||
    recorded.checksum_sha256 !== manifest.checksum_sha256
  ) {
    throw new Error(`Export cleanup intent conflicts with manifest: ${manifest.publication_id}`);
  }
}

export function assertCleanupIntentMatches(
  row: CleanupIntentRow,
  intent: PublicationCleanupIntent,
): void {
  assertCleanupIntentMatchesManifest(row, intent.manifest);
  const recorded = cleanupIntentOwnership(row);
  if (
    recorded.stage.dev !== intent.stageIdentity.dev ||
    recorded.stage.ino !== intent.stageIdentity.ino ||
    recorded.manifest.dev !== intent.manifestIdentity.dev ||
    recorded.manifest.ino !== intent.manifestIdentity.ino
  ) {
    throw new Error(
      `Export cleanup intent conflicts with file identity: ${intent.manifest.publication_id}`,
    );
  }
}

function safeId(value: string): boolean {
  return /^[A-Za-z0-9_-]+$/.test(value);
}

function validBigint(value: string): boolean {
  return /^(0|[1-9][0-9]*)$/.test(value);
}
