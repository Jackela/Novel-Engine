import { describe, expect, it } from "vitest";

import { buildStudioApp, call, ownerJar, seedDocument, seedProject } from "./studio_helpers.js";

/**
 * DR-030 input bounds of the search surface: `q` is capped by the request
 * schema (a longer value is a validation refusal, never a query), and
 * SQL-shaped input stays inert because the MATCH expression is always a
 * bound parameter built from quoted elements.
 */

async function queryDocuments(
  app: Parameters<typeof call>[0],
  jar: Parameters<typeof call>[1],
  projectId: string,
  q: string,
): Promise<{ statusCode: number; body: string; results: { document_id: string }[] }> {
  const response = await call(
    app,
    jar,
    "GET",
    `/api/projects/${projectId}/search?q=${encodeURIComponent(q)}`,
  );
  const parsed = response.statusCode === 200 ? response.json() : { results: [] };
  return { statusCode: response.statusCode, body: response.body, results: parsed.results };
}

describe("search input bounds (DR-030)", () => {
  it("rejects a query beyond the schema maxLength with 422 and accepts the bound itself", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Bounded");

      const tooLong = await call(
        app,
        jar,
        "GET",
        `/api/projects/${project.id}/search?q=${encodeURIComponent("a".repeat(201))}`,
      );
      expect(tooLong.statusCode).toBe(422);
      expect(tooLong.json().error.code).toBe("VALIDATION_ERROR");

      const atBound = await queryDocuments(app, jar, project.id, "a".repeat(200));
      expect(atBound.statusCode, atBound.body).toBe(200);
      expect(atBound.results).toEqual([]);
    } finally {
      await app.close();
    }
  });

  it("keeps SQL-shaped input inert and the index intact (parameter-bound MATCH)", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Inert");
      const doc = await seedDocument(app, jar, project.id, {
        kind: "note",
        title: "Keep",
        content_markdown: "keepword stays indexed through hostile input",
      });

      const hostile = await queryDocuments(
        app,
        jar,
        project.id,
        `"' ; DROP TABLE document_search; --`,
      );
      expect(hostile.statusCode, hostile.body).toBe(200);
      expect(hostile.results).toEqual([]);

      const intact = await queryDocuments(app, jar, project.id, "keepword");
      expect(intact.statusCode, intact.body).toBe(200);
      expect(intact.results.map((item) => item.document_id)).toEqual([doc.id]);
    } finally {
      await app.close();
    }
  });
});
