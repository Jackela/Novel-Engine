import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  documentRevisions,
  documents,
  projects,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import {
  anonymousCall,
  buildStudioApp,
  call,
  getProject,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

describe("projects surface", () => {
  it("creates a project with the Chapter 1 seed and default provider settings", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const response = await call(app, jar, "POST", "/api/projects", {
        title: "The Northern Light",
        description: "A slow-burn mystery",
      });
      expect(response.statusCode, response.body).toBe(201);
      const body = response.json();
      expect(body.title).toBe("The Northern Light");
      expect(body.description).toBe("A slow-burn mystery");
      expect(body.settings).toEqual({ provider: "mock" });
      expect(body.import_hash).toBeNull();
      expect(body.documents).toHaveLength(1);

      const seed = body.documents[0];
      if (seed === undefined) throw new Error("expected seeded document");
      expect(seed.kind).toBe("chapter");
      expect(seed.title).toBe("Chapter 1");
      expect(seed.position).toBe(1);
      expect(seed.current_revision_id).toBeTruthy();
      expect(seed.word_count).toBe(2);
      expect(seed).not.toHaveProperty("content_markdown");
      expect(seed).not.toHaveProperty("metadata");
      expect(seed).not.toHaveProperty("revision_source");

      const revisions = await call(
        app,
        jar,
        "GET",
        `/api/projects/${body.id}/documents/${seed.id}/revisions`,
      );
      expect(revisions.statusCode).toBe(200);
      const list = revisions.json().revisions;
      expect(list).toHaveLength(1);
      expect(list[0].revision_number).toBe(1);
      expect(list[0].parent_revision_id).toBeNull();
      expect(list[0].source).toBe("author");
      expect(list[0].word_count).toBe(2);
    } finally {
      await app.close();
    }
  });

  it("rejects anonymous and invalid project creates", async () => {
    const { app } = await buildStudioApp();
    try {
      const anonymous = await app.inject({
        method: "POST",
        url: "/api/projects",
        payload: { title: "No Principal" },
      });
      expect(anonymous.statusCode).toBe(401);
      expect(anonymous.json().error.code).toBe("UNAUTHORIZED");

      const jar = await ownerJar(app);
      const emptyTitle = await call(app, jar, "POST", "/api/projects", { title: "" });
      expect(emptyTitle.statusCode).toBe(422);
      expect(emptyTitle.json().error.code).toBe("VALIDATION_ERROR");

      const longTitle = await call(app, jar, "POST", "/api/projects", {
        title: "x".repeat(241),
      });
      expect(longTitle.statusCode).toBe(422);
    } finally {
      await app.close();
    }
  });

  it("lists projects most recently updated first", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const older = await seedProject(app, jar, "Written first");
      const newer = await seedProject(app, jar, "Written second");
      // Any accepted write bumps the project's updated_at: a reorder of the
      // older project's seed document makes it the most recently updated.
      const olderView = await getProject(app, jar, older.id);
      const seed = olderView.documents[0];
      if (seed === undefined) throw new Error("expected seeded document");
      const reorder = await call(app, jar, "PUT", `/api/projects/${older.id}/documents/reorder`, {
        document_ids: [seed.id],
      });
      expect(reorder.statusCode, reorder.body).toBe(200);

      const response = await call(app, jar, "GET", "/api/projects");
      expect(response.statusCode).toBe(200);
      const listed = response.json().projects.map((project: { id: string }) => project.id);
      expect(listed).toEqual([older.id, newer.id]);
    } finally {
      await app.close();
    }
  });

  it("breaks equal project update times by id for a stable total order", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const seeded = await seedProject(app, jar, "Scope owner");
      const db = app.studioDb?.db;
      if (db === undefined) throw new Error("expected studio database handle");
      const ownerId = db.select({ ownerId: projects.ownerId }).from(projects).get()?.ownerId;
      if (ownerId === undefined) throw new Error("expected project owner");
      const tiedAt = new Date("2026-01-01T00:00:00.000Z");
      const lowerId = "00000000-0000-4000-8000-000000000001";
      const higherId = "00000000-0000-4000-8000-000000000002";
      db.update(projects)
        .set({ updatedAt: new Date(0) })
        .run();
      db.insert(projects)
        .values([
          {
            id: lowerId,
            ownerId,
            title: "Lower id",
            description: "",
            settingsJson: '{"provider":"mock"}',
            importHash: null,
            createdAt: tiedAt,
            updatedAt: tiedAt,
          },
          {
            id: higherId,
            ownerId,
            title: "Higher id",
            description: "",
            settingsJson: '{"provider":"mock"}',
            importHash: null,
            createdAt: tiedAt,
            updatedAt: tiedAt,
          },
        ])
        .run();

      const response = await call(app, jar, "GET", "/api/projects");
      expect(response.statusCode, response.body).toBe(200);
      expect(response.json().projects.map((project: { id: string }) => project.id)).toEqual([
        higherId,
        lowerId,
        seeded.id,
      ]);
    } finally {
      await app.close();
    }
  });

  it("answers 401 for unauthenticated list and read requests", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const owned = await seedProject(app, owner, "Owner only");

      const anonymousList = await anonymousCall(app, "GET", "/api/projects");
      expect(anonymousList.statusCode).toBe(401);

      const anonymousRead = await anonymousCall(app, "GET", `/api/projects/${owned.id}`);
      expect(anonymousRead.statusCode).toBe(401);
      expect(anonymousRead.json().error.code).toBe("UNAUTHORIZED");
    } finally {
      await app.close();
    }
  });

  it("deletes a project with cascades and removes its export directory", async () => {
    const { app, directory } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Doomed");
      const exportDir = join(directory, "exports", project.id);
      mkdirSync(exportDir, { recursive: true });
      writeFileSync(join(exportDir, "keep.md"), "# exported\n");

      const response = await call(app, jar, "DELETE", `/api/projects/${project.id}`);
      expect(response.statusCode).toBe(204);

      const db = app.studioDb?.db;
      if (db === undefined) throw new Error("expected studio database handle");
      expect(db.select().from(projects).all()).toEqual([]);
      expect(db.select().from(documents).all()).toEqual([]);
      expect(db.select().from(documentRevisions).all()).toEqual([]);
      expect(existsSync(exportDir)).toBe(false);

      const gone = await call(app, jar, "GET", `/api/projects/${project.id}`);
      expect(gone.statusCode).toBe(404);
    } finally {
      await app.close();
    }
  });

  it("returns not-found for unknown projects", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const response = await call(app, jar, "GET", "/api/projects/does-not-exist");
      expect(response.statusCode).toBe(404);
      expect(response.json().error.code).toBe("NOT_FOUND");
    } finally {
      await app.close();
    }
  });
});
