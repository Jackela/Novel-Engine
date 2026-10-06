import { describe, expect, it } from "vitest";

import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

interface MatchPayload {
  document_id: string;
  title: string;
  excerpt: string;
}

async function queryDocuments(
  app: Parameters<typeof call>[0],
  jar: Parameters<typeof call>[1],
  projectId: string,
  q: string,
): Promise<{ statusCode: number; body: string; results: MatchPayload[] }> {
  const response = await call(
    app,
    jar,
    "GET",
    `/api/projects/${projectId}/search?q=${encodeURIComponent(q)}`,
  );
  const parsed = response.statusCode === 200 ? response.json() : { results: [] };
  return { statusCode: response.statusCode, body: response.body, results: parsed.results };
}

/**
 * Relocated from studio_search.test.ts to keep that file inside the 300-code-
 * line budget; the assertions are unchanged. It pins the index-row reading
 * order — raw rows inserted straight into `document_search` — which is why it
 * lives with the store-level fixtures instead of the HTTP query surface.
 */
describe("project full-text index rows", () => {
  it("breaks equal relevance ranks by document id", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Rank ties");
      const raw = app.studioDb?.raw;
      if (raw === undefined) throw new Error("expected studio database handle");
      const lowerId = "00000000-0000-4000-8000-000000000001";
      const higherId = "00000000-0000-4000-8000-000000000002";
      const insert = raw.prepare(
        "INSERT INTO document_search(document_id, project_id, title, content) VALUES (?, ?, ?, ?)",
      );
      insert.run(higherId, project.id, "Equal B", "ranktietoken identical words");
      insert.run(lowerId, project.id, "Equal A", "ranktietoken identical words");

      const found = await queryDocuments(app, jar, project.id, "ranktietoken");
      expect(found.statusCode, found.body).toBe(200);
      expect(found.results.map((item) => item.document_id)).toEqual([lowerId, higherId]);
    } finally {
      await app.close();
    }
  });
});
