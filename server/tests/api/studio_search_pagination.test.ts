import { describe, expect, it } from "vitest";

import { buildStudioApp, call, ownerJar, seedDocument, seedProject } from "./studio_helpers.js";

/**
 * DR-029 search pagination and locate data. The former `caps results at 30`
 * case moved here from studio_search.test.ts (that file's line budget) and is
 * strengthened: the default page still holds 30 rows, and the envelope now
 * carries the honest project-wide `total` plus the `next_offset` walk. A page
 * walk asserts sequential pages neither duplicate nor skip rows.
 */

interface MatchPayload {
  document_id: string;
  title: string;
  excerpt: string;
  match_term: string;
}

interface SearchEnvelope {
  statusCode: number;
  body: string;
  results: MatchPayload[];
  total: number | null;
  nextOffset: number | null;
}

async function queryDocuments(
  app: Parameters<typeof call>[0],
  jar: Parameters<typeof call>[1],
  projectId: string,
  q: string,
  page: { limit?: number; offset?: number } = {},
): Promise<SearchEnvelope> {
  const params = new URLSearchParams({ q });
  if (page.limit !== undefined) params.set("limit", String(page.limit));
  if (page.offset !== undefined) params.set("offset", String(page.offset));
  const response = await call(app, jar, "GET", `/api/projects/${projectId}/search?${params}`);
  const parsed =
    response.statusCode === 200 ? response.json() : { results: [], total: null, next_offset: null };
  return {
    statusCode: response.statusCode,
    body: response.body,
    results: parsed.results,
    total: parsed.total,
    nextOffset: parsed.next_offset,
  };
}

describe("search pagination and locate data (DR-029)", () => {
  it("caps the default page at 30 with an honest total and next offset", async () => {
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
      expect(found.total).toBe(32);
      expect(found.nextOffset).toBe(30);
    } finally {
      await app.close();
    }
  });

  it("walks pages beyond the first 30 without duplicates or skipped rows", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Paged");
      const seeded = new Set<string>();
      for (let index = 1; index <= 35; index += 1) {
        const doc = await seedDocument(app, jar, project.id, {
          kind: "note",
          title: `Page ${String(index).padStart(2, "0")}`,
          content_markdown: `willowquill page item ${index} of many`,
        });
        seeded.add(doc.id);
      }

      const first = await queryDocuments(app, jar, project.id, "willowquill", { limit: 10 });
      expect(first.statusCode, first.body).toBe(200);
      expect(first.results).toHaveLength(10);
      expect(first.total).toBe(35);
      expect(first.nextOffset).toBe(10);

      const second = await queryDocuments(app, jar, project.id, "willowquill", {
        limit: 10,
        offset: first.nextOffset ?? 0,
      });
      expect(second.results).toHaveLength(10);
      expect(second.nextOffset).toBe(20);

      const third = await queryDocuments(app, jar, project.id, "willowquill", {
        limit: 10,
        offset: second.nextOffset ?? 0,
      });
      expect(third.results).toHaveLength(10);
      const fourth = await queryDocuments(app, jar, project.id, "willowquill", {
        limit: 10,
        offset: third.nextOffset ?? 0,
      });
      expect(fourth.results).toHaveLength(5);
      expect(fourth.nextOffset).toBeNull();

      const delivered = [...first.results, ...second.results, ...third.results, ...fourth.results];
      const ids = delivered.map((item) => item.document_id);
      expect(new Set(ids).size).toBe(35);
      expect(new Set(ids)).toEqual(seeded);
    } finally {
      await app.close();
    }
  });

  it("carries the first reduced element as the locate term, CJK included", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Locator");
      const doc = await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "贾府初见",
        content_markdown: "林黛玉初进贾府，宝玉叹道：这个妹妹我曾见过的。",
      });

      const latin = await queryDocuments(app, jar, project.id, "chapter");
      expect(latin.results[0]?.match_term).toBe("chapter");

      const cjk = await queryDocuments(app, jar, project.id, "黛玉");
      expect(cjk.results.map((item) => item.document_id)).toEqual([doc.id]);
      expect(cjk.results[0]?.match_term).toBe("黛玉");
      expect(cjk.results[0]?.match_term).not.toContain(" ");

      const mixed = await queryDocuments(app, jar, project.id, "黛玉 宝玉");
      expect(mixed.results.map((item) => item.document_id)).toEqual([doc.id]);
      expect(mixed.results[0]?.match_term).toBe("黛玉");
    } finally {
      await app.close();
    }
  });
});
