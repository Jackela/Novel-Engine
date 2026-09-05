import { drizzle } from "drizzle-orm/better-sqlite3";
import { describe, expect, it } from "vitest";

import { reviewPageLimit } from "../../src/contexts/studio/application/ports/studio_store.js";
import { buildReviewSummariesQuery } from "../../src/contexts/studio/infrastructure/review_page_queries.js";
import { ReviewStorePart } from "../../src/contexts/studio/infrastructure/review_store_part.js";
import * as databaseSchema from "../../src/shared/infrastructure/db/schema.js";
import {
  openReviewPageHarness,
  type ReviewPageHarness,
  recordReview,
  seedForeignProject,
} from "./review_page_harness.js";

describe("review page query budget and detail reads", () => {
  it("serves any page with one fixed statement budget and an index-backed plan", async () => {
    const harness = await openReviewPageHarness();
    try {
      for (let index = 0; index < 5; index += 1) recordReview(harness, index);
      const tracedFive = tracedStatements(harness, 5);
      for (let index = 5; index < 20; index += 1) recordReview(harness, index);
      const tracedTwenty = tracedStatements(harness, 20);

      const selectsFive = tracedFive.filter((query) => query.trim().startsWith("select"));
      const selectsTwenty = tracedTwenty.filter((query) => query.trim().startsWith("select"));
      expect(selectsTwenty.length).toBe(selectsFive.length);
      expect(selectsFive.length).toBe(3);
      expect(tracedFive.filter((query) => query.includes("review_issues"))).toHaveLength(1);
      const pageSql = selectsFive.filter((query) => query.includes('from "reviews"'));
      expect(pageSql.join("\n")).not.toContain("review_issues");
      expect(pageSql.join("\n")).not.toContain("snapshot_documents");
      expect(pageSql.join("\n")).not.toContain("document_revisions");

      const query = harness.database.db.transaction((tx) =>
        buildReviewSummariesQuery(tx, harness.projectId, {
          limit: reviewPageLimit(2),
          cursor: { createdAtMs: Date.parse("2026-09-05T01:00:00.000Z"), id: "boundary" },
        }).toSQL(),
      );
      expect(query.params.at(-1)).toBe(3);
      const plan = harness.database.raw
        .prepare(`EXPLAIN QUERY PLAN ${query.sql}`)
        .all(...query.params) as Array<{ detail: string }>;
      const details = plan.map((row) => row.detail).join("\n");
      expect(details).toContain("idx_reviews_project_created_id");
      expect(details).not.toContain("USE TEMP B-TREE");
    } finally {
      await harness.cleanup();
    }
  });

  it("resolves the scoped detail once without selecting revision bodies", async () => {
    const harness = await openReviewPageHarness();
    try {
      recordReview(harness, 0);
      const page = harness.reviewsStore.collectProjectReviewSummaries(
        harness.scope,
        harness.projectId,
        {
          limit: reviewPageLimit(1),
        },
      );
      const reviewId = page.reviews[0]?.id;
      if (reviewId === undefined) throw new Error("Expected a stored review.");

      const detail = harness.reviewsStore.findProjectReview(
        harness.scope,
        harness.projectId,
        reviewId,
      );
      expect(detail.issues).toHaveLength(1);
      expect(detail.issues[0]).toMatchObject({ code: "thin_chapter", severity: "warning" });

      const executedSql: string[] = [];
      const traced = drizzle(harness.database.raw, {
        schema: databaseSchema,
        logger: { logQuery: (query: string) => executedSql.push(query) },
      });
      new ReviewStorePart(traced as never).findProjectReview(
        harness.scope,
        harness.projectId,
        reviewId,
      );
      expect(executedSql.filter((query) => query.trim().startsWith("select"))).toHaveLength(4);
      expect(executedSql.join("\n")).not.toContain("content_markdown");
      expect(executedSql.join("\n")).not.toContain("metadata_json");

      const foreign = seedForeignProject(harness, "Foreign detail");
      expect(() =>
        harness.reviewsStore.findProjectReview(harness.scope, foreign.id, reviewId),
      ).toThrowError(expect.objectContaining({ name: "NotFoundError" }));
      expect(() =>
        harness.reviewsStore.findProjectReview(harness.scope, harness.projectId, "missing-review"),
      ).toThrowError(expect.objectContaining({ name: "NotFoundError" }));
    } finally {
      await harness.cleanup();
    }
  });
});

function tracedStatements(harness: ReviewPageHarness, expectedReviews: number): string[] {
  const count = (
    harness.database.raw.prepare("select count(*) as c from reviews").get() as { c: number }
  ).c;
  expect(count).toBe(expectedReviews);
  const executedSql: string[] = [];
  const traced = drizzle(harness.database.raw, {
    schema: databaseSchema,
    logger: { logQuery: (query: string) => executedSql.push(query) },
  });
  new ReviewStorePart(traced as never).collectProjectReviewSummaries(
    harness.scope,
    harness.projectId,
    {
      limit: reviewPageLimit(10),
    },
  );
  return executedSql;
}
