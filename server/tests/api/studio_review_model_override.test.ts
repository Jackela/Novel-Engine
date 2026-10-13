import { afterEach, describe, expect, it, vi } from "vitest";

import type { TextGenerationProviderFactory } from "../../src/contexts/ai/application/ports/text_generation.js";
import { loadServerConfig } from "../../src/shared/infrastructure/config/server_config.js";
import { fixtureApiKey } from "../credential_fixtures.js";
import { validProposalProse } from "./proposal_test_helpers.js";
import { retryJobRequest } from "./retry_test_helpers.js";
import { buildStudioApp, call, draftProposal, ownerJar, seedProject } from "./studio_helpers.js";

function providerConfig(settings: Record<string, string | undefined>, configured = true) {
  return loadServerConfig({
    envFile: null,
    workingDirectory: process.cwd(),
    env: {
      APP_ENVIRONMENT: "testing",
      LLM_PROVIDER: "dashscope",
      ...(configured ? { DASHSCOPE_API_KEY: fixtureApiKey("review", "model", "fixture") } : {}),
      ...settings,
    },
  });
}

/** Replace only outbound HTTP; the API retains its real provider factory and model resolution. */
function captureTransport(models: string[], failFirst = false) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (_target, init) => {
    const body = JSON.parse(String(init?.body));
    models.push(body.model);
    if (failFirst && models.length === 1) return new Response(null, { status: 400 });
    return Response.json({
      choices: [
        {
          message: {
            content: JSON.stringify({ findings: [], chapter_markdown: validProposalProse }),
          },
        },
      ],
      output: {
        choices: [
          {
            message: {
              content: [
                { text: JSON.stringify({ findings: [], chapter_markdown: validProposalProse }) },
              ],
            },
          },
        ],
      },
    });
  });
}

afterEach(() => vi.restoreAllMocks());

