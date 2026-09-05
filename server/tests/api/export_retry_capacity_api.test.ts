import { describe, expect, it } from "vitest";

import {
  EXPORT_CAPACITY_LIMITS,
  ExportCapacityExceededError,
} from "../../src/contexts/studio/domain/exceptions.js";
import {
  exports as exportArtifacts,
  projectSnapshots,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { jobEvents, jobs } from "../../src/shared/infrastructure/db/schema.js";
import { seedProjectWithChapter, studioDatabase } from "./job_test_helpers.js";
import { retryJobRequest } from "./retry_test_helpers.js";
import { buildStudioApp, monotonicClock, ownerJar } from "./studio_helpers.js";

class CapacityExportStore extends ExportStorePart {
  reads = 0;

  override readExportSource(): never {
    this.reads += 1;
    const limit = EXPORT_CAPACITY_LIMITS.source_bytes;
    throw new ExportCapacityExceededError("source_bytes", limit, limit + 99);
  }
}

describe("keyed export retry capacity API", () => {
  it("returns an identical 422 replay without adding work or evidence", async () => {
    let exportStore: CapacityExportStore | undefined;
    const clock = monotonicClock();
    const { app } = await buildStudioApp(clock, {
      exportStoreFactory: (database) => {
        exportStore = new CapacityExportStore(database);
        return exportStore;
      },
    });
    try {
      const owner = await ownerJar(app);
      const projectId = await seedProjectWithChapter(app, owner, "Capacity replay");
      const sourceId = "capacity-retry-source";
      const database = studioDatabase(app);
      database
        .insert(jobs)
        .values({
          id: sourceId,
          project_id: projectId,
          document_id: null,
          kind: "export",
          operation: "export",
          status: "interrupted",
          provider: "studio",
          model: "",
          request_json: '{"format":"markdown"}',
          result_json: "{}",
          error: "fixture interruption",
          created_at: clock(),
          updated_at: clock(),
        })
        .run();
      const url = `/api/projects/${projectId}/jobs/${sourceId}/retry`;
      const key = "capacity-http-replay-key-0001";

      const first = await retryJobRequest(app, owner, url, key);
      expect(first.statusCode, first.body).toBe(422);
      expect(first.json().error).toEqual({
        code: "EXPORT_CAPACITY_EXCEEDED",
        message: "Export capacity exceeded.",
        details: {
          resource: "source_bytes",
          limit: EXPORT_CAPACITY_LIMITS.source_bytes,
          observed: EXPORT_CAPACITY_LIMITS.source_bytes + 1,
        },
      });
      const jobsAfterFirst = database.select().from(jobs).all();
      const eventsAfterFirst = database.select().from(jobEvents).all();

      const replay = await retryJobRequest(app, owner, url, key);
      expect(replay.statusCode, replay.body).toBe(422);
      expect(replay.body).toBe(first.body);
      expect(exportStore?.reads).toBe(1);
      expect(database.select().from(jobs).all()).toEqual(jobsAfterFirst);
      expect(database.select().from(jobEvents).all()).toEqual(eventsAfterFirst);
      expect(eventsAfterFirst.map((event) => event.status)).toEqual(["running", "failed"]);
      expect(database.select().from(projectSnapshots).all()).toEqual([]);
      expect(database.select().from(snapshotDocuments).all()).toEqual([]);
      expect(database.select().from(exportArtifacts).all()).toEqual([]);
    } finally {
      await app.close();
    }
  });
});
