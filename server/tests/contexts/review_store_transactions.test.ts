import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { eq } from "drizzle-orm";
import { afterEach, describe, expect, it } from "vitest";

import type { EvaluatedReview } from "../../src/contexts/studio/application/ports/review_outcome_store.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { ReviewSourceInvalidatedError } from "../../src/contexts/studio/domain/exceptions.js";
import {
  documentRevisions,
  projectSnapshots,
  reviewIssues,
  reviews,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { ReviewStorePart } from "../../src/contexts/studio/infrastructure/review_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import type { StudioSqliteDatabase } from "../../src/shared/infrastructure/db/connection.js";
import { jobEvents, jobs } from "../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const directories: string[] = [];
const NO_REVIEW_ROWS = {
  snapshots: 0,
  snapshotDocuments: 0,
  reviews: 0,
  issues: 0,
  jobs: 0,
  events: 0,
};

afterEach(async () => {
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true })));
});

function clock(): () => Date {
  let milliseconds = Date.parse("2026-08-31T12:00:00.000Z");
  return () => new Date(++milliseconds);
}

async function openHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-review-outcome-"));
  directories.push(directory);
  const database = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  const now = clock();
  const store = new DrizzleStudioStore({ database: database.db });
  const auth = new AuthService({
    store: new DrizzleAuthStore(database.db),
    sessionSecret: "review-outcome-test-secret",
    now,
  });
  await auth.configureOwner("review-outcome-owner", "long-test-password");
  const principal = (await auth.createOwnerSession("review-outcome-owner", "long-test-password"))
    .principal;
  const scope = scopeForPrincipal(principal);
  const seeded = store.addProject(scope, {
    title: "Atomic review",
    description: "",
    settingsJson: "{}",
    seed: {
      kind: "chapter",
      title: "Chapter 1",
      contentMarkdown: "The first immutable review source.",
      metadataJson: "{}",
    },
    now: now(),
  });
  const document = seeded.documents[0];
  if (document === undefined) throw new Error("Expected a seeded review document.");
  const reviewsStore = new ReviewStorePart(database.db);
  const evaluation: EvaluatedReview = {
    source: reviewsStore.readReviewSource(scope, seeded.project.id, now()),
    provider: "mock",
    model: "review-model",
    summary: "review completed",
    completedAt: now(),
    issues: [
      {
        documentId: document.id,
        severity: "warning",
        code: "pacing",
        message: "The scene moves too quickly.",
        suggestion: "Add a reflective beat.",
        evidence: {},
      },
    ],
  };
  return { database, document, evaluation, now, project: seeded.project, scope, store };
}

function evidenceCounts(db: StudioSqliteDatabase) {
  return {
    snapshots: db.select().from(projectSnapshots).all().length,
    snapshotDocuments: db.select().from(snapshotDocuments).all().length,
    reviews: db.select().from(reviews).all().length,
    issues: db.select().from(reviewIssues).all().length,
    jobs: db.select().from(jobs).all().length,
    events: db.select().from(jobEvents).all().length,
  };
}

describe("review outcome transactions", () => {
  it("lands the originally read revision after a concurrent author edit", async () => {
    const harness = await openHarness();
    try {
      const sourceDocument = harness.evaluation.source.documents[0];
      if (sourceDocument === undefined) throw new Error("Expected a captured source document.");
      const advanced = harness.store.advanceDocument(
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
      harness.store.dropDocument(harness.scope, harness.project.id, harness.document.id);
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
      harness.store.dropDocument(harness.scope, harness.project.id, harness.document.id);
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
      const original = harness.store.addJob(harness.scope, {
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
      const retry = harness.store.addJob(harness.scope, {
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
      const retryBefore = harness.store.findJob(harness.scope, harness.project.id, retry.id);
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
      const retryAfter = harness.store.findJob(harness.scope, harness.project.id, retry.id);
      expect(retryAfter).toMatchObject({
        status: "running",
        model: "",
        resultJson: "{}",
        error: null,
      });
      expect(retryAfter.updatedAt).toEqual(retryBefore.updatedAt);
      expect(retryAfter.events).toEqual(retryBefore.events);
      harness.store.dropDocument(harness.scope, harness.project.id, harness.document.id);
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
      harness.store.dropDocument(harness.scope, harness.project.id, harness.document.id);
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
