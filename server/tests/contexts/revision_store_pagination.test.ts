import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { eq } from "drizzle-orm";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { describe, expect, it } from "vitest";

import {
  type RevisionPageLimit,
  revisionPageLimit,
  scopeForPrincipal,
} from "../../src/contexts/studio/application/ports/studio_store.js";
import { documentRevisions } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { buildRevisionSummariesQuery } from "../../src/contexts/studio/infrastructure/revision_page_queries.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import * as databaseSchema from "../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

async function openHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-revision-page-"));
  const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3")).catch(
    async (error: unknown) => {
      await rm(directory, { recursive: true, force: true });
      throw error;
    },
  );
  const cleanup = async (): Promise<void> => {
    try {
      studio.close();
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  };
  try {
    const store = new DrizzleStudioStore({ database: studio.db });
    const now = new Date("2026-09-03T00:00:00.000Z");
    const auth = new AuthService({
      store: new DrizzleAuthStore(studio.db),
      sessionSecret: "revision-page-test-secret",
      now: () => now,
    });
    await auth.configureOwner("page-owner", "long-test-password");
    const principal = (await auth.createOwnerSession("page-owner", "long-test-password")).principal;
    const scope = scopeForPrincipal(principal);
    const { project, documents } = store.addProject(scope, {
      title: "Revision page",
      description: "",
      settingsJson: "{}",
      seed: {
        kind: "chapter",
        title: "Chapter 1",
        contentMarkdown: "seed",
        metadataJson: '{"large":"metadata"}',
      },
      now,
    });
    const document = documents[0];
    if (document === undefined) throw new Error("Expected the seeded document.");
    return { cleanup, documentId: document.id, projectId: project.id, scope, store, studio };
  } catch (error) {
    await cleanup();
    throw error;
  }
}

