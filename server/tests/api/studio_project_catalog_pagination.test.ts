import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";
import { projectPageLimit } from "../../src/contexts/studio/application/ports/project_catalog_store.js";
import { projects as projectsTable } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { buildProjectCatalogSummariesQuery } from "../../src/contexts/studio/infrastructure/project_page_queries.js";
import { owners } from "../../src/shared/infrastructure/db/schema.js";
import { buildStudioApp, call, monotonicClock, ownerJar, seedProject } from "./studio_helpers.js";

function ownerScope(app: FastifyInstance): string {
  const database = app.studioDb?.db;
  if (database === undefined) throw new Error("expected studio database");
  const owner = database.select().from(owners).get();
  if (owner === undefined) throw new Error("expected owner row");
  return owner.id;
}

function insertCatalogRows(
  app: FastifyInstance,
  ownerId: string,
  rows: Array<{ id: string; title: string; updatedAt: Date }>,
): void {
  const database = app.studioDb?.db;
  if (database === undefined) throw new Error("expected studio database");
  database
    .insert(projectsTable)
    .values(
      rows.map((row) => ({
        id: row.id,
        ownerId,
        title: row.title,
        description: "",
        settingsJson: '{"provider":"mock"}',
        importHash: null,
        createdAt: row.updatedAt,
        updatedAt: row.updatedAt,
      })),
    )
    .run();
}

async function traverseCatalog(
  app: FastifyInstance,
  owner: Map<string, string>,
): Promise<Array<Record<string, unknown>>> {
  const collected: Array<Record<string, unknown>> = [];
  let cursor: string | null = null;
  do {
    const url =
      cursor === null
        ? "/api/projects?limit=3"
        : `/api/projects?limit=3&cursor=${encodeURIComponent(cursor)}`;
    const page = await call(app, owner, "GET", url);
    expect(page.statusCode, page.body).toBe(200);
    collected.push(...page.json().projects);
    cursor = page.json().next_cursor;
  } while (cursor !== null);
  return collected;
}

