import { describe, expect, it } from "vitest";
import {
  buildStudioApp,
  call,
  getProject,
  type JobPayload,
  monotonicClock,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

function evidenceIds(job: JobPayload): { exportId: string; snapshotId: string } {
  const exportId = job.result.export_id;
  const snapshotId = job.result.snapshot_id;
  if (typeof exportId !== "string" || typeof snapshotId !== "string") {
    throw new Error("Completed export must expose artifact and snapshot ids.");
  }
  return { exportId, snapshotId };
}

describe("export snapshot source identity", () => {
  it("creates a new snapshot after reorder and reuses it while order stays unchanged", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Ordered export identity");
      const firstChapter = project.documents[0];
      if (firstChapter === undefined) throw new Error("Expected the seeded chapter.");
      const secondChapter = await seedDocument(app, owner, project.id, {
        kind: "chapter",
        title: "Chapter 2",
        content_markdown: "SECOND CHAPTER BODY",
      });
      const before = await getProject(app, owner, project.id);
      const revisionById = new Map(
        before.documents.map((document) => [document.id, document.current_revision_id]),
      );

      const firstResponse = await call(app, owner, "POST", `/api/projects/${project.id}/exports`, {
        format: "markdown",
      });
      expect(firstResponse.statusCode, firstResponse.body).toBe(201);
      const first = evidenceIds(firstResponse.json<JobPayload>());

      const reordered = await call(
        app,
        owner,
        "PUT",
        `/api/projects/${project.id}/documents/reorder`,
        { document_ids: [secondChapter.id, firstChapter.id] },
      );
      expect(reordered.statusCode, reordered.body).toBe(200);
      const after = await getProject(app, owner, project.id);
      expect(after.documents.map((document) => document.id)).toEqual([
        secondChapter.id,
        firstChapter.id,
      ]);
      expect(
        after.documents.every(
          (document) => revisionById.get(document.id) === document.current_revision_id,
        ),
      ).toBe(true);

      const secondResponse = await call(app, owner, "POST", `/api/projects/${project.id}/exports`, {
        format: "markdown",
      });
      expect(secondResponse.statusCode, secondResponse.body).toBe(201);
      const second = evidenceIds(secondResponse.json<JobPayload>());
      expect(second.snapshotId).not.toBe(first.snapshotId);
      const downloaded = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/exports/${second.exportId}/download`,
      );
      expect(downloaded.statusCode, downloaded.body).toBe(200);
      const text = downloaded.rawPayload.toString("utf8");
      expect(text).toContain("SECOND CHAPTER BODY");
      expect(text).toContain("# Chapter 1");
      expect(text.indexOf("SECOND CHAPTER BODY")).toBeLessThan(text.indexOf("# Chapter 1"));

      const thirdResponse = await call(app, owner, "POST", `/api/projects/${project.id}/exports`, {
        format: "docx",
      });
      expect(thirdResponse.statusCode, thirdResponse.body).toBe(201);
      expect(evidenceIds(thirdResponse.json<JobPayload>()).snapshotId).toBe(second.snapshotId);
    } finally {
      await app.close();
    }
  });
});
