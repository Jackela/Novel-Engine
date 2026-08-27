import { describe, expect, it } from "vitest";

import { loadServerConfig } from "../../src/shared/infrastructure/config/server_config.js";
import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

interface JobPayload {
  id: string;
  kind: string;
  provider: string;
  model: string;
  status: string;
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

  it("runs DashScope-provenance reviews without ever falling back to the mock", async () => {
    const { app } = await buildStudioApp(undefined, {
      config: dashscopeConfig({
        LLM_MODEL: "generic-story-model",
        DASHSCOPE_MODEL: "dashscope-story-model",
        DASHSCOPE_REVIEW_MODEL: "dashscope-review-model",
      }),
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Review override");
      const created = await call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
      expect(created.statusCode).toBe(201);

      // No API key is configured in the test environment, so the real
      // DashScope adapter fails loudly: the review job records the failure
      // instead of fabricating a mock review.
      expect(created.json().status).toBe("failed");
      expect(created.json().provider).toBe("dashscope");
      expect(created.json().error).toContain("dashscope");
      expect(created.json().result.review_id).toBeNull();

      const listed = await call(app, jar, "GET", `/api/projects/${project.id}/reviews`);
      expect(listed.json().reviews).toEqual([]);
    } finally {
      await app.close();
    }
  });

  it("records the DashScope model fallback in the provider failure path", async () => {
    const { app } = await buildStudioApp(undefined, {
      config: dashscopeConfig({
        LLM_MODEL: "generic-story-model",
        DASHSCOPE_MODEL: "dashscope-story-model",
      }),
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Review fallback");
      const created = await call(app, jar, "POST", `/api/projects/${project.id}/reviews`);
      expect(created.statusCode).toBe(201);
      expect(created.json().status).toBe("failed");
      expect(created.json().provider).toBe("dashscope");
    } finally {
      await app.close();
    }
  });
});
