import { describe, expect, it } from "vitest";

import { buildFtsMatchQuery } from "../../src/contexts/studio/application/fts_match_query.js";
import {
  anonymousCall,
  buildStudioApp,
  call,
  getProject,
  ownerJar,
  seedDocument,
  seedProject,
} from "./studio_helpers.js";

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

function ftsRowCount(app: Parameters<typeof call>[0], sql: string, value: string): number {
  const row = app.studioDb?.raw.prepare(sql).get(value) as { n: number } | undefined;
  return row?.n ?? -1;
}

describe("match-query reduction (pure)", () => {
  it("reduces the operator-laden spec query to first-8 quoted word tokens joined with AND", () => {
    expect(buildFtsMatchQuery('dragon OR title:( NEAR(a b) wolf* ) "quotes"')).toBe(
      '"dragon" "or" "title" "near" "a" "b" "wolf" "quotes"',
    );
  });

  it("case-folds and de-duplicates preserving first occurrence, capping at 8 tokens", () => {
    expect(buildFtsMatchQuery("Lantern lantern LANTERN glows")).toBe('"lantern" "glows"');
    const crowded = "b b a a c c d d e e f f g g h h i i j j";
    expect(buildFtsMatchQuery(crowded)).toBe('"b" "a" "c" "d" "e" "f" "g" "h"');
  });

  it("returns null for empty and punctuation-only input", () => {
    expect(buildFtsMatchQuery("")).toBeNull();
    expect(buildFtsMatchQuery("!!! ??? *** ( ) \" '")).toBeNull();
  });
});

