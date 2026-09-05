import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import type { EvaluatedReview } from "../../src/contexts/studio/application/ports/review_outcome_store.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { ReviewStorePart } from "../../src/contexts/studio/infrastructure/review_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import {
  openStudioDatabase,
  type StudioDatabase,
} from "../../src/shared/infrastructure/db/startup.js";

const CHAPTER_BODY = "The chapter narrative develops across several words. ";

export interface ReviewPageHarness {
  cleanup: () => Promise<void>;
  database: StudioDatabase;
  document: { id: string };
  now: () => Date;
  projectId: string;
  reviewsStore: ReviewStorePart;
  scope: ReturnType<typeof scopeForPrincipal>;
  store: DrizzleStudioStore;
}

/**
 * One hermetic project with a seeded chapter, an authenticated owner scope,
 * and the review store part under test (#459).
 */
export async function openReviewPageHarness(): Promise<ReviewPageHarness> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-review-page-"));
  const database = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  const cleanup = async (): Promise<void> => {
    database.close();
    await rm(directory, { recursive: true, force: true });
  };
  try {
    let milliseconds = Date.parse("2026-09-05T00:00:00.000Z");
    const now = () => new Date(++milliseconds);
    const store = new DrizzleStudioStore({ database: database.db });
    const auth = new AuthService({
      store: new DrizzleAuthStore(database.db),
      sessionSecret: "review-page-test-secret",
      now,
    });
    await auth.configureOwner("review-page-owner", "long-test-password");
    const principal = (await auth.createOwnerSession("review-page-owner", "long-test-password"))
      .principal;
    const scope = scopeForPrincipal(principal);
    const seeded = store.addProject(scope, {
      title: "Review page",
      description: "",
      settingsJson: "{}",
      seed: {
        kind: "chapter",
        title: "Chapter 1",
        contentMarkdown: CHAPTER_BODY,
        metadataJson: "{}",
      },
      now: now(),
    });
    const document = seeded.documents[0];
    if (document === undefined) throw new Error("Expected the seeded document.");
    const reviewsStore = new ReviewStorePart(database.db);
    return {
      cleanup,
      database,
      document,
      now,
      projectId: seeded.project.id,
      reviewsStore,
      scope,
      store,
    };
  } catch (error) {
    await cleanup();
    throw error;
  }
}

/** Persist one completed review; even indexes carry a single warning issue. */
export function recordReview(harness: ReviewPageHarness, index: number, completedAt?: Date): void {
  const source = harness.reviewsStore.readReviewSource(
    harness.scope,
    harness.projectId,
    harness.now(),
  );
  const evaluation: EvaluatedReview = {
    source,
    provider: "mock",
    model: "review-model",
    summary: "review completed",
    completedAt: completedAt ?? new Date(Date.parse("2026-09-05T01:00:00.000Z") + index * 1000),
    issues:
      index % 2 === 0
        ? [
            {
              documentId: harness.document.id,
              severity: "warning",
              code: "thin_chapter",
              message: `Finding ${index}`,
              suggestion: "Develop the scene.",
              evidence: { word_count: 8 },
            },
          ]
        : [],
  };
  harness.reviewsStore.recordCompletedReviewJob(harness.scope, evaluation);
}

/** Seed a foreign sibling project with one chapter for scope tests. */
export function seedForeignProject(harness: ReviewPageHarness, title: string): { id: string } {
  return harness.store.addProject(harness.scope, {
    title,
    description: "",
    settingsJson: "{}",
    seed: {
      kind: "chapter",
      title: "Chapter 1",
      contentMarkdown: CHAPTER_BODY,
      metadataJson: "{}",
    },
    now: harness.now(),
  }).project;
}
