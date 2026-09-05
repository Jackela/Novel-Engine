import type { FastifyInstance } from "fastify";
import { expect } from "vitest";

import type {
  TextGenerationProvider,
  TextGenerationProviderFactory,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { jobs } from "../../src/shared/infrastructure/db/schema.js";
import { studioDatabase } from "./job_test_helpers.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import { type CookieJar, call } from "./studio_helpers.js";

export type ApiResponse = Awaited<ReturnType<typeof call>>;

export function cleanupGatedProvider(options: { failFirstDispose?: boolean } = {}): {
  factory: TextGenerationProviderFactory;
  firstDisposeStarted: Promise<void>;
  releaseFirstDispose: () => void;
  secondWorkStarted: Promise<void>;
  releaseSecondWork: () => void;
  factoryCalls: () => number;
  cleanupFailureMessage: string;
} {
  let factoryCalls = 0;
  let announceFirstDispose: (() => void) | undefined;
  let finishFirstDispose: (() => void) | undefined;
  let announceSecondWork: (() => void) | undefined;
  let finishSecondWork: (() => void) | undefined;
  const cleanupFailureMessage = "capacity cleanup failure must stay out of responses";
  const firstDisposeStarted = new Promise<void>((resolve) => {
    announceFirstDispose = resolve;
  });
  const firstDisposeGate = new Promise<void>((resolve) => {
    finishFirstDispose = resolve;
  });
  const secondWorkStarted = new Promise<void>((resolve) => {
    announceSecondWork = resolve;
  });
  const secondWorkGate = new Promise<void>((resolve) => {
    finishSecondWork = resolve;
  });

  const factory: TextGenerationProviderFactory = (provider) => {
    const requestIndex = factoryCalls;
    factoryCalls += 1;
    const implementation: TextGenerationProvider = {
      async generateStructured(task) {
        if (requestIndex === 1) {
          announceSecondWork?.();
          await secondWorkGate;
        }
        const content =
          task.step === "editorial_review"
            ? { findings: [] }
            : { chapter_markdown: validProposalProse };
        return {
          step: task.step,
          provider,
          model: "capacity-cleanup-model",
          rawText: JSON.stringify(content),
          content,
          promptTokens: 1,
          completionTokens: 1,
        };
      },
      async dispose() {
        if (requestIndex !== 0) return;
        announceFirstDispose?.();
        await firstDisposeGate;
        if (options.failFirstDispose === true) {
          throw new Error(cleanupFailureMessage);
        }
      },
    };
    return implementation;
  };

  return {
    factory,
    firstDisposeStarted,
    releaseFirstDispose: () => finishFirstDispose?.(),
    secondWorkStarted,
    releaseSecondWork: () => finishSecondWork?.(),
    factoryCalls: () => factoryCalls,
    cleanupFailureMessage,
  };
}

export async function expectApplicationCapacity(
  response: ApiResponse,
  projectId: string,
): Promise<void> {
  expect(response.statusCode, response.body).toBe(503);
  expect(response.headers["retry-after"]).toBe("5");
  expect(response.json()).toEqual({
    error: {
      code: "OPERATION_CAPACITY_EXCEEDED",
      message: "Studio operation capacity is exhausted.",
      details: {
        scope: "application",
        limit: 1,
        in_flight: 1,
        project_id: projectId,
        retry_after_seconds: 5,
      },
    },
  });
}

export function proposalRequest(
  app: FastifyInstance,
  owner: CookieJar,
  project: { id: string; documents: Array<{ id: string }> },
): Promise<ApiResponse> {
  const document = project.documents[0];
  if (document === undefined) throw new Error("Expected the seeded chapter.");
  return call(
    app,
    owner,
    "POST",
    `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
    { operation: "continue", provider: "mock" },
  );
}

export async function proveExactlyOnePermitRecovered(
  app: FastifyInstance,
  owner: CookieJar,
  activeProjectId: string,
  waitingProject: { id: string; documents: Array<{ id: string }> },
  provider: ReturnType<typeof cleanupGatedProvider>,
): Promise<void> {
  const recovery = proposalRequest(app, owner, waitingProject);
  await provider.secondWorkStarted;
  const stillBounded = await call(
    app,
    owner,
    "POST",
    `/api/projects/${activeProjectId}/reviews`,
    {},
  );
  await expectApplicationCapacity(stillBounded, activeProjectId);
  expect(provider.factoryCalls()).toBe(2);

  provider.releaseSecondWork();
  expect((await recovery).statusCode).toBe(200);
}

export function seedFailedProposalRetry(
  app: FastifyInstance,
  projectId: string,
  documentId: string,
  baseRevisionId: string,
  now: Date,
): string {
  const id = "provider-cleanup-retry-source";
  studioDatabase(app)
    .insert(jobs)
    .values({
      id,
      project_id: projectId,
      document_id: documentId,
      kind: "proposal",
      operation: "continue",
      status: "failed",
      provider: "mock",
      model: "fixture-model",
      request_json: JSON.stringify({ instruction: "", base_revision_id: baseRevisionId }),
      result_json: "{}",
      error: "fixture failure",
      created_at: now,
      updated_at: now,
      started_at: now,
      finished_at: now,
    })
    .run();
  return id;
}
