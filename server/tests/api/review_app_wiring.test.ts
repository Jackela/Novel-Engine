import { describe, expect, it } from "vitest";

import type { TextGenerationProviderFactory } from "../../src/contexts/ai/application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import { loadServerConfig } from "../../src/shared/infrastructure/config/server_config.js";
import { fixtureApiKey } from "../credential_fixtures.js";
import { retryJobRequest } from "./retry_test_helpers.js";
import { buildStudioApp, call, monotonicClock, ownerJar, seedProject } from "./studio_helpers.js";

interface JobPayload {
  id: string;
  kind: string;
  provider: string;
  model: string;
  status: string;
  error: string | null;
  result: { review_id?: string; snapshot_id?: string };
}

interface ReviewPayload {
  id: string;
  snapshot_id: string;
  provider: string;
  model: string;
}

function dashscopeConfig(models: Record<string, string>) {
  return loadServerConfig({
    envFile: null,
    workingDirectory: process.cwd(),
    env: { APP_ENVIRONMENT: "testing", LLM_PROVIDER: "dashscope", ...models },
  });
}

/** Select the project's provider through the author-facing settings surface. */
async function selectProjectProvider(
  app: Awaited<ReturnType<typeof buildStudioApp>>["app"],
  jar: Awaited<ReturnType<typeof ownerJar>>,
  projectId: string,
  provider: string,
): Promise<void> {
  const updated = await call(app, jar, "PATCH", `/api/projects/${projectId}`, {
    settings: { provider },
  });
  expect(updated.statusCode, updated.body).toBe(200);
  expect(updated.json().settings).toEqual({ provider });
}

async function createAndReadReview(
  app: Awaited<ReturnType<typeof buildStudioApp>>["app"],
  projectTitle: string,
): Promise<{ created: JobPayload; listed: ReviewPayload }> {
  const jar = await ownerJar(app);
  const project = await seedProject(app, jar, projectTitle);
  const created = await call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
  expect(created.statusCode, created.body).toBe(201);
  expect(created.json().status).toBe("completed");

  const listed = await call(app, jar, "GET", `/api/projects/${project.id}/reviews`);
  expect(listed.statusCode, listed.body).toBe(200);
  expect(listed.json().reviews).toHaveLength(1);
  return { created: created.json(), listed: listed.json().reviews[0] };
}

