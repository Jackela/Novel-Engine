import { describe, expect, it } from "vitest";

import {
  buildStudioApp,
  call,
  getProject,
  listRevisions,
  monotonicClock,
  ownerJar,
  type RevisionPayload,
  seedProject,
} from "./studio_helpers.js";

async function putDocument(
  app: Parameters<typeof call>[0],
  jar: Parameters<typeof call>[1],
  projectId: string,
  documentId: string,
  body: Record<string, unknown>,
): Promise<ReturnType<typeof call>> {
  return call(app, jar, "PUT", `/api/projects/${projectId}/documents/${documentId}`, body);
}

describe("revision chain", () => {
  it("creates and advances atomically on a fresh base, keeping the parent readable", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Atomic");
      const document = (await getProject(app, jar, project.id)).documents[0]!;
      const baseId = document.current_revision_id;

      const saved = await putDocument(app, jar, project.id, document.id, {
        content_markdown: "# Chapter 1\n\nThe lantern flickered twice.",
        base_revision_id: baseId,
        title: "Chapter One",
        metadata: { scene: "harbor" },
      });
      expect(saved.statusCode, saved.body).toBe(200);
      const body = saved.json();
      expect(body.title).toBe("Chapter One");
      expect(body.metadata).toEqual({ scene: "harbor" });
      expect(body.content_markdown).toContain("lantern");
      expect(body.current_revision_id).not.toBe(baseId);

      const revisions = await listRevisions(app, jar, project.id, document.id);
      expect(revisions).toHaveLength(2);
      const first = revisions[0]!;
      const second = revisions[1]!;
      expect(first.id).toBe(baseId);
      expect(first.content_markdown).toBe("# Chapter 1\n\n");
      expect(second.parent_revision_id).toBe(baseId);
      expect(second.revision_number).toBe(2);
      expect(second.source).toBe("author");
    } finally {
      await app.close();
    }
  });

  it("rejects a stale base with 409 REVISION_CONFLICT and the current revision id", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Conflict");
      const document = (await getProject(app, jar, project.id)).documents[0]!;
      const staleBase = document.current_revision_id;

      const first = await putDocument(app, jar, project.id, document.id, {
        content_markdown: "first",
        base_revision_id: staleBase,
      });
      expect(first.statusCode).toBe(200);
      const currentId = first.json().current_revision_id;

      const stale = await putDocument(app, jar, project.id, document.id, {
        content_markdown: "written against the past",
        base_revision_id: staleBase,
      });
      expect(stale.statusCode).toBe(409);
      const error = stale.json().error;
      expect(error.code).toBe("REVISION_CONFLICT");
      expect(error.details.current_revision_id).toBe(currentId);

      const revisions = await listRevisions(app, jar, project.id, document.id);
      expect(revisions).toHaveLength(2);
      expect(revisions.map((revision: RevisionPayload) => revision.revision_number)).toEqual([
        1, 2,
      ]);
    } finally {
      await app.close();
    }
  });

  it("keeps revision numbers monotonic across sequential saves and a restore", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Monotonic");
      const document = (await getProject(app, jar, project.id)).documents[0]!;

      let baseId: string = document.current_revision_id;
      for (const content of ["two", "three", "four", "five"]) {
        const saved = await putDocument(app, jar, project.id, document.id, {
          content_markdown: content,
          base_revision_id: baseId,
        });
        expect(saved.statusCode, saved.body).toBe(200);
        baseId = saved.json().current_revision_id;
      }

      const restore = await call(
        app,
        jar,
        "POST",
        `/api/projects/${project.id}/documents/${document.id}/revisions/${baseId}/restore`,
        { base_revision_id: baseId },
      );
      expect(restore.statusCode, restore.body).toBe(200);
      const restored = restore.json();
      expect(restored.revision_source).toBe("restore");

      const revisions = await listRevisions(app, jar, project.id, document.id);
      expect(revisions).toHaveLength(6);
      expect(revisions.map((revision) => revision.revision_number)).toEqual([1, 2, 3, 4, 5, 6]);
      const last = revisions[5]!;
      expect(last.parent_revision_id).toBe(baseId);
      expect(last.source).toBe("restore");
      expect(last.content_markdown).toBe("five");
      expect(last.metadata.restored_from).toBe(baseId);
    } finally {
      await app.close();
    }
  });

  it("never accepts a client-supplied source", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Closed enum");
      const document = (await getProject(app, jar, project.id)).documents[0]!;

      // The save schema exposes no source field: smuggled values are stripped
      // before validation reaches the service, so the server-assigned enum
      // alone decides the created revision's source.
      const smuggled = await putDocument(app, jar, project.id, document.id, {
        content_markdown: "injecting",
        base_revision_id: document.current_revision_id,
        source: "ai-accepted",
      });
      expect(smuggled.statusCode, smuggled.body).toBe(200);
      expect(smuggled.json().revision_source).toBe("author");

      const revisions = await listRevisions(app, jar, project.id, document.id);
      expect(revisions).toHaveLength(2);
      expect(revisions[1]!.source).toBe("author");
    } finally {
      await app.close();
    }
  });

  it("returns not-found for saves against missing documents", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Missing");
      const response = await putDocument(app, jar, project.id, "no-such-document", {
        content_markdown: "content",
        base_revision_id: null,
      });
      expect(response.statusCode).toBe(404);
      expect(response.json().error.code).toBe("NOT_FOUND");
    } finally {
      await app.close();
    }
  });
});
