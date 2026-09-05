import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { DocumentService } from "../../src/contexts/studio/application/document_service.js";
import type { StudioStore } from "../../src/contexts/studio/application/ports/studio_store.js";
import {
  reviewPageLimit,
  scopeForPrincipal,
} from "../../src/contexts/studio/application/ports/studio_store.js";
import { ProjectService } from "../../src/contexts/studio/application/project_service.js";
import {
  type EditorialAssessment,
  ReviewService,
} from "../../src/contexts/studio/application/review_service.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { AuthService } from "../../src/shared/application/auth_service.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";
import { DrizzleAuthStore } from "../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

function monotonicClock(): () => Date {
  let milliseconds = Date.parse("2026-08-24T00:00:00.000Z");
  return () => {
    milliseconds += 1;
    return new Date(milliseconds);
  };
}

function words(count: number): string {
  return Array.from({ length: count }, () => "word").join(" ");
}

function assessmentCodes(assessment: EditorialAssessment): string[] {
  return assessment.issues.map((issue) => `${issue.severity}:${issue.code}`);
}

interface Harness {
  store: StudioStore;
  projects: ProjectService;
  documents: DocumentService;
  principal: Principal;
  cleanup: () => Promise<void>;
}

async function openHarness(): Promise<Harness> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-review-service-"));
  const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3"));
  const clock = monotonicClock();
  const store: StudioStore = new DrizzleStudioStore({
    database: studio.db,
  });
  const auth = new AuthService({
    store: new DrizzleAuthStore(studio.db),
    sessionSecret: "review-service-test-secret",
    now: clock,
  });
  await auth.configureOwner("reviewer", "long-test-password");
  return {
    store,
    projects: new ProjectService(store, clock),
    documents: new DocumentService(store, clock),
    principal: (await auth.createOwnerSession("reviewer", "long-test-password")).principal,
    cleanup: async () => {
      studio.close();
      await rm(directory, { recursive: true, force: true });
    },
  };
}

/** Factory double whose generated findings the test controls. */
function staticFactory(content: unknown): {
  factory: TextGenerationProviderFactory;
} {
  const factory: TextGenerationProviderFactory = (provider) => {
    const impl: TextGenerationProvider = {
      generateStructured: async (task) => {
        void task;
        return {
          step: "editorial_review",
          provider,
          model: "static-review-model",
          rawText: JSON.stringify(content),
          content: content as Record<string, unknown>,
          promptTokens: null,
          completionTokens: null,
        };
      },
    };
    return impl;
  };
  return { factory };
}

function failingFactory(): TextGenerationProviderFactory {
  return () => ({
    generateStructured: async () => {
      throw new TextGenerationProviderError("review provider exploded");
    },
  });
}

describe("ReviewService (#316 provider-driven review)", () => {
  it("persists coerced provider findings snapshot-bound and lists newest first", async () => {
    const harness = await openHarness();
    try {
      const project = harness.projects.newProject(harness.principal, {
        title: "Frozen editorial evidence",
      }) as { id: string; documents: Array<{ id: string; current_revision_id: string }> };
      const seed = project.documents[0];
      if (seed === undefined) {
        throw new Error("Project creation must provide its seed document.");
      }
      harness.documents.storeDocument(harness.principal, project.id, seed.id, {
        baseRevisionId: seed.current_revision_id,
        contentMarkdown: words(250),
      });
      const thin = harness.documents.newDocument(harness.principal, project.id, {
        kind: "chapter",
        title: "Short crossing",
        contentMarkdown: "two words",
      }) as { id: string };

      const { factory } = staticFactory({
        findings: [
          {
            document_id: thin.id,
            severity: "warning",
            dimension: "pacing",
            message: "The crossing is over too fast.",
            suggestion: "Let the scene breathe.",
          },
        ],
      });
      const reviews = new ReviewService(harness.store, {
        now: monotonicClock(),
        provenance: { provider: "mock", model: "deterministic-story-v1" },
        providerFactory: factory,
      });

      const firstEvaluation = await reviews.evaluateProject(harness.principal, project.id);
      const first = harness.store.recordCompletedReviewJob(
        scopeForPrincipal(harness.principal),
        firstEvaluation,
      ).assessment;

      expect(first.provider).toBe("mock");
      expect(first.model).toBe("static-review-model");
      expect(assessmentCodes(first)).toEqual(["warning:pacing"]);
      expect(first.issues[0]?.documentId).toBe(thin.id);

      const secondEvaluation = await reviews.evaluateProject(harness.principal, project.id);
      const second = harness.store.recordCompletedReviewJob(
        scopeForPrincipal(harness.principal),
        secondEvaluation,
      ).assessment;
      const listed = reviews.collectProjectReviewSummaries(harness.principal, project.id, {
        limit: reviewPageLimit(10),
      });

      expect(listed.reviews.map((summary) => summary.id)).toEqual([second.id, first.id]);
      expect(listed.nextCursor).toBeNull();
      const detailed = reviews.findEditorialAssessment(harness.principal, project.id, second.id);
      expect(assessmentCodes(detailed)).toEqual(["warning:pacing"]);
    } finally {
      await harness.cleanup();
    }
  });

  it("drops findings outside the closed dimension set instead of persisting them", async () => {
    const harness = await openHarness();
    try {
      const project = harness.projects.newProject(harness.principal, {
        title: "Closed vocabulary",
      }) as { id: string };
      const { factory } = staticFactory({
        findings: [
          {
            document_id: "ghost",
            severity: "blocker",
            dimension: "vibes",
            message: "fabricated",
          },
        ],
      });
      const reviews = new ReviewService(harness.store, {
        now: monotonicClock(),
        providerFactory: factory,
      });

      const assessment = await reviews.evaluateProject(harness.principal, project.id);
      expect(assessment.issues).toEqual([]);
    } finally {
      await harness.cleanup();
    }
  });

  it("propagates provider failures so the terminal job records them, without findings", async () => {
    const harness = await openHarness();
    try {
      const project = harness.projects.newProject(harness.principal, {
        title: "Provider failure",
      }) as { id: string };
      const reviews = new ReviewService(harness.store, {
        now: monotonicClock(),
        providerFactory: failingFactory(),
      });

      const failure = await reviews.evaluateProject(harness.principal, project.id).then(
        () => null,
        (error: unknown) => error,
      );
      expect(failure).toBeInstanceOf(TextGenerationProviderError);
      expect((failure as TextGenerationProviderError).message).toContain(
        "review provider exploded",
      );
      expect(
        reviews.collectProjectReviewSummaries(harness.principal, project.id, {
          limit: reviewPageLimit(10),
        }).reviews,
      ).toEqual([]);
    } finally {
      await harness.cleanup();
    }
  });
});
