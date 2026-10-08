import { rm } from "node:fs/promises";
import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";
import type { TextGenerationProviderFactory } from "../../src/contexts/ai/application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import {
  documentRevisions,
  projectSnapshots,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { deferredReviewFactory } from "./job_test_helpers.js";
import { retryJobRequest } from "./retry_test_helpers.js";
import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

/** The normal editor autosave and review endpoints must share one revision-retention owner. */
describe("Review capture across live editor autosaves", () => {
  it.each([false, true])(
    "records the original captured revision after two saves (autosave=%s)",
    async (autosave) => {
      let start = () => {};
      let release = () => {};
      const started = new Promise<void>((resolve) => {
        start = resolve;
      });
      const waiting = new Promise<void>((resolve) => {
        release = resolve;
      });
      const factory: TextGenerationProviderFactory = (provider) => ({
        generateStructured: async () => {
          start();
          await waiting;
          return {
            step: "editorial_review",
            provider,
            model: "captured-review-model",
            rawText: '{"findings":[]}',
            content: { findings: [] },
            promptTokens: null,
            completionTokens: null,
          };
        },
      });
      const { app, directory } = await buildStudioApp(undefined, { textProviderFactory: factory });
      try {
        const owner = await ownerJar(app);
        const project = await seedProject(app, owner, "Review autosave race");
        const document = project.documents[0];
        if (document === undefined) throw new Error("Expected seed chapter");
        const path = `/api/projects/${project.id}/documents/${document.id}`;
        const initial = (await call(app, owner, "GET", path)).json();
        const captured = await call(app, owner, "PUT", path, {
          base_revision_id: initial.current_revision_id,
          content_markdown: "Captured review prose.",
          autosave: true,
        });
        expect(captured.statusCode, captured.body).toBe(200);
        const pending = call(app, owner, "POST", `/api/projects/${project.id}/reviews`, {});
        await started;
        const second = await call(app, owner, "PUT", path, {
          base_revision_id: captured.json().current_revision_id,
          content_markdown: "Second live prose.",
          autosave,
        });
        const third = await call(app, owner, "PUT", path, {
          base_revision_id: second.json().current_revision_id,
          content_markdown: "Third live prose.",
          autosave,
        });
        expect(third.statusCode).toBe(200);
        release();
        const completion = await pending;
        expect(completion.json().status, completion.body).toBe("completed");
        const pinned = app.studioDb?.db.select().from(snapshotDocuments).all();
        expect(pinned?.find((row) => row.documentId === document.id)).toMatchObject({
          revisionId: captured.json().current_revision_id,
        });
        expect((await call(app, owner, "GET", path)).json().content_markdown).toBe(
          "Third live prose.",
        );
      } finally {
        release();
        await app.close();
        await rm(directory, { recursive: true, force: true });
      }
    },
  );

  it("releases a failed provider capture so the next normal autosave can fold it", async () => {
    let start = () => {};
    let release = () => {};
    const started = new Promise<void>((resolve) => {
      start = resolve;
    });
    const waiting = new Promise<void>((resolve) => {
      release = resolve;
    });
    const factory: TextGenerationProviderFactory = () => ({
      generateStructured: async () => {
        start();
        await waiting;
        throw new TextGenerationProviderError("Deferred provider failure");
      },
    });
    const { app, directory } = await buildStudioApp(undefined, { textProviderFactory: factory });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Failed review releases capture");
      const document = project.documents[0];
      if (document === undefined) throw new Error("Expected seed chapter");
      const path = `/api/projects/${project.id}/documents/${document.id}`;
      const initial = (await call(app, owner, "GET", path)).json();
      const captured = await call(app, owner, "PUT", path, {
        base_revision_id: initial.current_revision_id,
        content_markdown: "Captured before failure.",
        autosave: true,
      });
      const pending = call(app, owner, "POST", `/api/projects/${project.id}/reviews`, {});
      await started;
      expect(app.studioDb?.db.select().from(projectSnapshots).all()).toHaveLength(0);
      release();
      const failed = await pending;
      expect(failed.json().status, failed.body).toBe("failed");
      expect(app.studioDb?.db.select().from(projectSnapshots).all()).toHaveLength(0);
      const saved = await call(app, owner, "PUT", path, {
        base_revision_id: captured.json().current_revision_id,
        content_markdown: "Autosave after provider failure.",
        autosave: true,
      });
      expect(saved.statusCode, saved.body).toBe(200);
      expect(
        app.studioDb?.db
          .select()
          .from(documentRevisions)
          .where(eq(documentRevisions.id, captured.json().current_revision_id))
          .get(),
      ).toBeUndefined();
    } finally {
      release();
      await app.close();
      await rm(directory, { recursive: true, force: true });
    }
  });

  it("retains a retry capture through provider wait and the atomic retry outcome", async () => {
    const deferred = deferredReviewFactory(1);
    const { app, directory } = await buildStudioApp(undefined, {
      textProviderFactory: deferred.factory,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Retry autosave race");
      const document = project.documents[0];
      if (document === undefined) throw new Error("Expected seed chapter");
      const path = `/api/projects/${project.id}/documents/${document.id}`;
      const initial = (await call(app, owner, "GET", path)).json();
      const captured = await call(app, owner, "PUT", path, {
        base_revision_id: initial.current_revision_id,
        content_markdown: "Captured retry prose.",
        autosave: true,
      });
      const original = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`, {});
      expect(original.json().status).toBe("failed");
      const pending = retryJobRequest(
        app,
        owner,
        `/api/projects/${project.id}/jobs/${original.json().id}/retry`,
        "autosave-capture-retry-0001",
      );
      await deferred.started;
      const second = await call(app, owner, "PUT", path, {
        base_revision_id: captured.json().current_revision_id,
        content_markdown: "Later retry prose.",
        autosave: true,
      });
      const third = await call(app, owner, "PUT", path, {
        base_revision_id: second.json().current_revision_id,
        content_markdown: "Newest retry prose.",
        autosave: true,
      });
      expect(third.statusCode, third.body).toBe(200);
      deferred.succeed();
      const completed = await pending;
      expect(completed.json().status, completed.body).toBe("completed");
      expect(
        app.studioDb?.db
          .select()
          .from(snapshotDocuments)
          .all()
          .find((row) => row.documentId === document.id)?.revisionId,
      ).toBe(captured.json().current_revision_id);
    } finally {
      deferred.succeed();
      await app.close();
      await rm(directory, { recursive: true, force: true });
    }
  });
});
