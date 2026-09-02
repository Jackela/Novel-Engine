import { randomUUID } from "node:crypto";
import { describe, expect, it } from "vitest";
import {
  documentRevisions,
  documents,
  projects,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { owners } from "../../src/shared/infrastructure/db/schema.js";
import {
  anonymousCall,
  buildStudioApp,
  call,
  monotonicClock,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

const SUMMARY_KEYS = [
  "beat_ref",
  "created_at",
  "current_revision_id",
  "id",
  "kind",
  "lore_status",
  "position",
  "project_id",
  "title",
  "updated_at",
  "volume_id",
  "word_count",
];

const DOCUMENT_KEYS = [...SUMMARY_KEYS, "content_markdown", "metadata", "revision_source"].sort();

function expectSummary(value: Record<string, unknown>): void {
  expect(Object.keys(value).sort()).toEqual(SUMMARY_KEYS);
  expect(value.current_revision_id).toEqual(expect.any(String));
  expect(value.word_count).toEqual(expect.any(Number));
  expect(value).not.toHaveProperty("content_markdown");
  expect(value).not.toHaveProperty("metadata");
  expect(value).not.toHaveProperty("revision_source");
}

describe("bounded project shell contract", () => {
  it("returns strict summaries from creation and project detail", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const create = await call(app, owner, "POST", "/api/projects", {
        title: "Bounded shell",
      });
      expect(create.statusCode, create.body).toBe(201);
      const created = create.json();
      expect(created.documents).toHaveLength(1);
      expect(created.volumes).toHaveLength(1);
      expectSummary(created.documents[0]);
      expect(created.documents[0].word_count).toBe(2);

      await seedDocument(app, owner, created.id, {
        kind: "note",
        title: "Large sibling",
        content_markdown: "large ".repeat(10_000),
      });
      const detail = await call(app, owner, "GET", `/api/projects/${created.id}`);
      expect(detail.statusCode, detail.body).toBe(200);
      expect(detail.json().documents).toHaveLength(2);
      for (const summary of detail.json().documents) expectSummary(summary);
      expect(detail.body).not.toContain("large large");
    } finally {
      await app.close();
    }
  });

  it("returns exactly one complete current Document", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "One body");
      const target = await seedDocument(app, owner, project.id, {
        kind: "note",
        title: "Target",
        content_markdown: "Target accepted body",
      });
      await seedDocument(app, owner, project.id, {
        kind: "note",
        title: "Sibling",
        content_markdown: "Sibling secret body",
      });

      const response = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/documents/${target.id}`,
      );
      expect(response.statusCode, response.body).toBe(200);
      const body = response.json();
      expect(Object.keys(body).sort()).toEqual(DOCUMENT_KEYS);
      expect(body).toMatchObject({
        id: target.id,
        project_id: project.id,
        current_revision_id: target.current_revision_id,
        content_markdown: "Target accepted body",
        metadata: {},
        revision_source: "author",
      });
      expect(response.body).not.toContain("Sibling secret body");
    } finally {
      await app.close();
    }
  });

  it("authenticates before lookup and normalizes every scoped miss", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const first = await seedProject(app, owner, "First scope");
      const second = await seedProject(app, owner, "Second scope");
      const secondDocument = second.documents[0];
      if (secondDocument === undefined) throw new Error("expected seeded document");

      const anonymous = await anonymousCall(
        app,
        "GET",
        `/api/projects/${first.id}/documents/${randomUUID()}`,
      );
      expect(anonymous.statusCode).toBe(401);

      const db = app.studioDb?.db;
      if (db === undefined) throw new Error("expected database");
      const foreignOwnerId = randomUUID();
      const foreignProjectId = randomUUID();
      const foreignDocumentId = randomUUID();
      const foreignRevisionId = randomUUID();
      const now = new Date();
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
          title: "Foreign",
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
          title: "Foreign note",
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
          contentMarkdown: "foreign",
          metadataJson: "{}",
          source: "author",
          wordCount: 1,
          createdAt: now,
        })
        .run();

      const urls = [
        `/api/projects/${first.id}/documents/${randomUUID()}`,
        `/api/projects/${first.id}/documents/${secondDocument.id}`,
        `/api/projects/${foreignProjectId}/documents/${foreignDocumentId}`,
      ];
      const misses = await Promise.all(urls.map((url) => call(app, owner, "GET", url)));
      expect(misses.map((response) => response.statusCode)).toEqual([404, 404, 404]);
      expect(new Set(misses.map((response) => response.body)).size).toBe(1);
      expect(misses[0]?.json()).toEqual({
        error: { code: "NOT_FOUND", message: "Document not found." },
      });
    } finally {
      await app.close();
    }
  });

  it("keeps full-set reorder atomic while returning summaries only", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Summary reorder");
      const first = project.documents[0];
      if (first === undefined) throw new Error("expected seeded document");
      const second = await seedDocument(app, owner, project.id, {
        kind: "chapter",
        title: "Chapter 2",
        content_markdown: "second body",
      });
      const invalid = await call(
        app,
        owner,
        "PUT",
        `/api/projects/${project.id}/documents/reorder`,
        { document_ids: [second.id] },
      );
      expect(invalid.statusCode).toBe(422);

      const reordered = await call(
        app,
        owner,
        "PUT",
        `/api/projects/${project.id}/documents/reorder`,
        { document_ids: [second.id, first.id] },
      );
      expect(reordered.statusCode, reordered.body).toBe(200);
      expect(reordered.json().documents.map((item: { id: string }) => item.id)).toEqual([
        second.id,
        first.id,
      ]);
      for (const summary of reordered.json().documents) expectSummary(summary);
      expect(reordered.body).not.toContain("second body");
    } finally {
      await app.close();
    }
  });
});
