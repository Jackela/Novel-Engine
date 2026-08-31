import { describe, expect, it, vi } from "vitest";

import type {
  TextGenerationProvider,
  TextGenerationProviderFactory,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { forceJobStatus } from "./job_test_helpers.js";
import {
  buildStudioApp,
  call,
  type JobPayload,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

describe("review provider lifecycle", () => {
  it("reports disposal failures for fresh and retried reviews", async () => {
    let disposed = 0;
    let created = 0;
    const cleanupFailure = new Error("review cleanup failed");
    const factory: TextGenerationProviderFactory = (provider) => {
      const requestIndex = created;
      created += 1;
      const implementation: TextGenerationProvider = {
        generateStructured: async () => {
          if (requestIndex === 2) {
            throw new TextGenerationProviderError("known review provider failure");
          }
          if (requestIndex === 4) throw new Error("unexpected review provider failure");
          const content = requestIndex === 3 ? { wrong_key: [] } : { findings: [] };
          return {
            step: "editorial_review",
            provider,
            model: "cleanup-model",
            rawText: JSON.stringify(content),
            content,
            promptTokens: null,
            completionTokens: null,
          };
        },
        dispose: async () => {
          disposed += 1;
          throw cleanupFailure;
        },
      };
      return implementation;
    };
    const { app } = await buildStudioApp(monotonicClock(), { textProviderFactory: factory });
    const logError = vi.spyOn(app.log, "error").mockImplementation(() => undefined);
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Review cleanup reporting");
      const first = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      expect(first.statusCode, first.body).toBe(201);
      const firstJob = first.json<JobPayload>();
      expect(firstJob.status).toBe("completed");
      forceJobStatus(app, firstJob.id, "failed");

      const retry = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/jobs/${firstJob.id}/retry`,
      );
      expect(retry.statusCode, retry.body).toBe(200);
      expect(retry.json<JobPayload>()).toMatchObject({
        status: "completed",
        model: "cleanup-model",
      });

      const knownFailure = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      expect(knownFailure.json<JobPayload>().status).toBe("failed");
      const malformed = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      expect(malformed.json<JobPayload>().status).toBe("failed");
      const unexpected = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      expect(unexpected.statusCode, unexpected.body).toBe(500);
      for (const response of [first, retry, knownFailure, malformed, unexpected]) {
        expect(response.body).not.toContain(cleanupFailure.message);
      }
      expect(disposed).toBe(5);
      expect(
        logError.mock.calls.filter(
          ([details, message]) =>
            message === "provider cleanup failed" &&
            typeof details === "object" &&
            (details as Record<string, unknown>).provider_cleanup_failed === true,
        ),
      ).toHaveLength(5);
    } finally {
      await app.close();
    }
  });
});
