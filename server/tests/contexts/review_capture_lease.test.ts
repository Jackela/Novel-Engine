import { describe, expect, it } from "vitest";
import type { TextGenerationProviderFactory } from "../../src/contexts/ai/application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { ReviewService } from "../../src/contexts/studio/application/review_service.js";
import {
  projectSnapshots,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DocumentStorePart } from "../../src/contexts/studio/infrastructure/document_store_part.js";
import { RevisionRetentionPins } from "../../src/contexts/studio/infrastructure/RevisionRetentionPins.js";
import { ReviewStorePart } from "../../src/contexts/studio/infrastructure/review_store_part.js";
import {
  latestRevisionId,
  openRetentionHarness,
  revisionRows,
  SEED_TIME,
  save,
} from "./revision_retention_harness.js";

const validProvider: TextGenerationProviderFactory = (provider) => ({
  generateStructured: async () => ({
    step: "editorial_review",
    provider,
    model: "lease-model",
    rawText: '{"findings":[]}',
    content: { findings: [] },
    promptTokens: null,
    completionTokens: null,
  }),
});

/** The same explicit owner that the composition root supplies, with a real retention store. */
async function openPinnedHarness(factory = validProvider) {
  const harness = await openRetentionHarness();
  const pins = new RevisionRetentionPins();
  harness.store.documents = new DocumentStorePart(harness.studio.db, pins);
  const store = new ReviewStorePart(harness.studio.db, pins);
  const service = new ReviewService(store, {
    providerFactory: factory,
    now: () => new Date(SEED_TIME.getTime() + 2000),
  });
  const principal = {
    sessionId: "capture-test",
    kind: "owner" as const,
    ownerId: harness.scope.ownerId,
    expiresAt: null,
  };
  save(harness, "Captured prose", { at: 1000 });
  return { harness, pins, store, service, principal, capturedId: latestRevisionId(harness) };
}

describe("Review revision capture lease", () => {
  it("retains the captured revision after provider return until atomic landing, then releases", async () => {
    const { harness, pins, store, service, principal, capturedId } = await openPinnedHarness();
    try {
      const evaluation = await service.evaluateProject(principal, harness.projectId);
      expect(pins.has(capturedId)).toBe(true);
      expect(harness.studio.db.select().from(projectSnapshots).all()).toHaveLength(0);
      save(harness, "Edit between provider completion and landing", { at: 3000 });
      expect(revisionRows(harness.studio).some((row) => row.id === capturedId)).toBe(true);
      const completed = store.recordCompletedReviewJob(harness.scope, evaluation);
      expect(completed.job.status).toBe("completed");
      expect(pins.has(capturedId)).toBe(false);
      expect(harness.studio.db.select().from(snapshotDocuments).all()[0]?.revisionId).toBe(
        capturedId,
      );
      const unreferenced = latestRevisionId(harness);
      save(harness, "Normal autosave after successful landing", { at: 4000 });
      expect(revisionRows(harness.studio).some((row) => row.id === unreferenced)).toBe(false);
      expect(revisionRows(harness.studio).some((row) => row.id === capturedId)).toBe(true);
    } finally {
      await harness.cleanup();
    }
  });

  it.each(["provider", "invalid-payload", "cleanup"])(
    "releases without a snapshot after %s failure",
    async (failure) => {
      const factory: TextGenerationProviderFactory = (provider) => ({
        generateStructured: async () => {
          if (failure === "provider") throw new TextGenerationProviderError("provider failed");
          return {
            step: "editorial_review",
            provider,
            model: "lease-model",
            rawText: "{}",
            content: failure === "invalid-payload" ? {} : { findings: [] },
            promptTokens: null,
            completionTokens: null,
          };
        },
        dispose: async () => {
          if (failure === "cleanup") throw new Error("cleanup failed");
        },
      });
      const { harness, pins, service, principal, capturedId } = await openPinnedHarness(factory);
      try {
        if (failure === "cleanup") {
          const evaluation = await service.evaluateProject(principal, harness.projectId);
          evaluation.sourceLease?.release();
        } else
          await expect(service.evaluateProject(principal, harness.projectId)).rejects.toThrow();
        expect(pins.has(capturedId)).toBe(false);
        expect(harness.studio.db.select().from(projectSnapshots).all()).toHaveLength(0);
        save(harness, "Normal autosave after failed evaluation", { at: 3000 });
        expect(revisionRows(harness.studio).some((row) => row.id === capturedId)).toBe(false);
      } finally {
        await harness.cleanup();
      }
    },
  );

  it("independent concurrent reviews retain their own references, with idempotent release", async () => {
    const { harness, pins, service, principal, capturedId } = await openPinnedHarness();
    try {
      const [first, second] = await Promise.all([
        service.evaluateProject(principal, harness.projectId),
        service.evaluateProject(principal, harness.projectId),
      ]);
      first.sourceLease?.release();
      first.sourceLease?.release();
      expect(pins.has(capturedId)).toBe(true);
      save(harness, "Edit while second review owns capture", { at: 3000 });
      expect(revisionRows(harness.studio).some((row) => row.id === capturedId)).toBe(true);
      second.sourceLease?.release();
      expect(pins.has(capturedId)).toBe(false);
      expect(harness.studio.db.select().from(projectSnapshots).all()).toHaveLength(0);
    } finally {
      await harness.cleanup();
    }
  });

  it("releases on atomic landing failure without leaving provisional snapshot rows", async () => {
    const { harness, pins, service, principal, capturedId } = await openPinnedHarness();
    try {
      class ExplodingReviewStore extends ReviewStorePart {
        protected override beforeFreshJobEventInsert(): never {
          throw new Error("event failed");
        }
      }
      const evaluation = await service.evaluateProject(principal, harness.projectId);
      expect(() =>
        new ExplodingReviewStore(harness.studio.db, pins).recordCompletedReviewJob(
          harness.scope,
          evaluation,
        ),
      ).toThrow("event failed");
      expect(pins.has(capturedId)).toBe(false);
      expect(harness.studio.db.select().from(projectSnapshots).all()).toHaveLength(0);
      save(harness, "Normal autosave after failed landing", { at: 3000 });
      expect(revisionRows(harness.studio).some((row) => row.id === capturedId)).toBe(false);
    } finally {
      await harness.cleanup();
    }
  });

  it("protects old captures from pruning until the last release, then restores bounded retention", async () => {
    const { harness, pins, store, capturedId } = await openPinnedHarness();
    try {
      const first = store.captureReviewSource(harness.scope, harness.projectId, SEED_TIME);
      const second = store.captureReviewSource(harness.scope, harness.projectId, SEED_TIME);
      const future = 200 * 86_400_000;
      for (let index = 1; index <= 205; index++)
        save(harness, `Later prose ${index}`, { at: future + index * 60_000 });
      first.lease.release();
      save(harness, "Still retained by second review", { at: future + 206 * 60_000 });
      expect(pins.has(capturedId)).toBe(true);
      expect(revisionRows(harness.studio).some((row) => row.id === capturedId)).toBe(true);
      second.lease.release();
      save(harness, "Prune released capture", { at: future + 100 * 86_400_000 });
      expect(revisionRows(harness.studio).some((row) => row.id === capturedId)).toBe(false);
      const rows = revisionRows(harness.studio);
      expect(rows).toHaveLength(200);
      const ids = new Set(rows.map((row) => row.id));
      expect(
        rows.every((row) => row.parentRevisionId === null || ids.has(row.parentRevisionId)),
      ).toBe(true);
    } finally {
      await harness.cleanup();
    }
  });
});
