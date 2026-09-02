import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import { projects } from "../../src/contexts/studio/infrastructure/db/schema.js";
import {
  buildDocumentSummariesQuery,
  buildScopedCurrentDocumentQuery,
} from "../../src/contexts/studio/infrastructure/db/studio_query_helpers.js";
import {
  buildStudioApp,
  call,
  monotonicClock,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

interface Statement {
  query: string;
  params: unknown[];
}

function authStatements(statements: Statement[]): Statement[] {
  return statements.filter(({ query }) => query.includes('"sessions"'));
}

function studioStatements(statements: Statement[]): Statement[] {
  return statements.filter(({ query }) => !query.includes('"sessions"'));
}

describe("public project-read query budgets", () => {
  it("attributes fixed auth and bounded shell/current projections", async () => {
    const statements: Statement[] = [];
    const { app } = await buildStudioApp(monotonicClock(), {
      databaseQueryLogger: {
        logQuery: (query, params) => statements.push({ query, params }),
      },
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Query budgets");
      const target = await seedDocument(app, owner, project.id, {
        kind: "note",
        title: "Target",
        content_markdown: "target body",
      });
      for (let index = 0; index < 8; index += 1) {
        await seedDocument(app, owner, project.id, {
          kind: "note",
          title: `Sibling ${index}`,
          content_markdown: `private sibling body ${index} `.repeat(2_000),
        });
      }

      statements.length = 0;
      const shell = await call(app, owner, "GET", `/api/projects/${project.id}`);
      expect(shell.statusCode, shell.body).toBe(200);
      const shellAuth = authStatements(statements);
      const shellProjection = studioStatements(statements);
      expect(shellAuth).toHaveLength(2);
      expect(shellProjection).toHaveLength(3);
      expect(statements).toHaveLength(shellAuth.length + shellProjection.length);
      expect(shellProjection.map(({ query }) => query).join("\n")).not.toMatch(
        /content_markdown|metadata_json|\."source"/,
      );

      statements.length = 0;
      const current = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/documents/${target.id}`,
      );
      expect(current.statusCode, current.body).toBe(200);
      const currentAuth = authStatements(statements);
      const currentProjection = studioStatements(statements);
      expect(currentAuth).toHaveLength(2);
      expect(currentProjection.length).toBeLessThanOrEqual(2);
      expect(statements).toHaveLength(currentAuth.length + currentProjection.length);
      expect(
        currentProjection.filter(({ query }) => query.includes("content_markdown")),
      ).toHaveLength(1);
      expect(
        currentProjection
          .flatMap(({ params }) => params)
          .filter((parameter) => parameter === target.id),
      ).toHaveLength(1);

      statements.length = 0;
      const documentIds = shell
        .json()
        .documents.map((document: { id: string }) => document.id)
        .reverse();
      const reorder = await call(
        app,
        owner,
        "PUT",
        `/api/projects/${project.id}/documents/reorder`,
        { document_ids: documentIds },
      );
      expect(reorder.statusCode, reorder.body).toBe(200);
      expect(
        studioStatements(statements)
          .map(({ query }) => query)
          .join("\n"),
      ).not.toMatch(/content_markdown|metadata_json|\."source"/);

      statements.length = 0;
      const anonymous = await app.inject({
        method: "GET",
        url: `/api/projects/${project.id}/documents/${target.id}`,
      });
      expect(anonymous.statusCode).toBe(401);
      expect(statements).toEqual([]);
    } finally {
      await app.close();
    }
  });

  it("uses indexed scope/current-revision access without history scans", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Read plans");
      const document = project.documents[0];
      if (document === undefined) throw new Error("expected seeded document");
      const studio = app.studioDb;
      if (studio === undefined) throw new Error("expected database");
      const ownerId = studio.db
        .select({ ownerId: projects.ownerId })
        .from(projects)
        .where(eq(projects.id, project.id))
        .get()?.ownerId;
      if (ownerId === undefined) throw new Error("expected project owner");

      const shellQuery = studio.db.transaction((tx) =>
        buildDocumentSummariesQuery(tx, project.id).toSQL(),
      );
      expect(shellQuery.sql).not.toMatch(/content_markdown|metadata_json|\."source"/);
      const shellPlan = studio.raw
        .prepare(`EXPLAIN QUERY PLAN ${shellQuery.sql}`)
        .all(...shellQuery.params) as Array<{ detail: string }>;
      const shellDetails = shellPlan.map(({ detail }) => detail).join("\n");
      expect(shellDetails).toContain("idx_documents_project_kind");
      expect(shellDetails).not.toMatch(/SCAN document_revisions|USE TEMP B-TREE/);

      const currentQuery = studio.db.transaction((tx) =>
        buildScopedCurrentDocumentQuery(tx, { ownerId }, project.id, document.id).toSQL(),
      );
      const currentPlan = studio.raw
        .prepare(`EXPLAIN QUERY PLAN ${currentQuery.sql}`)
        .all(...currentQuery.params) as Array<{ detail: string }>;
      const currentDetails = currentPlan.map(({ detail }) => detail).join("\n");
      expect(currentDetails).toMatch(/documents.*PRIMARY KEY|sqlite_autoindex_documents_1/);
      expect(currentDetails).toMatch(/projects.*PRIMARY KEY|sqlite_autoindex_projects_1/);
      expect(currentDetails).not.toMatch(/SCAN document_revisions|USE TEMP B-TREE/);
    } finally {
      await app.close();
    }
  });
});
