import { describe, expect, it } from "vitest";

import {
  buildStudioApp,
  call,
  type DocumentPayload,
  draftProposal,
  getDocument,
  listRevisions,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

describe("proposal acceptance conflicts", () => {
  it("answers 409 REVISION_CONFLICT when the manuscript advanced past the proposal base", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Stale accept");
      const document = project.documents[0] as DocumentPayload;
      const baseId = document.current_revision_id;
      const job = await draftProposal(app, jar, project.id, document.id, {
        operation: "continue",
        provider: "mock",
      });
      expect(job.request.base_revision_id).toBe(baseId);

      // The author saves against the same base first: the proposal's landing
      // base is now stale and acceptance must refuse instead of clobbering.
      const saved = await call(
        app,
        jar,
        "PUT",
        `/api/projects/${project.id}/documents/${document.id}`,
        {
          content_markdown: "author edit past the proposal base",
          base_revision_id: baseId,
        },
      );
      expect(saved.statusCode, saved.body).toBe(200);
      const currentId: string = saved.json().current_revision_id;
      expect(currentId).not.toBe(baseId);

      const conflict = await call(
        app,
        jar,
        "POST",
        `/api/projects/${project.id}/ai-proposals/${job.id}/accept`,
      );
      expect(conflict.statusCode, conflict.body).toBe(409);
      const error = conflict.json().error;
      expect(error.code).toBe("REVISION_CONFLICT");
      expect(error.details.current_revision_id).toBe(currentId);

      // Landing never happened: the chain holds only the author's revision B.
      const revisions = await listRevisions(app, jar, project.id, document.id);
      expect(revisions).toHaveLength(2);
      expect(revisions[0]?.id).toBe(currentId);
      expect(revisions[0]?.source).toBe("author");
      expect((await getDocument(app, jar, project.id, document.id)).current_revision_id).toBe(
        currentId,
      );
    } finally {
      await app.close();
    }
  });
});