describe("project catalog pagination HTTP contract", () => {
  it("returns strict scalar summaries instead of complete projects", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      await seedProject(app, owner, "Catalog summary contract");

      const response = await call(app, owner, "GET", "/api/projects");
      expect(response.statusCode, response.body).toBe(200);
      expect(response.json().next_cursor).toBeNull();
      const [summary] = response.json().projects as Array<Record<string, unknown>>;
      expect(Object.keys(summary ?? {}).sort()).toEqual(
        ["created_at", "description", "id", "title", "updated_at"].sort(),
      );
      expect(summary).not.toHaveProperty("settings");
      expect(summary).not.toHaveProperty("import_hash");
    } finally {
      await app.close();
    }
  });

  it("rejects invalid limits through the validation envelope", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      await seedProject(app, owner, "Invalid catalog limits");
      for (const limit of ["0", "101", "1.5", "not-an-integer"]) {
        const response = await call(
          app,
          owner,
          "GET",
          `/api/projects?limit=${encodeURIComponent(limit)}`,
        );
        expect(response.statusCode, response.body).toBe(422);
        expect(response.json().error.code).toBe("VALIDATION_ERROR");
      }
    } finally {
      await app.close();
    }
  });

  it("returns and follows an owner-bound HTTP cursor without gaps or duplicates", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const seeded = await seedProject(app, owner, "Traversal seeded");
      insertCatalogRows(
        app,
        ownerScope(app),
        Array.from({ length: 8 }, (_, index) => ({
          id: `00000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
          title: `Direct ${index + 1}`,
          updatedAt: new Date(1_700_000_000_000 + index * 1_000),
        })),
      );

      const collected = await traverseCatalog(app, owner);
      expect(collected).toHaveLength(9);
      const ids = collected.map((row) => row.id);
      expect(new Set(ids).size).toBe(ids.length);
      expect(ids[0]).toBe(seeded.id);
      expect(ids.at(-1)).toBe("00000000-0000-4000-8000-000000000001");
      for (let index = 1; index < ids.length; index += 1) {
        const previous = collected[index - 1];
        const current = collected[index];
        if (previous === undefined || current === undefined) {
          throw new Error("expected ordered traversal pair");
        }
        expect(
          Date.parse(previous.updated_at as string) > Date.parse(current.updated_at as string) ||
            (Date.parse(previous.updated_at as string) ===
              Date.parse(current.updated_at as string) &&
              (previous.id as string) > (current.id as string)),
        ).toBe(true);
      }
    } finally {
      await app.close();
    }
  });

  it("applies the default and maximum page bounds at the authenticated HTTP seam", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      await seedProject(app, owner, "Bounds seeded");
      insertCatalogRows(
        app,
        ownerScope(app),
        Array.from({ length: 101 }, (_, index) => ({
          id: `20000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
          title: `Bounds ${index + 1}`,
          updatedAt: new Date(1_600_000_000_000 + index * 1_000),
        })),
      );

      const defaultPage = await call(app, owner, "GET", "/api/projects");
      expect(defaultPage.statusCode, defaultPage.body).toBe(200);
      expect(defaultPage.json().projects).toHaveLength(50);
      expect(defaultPage.json().next_cursor).toEqual(expect.any(String));

      const maximumPage = await call(app, owner, "GET", "/api/projects?limit=100");
      expect(maximumPage.statusCode, maximumPage.body).toBe(200);
      expect(maximumPage.json().projects).toHaveLength(100);
      expect(maximumPage.json().next_cursor).toEqual(expect.any(String));
    } finally {
      await app.close();
    }
  });

  it("keeps the id tie-break across a page boundary", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const tiedAt = new Date("2026-01-01T00:00:00.000Z");
      insertCatalogRows(
        app,
        ownerScope(app),
        Array.from({ length: 3 }, (_, index) => ({
          id: `30000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
          title: `Tied ${index + 1}`,
          updatedAt: tiedAt,
        })),
      );

      const first = await call(app, owner, "GET", "/api/projects?limit=2");
      expect(first.statusCode, first.body).toBe(200);
      expect(first.json().projects.map((row: { id: string }) => row.id)).toEqual([
        "30000000-0000-4000-8000-000000000003",
        "30000000-0000-4000-8000-000000000002",
      ]);
      const second = await call(
        app,
        owner,
        "GET",
        `/api/projects?limit=2&cursor=${encodeURIComponent(first.json().next_cursor)}`,
      );
      expect(second.statusCode, second.body).toBe(200);
      expect(second.json().projects.map((row: { id: string }) => row.id)).toEqual([
        "30000000-0000-4000-8000-000000000001",
      ]);
      expect(second.json().next_cursor).toBeNull();
    } finally {
      await app.close();
    }
  });

  it("does not inject a repositioned project into an older traversal", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const older = await seedProject(app, owner, "Older project");
      const newer = await seedProject(app, owner, "Newer project");
      insertCatalogRows(
        app,
        ownerScope(app),
        Array.from({ length: 2 }, (_, index) => ({
          id: `40000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
          title: `Below ${index + 1}`,
          updatedAt: new Date(1_500_000_000_000 + index * 1_000),
        })),
      );

      const first = await call(app, owner, "GET", "/api/projects?limit=2");
      expect(first.json().projects.map((row: { id: string }) => row.id)).toEqual([
        newer.id,
        older.id,
      ]);
      const retainedCursor = first.json().next_cursor;

      const patched = await call(app, owner, "PATCH", `/api/projects/${older.id}`, {
        title: "Older project, repositioned",
      });
      expect(patched.statusCode, patched.body).toBe(200);

      const olderPage = await call(
        app,
        owner,
        "GET",
        `/api/projects?limit=2&cursor=${encodeURIComponent(retainedCursor)}`,
      );
      expect(olderPage.statusCode, olderPage.body).toBe(200);
      expect(olderPage.json().projects.map((row: { id: string }) => row.id)).toEqual([
        "40000000-0000-4000-8000-000000000002",
        "40000000-0000-4000-8000-000000000001",
      ]);

      const fresh = await call(app, owner, "GET", "/api/projects?limit=1");
      expect(fresh.json().projects[0].id).toBe(older.id);
    } finally {
      await app.close();
    }
  });

  it("answers 401 before cursor validation for anonymous requests", async () => {
    const { app } = await buildStudioApp();
    try {
      const anonymous = await app.inject({
        method: "GET",
        url: "/api/projects?cursor=not-a-cursor&limit=0",
      });
      expect(anonymous.statusCode).toBe(401);
      expect(anonymous.json().error.code).toBe("UNAUTHORIZED");
    } finally {
      await app.close();
    }
  });

  it("projects only summary columns through the covering index", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      await seedProject(app, owner, "Plan evidence");
      const studio = app.studioDb;
      if (studio === undefined) throw new Error("expected database");

      const query = studio.db.transaction((tx) =>
        buildProjectCatalogSummariesQuery(
          tx,
          { ownerId: ownerScope(app) },
          { limit: projectPageLimit(50) },
        ).toSQL(),
      );
      const sqlText = query.sql;
      expect(sqlText).not.toMatch(/settings_json|import_hash/);
      const plan = studio.raw
        .prepare(`EXPLAIN QUERY PLAN ${sqlText}`)
        .all(...query.params) as Array<{ detail: string }>;
      const details = plan.map(({ detail }) => detail).join("\n");
      expect(details).toContain("idx_projects_owner_updated_id");
      expect(details).not.toMatch(/USE TEMP B-TREE/);
    } finally {
      await app.close();
    }
  });
});
