import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import { documentRevisions, projects } from "../../src/contexts/studio/infrastructure/db/schema.js";
import {
  buildStudioApp,
  call,
  getDocument,
  monotonicClock,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

describe("document save identity conflicts", () => {
  it("rejects a duplicate rename atomically and preserves stale-revision precedence", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Rename conflicts");
      const document = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Second",
        content_markdown: "original manuscript",
      });
      const path = `/api/projects/${project.id}/documents/${document.id}`;
      const saved = await call(app, jar, "PUT", path, {
        content_markdown: "accepted manuscript",
        base_revision_id: document.current_revision_id,
      });
      expect(saved.statusCode, saved.body).toBe(200);
      const currentRevisionId: string = saved.json().current_revision_id;
      const db = app.studioDb;
      if (db === undefined) throw new Error("Expected a Studio database.");
      const readState = async () => ({
        document: await getDocument(app, jar, project.id, document.id),
        revisions: db.db
          .select()
          .from(documentRevisions)
          .where(eq(documentRevisions.documentId, document.id))
          .all(),
        index: db.raw
          .prepare("SELECT title, content FROM document_search WHERE document_id = ?")
          .all(document.id),
        project: db.db.select().from(projects).where(eq(projects.id, project.id)).get(),
      });
      const before = await readState();
      const duplicate = await call(app, jar, "PUT", path, {
        content_markdown: "rejected manuscript",
        base_revision_id: currentRevisionId,
        title: "Chapter 1",
        autosave: true,
      });
      expect(duplicate.statusCode, duplicate.body).toBe(409);
      expect(duplicate.json().error.code).toBe("DOCUMENT_CONFLICT");
      expect(await readState()).toEqual(before);

      const stale = await call(app, jar, "PUT", path, {
        content_markdown: "stale manuscript",
        base_revision_id: document.current_revision_id,
        title: "Chapter 1",
      });
      expect(stale.statusCode, stale.body).toBe(409);
      expect(stale.json().error).toMatchObject({
        code: "REVISION_CONFLICT",
        details: { current_revision_id: currentRevisionId },
      });
      expect(await readState()).toEqual(before);
    } finally {
      await app.close();
    }
  });
});
