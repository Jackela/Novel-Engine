import { eq } from "drizzle-orm";
import type { FastifyInstance } from "fastify";
import { expect } from "vitest";

import {
  documentRevisions,
  documents,
  volumes,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { studioDatabase } from "./job_test_helpers.js";

/**
 * Raw-row population helpers for the structure-capacity contract tests
 * (#461): boundaries sit at thousands of rows, so tests seed the live
 * Studio database directly (the export-capacity test pattern) instead of
 * issuing thousands of HTTP calls.
 */
export function firstVolumeId(app: FastifyInstance, projectId: string): string {
  const row = studioDatabase(app)
    .select()
    .from(volumes)
    .where(eq(volumes.projectId, projectId))
    .orderBy(volumes.position)
    .get();
  if (row === undefined) throw new Error("expected a seeded default volume");
  return row.id;
}

/** Seed chapter documents plus their current revisions directly. */
let seedBatch = 0;

export function seedChapterRows(
  app: FastifyInstance,
  projectId: string,
  volumeId: string,
  count: number,
): void {
  seedBatch += 1;
  const tag = `${projectId.slice(0, 6)}-${seedBatch}`;
  const database = studioDatabase(app);
  const now = new Date();
  const documentRows: (typeof documents.$inferInsert)[] = [];
  const revisionRows: (typeof documentRevisions.$inferInsert)[] = [];
  for (let index = 0; index < count; index += 1) {
    const id = `capacity-document-${tag}-${index}`;
    const revisionId = `capacity-revision-${tag}-${index}`;
    documentRows.push({
      id,
      projectId,
      kind: "chapter",
      title: `Capacity ${tag} ${index}`,
      position: index + 2,
      volumeId,
      currentRevisionId: revisionId,
      createdAt: now,
      updatedAt: now,
    });
    revisionRows.push({
      id: revisionId,
      documentId: id,
      parentRevisionId: null,
      revisionNumber: 1,
      contentMarkdown: "capacity seed",
      metadataJson: "{}",
      source: "author",
      wordCount: 2,
      createdAt: now,
    });
  }
  database.transaction((tx) => {
    tx.insert(documents).values(documentRows).run();
    tx.insert(documentRevisions).values(revisionRows).run();
  });
  const seeded = studioDatabase(app)
    .select({ id: documents.id })
    .from(documents)
    .where(eq(documents.projectId, projectId))
    .all();
  expect(seeded.length).toBeGreaterThanOrEqual(count);
}