describe("document revision keyset pages", () => {
  it("returns at most the newest 50 lightweight summaries by default", async () => {
    const { cleanup, documentId, projectId, scope, store } = await openHarness();
    try {
      let baseRevisionId = store.findDocument(scope, projectId, documentId).currentRevisionId;
      for (let revisionNumber = 2; revisionNumber <= 51; revisionNumber += 1) {
        const advanced = store.advanceDocument(scope, projectId, documentId, {
          contentMarkdown: `body ${revisionNumber}`,
          baseRevisionId,
          title: null,
          metadataJson: `{"revision":${revisionNumber}}`,
          source: "author",
          now: new Date(revisionNumber),
        });
        baseRevisionId = advanced.currentRevisionId;
      }

      const page = store.findRevisionSummaries(scope, projectId, documentId, {
        limit: revisionPageLimit(50),
      });

      expect(page.revisions).toHaveLength(50);
      expect(page.revisions[0]?.revisionNumber).toBe(51);
      expect(page.revisions[49]?.revisionNumber).toBe(2);
      expect(page.nextCursor).toEqual({
        revisionNumber: 2,
        id: page.revisions[49]?.id,
      });
      expect(Object.keys(page.revisions[0] ?? {}).sort()).toEqual(
        [
          "createdAt",
          "documentId",
          "id",
          "parentRevisionId",
          "revisionNumber",
          "source",
          "wordCount",
        ].sort(),
      );
    } finally {
      await cleanup();
    }
  });

  it("rejects invalid direct-store limits before reading a page", async () => {
    const { cleanup, documentId, projectId, scope, store } = await openHarness();
    try {
      for (const invalid of [0, 101, 1.5, Number.NaN]) {
        expect(() =>
          store.findRevisionSummaries(scope, projectId, documentId, {
            limit: invalid as RevisionPageLimit,
          }),
        ).toThrow(RangeError);
      }
    } finally {
      await cleanup();
    }
  });

  it("continues below a deleted boundary without admitting a concurrently newer revision", async () => {
    const { cleanup, documentId, projectId, scope, store, studio } = await openHarness();
    try {
      let baseRevisionId = store.findDocument(scope, projectId, documentId).currentRevisionId;
      for (let revisionNumber = 2; revisionNumber <= 5; revisionNumber += 1) {
        const advanced = store.advanceDocument(scope, projectId, documentId, {
          contentMarkdown: `body ${revisionNumber}`,
          baseRevisionId,
          title: null,
          metadataJson: "{}",
          source: "author",
          now: new Date(revisionNumber),
        });
        baseRevisionId = advanced.currentRevisionId;
      }

      const first = store.findRevisionSummaries(scope, projectId, documentId, {
        limit: revisionPageLimit(2),
      });
      expect(first.revisions.map((revision) => revision.revisionNumber)).toEqual([5, 4]);
      expect(first.nextCursor).not.toBeNull();
      if (first.nextCursor === null) throw new Error("Expected an older revision page.");

      studio.db
        .delete(documentRevisions)
        .where(eq(documentRevisions.id, first.nextCursor.id))
        .run();
      store.advanceDocument(scope, projectId, documentId, {
        contentMarkdown: "body 6",
        baseRevisionId,
        title: null,
        metadataJson: "{}",
        source: "author",
        now: new Date(6),
      });

      const second = store.findRevisionSummaries(scope, projectId, documentId, {
        limit: revisionPageLimit(2),
        cursor: first.nextCursor,
      });
      expect(second.revisions.map((revision) => revision.revisionNumber)).toEqual([3, 2]);
      expect(second.revisions.map((revision) => revision.revisionNumber)).not.toContain(6);
      expect(second.nextCursor).not.toBeNull();
      if (second.nextCursor === null) throw new Error("Expected the terminal revision page.");

      const terminal = store.findRevisionSummaries(scope, projectId, documentId, {
        limit: revisionPageLimit(2),
        cursor: second.nextCursor,
      });
      expect(terminal.revisions.map((revision) => revision.revisionNumber)).toEqual([1]);
      expect(terminal.nextCursor).toBeNull();
    } finally {
      await cleanup();
    }
  });

  it("projects only stored summaries with one-row lookahead and index-backed ordering", async () => {
    const { cleanup, documentId, projectId, scope, studio } = await openHarness();
    try {
      studio.db
        .update(documentRevisions)
        .set({ wordCount: 777 })
        .where(eq(documentRevisions.documentId, documentId))
        .run();
      const executedSql: string[] = [];
      const tracedDatabase = drizzle(studio.raw, {
        schema: databaseSchema,
        logger: { logQuery: (query: string) => executedSql.push(query) },
      });
      const store = new DrizzleStudioStore({ database: tracedDatabase });

      const page = store.findRevisionSummaries(scope, projectId, documentId, {
        limit: revisionPageLimit(1),
      });

      expect(page.revisions[0]?.wordCount).toBe(777);
      const revisionSql = executedSql.find((query) => query.includes('from "document_revisions"'));
      expect(revisionSql).toBeDefined();
      expect(revisionSql).not.toContain("content_markdown");
      expect(revisionSql).not.toContain("metadata_json");

      const query = studio.db.transaction((tx) =>
        buildRevisionSummariesQuery(tx, documentId, {
          limit: revisionPageLimit(2),
          cursor: { revisionNumber: 5, id: "boundary" },
        }).toSQL(),
      );
      expect(query.sql).not.toContain("content_markdown");
      expect(query.sql).not.toContain("metadata_json");
      expect(query.params.at(-1)).toBe(3);
      const plan = studio.raw
        .prepare(`EXPLAIN QUERY PLAN ${query.sql}`)
        .all(...query.params) as Array<{ detail: string }>;
      const details = plan.map((row) => row.detail).join("\n");
      expect(details).toContain("uq_document_revision_number");
      expect(details).not.toContain("USE TEMP B-TREE");
    } finally {
      await cleanup();
    }
  });
});
