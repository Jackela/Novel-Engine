import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import { projects } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { buildStudioApp, call, ownerJar } from "./studio_helpers.js";

const SCALAR_FIELDS = [
  "created_at",
  "description",
  "id",
  "import_hash",
  "settings",
  "title",
  "updated_at",
];

function frozenClock(iso: string): () => Date {
  return () => new Date(iso);
}

describe("Project settings PATCH persistence", () => {
  it("updates each selected scalar, preserves omissions, and returns only Project scalars", async () => {
    const { app } = await buildStudioApp(frozenClock("2026-09-03T10:00:00.000Z"));
    try {
      const jar = await ownerJar(app);
      const created = await call(app, jar, "POST", "/api/projects", {
        title: "Original",
        description: "Initial description",
      });
      expect(created.statusCode, created.body).toBe(201);
      const initial = created.json();
      const path = `/api/projects/${String(initial.id)}`;
      const db = app.studioDb?.db;
      if (db === undefined) throw new Error("expected database");
      db.update(projects)
        .set({ importHash: "import-fixture" })
        .where(eq(projects.id, String(initial.id)))
        .run();

      const description = await call(app, jar, "PATCH", path, {
        description: "  Revised description  ",
      });
      expect(description.statusCode, description.body).toBe(200);
      expect(description.json()).toMatchObject({
        title: "Original",
        description: "Revised description",
        settings: { provider: "mock" },
        import_hash: "import-fixture",
        created_at: initial.created_at,
      });

      const settings = await call(app, jar, "PATCH", path, {
        settings: { provider: "dashscope" },
      });
      expect(settings.statusCode, settings.body).toBe(200);
      expect(settings.json()).toMatchObject({
        title: "Original",
        description: "Revised description",
        settings: { provider: "dashscope" },
      });

      const title = await call(app, jar, "PATCH", path, { title: "  Renamed  " });
      expect(title.statusCode, title.body).toBe(200);
      expect(title.json()).toMatchObject({
        title: "Renamed",
        description: "Revised description",
        settings: { provider: "dashscope" },
      });

      const combined = await call(app, jar, "PATCH", path, {
        title: "  Final  ",
        description: "  Complete  ",
        settings: { provider: "openai-compatible", nested: { keep: true } },
      });
      expect(combined.statusCode, combined.body).toBe(200);
      const payload = combined.json();
      expect(Object.keys(payload).sort()).toEqual(SCALAR_FIELDS);
      expect(payload).toMatchObject({
        id: initial.id,
        title: "Final",
        description: "Complete",
        settings: { provider: "openai-compatible", nested: { keep: true } },
        import_hash: "import-fixture",
        created_at: initial.created_at,
      });
      expect(payload).not.toHaveProperty("documents");
      expect(payload).not.toHaveProperty("volumes");
      expect(payload).not.toHaveProperty("content_markdown");
      expect(payload).not.toHaveProperty("metadata");

      const shell = await call(app, jar, "GET", path);
      expect(shell.json()).toMatchObject(payload);
      expect(shell.json().documents).toEqual(initial.documents);
    } finally {
      await app.close();
    }
  });

  it("replaces the complete settings object rather than recursively merging it", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const created = await call(app, jar, "POST", "/api/projects", { title: "Settings" });
      const projectId = String(created.json().id);
      await call(app, jar, "PATCH", `/api/projects/${projectId}`, {
        settings: { provider: "mock", retained: true },
      });

      const replaced = await call(app, jar, "PATCH", `/api/projects/${projectId}`, {
        settings: { provider: "dashscope" },
      });

      expect(replaced.statusCode, replaced.body).toBe(200);
      expect(replaced.json().settings).toEqual({ provider: "dashscope" });
    } finally {
      await app.close();
    }
  });

  it("advances updated_at under same or backwards clocks and restores catalog ordering", async () => {
    const supplied = "2026-09-03T11:00:00.000Z";
    let clockTime = Date.parse(supplied);
    const { app } = await buildStudioApp(() => new Date(clockTime));
    try {
      const jar = await ownerJar(app);
      const first = await call(app, jar, "POST", "/api/projects", { title: "First" });
      const second = await call(app, jar, "POST", "/api/projects", { title: "Second" });
      const projectId = String(first.json().id);

      const same = await call(app, jar, "PATCH", `/api/projects/${projectId}`, {
        title: "First",
      });
      clockTime -= 1_000;
      const backwards = await call(app, jar, "PATCH", `/api/projects/${projectId}`, {
        description: "backwards clock",
      });
      clockTime = Date.parse(supplied) + 10_000;
      const forward = await call(app, jar, "PATCH", `/api/projects/${projectId}`, {
        description: "forward clock",
      });
      expect(Date.parse(same.json().updated_at)).toBe(Date.parse(supplied) + 1);
      expect(Date.parse(backwards.json().updated_at)).toBe(Date.parse(supplied) + 2);
      expect(Date.parse(forward.json().updated_at)).toBe(clockTime);
      const persisted = app.studioDb?.db
        .select({ updatedAt: projects.updatedAt })
        .from(projects)
        .where(eq(projects.id, projectId))
        .get();
      expect(persisted?.updatedAt.getTime()).toBe(clockTime);

      const listed = await call(app, jar, "GET", "/api/projects");
      expect(listed.json().projects.map((row: { id: string }) => row.id)).toEqual([
        projectId,
        second.json().id,
      ]);
    } finally {
      await app.close();
    }
  });

  it("keeps every scalar and timestamp unchanged when SQLite rejects the atomic statement", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const created = await call(app, jar, "POST", "/api/projects", { title: "Atomic" });
      const projectId = String(created.json().id);
      const db = app.studioDb?.db;
      const raw = app.studioDb?.raw;
      if (db === undefined || raw === undefined) throw new Error("expected database");
      const before = db.select().from(projects).where(eq(projects.id, projectId)).get();
      raw.exec(`
        CREATE TRIGGER reject_project_patch
        BEFORE UPDATE OF title ON projects
        BEGIN
          SELECT RAISE(ABORT, 'injected project update failure');
        END;
      `);

      const failed = await call(app, jar, "PATCH", `/api/projects/${projectId}`, {
        title: "Must not land",
        description: "Must not land either",
      });

      expect(failed.statusCode, failed.body).toBe(500);
      expect(failed.json().error).toMatchObject({
        code: "INTERNAL_ERROR",
        message: "An internal error occurred.",
      });
      expect(db.select().from(projects).where(eq(projects.id, projectId)).get()).toEqual(before);
    } finally {
      await app.close();
    }
  });
});
