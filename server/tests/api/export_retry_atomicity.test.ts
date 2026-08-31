import { readdir } from "node:fs/promises";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  exports as exportRecords,
  projectSnapshots,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { jobEvents, jobs } from "../../src/shared/infrastructure/db/schema.js";
import { seedProjectWithChapter, studioDatabase } from "./job_test_helpers.js";
import {
  buildStudioApp,
  call,
  type JobPayload,
  monotonicClock,
  ownerJar,
} from "./studio_helpers.js";

describe("export retry atomicity", () => {
  it("compensates the file and leaves the retry running when its completed event fails", async () => {
    class ExplodingRetryEventStore extends ExportStorePart {
      protected override beforeRetryEventInsert(): never {
        throw new Error("simulated retry completed-event failure");
      }
    }
    const clock = monotonicClock();
    const { app, directory } = await buildStudioApp(clock, {
      exportStoreFactory: (database) => new ExplodingRetryEventStore(database),
    });
    try {
      const owner = await ownerJar(app);
      const projectId = await seedProjectWithChapter(app, owner, "Atomic export retry");
      const database = studioDatabase(app);
      const interruptedAt = clock();
      database
        .insert(jobs)
        .values({
          id: "interrupted-export",
          project_id: projectId,
          document_id: null,
          kind: "export",
          operation: "export",
          status: "interrupted",
          provider: "studio",
          model: "",
          request_json: JSON.stringify({ format: "markdown" }),
          result_json: "{}",
          error: "restart interrupted the export",
          created_at: interruptedAt,
          updated_at: interruptedAt,
        })
        .run();

      const response = await call(
        app,
        owner,
        "POST",
        `/api/projects/${projectId}/jobs/interrupted-export/retry`,
      );

      expect(response.statusCode, response.body).toBe(500);
      expect(response.body).not.toContain("simulated retry completed-event failure");
      const listed = await call(app, owner, "GET", `/api/projects/${projectId}/jobs`);
      expect(listed.json().jobs as JobPayload[]).toMatchObject([
        {
          status: "running",
          retry_of_job_id: "interrupted-export",
          events: [{ status: "running" }],
        },
        { id: "interrupted-export", status: "interrupted" },
      ]);
      expect(database.select().from(projectSnapshots).all()).toEqual([]);
      expect(database.select().from(snapshotDocuments).all()).toEqual([]);
      expect(database.select().from(exportRecords).all()).toEqual([]);
      expect(database.select().from(jobs).all()).toHaveLength(2);
      expect(database.select().from(jobEvents).all()).toHaveLength(1);
      await expect(readdir(join(directory, "exports", projectId))).resolves.toEqual([]);
    } finally {
      await app.close();
    }
  });
});