describe("review application wiring", () => {
  it("mounts bodyless review routes for an owner project and uses deterministic mock provenance by default", async () => {
    const { app } = await buildStudioApp();
    try {
      const { created, listed } = await createAndReadReview(app, "Default review");

      expect(created).toMatchObject({
        kind: "review",
        provider: "mock",
        model: "deterministic-story-v1",
      });
      expect(listed).toMatchObject({
        id: created.result.review_id,
        snapshot_id: created.result.snapshot_id,
        provider: "mock",
        model: "deterministic-story-v1",
      });

      const openapi = await app.inject({ method: "GET", url: "/openapi.json" });
      expect(openapi.statusCode).toBe(200);
      expect(
        openapi.json().paths["/api/projects/{projectId}/reviews"].post.requestBody,
      ).toBeUndefined();
    } finally {
      await app.close();
    }
  });

  // DR-024 contract change: the review provider comes from the project's own
  // selection, not from the environment's LLM_PROVIDER. The assertion that
  // used to read "DashScope provenance because the environment said so" now
  // reads "DashScope provenance because the project selected DashScope"; the
  // no-silent-mock-fallback guarantee it protected is unchanged.
  it("runs a project-selected DashScope review without ever falling back to the mock", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Review override");
      await selectProjectProvider(app, jar, project.id, "dashscope");
      const created = await call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
      expect(created.statusCode, created.body).toBe(201);

      // No API key is configured in the test environment, so the real
      // DashScope adapter fails loudly: the review job records the failure
      // instead of fabricating a mock review.
      expect(created.json()).toMatchObject({ status: "failed", provider: "dashscope" });
      expect(created.json().error).toContain("dashscope");
      expect(created.json().result.review_id).toBeNull();

      const listed = await call(app, jar, "GET", `/api/projects/${project.id}/reviews`);
      expect(listed.json().reviews).toEqual([]);
    } finally {
      await app.close();
    }
  });

  it("keeps the project's provider when the environment default differs (DR-024)", async () => {
    const { app } = await buildStudioApp(undefined, {
      config: dashscopeConfig({ DASHSCOPE_MODEL: "dashscope-story-model" }),
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Project provider wins");
      // New projects start on the trial provider; the environment default is
      // DashScope here, so a mock review proves the project selection decided.
      const created = await call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
      expect(created.statusCode, created.body).toBe(201);
      expect(created.json()).toMatchObject({
        status: "completed",
        provider: "mock",
        model: "deterministic-story-v1",
      });

      const listed = await call(app, jar, "GET", `/api/projects/${project.id}/reviews`);
      expect(listed.json().reviews).toMatchObject([{ provider: "mock" }]);
    } finally {
      await app.close();
    }
  });

  it("labels a failed project-selected review with its project provider and retries it there", async () => {
    const requested: string[] = [];
    const factory: TextGenerationProviderFactory = (provider) => {
      requested.push(provider);
      return {
        generateStructured: async () => {
          if (requested.length === 1) {
            throw new TextGenerationProviderError("project provider is unreachable");
          }
          return {
            step: "editorial_review",
            provider,
            model: "project-provider-model",
            rawText: '{"findings": []}',
            content: { findings: [] },
            promptTokens: null,
            completionTokens: null,
          };
        },
      };
    };
    const { app } = await buildStudioApp(monotonicClock(), { textProviderFactory: factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Failed project provider review");
      await selectProjectProvider(app, jar, project.id, "dashscope");

      const failed = await call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
      expect(failed.statusCode, failed.body).toBe(201);
      // The failed job names the provider the attempt used — not the
      // environment's default — so the retry chain and the jobs surface agree.
      expect(failed.json<JobPayload>()).toMatchObject({
        status: "failed",
        provider: "dashscope",
        error: "project provider is unreachable",
      });

      const retried = await retryJobRequest(
        app,
        jar,
        `/api/projects/${project.id}/jobs/${failed.json<JobPayload>().id}/retry`,
        "review-project-provider-retry-0001",
      );
      expect(retried.statusCode, retried.body).toBe(200);
      expect(retried.json<JobPayload>()).toMatchObject({
        status: "completed",
        provider: "dashscope",
        model: "project-provider-model",
      });
      expect(requested).toEqual(["dashscope", "dashscope"]);
    } finally {
      await app.close();
    }
  });

  it("reports the editorial review's floored timeout in the job error (DR-025)", async () => {
    const transportCalls: string[] = [];
    const requested: string[] = [];
    const factory: TextGenerationProviderFactory = (provider) => {
      requested.push(provider);
      return new DashScopeTextProvider({
        apiKey: fixtureApiKey("sk-dashscope", "review-timeout-floor"),
        model: "dashscope-review-model",
        timeoutSeconds: 30,
        retry: { maxAttempts: 3, delayMs: 0, sleep: async () => {} },
        transport: (url) => {
          transportCalls.push(url);
          // What the transport boundary reports once the adapter's effective
          // deadline elapses; the message carries that effective timeout.
          return Promise.reject(new DOMException("aborted", "TimeoutError"));
        },
      });
    };
    const { app } = await buildStudioApp(monotonicClock(), { textProviderFactory: factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Slow editorial review");
      await selectProjectProvider(app, jar, project.id, "dashscope");

      const created = await call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
      expect(created.statusCode, created.body).toBe(201);
      const job = created.json<JobPayload>();
      expect(job).toMatchObject({ status: "failed", provider: "dashscope" });
      // The floor — not the 30s base — is what the author can read in the job
      // error the UI surfaces.
      expect(job.error).toContain("timed out after 180s");
      // The adapter keeps its bounded retry policy; the floor is what stops a
      // long manuscript from consuming every attempt.
      expect(transportCalls).toHaveLength(3);
      expect(requested).toEqual(["dashscope"]);
    } finally {
      await app.close();
    }
  });
});
