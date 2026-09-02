import { randomUUID } from "node:crypto";
import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import {
  documentRevisions,
  documents,
  projects,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { owners } from "../../src/shared/infrastructure/db/schema.js";
import { buildStudioApp, call, monotonicClock, ownerJar, seedProject } from "./studio_helpers.js";

describe("current revision pointer integrity", () => {
  it("never publishes another owner's revision through an inconsistent scoped document", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Pointer integrity");
      const document = project.documents[0];
      if (document === undefined) throw new Error("expected seeded document");

      const db = app.studioDb?.db;
      if (db === undefined) throw new Error("expected database");
      const foreignOwnerId = randomUUID();
      const foreignProjectId = randomUUID();
      const foreignDocumentId = randomUUID();
      const foreignRevisionId = randomUUID();
      const now = new Date("2026-09-03T00:00:00.000Z");
      db.insert(owners)
        .values({
          id: foreignOwnerId,
          username: `foreign-${foreignOwnerId}`,
          password_hash: "not-a-login-credential",
          created_at: now,
        })
        .run();
      db.insert(projects)
        .values({
          id: foreignProjectId,
          ownerId: foreignOwnerId,
          title: "Foreign project",
          description: "",
          settingsJson: "{}",
          createdAt: now,
          updatedAt: now,
        })
        .run();
      db.insert(documents)
        .values({
          id: foreignDocumentId,
          projectId: foreignProjectId,
          kind: "note",
          title: "Foreign document",
          position: 1,
          currentRevisionId: foreignRevisionId,
          createdAt: now,
          updatedAt: now,
        })
        .run();
      db.insert(documentRevisions)
        .values({
          id: foreignRevisionId,
          documentId: foreignDocumentId,
          revisionNumber: 1,
          contentMarkdown: "FOREIGN_BODY_SENTINEL",
          metadataJson: '{"foreign_secret":true}',
          source: "import",
          wordCount: 987_654,
          createdAt: now,
        })
        .run();
      db.update(documents)
        .set({ currentRevisionId: foreignRevisionId })
        .where(eq(documents.id, document.id))
        .run();

      const current = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/documents/${document.id}`,
      );
      expect(current.statusCode, current.body).toBe(404);
      expect(current.json()).toEqual({
        error: { code: "NOT_FOUND", message: "Document not found." },
      });

      const shell = await call(app, owner, "GET", `/api/projects/${project.id}`);
      expect(shell.statusCode, shell.body).toBe(500);
      expect(shell.json().error).toMatchObject({
        code: "INTERNAL_ERROR",
        message: "An internal error occurred.",
      });
      for (const response of [current, shell]) {
        expect(response.body).not.toContain("FOREIGN_BODY_SENTINEL");
        expect(response.body).not.toContain("foreign_secret");
        expect(response.body).not.toContain("987654");
      }
    } finally {
      await app.close();
    }
  });
});
