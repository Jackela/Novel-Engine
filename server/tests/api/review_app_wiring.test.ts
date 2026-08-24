import { describe, expect, it } from "vitest";

import { loadServerConfig } from "../../src/shared/infrastructure/config/server_config.js";
import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

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

async function createAndReadReview(
  app: Awaited<ReturnType<typeof buildStudioApp>>["app"],
  projectTitle: string,
): Promise<{ created: ReviewPayload; listed: ReviewPayload }> {
  const jar = await ownerJar(app);
  const project = await seedProject(app, jar, projectTitle);
  const created = await call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
  expect(created.statusCode, created.body).toBe(201);

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
        provider: "mock",
        model: "deterministic-story-v1",
      });
      expect(listed).toMatchObject({
        id: created.id,
        snapshot_id: created.snapshot_id,
        provider: "mock",
        model: "deterministic-story-v1",
      });

      const openapi = await app.inject({ method: "GET", url: "/openapi.json" });
      expect(openapi.statusCode, openapi.body).toBe(200);
      expect(
        openapi.json().paths["/api/projects/{projectId}/reviews"].post.requestBody,
      ).toBeUndefined();
    } finally {
      await app.close();
    }
  });

  it("persists the DashScope review override ahead of ordinary and generic model settings", async () => {
    const { app } = await buildStudioApp(undefined, {
      config: dashscopeConfig({
        LLM_MODEL: "generic-story-model",
        DASHSCOPE_MODEL: "dashscope-story-model",
        DASHSCOPE_REVIEW_MODEL: "dashscope-review-model",
      }),
    });
    try {
      const { created, listed } = await createAndReadReview(app, "Review override");

      expect(created).toMatchObject({ provider: "dashscope", model: "dashscope-review-model" });
      expect(listed).toMatchObject({
        id: created.id,
        snapshot_id: created.snapshot_id,
        provider: "dashscope",
        model: "dashscope-review-model",
      });
    } finally {
      await app.close();
    }
  });

  it("falls back to the ordinary DashScope model when no review override is configured", async () => {
    const { app } = await buildStudioApp(undefined, {
      config: dashscopeConfig({
        LLM_MODEL: "generic-story-model",
        DASHSCOPE_MODEL: "dashscope-story-model",
      }),
    });
    try {
      const { created, listed } = await createAndReadReview(app, "Review fallback");

      expect(created).toMatchObject({ provider: "dashscope", model: "dashscope-story-model" });
      expect(listed).toMatchObject({
        id: created.id,
        snapshot_id: created.snapshot_id,
        provider: "dashscope",
        model: "dashscope-story-model",
      });
    } finally {
      await app.close();
    }
  });
});
