import { eq } from "drizzle-orm";
import type { FastifyInstance } from "fastify";
import { expect } from "vitest";

import type {
  TextGenerationProvider,
  TextGenerationProviderFactory,
  TextGenerationTask,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { jobs as jobsTable } from "../../src/shared/infrastructure/db/schema.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import { type CookieJar, seedProject } from "./studio_helpers.js";

/** First calls throw; once `failures.count` reaches zero the provider recovers. */
export function flakyProviderFactory(failures: { count: number }): TextGenerationProviderFactory {
  return (provider) => {
    const impl: TextGenerationProvider = {
      generateStructured: async (task: TextGenerationTask) => {
        if (failures.count > 0) {
          failures.count -= 1;
          throw new TextGenerationProviderError(`simulated provider failure ${provider}`);
        }
        const content =
          task.step === "editorial_review"
            ? { findings: [] }
            : { chapter_markdown: validProposalProse };
        return {
          step: task.step,
          provider,
          model: "recovered-model",
          rawText: JSON.stringify(content),
          content,
          promptTokens: 3,
          completionTokens: 5,
        };
      },
    };
    return impl;
  };
}

/** Fail early calls, then pause one valid review result until the test releases it. */
export function deferredReviewFactory(failuresBeforeWait = 0): {
  factory: TextGenerationProviderFactory;
  started: Promise<void>;
  succeed: () => void;
} {
  let failures = failuresBeforeWait;
  let announceStarted: (() => void) | undefined;
  let complete: (() => void) | undefined;
  const started = new Promise<void>((resolve) => {
    announceStarted = resolve;
  });
  const pending = new Promise<void>((resolve) => {
    complete = resolve;
  });
  return {
    factory: (provider) => ({
      generateStructured: async () => {
        if (failures > 0) {
          failures -= 1;
          throw new TextGenerationProviderError(`simulated provider failure ${provider}`);
        }
        announceStarted?.();
        await pending;
        return {
          step: "editorial_review",
          provider,
          model: "deferred-review-model",
          rawText: '{"findings":[]}',
          content: { findings: [] },
          promptTokens: null,
          completionTokens: null,
        };
      },
    }),
    started,
    succeed: () => complete?.(),
  };
}

/** The first seeded chapter document (seedProject always creates one). */
export function firstDocument(project: { documents: Array<{ id: string }> }): { id: string } {
  const document = project.documents.at(0);
  if (document === undefined) throw new Error("Seeded projects must include a document.");
  return document;
}

export async function seedProjectWithChapter(
  app: FastifyInstance,
  jar: CookieJar,
  title: string,
): Promise<string> {
  const project = await seedProject(app, jar, title);
  firstDocument(project);
  return project.id;
}

/** Force a persisted job row into another state (test seam). */
export function forceJobStatus(app: FastifyInstance, jobId: string, status: string): void {
  const database = app.studioDb?.db;
  if (database === undefined) throw new Error("Expected the real Studio database.");
  database.update(jobsTable).set({ status }).where(eq(jobsTable.id, jobId)).run();
}

/** The live studio database behind an app built with a data directory. */
export function studioDatabase(app: FastifyInstance) {
  const database = app.studioDb?.db;
  if (database === undefined) throw new Error("Expected the real Studio database.");
  expect(database).toBeDefined();
  return database;
}
