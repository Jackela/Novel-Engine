import { describe, expect, it, vi } from "vitest";

import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";

import {
  buildStudioApp,
  call,
  getProject,
  listRevisions,
  monotonicClock,
  ownerJar,
  type RevisionPayload,
  seedDocument,
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
      const projectView = await getProject(app, jar, project.id);
      const document = projectView.documents[0];
      if (document === undefined) throw new Error("expected seeded document");
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
      const newest = revisions[0];
      if (newest === undefined) throw new Error("expected newest revision");
      const parent = revisions[1];
      if (parent === undefined) throw new Error("expected parent revision");
      expect(parent.id).toBe(baseId);
      expect(newest.parent_revision_id).toBe(baseId);
      expect(newest.revision_number).toBe(2);
      expect(newest.source).toBe("author");
    } finally {
      await app.close();
    }
  });

  it("rejects a stale base with 409 REVISION_CONFLICT and the current revision id", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Conflict");
      const projectView = await getProject(app, jar, project.id);
      const document = projectView.documents[0];
      if (document === undefined) throw new Error("expected seeded document");
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
        2, 1,
      ]);
    } finally {
      await app.close();
    }
  });

  it("restores historic A exactly against current B while keeping summary-only history", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Monotonic");
      const projectView = await getProject(app, jar, project.id);
      const document = projectView.documents[0];
      if (document === undefined) throw new Error("expected seeded document");

      const baseId: string = document.current_revision_id;
      const historic = await putDocument(app, jar, project.id, document.id, {
        content_markdown: "historic A",
        base_revision_id: baseId,
        metadata: { marker: "A" },
      });
      expect(historic.statusCode, historic.body).toBe(200);
      const historicId = historic.json().current_revision_id as string;
      const current = await putDocument(app, jar, project.id, document.id, {
        content_markdown: "current B",
        base_revision_id: historicId,
        metadata: { marker: "B" },
      });
      expect(current.statusCode, current.body).toBe(200);
      const currentId = current.json().current_revision_id as string;

      const before = await listRevisions(app, jar, project.id, document.id);
      const historicSummary = before.find((revision) => revision.id === historicId);
      expect(historicSummary).toBeDefined();
      expect(historicSummary).not.toHaveProperty("content_markdown");
      expect(historicSummary).not.toHaveProperty("metadata");

      const exactRevisionRead = vi.spyOn(DrizzleStudioStore.prototype, "findRevision");
      const restore = await call(
        app,
        jar,
        "POST",
        `/api/projects/${project.id}/documents/${document.id}/revisions/${historicId}/restore`,
        { base_revision_id: currentId },
      );
      expect(restore.statusCode, restore.body).toBe(200);
      const restored = restore.json();
      expect(restored.revision_source).toBe("restore");
      expect(restored.content_markdown).toBe("historic A");
      expect(restored.metadata).toEqual({ marker: "A", restored_from: historicId });
      expect(exactRevisionRead).toHaveBeenCalledTimes(1);
      expect(exactRevisionRead).toHaveBeenCalledWith(
        expect.objectContaining({ ownerId: expect.any(String) }),
        project.id,
        document.id,
        historicId,
      );
      exactRevisionRead.mockRestore();

      const revisions = await listRevisions(app, jar, project.id, document.id);
      expect(revisions.map((revision) => revision.revision_number)).toEqual([4, 3, 2, 1]);
      const newest = revisions[0];
      if (newest === undefined) throw new Error("expected restored revision");
      expect(newest.parent_revision_id).toBe(currentId);
      expect(newest.source).toBe("restore");
    } finally {
      vi.restoreAllMocks();
      await app.close();
    }
  });

  it("never accepts a client-supplied source", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Closed enum");
      const projectView = await getProject(app, jar, project.id);
      const document = projectView.documents[0];
      if (document === undefined) throw new Error("expected seeded document");

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
      const secondRevision = revisions[0];
      if (secondRevision === undefined) throw new Error("expected second revision");
      expect(secondRevision.source).toBe("author");
    } finally {
      await app.close();
    }
  });

  it("keeps restore conflicts and cross-document revision ids closed without new revisions", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Restore guards");
      const document = (await getProject(app, jar, project.id)).documents[0];
      if (document === undefined) throw new Error("expected seeded document");
      const staleBase = document.current_revision_id;
      const saved = await putDocument(app, jar, project.id, document.id, {
        content_markdown: "current",
        base_revision_id: staleBase,
      });
      expect(saved.statusCode, saved.body).toBe(200);
      const currentId = saved.json().current_revision_id as string;
      const beforeConflict = await listRevisions(app, jar, project.id, document.id);

      const conflict = await call(
        app,
        jar,
        "POST",
        `/api/projects/${project.id}/documents/${document.id}/revisions/${staleBase}/restore`,
        { base_revision_id: staleBase },
      );
      expect(conflict.statusCode, conflict.body).toBe(409);
      expect(conflict.json().error.details.current_revision_id).toBe(currentId);
      expect(await listRevisions(app, jar, project.id, document.id)).toEqual(beforeConflict);

      const other = await seedDocument(app, jar, project.id, {
        kind: "note",
        title: "Other",
        content_markdown: "other",
      });
      const otherRevisionId = (await listRevisions(app, jar, project.id, other.id))[0]?.id;
      if (otherRevisionId === undefined) throw new Error("expected other revision");
      const crossDocument = await call(
        app,
        jar,
        "POST",
        `/api/projects/${project.id}/documents/${document.id}/revisions/${otherRevisionId}/restore`,
        { base_revision_id: currentId },
      );
      expect(crossDocument.statusCode, crossDocument.body).toBe(404);
      expect(await listRevisions(app, jar, project.id, document.id)).toEqual(beforeConflict);
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