describe("review model through the default API provider factory", () => {
  it.each([
    {
      name: "review override",
      settings: { DASHSCOPE_MODEL: "story-model", DASHSCOPE_REVIEW_MODEL: "review-model" },
      proposalModel: "story-model",
      reviewModel: "review-model",
    },
    {
      name: "project provider differs from the server default",
      settings: {
        LLM_PROVIDER: "mock",
        DASHSCOPE_MODEL: "story-model",
        DASHSCOPE_REVIEW_MODEL: "review-model",
      },
      proposalModel: "story-model",
      reviewModel: "review-model",
    },
    {
      name: "provider model without a review override",
      settings: { DASHSCOPE_MODEL: "story-model" },
      proposalModel: "story-model",
      reviewModel: "story-model",
    },
    {
      name: "generic model without provider overrides",
      settings: { LLM_MODEL: "generic-model" },
      proposalModel: "generic-model",
      reviewModel: "generic-model",
    },
    {
      name: "hard default without model configuration",
      settings: {},
      proposalModel: "qwen3.5-flash",
      reviewModel: "qwen3.5-flash",
    },
    {
      name: "OpenAI-compatible model despite a DashScope review override",
      provider: "openai_compatible",
      settings: {
        LLM_API_KEY: fixtureApiKey("openai", "review", "fixture"),
        OPENAI_COMPATIBLE_MODEL: "compatible-model",
        DASHSCOPE_REVIEW_MODEL: "review-model",
      },
      proposalModel: "compatible-model",
      reviewModel: "compatible-model",
    },
  ])("uses $name and preserves the normal proposal model", async (scenario) => {
    const provider = scenario.provider ?? "dashscope";
    const models: string[] = [];
    captureTransport(models);
    const { app } = await buildStudioApp(undefined, { config: providerConfig(scenario.settings) });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, scenario.name);
      const document = project.documents[0];
      if (document === undefined) throw new Error("Project fixture must create a document.");
      const selected = await call(app, jar, "PATCH", `/api/projects/${project.id}`, {
        settings: { provider },
      });
      expect(selected.statusCode, selected.body).toBe(200);
      const proposal = await draftProposal(app, jar, project.id, document.id, {
        operation: "continue",
        provider,
      });
      expect(proposal).toMatchObject({ status: "completed", model: scenario.proposalModel });
      const review = await call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
      expect(review.statusCode, review.body).toBe(201);
      expect(models).toEqual([scenario.proposalModel, scenario.reviewModel]);
      expect(review.json()).toMatchObject({
        status: "completed",
        provider,
        model: scenario.reviewModel,
      });
      const listed = await call(app, jar, "GET", `/api/projects/${project.id}/reviews`);
      expect(listed.statusCode, listed.body).toBe(200);
      expect(listed.json().reviews).toMatchObject([{ model: scenario.reviewModel }]);
    } finally {
      await app.close();
    }
  });

  it("keeps an injected factory for both proposal and review even with a reviewer override", async () => {
    const steps: string[] = [];
    const factory: TextGenerationProviderFactory = (provider) => ({
      generateStructured: async (task) => {
        steps.push(task.step);
        const content = { findings: [], chapter_markdown: validProposalProse };
        return {
          step: task.step,
          provider,
          model: "injected-model",
          content,
          rawText: JSON.stringify(content),
          promptTokens: null,
          completionTokens: null,
        };
      },
    });
    const { app } = await buildStudioApp(undefined, {
      config: providerConfig({ DASHSCOPE_REVIEW_MODEL: "review-model" }),
      textProviderFactory: factory,
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Injected reviewer");
      const document = project.documents[0];
      if (document === undefined) throw new Error("Project fixture must create a document.");
      const proposal = await draftProposal(app, jar, project.id, document.id, {
        operation: "continue",
      });
      expect(proposal).toMatchObject({ status: "completed", model: "injected-model" });
      const review = await call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
      expect(review.statusCode, review.body).toBe(201);
      expect(review.json()).toMatchObject({ status: "completed", model: "injected-model" });
      expect(steps).toEqual(["chapter_revision", "editorial_review"]);
    } finally {
      await app.close();
    }
  });

  it("uses the review override again when retrying the original provider after project selection changes", async () => {
    const models: string[] = [];
    captureTransport(models, true);
    const { app } = await buildStudioApp(undefined, {
      config: providerConfig({
        DASHSCOPE_MODEL: "story-model",
        DASHSCOPE_REVIEW_MODEL: "review-model",
      }),
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Retry reviewer");
      const selected = await call(app, jar, "PATCH", `/api/projects/${project.id}`, {
        settings: { provider: "dashscope" },
      });
      expect(selected.statusCode, selected.body).toBe(200);
      const failed = await call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
      expect(failed.statusCode, failed.body).toBe(201);
      expect(failed.json()).toMatchObject({ status: "failed", provider: "dashscope" });
      const switched = await call(app, jar, "PATCH", `/api/projects/${project.id}`, {
        settings: { provider: "mock" },
      });
      expect(switched.statusCode, switched.body).toBe(200);
      expect(switched.json().settings).toEqual({ provider: "mock" });
      const retried = await retryJobRequest(
        app,
        jar,
        `/api/projects/${project.id}/jobs/${failed.json().id}/retry`,
        "review-model-retry-0001",
      );
      expect(retried.statusCode, retried.body).toBe(200);
      expect(models).toEqual(["review-model", "review-model"]);
      expect(retried.json()).toMatchObject({
        status: "completed",
        provider: "dashscope",
        model: "review-model",
      });
    } finally {
      await app.close();
    }
  });

  it("keeps the trial provider default and fails an unconfigured DashScope review without transport", async () => {
    const models: string[] = [];
    const transport = captureTransport(models);
    const { app } = await buildStudioApp(undefined, {
      config: providerConfig({ DASHSCOPE_REVIEW_MODEL: "review-model" }, false),
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Unconfigured reviewer");
      const mock = await call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
      expect(mock.statusCode, mock.body).toBe(201);
      expect(mock.json()).toMatchObject({
        status: "completed",
        provider: "mock",
        model: "deterministic-story-v1",
      });
      const selected = await call(app, jar, "PATCH", `/api/projects/${project.id}`, {
        settings: { provider: "dashscope" },
      });
      expect(selected.statusCode, selected.body).toBe(200);
      const failed = await call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
      expect(failed.statusCode, failed.body).toBe(201);
      expect(failed.json()).toMatchObject({
        status: "failed",
        provider: "dashscope",
        result: { review_id: null },
      });
      expect(failed.json().error).toContain("DASHSCOPE_API_KEY");
      expect(transport).not.toHaveBeenCalled();
    } finally {
      await app.close();
    }
  });
});
