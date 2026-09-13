import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import type { EvaluatedReview } from "../../src/contexts/studio/application/ports/review_outcome_store.js";
import { scopeForPrincipal } from "../../src/contexts/studio/application/ports/studio_store.js";
import {
  jobEvents,
  jobs,
  projectSnapshots,
  reviewIssues,
  reviews,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DocumentStorePart } from "../../src/contexts/studio/infrastructure/document_store_part.js";
import { JobStorePart } from "../../src/contexts/studio/infrastructure/job_store_part.js";
import { ProjectStorePart } from "../../src/contexts/studio/infrastructure/project_store_part.js";
import { ReviewStorePart } from "../../src/contexts/studio/infrastructure/review_store_part.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import type { StudioSqliteDatabase } from "../../src/shared/infrastructure/db/connection.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const directories: string[] = [];

export const NO_REVIEW_ROWS = {
  snapshots: 0,
  snapshotDocuments: 0,
  reviews: 0,
  issues: 0,
  jobs: 0,
  events: 0,
};

export function cleanupReviewOutcomeDirectories(): Promise<unknown[]> {
  return Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true })));
}

function clock(): () => Date {
  let milliseconds = Date.parse("2026-08-31T12:00:00.000Z");
  return () => new Date(++milliseconds);
}

export async function openHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-review-outcome-"));
  directories.push(directory);
  const database = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  const now = clock();
  const store = {
    projects: new ProjectStorePart(database.db),
    documents: new DocumentStorePart(database.db),
    jobs: new JobStorePart(database.db),
  };
  const auth = new AuthService({
    store: new DrizzleAuthStore(database.db),
    sessionSecret: "review-outcome-test-secret",
    now,
  });
  await auth.configureOwner("review-outcome-owner", "long-test-password");
  const principal = (await auth.createOwnerSession("review-outcome-owner", "long-test-password"))
    .principal;
  const scope = scopeForPrincipal(principal);
  const seeded = store.projects.addProject(scope, {
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

export function evidenceCounts(db: StudioSqliteDatabase) {
  return {
    snapshots: db.select().from(projectSnapshots).all().length,
    snapshotDocuments: db.select().from(snapshotDocuments).all().length,
    reviews: db.select().from(reviews).all().length,
    issues: db.select().from(reviewIssues).all().length,
    jobs: db.select().from(jobs).all().length,
    events: db.select().from(jobEvents).all().length,
  };
}
