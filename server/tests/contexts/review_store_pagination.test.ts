import { describe, expect, it } from "vitest";

import {
  type ReviewPageCursor,
  type ReviewPageLimit,
  reviewPageLimit,
} from "../../src/contexts/studio/application/ports/studio_store.js";
import { openReviewPageHarness, recordReview, seedForeignProject } from "./review_page_harness.js";

describe("review summary keyset pages", () => {
  it("returns at most the newest 50 lightweight summaries by default", async () => {
    const harness = await openReviewPageHarness();
    try {
      for (let index = 0; index < 51; index += 1) recordReview(harness, index);

      const page = harness.reviewsStore.collectProjectReviewSummaries(
        harness.scope,
        harness.projectId,
        {
          limit: reviewPageLimit(50),
        },
      );

      expect(page.reviews).toHaveLength(50);
      expect(page.reviews.at(0)?.summary).toBe("review completed");
      expect(Object.keys(page.reviews[0] ?? {}).sort()).toEqual(
        [
          "createdAt",
          "id",
          "issueCount",
          "model",
          "projectId",
          "provider",
          "snapshotId",
          "summary",
        ].sort(),
      );
      expect(page.reviews.filter((review) => review.issueCount === 1)).toHaveLength(25);
      expect(page.reviews.filter((review) => review.issueCount === 0)).toHaveLength(25);
      expect(page.nextCursor).toEqual({
        createdAtMs: page.reviews[49]?.createdAt.getTime(),
        id: page.reviews[49]?.id,
      });
    } finally {
      await harness.cleanup();
    }
  });

  it("rejects invalid direct-store limits before reading a page", async () => {
    const harness = await openReviewPageHarness();
    try {
      for (const invalid of [0, 101, 1.5, Number.NaN]) {
        expect(() =>
          harness.reviewsStore.collectProjectReviewSummaries(harness.scope, harness.projectId, {
            limit: invalid as ReviewPageLimit,
          }),
        ).toThrow(RangeError);
      }
    } finally {
      await harness.cleanup();
    }
  });

  it("traverses every review once, tie-breaks equal timestamps by id, and ends null", async () => {
    const harness = await openReviewPageHarness();
    try {
      const sharedTimestamp = new Date(Date.parse("2026-09-05T02:00:00.000Z"));
      recordReview(harness, 0, sharedTimestamp);
      recordReview(harness, 1, sharedTimestamp);
      for (let index = 2; index < 5; index += 1) recordReview(harness, index);

      const first = harness.reviewsStore.collectProjectReviewSummaries(
        harness.scope,
        harness.projectId,
        {
          limit: reviewPageLimit(2),
        },
      );
      const tied = first.reviews;
      expect(tied).toHaveLength(2);
      const newerTied = tied[0];
      const olderTied = tied[1];
      if (newerTied === undefined || olderTied === undefined) {
        throw new Error("Expected two tied reviews.");
      }
      expect(newerTied.createdAt.getTime()).toBe(olderTied.createdAt.getTime());
      expect(newerTied.id > olderTied.id).toBe(true);
      expect(first.nextCursor).not.toBeNull();
      if (first.nextCursor === null) throw new Error("Expected an older review page.");

      const visited: string[] = [...tied.map((review) => review.id)];
      let cursor: ReviewPageCursor | null = first.nextCursor;
      while (cursor !== null) {
        const page = harness.reviewsStore.collectProjectReviewSummaries(
          harness.scope,
          harness.projectId,
          {
            limit: reviewPageLimit(2),
            cursor,
          },
        );
        visited.push(...page.reviews.map((review) => review.id));
        cursor = page.nextCursor;
      }
      expect(visited).toHaveLength(5);
      expect(new Set(visited).size).toBe(5);
    } finally {
      await harness.cleanup();
    }
  });

  it("keeps a saved cursor ahead of reviews completed after the page", async () => {
    const harness = await openReviewPageHarness();
    try {
      for (let index = 0; index < 3; index += 1) recordReview(harness, index);
      const first = harness.reviewsStore.collectProjectReviewSummaries(
        harness.scope,
        harness.projectId,
        {
          limit: reviewPageLimit(1),
        },
      );
      expect(first.nextCursor).not.toBeNull();
      if (first.nextCursor === null) throw new Error("Expected an older review page.");

      recordReview(harness, 99);

      const second = harness.reviewsStore.collectProjectReviewSummaries(
        harness.scope,
        harness.projectId,
        {
          limit: reviewPageLimit(2),
          cursor: first.nextCursor,
        },
      );
      expect(second.reviews.map((review) => review.id)).not.toContain(first.reviews[0]?.id);
      expect(second.reviews).toHaveLength(2);
    } finally {
      await harness.cleanup();
    }
  });

  it("scopes pages to the requesting owner's project", async () => {
    const harness = await openReviewPageHarness();
    try {
      recordReview(harness, 0);
      const foreign = seedForeignProject(harness, "Foreign");
      const page = harness.reviewsStore.collectProjectReviewSummaries(harness.scope, foreign.id, {
        limit: reviewPageLimit(10),
      });
      expect(page.reviews).toEqual([]);
      expect(page.nextCursor).toBeNull();
    } finally {
      await harness.cleanup();
    }
  });
});
