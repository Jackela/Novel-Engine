import { describe, expect, it, vi } from "vitest";
import { documentRevisions } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { encodeRevisionCursor } from "../../src/contexts/studio/interface/http/revision_cursor.js";
import { studioDatabase } from "./job_test_helpers.js";
import {
  anonymousCall,
  buildStudioApp,
  call,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

describe("revision pagination HTTP contract", () => {
  it("authenticates before query validation, then validates before scoped persistence", async () => {
    const { app } = await buildStudioApp();
    const historyRead = vi.spyOn(DrizzleStudioStore.prototype, "findRevisionSummaries");
    try {
      const projectId = "00000000-0000-4000-8000-000000000099";
      const documentId = "00000000-0000-4000-8000-000000000098";
      const path = `/api/projects/${projectId}/documents/${documentId}/revisions`;
      for (const query of [
        "limit=0",
        "cursor=not%2Bbase64url",
        `cursor=${"a".repeat(1025)}`,
        "limit=1&limit=2",
        "cursor=a&cursor=b",
      ]) {
        const anonymous = await anonymousCall(app, "GET", `${path}?${query}`);
        expect(anonymous.statusCode, anonymous.body).toBe(401);
        expect(anonymous.json().error.code).toBe("UNAUTHORIZED");
      }

      const owner = await ownerJar(app);
      const wrongProject = encodeRevisionCursor("another-project", documentId, {
        revisionNumber: 1,
        id: "revision-a",
      });
      const wrongDocument = encodeRevisionCursor(projectId, "another-document", {
        revisionNumber: 1,
        id: "revision-a",
      });
      const valid = encodeRevisionCursor(projectId, documentId, {
        revisionNumber: 1,
        id: "revision-a",
      });
      const encoded = (json: string) => Buffer.from(json, "utf8").toString("base64url");
      const invalidCursors = [
        "",
        "not+base64url",
        "a".repeat(1025),
        (valid ?? "").slice(0, -1),
        `${valid}=`,
        encoded(`[2,"${projectId}","${documentId}",1,"revision-a"]`),
        encoded(`[1,"${projectId}","${documentId}",-1,"revision-a"]`),
        encoded(`[1,"${projectId}","${documentId}",1.5,"revision-a"]`),
        encoded(`[1,"${projectId}","${documentId}",9007199254740992,"revision-a"]`),
        encoded(`[1,"${projectId}","${documentId}",1,"${"x".repeat(129)}"]`),
        encoded(`[1, "${projectId}","${documentId}",1,"revision-a"]`),
        wrongProject,
        wrongDocument,
      ];
      for (const cursor of invalidCursors) {
        const response = await call(
          app,
          owner,
          "GET",
          `${path}?cursor=${encodeURIComponent(cursor ?? "")}`,
        );
        expect(response.statusCode, response.body).toBe(422);
        expect(response.json().error.code).toBe("VALIDATION_ERROR");
        expect(response.json().error.details.errors[0].field).toBe("cursor");
      }
      expect(historyRead).not.toHaveBeenCalled();

      const validMissing = encodeRevisionCursor(projectId, documentId, {
        revisionNumber: 1,
        id: "revision-a",
      });
      const missing = await call(
        app,
        owner,
        "GET",
        `${path}?cursor=${encodeURIComponent(validMissing ?? "")}`,
      );
      expect(missing.statusCode, missing.body).toBe(404);
      expect(missing.json().error.code).toBe("NOT_FOUND");
      expect(historyRead).toHaveBeenCalledTimes(1);
    } finally {
      historyRead.mockRestore();
      await app.close();
    }
  });

  it("rejects every invalid limit and repeated query key after authentication", async () => {
    const { app } = await buildStudioApp();
    const historyRead = vi.spyOn(DrizzleStudioStore.prototype, "findRevisionSummaries");
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Revision limits");
      const document = project.documents[0];
      if (document === undefined) throw new Error("Expected the seeded document.");
      const path = `/api/projects/${project.id}/documents/${document.id}/revisions`;
      for (const query of [
        "limit=0",
        "limit=101",
        "limit=1.5",
        "limit=not-an-integer",
        "limit=1&limit=2",
        "cursor=a&cursor=b",
      ]) {
        const response = await call(app, owner, "GET", `${path}?${query}`);
        expect(response.statusCode, response.body).toBe(422);
        expect(response.json().error.code).toBe("VALIDATION_ERROR");
      }
      expect(historyRead).not.toHaveBeenCalled();
    } finally {
      historyRead.mockRestore();
      await app.close();
    }
  });

  it("binds a cursor to the route document even when another document exists", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Revision cursor scope");
      const first = project.documents[0];
      if (first === undefined) throw new Error("Expected the seeded document.");
      const second = await seedDocument(app, owner, project.id, {
        kind: "note",
        title: "Second",
      });
      const cursor = encodeRevisionCursor(project.id, first.id, {
        revisionNumber: 1,
        id: "revision-a",
      });
      const response = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/documents/${second.id}/revisions?cursor=${encodeURIComponent(cursor ?? "")}`,
      );
      expect(response.statusCode, response.body).toBe(422);
      expect(response.json().error.code).toBe("VALIDATION_ERROR");

      const otherProject = await seedProject(app, owner, "Other revision scope");
      const scopedCursor = encodeRevisionCursor(otherProject.id, first.id, {
        revisionNumber: 1,
        id: "revision-a",
      });
      const crossProjectDocument = await call(
        app,
        owner,
        "GET",
        `/api/projects/${otherProject.id}/documents/${first.id}/revisions?cursor=${encodeURIComponent(scopedCursor ?? "")}`,
      );
      expect(crossProjectDocument.statusCode, crossProjectDocument.body).toBe(404);
      expect(crossProjectDocument.json().error.code).toBe("NOT_FOUND");
    } finally {
      await app.close();
    }
  });

  it("returns bounded summary pages and traverses them without gaps or duplicates", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Revision HTTP traversal");
      const document = project.documents[0];
      if (document === undefined) throw new Error("Expected the seeded document.");
      studioDatabase(app)
        .insert(documentRevisions)
        .values(
          Array.from({ length: 100 }, (_, index) => {
            const revisionNumber = index + 2;
            return {
              id: `revision-${String(revisionNumber).padStart(3, "0")}`,
              documentId: document.id,
              parentRevisionId:
                revisionNumber === 2
                  ? null
                  : `revision-${String(revisionNumber - 1).padStart(3, "0")}`,
              revisionNumber,
              contentMarkdown: `word-${revisionNumber}`,
              metadataJson: `{"revision":${revisionNumber}}`,
              source: "author",
              wordCount: 1,
              createdAt: new Date(revisionNumber),
            };
          }),
        )
        .run();
      const path = `/api/projects/${project.id}/documents/${document.id}/revisions`;

      const defaultPage = await call(app, owner, "GET", path);
      expect(defaultPage.statusCode, defaultPage.body).toBe(200);
      expect(defaultPage.json().revisions).toHaveLength(50);
      expect(defaultPage.json().revisions[0]?.revision_number).toBe(101);
      expect(defaultPage.json().revisions[49]?.revision_number).toBe(52);
      expect(defaultPage.json().next_cursor).toEqual(expect.any(String));
      expect(Object.keys(defaultPage.json().revisions[0] ?? {}).sort()).toEqual(
        [
          "created_at",
          "document_id",
          "id",
          "parent_revision_id",
          "revision_number",
          "source",
          "word_count",
        ].sort(),
      );

      const minimumPage = await call(app, owner, "GET", `${path}?limit=1`);
      expect(minimumPage.statusCode, minimumPage.body).toBe(200);
      expect(minimumPage.json().revisions).toHaveLength(1);
      expect(minimumPage.json().revisions[0]?.revision_number).toBe(101);
      expect(minimumPage.json().next_cursor).toEqual(expect.any(String));

      const maximumPage = await call(app, owner, "GET", `${path}?limit=100`);
      expect(maximumPage.statusCode, maximumPage.body).toBe(200);
      expect(maximumPage.json().revisions).toHaveLength(100);
      expect(maximumPage.json().revisions[99]?.revision_number).toBe(2);
      expect(maximumPage.json().next_cursor).toEqual(expect.any(String));

      const revisionNumbers: number[] = [];
      let cursor: string | null = null;
      do {
        const response = await call(
          app,
          owner,
          "GET",
          `${path}?limit=37${cursor === null ? "" : `&cursor=${encodeURIComponent(cursor)}`}`,
        );
        expect(response.statusCode, response.body).toBe(200);
        revisionNumbers.push(
          ...response
            .json()
            .revisions.map((revision: { revision_number: number }) =>
              Number(revision.revision_number),
            ),
        );
        cursor = response.json().next_cursor;
      } while (cursor !== null);
      expect(revisionNumbers).toHaveLength(101);
      expect(new Set(revisionNumbers).size).toBe(101);
      expect(revisionNumbers).toEqual(Array.from({ length: 101 }, (_, index) => 101 - index));
    } finally {
      await app.close();
    }
  });

  it("documents bounded queries, validation, and the closed summary response", async () => {
    const { app } = await buildStudioApp();
    try {
      const document = (await app.inject({ method: "GET", url: "/openapi.json" })).json();
      const operation =
        document.paths["/api/projects/{projectId}/documents/{documentId}/revisions"].get;
      const parameters = Object.fromEntries(
        operation.parameters.map((parameter: { name: string; schema: object }) => [
          parameter.name,
          parameter.schema,
        ]),
      );
      expect(parameters.limit).toMatchObject({
        type: "integer",
        default: 50,
        minimum: 1,
        maximum: 100,
      });
      expect(parameters.cursor).toMatchObject({
        type: "string",
        minLength: 1,
        maxLength: 1024,
        pattern: "^[A-Za-z0-9_-]+$",
      });
      expect(operation.responses["422"]).toBeDefined();
      const response = operation.responses["200"].content["application/json"].schema;
      expect(response.required).toEqual(expect.arrayContaining(["revisions", "next_cursor"]));
      expect(response.properties.next_cursor).toEqual({ type: "string", nullable: true });
      const summary = response.properties.revisions.items;
      expect(Object.keys(summary.properties).sort()).toEqual(
        [
          "created_at",
          "document_id",
          "id",
          "parent_revision_id",
          "revision_number",
          "source",
          "word_count",
        ].sort(),
      );
      expect(summary.required).toHaveLength(7);
      expect(summary.additionalProperties).toBe(false);
      expect(summary.properties.source.enum).toEqual(["author", "ai-accepted", "restore"]);
      expect(summary.properties.word_count).toMatchObject({ type: "integer", minimum: 0 });
      expect(summary.properties.created_at).toMatchObject({ type: "string", format: "date-time" });
      expect(summary.properties).not.toHaveProperty("content_markdown");
      expect(summary.properties).not.toHaveProperty("metadata");
    } finally {
      await app.close();
    }
  });
});