describe("project full-text query surface", () => {
  it("finds the new-project seed content (ranked snippets scenario)", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Seeded");
      const found = await queryDocuments(app, jar, project.id, "chapter");
      expect(found.statusCode, found.body).toBe(200);
      expect(found.results.length).toBe(1);
      const seed = found.results[0];
      if (seed === undefined) throw new Error("expected search result");
      expect(seed.title).toBe("Chapter 1");
      expect(seed.excerpt).not.toContain("<mark>");
      expect(seed.excerpt.length).toBeGreaterThan(0);
    } finally {
      await app.close();
    }
  });

  it("orders results by relevance rank; excerpts truncate to the 16-token window with ellipses", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Ranked");
      const fillerBefore = Array.from({ length: 24 }, (_, i) => `dune${i}`).join(" ");
      const fillerAfter = Array.from({ length: 24 }, (_, i) => `wave${i}`).join(" ");
      const rare = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Once Only",
        content_markdown: `${fillerBefore} a single lantern burns ${fillerAfter}`,
      });
      const frequent = await seedDocument(app, jar, project.id, {
        kind: "note",
        title: "Thrice Bright",
        content_markdown: "lantern lantern lantern above the cliffs the lantern keeper waits",
      });
      const found = await queryDocuments(app, jar, project.id, "lantern");
      expect(found.statusCode, found.body).toBe(200);
      expect(found.results.map((item) => item.document_id)).toEqual([frequent.id, rare.id]);
      for (const item of found.results) {
        expect(Object.keys(item).sort()).toEqual(["document_id", "excerpt", "title"]);
        expect(item.excerpt).toContain("lantern");
        expect(item.excerpt).not.toContain("<mark>");
      }
      const windowed = found.results.find((item) => item.document_id === rare.id);
      if (windowed === undefined) throw new Error("expected windowed result");
      expect(windowed.excerpt).toContain(" … ");
      const excerptTokens = windowed.excerpt.match(/[\p{L}\p{N}_]+/gu) ?? [];
      expect(excerptTokens.length).toBeLessThanOrEqual(16);
    } finally {
      await app.close();
    }
  });

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

  it("matches reduced tokens with AND semantics; operator-laden input stays a 200", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Operators");
      const doc = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Wolves",
        content_markdown: "the dragon sleeps while the wolf sings",
      });
      await seedDocument(app, jar, project.id, {
        kind: "note",
        title: "Only Dragon",
        content_markdown: "just a dragon here",
      });

      const reordered = await queryDocuments(app, jar, project.id, "sings wolf");
      expect(reordered.statusCode, reordered.body).toBe(200);
      expect(reordered.results.map((item) => item.document_id)).toEqual([doc.id]);

      const hostile = await queryDocuments(
        app,
        jar,
        project.id,
        'dragon OR title:( NEAR(a b) wolf* ) "quotes"',
      );
      expect(hostile.statusCode, hostile.body).toBe(200);
      expect(hostile.results).toEqual([]);

      const wildcardShaped = await queryDocuments(app, jar, project.id, "dragon* NEAR(wolf)");
      expect(wildcardShaped.statusCode, wildcardShaped.body).toBe(200);
      expect(wildcardShaped.results).toEqual([]);
    } finally {
      await app.close();
    }
  });

  it("returns an empty list for irreducible queries and 422 when q is missing", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Empty");
      for (const q of ["", "!!! ???", "  "]) {
        const found = await queryDocuments(app, jar, project.id, q);
        expect(found.statusCode, found.body).toBe(200);
        expect(found.results).toEqual([]);
      }
      const missing = await call(app, jar, "GET", `/api/projects/${project.id}/search`);
      expect(missing.statusCode).toBe(422);
      expect(missing.json().error.code).toBe("VALIDATION_ERROR");
    } finally {
      await app.close();
    }
  });

  it("refreshes the index inside the save transaction: new token found, old token gone, one row", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Refresh");
      const projectView = await getProject(app, jar, project.id);
      const doc = projectView.documents[0];
      if (doc === undefined) throw new Error("expected seeded document");
      const saved = await call(app, jar, "PUT", `/api/projects/${project.id}/documents/${doc.id}`, {
        content_markdown: "the moonrise ferry crosses at dawn",
        base_revision_id: doc.current_revision_id,
      });
      expect(saved.statusCode, saved.body).toBe(200);

      const fresh = await queryDocuments(app, jar, project.id, "moonrise");
      expect(fresh.results.map((item) => item.document_id)).toEqual([doc.id]);
      const stale = await queryDocuments(app, jar, project.id, "ferry OR moonrise");
      expect(stale.results).toEqual([]);
      expect(
        ftsRowCount(app, "SELECT COUNT(*) AS n FROM document_search WHERE document_id = ?", doc.id),
      ).toBe(1);
    } finally {
      await app.close();
    }
  });

  it("drops a deleted document from results immediately, cleaning its index row in the same transaction", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Vanish");
      const doc = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Zephyr",
        content_markdown: "the zephyrblade cuts the dune grass",
      });
      expect((await queryDocuments(app, jar, project.id, "zephyrblade")).results).toHaveLength(1);

      const removed = await call(
        app,
        jar,
        "DELETE",
        `/api/projects/${project.id}/documents/${doc.id}`,
      );
      expect(removed.statusCode).toBe(204);
      expect((await queryDocuments(app, jar, project.id, "zephyrblade")).results).toEqual([]);
      expect(
        ftsRowCount(app, "SELECT COUNT(*) AS n FROM document_search WHERE document_id = ?", doc.id),
      ).toBe(0);
    } finally {
      await app.close();
    }
  });

  it("clears every FTS row of a deleted project in its deleting transaction", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Project Cleanup");
      await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Bramble",
        content_markdown: "bramblequill scratches the parchment",
      });
      expect((await queryDocuments(app, jar, project.id, "bramblequill")).results).toHaveLength(1);

      const removed = await call(app, jar, "DELETE", `/api/projects/${project.id}`);
      expect(removed.statusCode).toBe(204);
      expect(
        ftsRowCount(
          app,
          "SELECT COUNT(*) AS n FROM document_search WHERE project_id = ?",
          project.id,
        ),
      ).toBe(0);
      expect((await queryDocuments(app, jar, project.id, "bramblequill")).statusCode).toBe(404);
    } finally {
      await app.close();
    }
  });

  it("caps results at 30 when more documents match", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Capped");
      for (let index = 1; index <= 32; index += 1) {
        await seedDocument(app, jar, project.id, {
          kind: "note",
          title: `Cap ${String(index).padStart(2, "0")}`,
          content_markdown: `bramblequill note number ${index} of many`,
        });
      }
      const found = await queryDocuments(app, jar, project.id, "bramblequill");
      expect(found.statusCode, found.body).toBe(200);
      expect(found.results).toHaveLength(30);
    } finally {
      await app.close();
    }
  });

  it("stays principal-scoped: other principals' projects are not found", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Scoped");
      const anonymous = await anonymousCall(
        app,
        "GET",
        `/api/projects/${project.id}/search?q=chapter`,
      );
      expect(anonymous.statusCode).toBe(401);

      const unknown = await queryDocuments(
        app,
        jar,
        "00000000-0000-0000-0000-000000000000",
        "chapter",
      );
      expect(unknown.statusCode).toBe(404);
    } finally {
      await app.close();
    }
  });
});
