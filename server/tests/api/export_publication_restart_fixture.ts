import { join } from "node:path";
import { afterEach, expect } from "vitest";

import { type AppOptions, buildApp } from "../../src/apps/api/app.js";
import type {
  ArtifactFileEvidence,
  ExportArtifactGateway,
} from "../../src/contexts/studio/application/export_artifact_service.js";
import {
  exportPublicationCleanupIntents,
  exports as exportRecords,
  projectSnapshots,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { FilesystemExportArtifactGateway } from "../../src/contexts/studio/infrastructure/export_artifact_files.js";
import { DatabaseExportPublicationCleanupJournal } from "../../src/contexts/studio/infrastructure/export_publication_cleanup_journal.js";
import { DATABASE_FILENAME } from "../../src/shared/infrastructure/db/backup.js";
import {
  openConnection,
  type StudioSqliteDatabase,
} from "../../src/shared/infrastructure/db/connection.js";
import { jobEvents, jobs } from "../../src/shared/infrastructure/db/schema.js";
import { TEST_SESSION_SECRET } from "./auth_helpers.js";
import { studioDatabase } from "./job_test_helpers.js";
import { type CookieJar, call, ownerJar, seedProject } from "./studio_helpers.js";

const openApps: Array<Awaited<ReturnType<typeof buildApp>>> = [];

afterEach(async () => {
  while (openApps.length > 0) await openApps.pop()?.close();
});

export async function appAt(directory: string, options: Partial<AppOptions> = {}) {
  const app = await buildApp({
    logger: false,
    dataDirectory: directory,
    sessionSecret: TEST_SESSION_SECRET,
    ...options,
  });
  openApps.push(app);
  return app;
}

export async function closeTracked(app: Awaited<ReturnType<typeof buildApp>>): Promise<void> {
  const index = openApps.indexOf(app);
  if (index >= 0) openApps.splice(index, 1);
  await app.close();
}

export function seedRunningExportRetry(
  app: Awaited<ReturnType<typeof buildApp>>,
  projectId: string,
  prefix: string,
): string {
  const database = studioDatabase(app);
  const originalId = `${prefix}-original`;
  const retryId = `${prefix}-retry`;
  const now = new Date("2026-08-31T18:00:00.000Z");
  database
    .insert(jobs)
    .values([
      {
        id: originalId,
        project_id: projectId,
        document_id: null,
        kind: "export",
        operation: "export",
        status: "interrupted",
        provider: "studio",
        model: "",
        request_json: '{"format":"markdown"}',
        result_json: "{}",
        error: "previous restart",
        retry_of_job_id: null,
        created_at: now,
        updated_at: now,
        started_at: now,
        finished_at: now,
      },
      {
        id: retryId,
        project_id: projectId,
        document_id: null,
        kind: "export",
        operation: "export",
        status: "running",
        provider: "studio",
        model: "",
        request_json: '{"format":"markdown"}',
        result_json: "{}",
        error: null,
        retry_of_job_id: originalId,
        created_at: now,
        updated_at: now,
        started_at: now,
        finished_at: null,
      },
    ])
    .run();
  database
    .insert(jobEvents)
    .values({
      id: `${prefix}-running-event`,
      job_id: retryId,
      status: "running",
      details_json: "{}",
      created_at: now,
    })
    .run();
  return retryId;
}

export function auditEvidence(database: StudioSqliteDatabase) {
  const serialize = (rows: readonly unknown[]) => rows.map((row) => JSON.stringify(row)).sort();
  return {
    snapshots: serialize(database.select().from(projectSnapshots).all()),
    snapshotDocuments: serialize(database.select().from(snapshotDocuments).all()),
    artifacts: serialize(database.select().from(exportRecords).all()),
    cleanupIntents: serialize(database.select().from(exportPublicationCleanupIntents).all()),
    jobs: serialize(database.select().from(jobs).all()),
    events: serialize(database.select().from(jobEvents).all()),
  };
}

export function storedAuditEvidence(directory: string) {
  const connection = openConnection(join(directory, DATABASE_FILENAME));
  try {
    return auditEvidence(connection.db);
  } finally {
    connection.raw.close();
  }
}

interface UnacknowledgedExport {
  readonly app: Awaited<ReturnType<typeof buildApp>>;
  readonly owner: CookieJar;
  readonly projectId: string;
  readonly evidence: ArtifactFileEvidence;
  readonly downloadUrl: string;
}

export async function committedWithoutAcknowledgement(
  directory: string,
): Promise<UnacknowledgedExport> {
  const files = new FilesystemExportArtifactGateway(directory);
  let evidence: ArtifactFileEvidence | undefined;
  let app: Awaited<ReturnType<typeof buildApp>>;
  const gateway: ExportArtifactGateway = {
    async writeSnapshotArtifact(request, reportCleanupFailure) {
      evidence = await new FilesystemExportArtifactGateway(directory, {
        cleanupJournal: new DatabaseExportPublicationCleanupJournal(studioDatabase(app)),
      }).writeSnapshotArtifact(request, reportCleanupFailure);
      return { ...evidence, acknowledge: async () => undefined };
    },
    readArtifactBytes: (request) => files.readArtifactBytes(request),
  };
  app = await appAt(directory, { exportArtifactGateway: gateway });
  const owner = await ownerJar(app);
  const project = await seedProject(app, owner, "Durable committed export");
  const response = await call(app, owner, "POST", `/api/projects/${project.id}/exports`, {
    format: "markdown",
  });
  expect(response.statusCode, response.body).toBe(201);
  if (evidence === undefined) throw new Error("Expected captured artifact evidence.");
  return {
    app,
    owner,
    projectId: project.id,
    evidence,
    downloadUrl: response.json().result.download_url as string,
  };
}

export async function writeUncommittedPublication(
  directory: string,
  request: Parameters<ExportArtifactGateway["writeSnapshotArtifact"]>[0],
): Promise<ArtifactFileEvidence> {
  const connection = openConnection(join(directory, DATABASE_FILENAME));
  try {
    return await new FilesystemExportArtifactGateway(directory, {
      cleanupJournal: new DatabaseExportPublicationCleanupJournal(connection.db),
    }).writeSnapshotArtifact(request);
  } finally {
    connection.raw.close();
  }
}
