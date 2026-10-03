import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import {
  TextGenerationProviderError,
  type TextGenerationProviderFactory,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { wordCount } from "../../src/contexts/studio/application/payloads.js";
import {
  jobEvents,
  jobs,
  usageEvents,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { firstDocument, studioDatabase } from "./job_test_helpers.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import {
  buildStudioApp,
  call,
  type JobPayload,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

type RetryOutcome = "completed" | "failed";

function proposalRetryFactory(
  outcome: RetryOutcome,
  usage: { promptTokens: number; completionTokens: number } = {
    promptTokens: 7,
    completionTokens: 11,
  },
): {
  readonly factory: TextGenerationProviderFactory;
  readonly factoryCalls: () => number;
  readonly generateCalls: () => number;
} {
  let factoryCalls = 0;
  let generateCalls = 0;
  return {
    factory: (provider) => {
      factoryCalls += 1;
      return {
        generateStructured: async (task) => {
          generateCalls += 1;
          if (generateCalls === 1 || outcome === "failed") {
            throw new TextGenerationProviderError(`proposal provider failure ${generateCalls}`);
          }
          return {
            step: task.step,
            provider,
            model: "proposal-replay-model",
            rawText: validProposalProse,
            content: { chapter_markdown: validProposalProse },
            promptTokens: usage.promptTokens,
            completionTokens: usage.completionTokens,
          };
        },
      };
    },
    factoryCalls: () => factoryCalls,
    generateCalls: () => generateCalls,
  };
}

function retryEvidence(app: FastifyInstance) {
  const database = studioDatabase(app);
  return {
    jobs: database.select().from(jobs).all(),
    events: database.select().from(jobEvents).all(),
    usage: database.select().from(usageEvents).all(),
  };
}

describe("proposal retry terminal replay evidence", () => {
  it("falls back when a successful retry reports unsafe token counts", async () => {
    const provider = proposalRetryFactory("completed", {
      promptTokens: Number.MAX_SAFE_INTEGER + 1,
      completionTokens: Number.POSITIVE_INFINITY,
    });
    const { app } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: provider.factory,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "unsafe retry counts");
      const document = firstDocument(project);
      const instruction = "fail before retry";
      const original = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
        { operation: "continue", instruction },
      );
      const source = original.json<JobPayload>();
      expect(source.status).toBe("failed");

      const retried = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/jobs/${source.id}/retry`,
        undefined,
        { "idempotency-key": "unsafe-proposal-retry-key-0001" },
      );
      expect(retried.statusCode, retried.body).toBe(200);
      // DR-028: the failed original attempt and the successful retry both keep
      // rows — unreported first, the estimated retry usage second.
      const [failedAttempt, retriedUsage] = retryEvidence(app).usage;
      if (failedAttempt === undefined || retriedUsage === undefined) {
        throw new Error("expected the failed and retried usage events");
      }
      expect(failedAttempt).toMatchObject({
        outcome: "failed",
        token_source: "unreported",
        prompt_tokens: 0,
        completion_tokens: 0,
      });
      expect(retriedUsage).toMatchObject({ outcome: "completed", token_source: "estimated" });
      expect(retriedUsage.prompt_tokens).toBe(wordCount(instruction));
      expect(retriedUsage.completion_tokens).toBe(wordCount(validProposalProse));
    } finally {
      await app.close();
    }
  });

  it.each([
    {
      outcome: "completed",
      key: "completed-proposal-replay-key-0001",
      expectedRequests: 1,
      expectedFailedAttempts: 1,
    },
    {
      outcome: "failed",
      key: "failed-proposal-replay-key-0001",
      expectedRequests: 0,
      expectedFailedAttempts: 2,
    },
  ] as const)(
    "replays the exact $outcome Job without repeating provider work or evidence",
    async ({ outcome, key, expectedRequests, expectedFailedAttempts }) => {
      const provider = proposalRetryFactory(outcome);
      const { app } = await buildStudioApp(monotonicClock(), {
        textProviderFactory: provider.factory,
      });
      try {
        const owner = await ownerJar(app);
        const project = await seedProject(app, owner, `${outcome} proposal replay`);
        const document = firstDocument(project);
        const original = await call(
          app,
          owner,
          "POST",
          `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
          { operation: "continue", instruction: "fail before retry" },
        );
        expect(original.statusCode, original.body).toBe(200);
        const source = original.json<JobPayload>();
        expect(source.status).toBe("failed");

        const url = `/api/projects/${project.id}/jobs/${source.id}/retry`;
        const first = await call(app, owner, "POST", url, undefined, {
          "idempotency-key": key,
        });
        expect(first.statusCode, first.body).toBe(200);
        const terminal = first.json<JobPayload>();
        expect(terminal).toMatchObject({ status: outcome, retry_of_job_id: source.id });
        expect(terminal.events.map((event) => event.status)).toEqual(["running", outcome]);
        expect(provider.factoryCalls()).toBe(2);
        expect(provider.generateCalls()).toBe(2);

        const beforeReplay = retryEvidence(app);
        expect(beforeReplay.jobs).toHaveLength(2);
        expect(beforeReplay.events).toHaveLength(3);
        // DR-028: every provider attempt keeps its own row — the failed
        // original attempt first, the terminal retry attempt second.
        expect(beforeReplay.usage).toHaveLength(2);
        expect(beforeReplay.usage[0]).toMatchObject({
          job_id: source.id,
          outcome: "failed",
          token_source: "unreported",
          prompt_tokens: 0,
          completion_tokens: 0,
        });
        if (outcome === "completed") {
          expect(beforeReplay.usage[1]).toMatchObject({
            job_id: terminal.id,
            model: "proposal-replay-model",
            outcome: "completed",
            token_source: "provider",
            prompt_tokens: 7,
            completion_tokens: 11,
          });
        } else {
          expect(beforeReplay.usage[1]).toMatchObject({
            job_id: terminal.id,
            outcome: "failed",
            token_source: "unreported",
            prompt_tokens: 0,
            completion_tokens: 0,
          });
        }
        const usageBefore = await call(app, owner, "GET", `/api/projects/${project.id}/usage`);
        expect(usageBefore.statusCode, usageBefore.body).toBe(200);
        expect(usageBefore.json().request_count).toBe(expectedRequests);
        expect(usageBefore.json().failed_attempt_count).toBe(expectedFailedAttempts);

        const replay = await call(app, owner, "POST", url, undefined, {
          "idempotency-key": key,
        });
        expect(replay.statusCode, replay.body).toBe(200);
        expect(replay.body).toBe(first.body);
        expect(replay.json<JobPayload>()).toEqual(terminal);
        expect(provider.factoryCalls()).toBe(2);
        expect(provider.generateCalls()).toBe(2);
        expect(retryEvidence(app)).toEqual(beforeReplay);
        const usageAfter = await call(app, owner, "GET", `/api/projects/${project.id}/usage`);
        expect(usageAfter.json()).toEqual(usageBefore.json());
      } finally {
        await app.close();
      }
    },
  );
});
