import { eq } from "drizzle-orm";
import { afterEach, describe, expect, it } from "vitest";

import type { EvaluatedReview } from "../../src/contexts/studio/application/ports/review_outcome_store.js";
import { ReviewSourceInvalidatedError } from "../../src/contexts/studio/domain/exceptions.js";
import {
  documentRevisions,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { ReviewStorePart } from "../../src/contexts/studio/infrastructure/review_store_part.js";
import {
  cleanupReviewOutcomeDirectories,
  evidenceCounts,
  NO_REVIEW_ROWS,
  openHarness,
} from "./review_outcome_harness.js";

afterEach(async () => {
  await cleanupReviewOutcomeDirectories();
});

describe("review outcome transactions", () => {
  it("lands the originally read revision after a concurrent author edit", async () => {
    const harness = await openHarness();
    try {
      const sourceDocument = harness.evaluation.source.documents[0];
      if (sourceDocument === undefined) throw new Error("Expected a captured source document.");
      const advanced = harness.store.documents.advanceDocument(
        harness.scope,
        harness.project.id,
        harness.document.id,
        {
          contentMarkdown: "A later author edit.",
          baseRevisionId: harness.document.currentRevisionId,
          title: null,
          metadataJson: "{}",
          source: "author",
          now: harness.now(),
        },
      );

      const completed = new ReviewStorePart(harness.database.db).recordCompletedReviewJob(
        harness.scope,
        harness.evaluation,
      );
      const captured = harness.database.db.select().from(snapshotDocuments).all();
      expect(captured).toHaveLength(1);
      expect(captured[0]?.revisionId).toBe(sourceDocument.revisionId);
      expect(captured[0]?.revisionId).not.toBe(advanced.currentRevisionId);
      expect(completed.job.status).toBe("completed");
      expect(JSON.parse(completed.job.resultJson).snapshot_id).toBe(
        completed.assessment.snapshotId,
      );
    } finally {
      harness.database.close();
    }
  });

  it("rolls back all fresh evidence when the completed event insert fails", async () => {
    const harness = await openHarness();
    try {
      class ExplodingFreshEventStore extends ReviewStorePart {
        protected override beforeFreshJobEventInsert(): never {
          throw new Error("simulated completed review event failure");
        }
      }
      const exploding = new ExplodingFreshEventStore(harness.database.db);
      expect(() => exploding.recordCompletedReviewJob(harness.scope, harness.evaluation)).toThrow(
        "simulated completed review event failure",
      );
      expect(evidenceCounts(harness.database.db)).toEqual(NO_REVIEW_ROWS);
      harness.store.documents.dropDocument(harness.scope, harness.project.id, harness.document.id);
    } finally {
      harness.database.close();
    }
  });

  it("rolls provisional snapshot rows back when review insertion fails", async () => {
    const harness = await openHarness();
    try {
      class ExplodingReviewInsertStore extends ReviewStorePart {
        protected override beforeReviewInsert(): never {
          throw new Error("simulated review insert failure");
        }
      }
      const exploding = new ExplodingReviewInsertStore(harness.database.db);
      expect(() => exploding.recordCompletedReviewJob(harness.scope, harness.evaluation)).toThrow(
        "simulated review insert failure",
      );
      expect(evidenceCounts(harness.database.db)).toEqual(NO_REVIEW_ROWS);
      harness.store.documents.dropDocument(harness.scope, harness.project.id, harness.document.id);
    } finally {
      harness.database.close();
    }
  });

  it("keeps serialization defects visible and rolls review evidence back", async () => {
    const harness = await openHarness();
    try {
      const cyclicEvidence: Record<string, unknown> = {};
      cyclicEvidence.self = cyclicEvidence;
      const issue = harness.evaluation.issues[0];
      if (issue === undefined) throw new Error("Expected an evaluated review issue.");
      const invalidEvaluation: EvaluatedReview = {
        ...harness.evaluation,
        issues: [{ ...issue, evidence: cyclicEvidence }],
      };
      expect(() =>
        new ReviewStorePart(harness.database.db).recordCompletedReviewJob(
          harness.scope,
          invalidEvaluation,
        ),
      ).toThrow(TypeError);
      expect(evidenceCounts(harness.database.db)).toEqual(NO_REVIEW_ROWS);
    } finally {
      harness.database.close();
    }
  });

  it("rolls review evidence back when a retry transition fails", async () => {
    const harness = await openHarness();
    try {
      const original = harness.store.jobs.addJob(harness.scope, {
        projectId: harness.project.id,
        documentId: null,
        kind: "review",
        operation: "review",
        status: "failed",
        provider: "mock",
        model: "",
        requestJson: "{}",
        resultJson: "{}",
        error: "provider unavailable",
        eventDetailsJson: "{}",
        now: harness.now(),
      });
      const retry = harness.store.jobs.addJob(harness.scope, {
        projectId: harness.project.id,
        documentId: null,
        kind: "review",
        operation: "review",
        status: "running",
        provider: "mock",
        model: "",
        requestJson: "{}",
        resultJson: "{}",
        error: null,
        retryOfJobId: original.id,
        eventDetailsJson: JSON.stringify({ retry_of: original.id }),
        now: harness.now(),
      });
      const retryBefore = harness.store.jobs.findJob(harness.scope, harness.project.id, retry.id);
      class ExplodingRetryEventStore extends ReviewStorePart {
        protected override beforeRetryEventInsert(): never {
          throw new Error("simulated review retry event failure");
        }
      }
      const exploding = new ExplodingRetryEventStore(harness.database.db);
      expect(() =>
        exploding.completeReviewRetryJob(
          harness.scope,
          harness.project.id,
          retry.id,
          harness.evaluation,
        ),
      ).toThrow("simulated review retry event failure");
      expect(evidenceCounts(harness.database.db)).toMatchObject({
        snapshots: 0,
        snapshotDocuments: 0,
        reviews: 0,
        issues: 0,
        jobs: 2,
        events: 2,
      });
      const retryAfter = harness.store.jobs.findJob(harness.scope, harness.project.id, retry.id);
      expect(retryAfter).toMatchObject({
        status: "running",
        model: "",
        resultJson: "{}",
        error: null,
      });
      expect(retryAfter.updatedAt).toEqual(retryBefore.updatedAt);
      expect(retryAfter.events).toEqual(retryBefore.events);
      harness.store.documents.dropDocument(harness.scope, harness.project.id, harness.document.id);
    } finally {
      harness.database.close();
    }
  });

  it("rejects a deleted source without writing partial evidence", async () => {
    const harness = await openHarness();
    try {
      const sourceDocument = harness.evaluation.source.documents[0];
      if (sourceDocument === undefined) throw new Error("Expected a captured source document.");
      harness.database.db
        .update(documentRevisions)
        .set({ contentMarkdown: "tampered immutable content" })
        .where(eq(documentRevisions.id, sourceDocument.revisionId))
        .run();
      expect(() =>
        new ReviewStorePart(harness.database.db).recordCompletedReviewJob(
          harness.scope,
          harness.evaluation,
        ),
      ).toThrow("Persisted immutable review source changed after capture.");
      expect(evidenceCounts(harness.database.db)).toEqual(NO_REVIEW_ROWS);
      harness.database.db
        .update(documentRevisions)
        .set({ contentMarkdown: sourceDocument.contentMarkdown })
        .where(eq(documentRevisions.id, sourceDocument.revisionId))
        .run();
      harness.store.documents.dropDocument(harness.scope, harness.project.id, harness.document.id);
      expect(() =>
        new ReviewStorePart(harness.database.db).recordCompletedReviewJob(
          harness.scope,
          harness.evaluation,
        ),
      ).toThrow(ReviewSourceInvalidatedError);
      expect(evidenceCounts(harness.database.db)).toEqual(NO_REVIEW_ROWS);
    } finally {
      harness.database.close();
    }
  });
});
