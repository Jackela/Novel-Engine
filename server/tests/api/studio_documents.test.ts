import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import {
  documentRevisions,
  documents,
  projectSnapshots,
  reviews,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import {
  buildStudioApp,
  call,
  getProject,
  listDocuments,
  listRevisions,
  monotonicClock,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

describe("documents surface", () => {
  it("rejects a duplicate (kind, title) but allows the same title across kinds", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Identity");
      await seedDocument(app, jar, project.id, { kind: "chapter", title: "Storm" });

      const duplicate = await call(app, jar, "POST", `/api/projects/${project.id}/documents`, {
        kind: "chapter",
        title: "Storm",
      });
      expect(duplicate.statusCode).toBe(409);
      const error = duplicate.json().error;
      expect(error.code).toBe("DOCUMENT_CONFLICT");
      expect(error.message).toContain("Storm");

      const chapters = (await listDocuments(app, jar, project.id)).filter(
        (document) => document.kind === "chapter" && document.title === "Storm",
      );
      expect(chapters).toHaveLength(1);

      const otherKind = await call(app, jar, "POST", `/api/projects/${project.id}/documents`, {
        kind: "character",
        title: "Storm",
      });
      expect(otherKind.statusCode, otherKind.body).toBe(201);
      const stormTitles = (await listDocuments(app, jar, project.id))
        .filter((document) => document.title === "Storm")
        .map((document) => document.kind)
        .sort();
      expect(stormTitles).toEqual(["chapter", "character"]);
    } finally {
      await app.close();
    }
  });

  it("rejects unsupported kinds and invalid titles", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Validation");
      const badKind = await call(app, jar, "POST", `/api/projects/${project.id}/documents`, {
        kind: "poem",
        title: "Storm",
      });
      expect(badKind.statusCode).toBe(422);
      expect(badKind.json().error.code).toBe("VALIDATION_ERROR");

      const longTitle = await call(app, jar, "POST", `/api/projects/${project.id}/documents`, {
        kind: "chapter",
        title: "y".repeat(241),
      });
      expect(longTitle.statusCode).toBe(422);
    } finally {
      await app.close();
    }
  });

  it("orders documents by kind, then position, then creation time", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Ordering");
      const seedId = project.documents[0]!.id; // chapter "Chapter 1", position 1

      const note = await seedDocument(app, jar, project.id, {
        kind: "note",
        title: "Scraps",
      });
      const secondChapter = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Chapter 2",
      });
      const character = await seedDocument(app, jar, project.id, {
        kind: "character",
        title: "Mara",
      });

      const listed = await listDocuments(app, jar, project.id);
      expect(listed.map((document) => document.id)).toEqual([
        seedId, // chapter position 1
        secondChapter.id, // chapter position 2 (auto-assigned)
        character.id, // kind "character" sorts after "chapter"
        note.id, // kind "note" sorts last
      ]);
    } finally {
      await app.close();
    }
  });

  it("rejects a partial reorder with 422 and leaves order unchanged", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Reorder");
      const before = await listDocuments(app, jar, project.id);
      expect(before).toHaveLength(1);

      const partial = await call(app, jar, "PUT", `/api/projects/${project.id}/documents/reorder`, {
        document_ids: [],
      });
      expect(partial.statusCode).toBe(422);

      const extra = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Chapter 2",
      });
      const missingOne = await call(
        app,
        jar,
        "PUT",
        `/api/projects/${project.id}/documents/reorder`,
        { document_ids: [extra.id] },
      );
      expect(missingOne.statusCode).toBe(422);
      expect(missingOne.json().error.code).toBe("INVALID_OPERATION");

      const after = await listDocuments(app, jar, project.id);
      expect(after.map((document) => [document.id, document.position])).toEqual(
        before.map((document) => [document.id, document.position]).concat([[extra.id, 2]]),
      );
    } finally {
      await app.close();
    }
  });

  it("renumbers positions 1..n for a full-set reorder and answers in order", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Renumber");
      const seed = project.documents[0]!;
      const second = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Chapter 2",
      });
      const third = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Chapter 3",
      });
      expect([seed.position, second.position, third.position]).toEqual([1, 2, 3]);

      const response = await call(
        app,
        jar,
        "PUT",
        `/api/projects/${project.id}/documents/reorder`,
        {
          document_ids: [third.id, seed.id, second.id],
        },
      );
      expect(response.statusCode, response.body).toBe(200);
      const returned = response.json().documents;
      expect(returned.map((document: { id: string }) => document.id)).toEqual([
        third.id,
        seed.id,
        second.id,
      ]);
      expect(returned.map((document: { position: number }) => document.position)).toEqual([
        1, 2, 3,
      ]);

      const persisted = (await listDocuments(app, jar, project.id))
        .filter((document) => document.kind === "chapter")
        .sort((left, right) => left.position - right.position);
      expect(persisted.map((document) => document.id)).toEqual([third.id, seed.id, second.id]);
    } finally {
      await app.close();
    }
  });

  it("deletes a document together with its revisions", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Deletion");
      const extra = await seedDocument(app, jar, project.id, {
        kind: "note",
        title: "Temporary",
        content_markdown: "bye",
      });
      expect(await listRevisions(app, jar, project.id, extra.id)).toHaveLength(1);

      const response = await call(
        app,
        jar,
        "DELETE",
        `/api/projects/${project.id}/documents/${extra.id}`,
      );
      expect(response.statusCode).toBe(204);

      const db = app.studioDb?.db;
      expect(db!.select().from(documents).all()).toHaveLength(1); // the seed remains
      expect(db!.select().from(documentRevisions).all()).toHaveLength(1); // seed revision remains

      const missing = await call(
        app,
        jar,
        "GET",
        `/api/projects/${project.id}/documents/${extra.id}`,
      );
      expect(missing.statusCode).toBe(404);
    } finally {
      await app.close();
    }
  });

  it("rejects deletion of a review-snapshotted document without losing immutable records", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Protected review");
      const protectedDocument = project.documents.at(0);
      if (protectedDocument === undefined) {
        throw new Error("Seeded projects must include a document.");
      }
      const createdReview = await call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
      expect(createdReview.statusCode, createdReview.body).toBe(201);
      const review = createdReview.json();

      const db = app.studioDb?.db;
      if (db === undefined) {
        throw new Error("Studio database must be available.");
      }
      const snapshotState = () => ({
        document: db.select().from(documents).where(eq(documents.id, protectedDocument.id)).get(),
        revisions: db
          .select()
          .from(documentRevisions)
          .where(eq(documentRevisions.documentId, protectedDocument.id))
          .all(),
        snapshots: db
          .select()
          .from(projectSnapshots)
          .where(eq(projectSnapshots.projectId, project.id))
          .all(),
        references: db
          .select()
          .from(snapshotDocuments)
          .where(eq(snapshotDocuments.documentId, protectedDocument.id))
          .all(),
        assessments: db.select().from(reviews).where(eq(reviews.projectId, project.id)).all(),
      });
      const before = snapshotState();
      expect(before.document).toMatchObject({ id: protectedDocument.id });
      const revisionId = before.document?.currentRevisionId;
      if (revisionId === null || revisionId === undefined) {
        throw new Error("Seeded document must have a current revision.");
      }
      expect(before.revisions).toHaveLength(1);
      expect(before.snapshots).toHaveLength(1);
      expect(before.references).toEqual([
        expect.objectContaining({
          documentId: protectedDocument.id,
          revisionId,
        }),
      ]);
      expect(before.assessments).toEqual([
        expect.objectContaining({
          id: review.id,
          snapshotId: review.snapshot_id,
        }),
      ]);

      const deletion = await call(
        app,
        jar,
        "DELETE",
        `/api/projects/${project.id}/documents/${protectedDocument.id}`,
      );
      expect(deletion.statusCode, deletion.body).toBe(409);
      const error = deletion.json().error;
      expect(error.code).toBe("SNAPSHOT_CONFLICT");
      expect(error.message).toBe("Document is referenced by an immutable snapshot.");
      expect(deletion.json()).not.toHaveProperty("detail");
      expect(error).not.toHaveProperty("detail");

      expect(snapshotState()).toEqual(before);
    } finally {
      await app.close();
    }
  });
});
