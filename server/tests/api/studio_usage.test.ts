import { describe, expect, it } from "vitest";

import { capturingFactory } from "./proposal_test_helpers.js";
import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

describe("project usage surface (#317)", () => {
  it("aggregates recorded events into totals and a per-model breakdown", async () => {
    const capture = capturingFactory({});
    const { app } = await buildStudioApp(undefined, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Counted");
      const document = project.documents[0];
      if (document === undefined) throw new Error("expected seeded document");
      const propose = () =>
        call(
          app,
          jar,
          "POST",
          `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
          { operation: "continue" },
        );

      await propose();
      await propose();

      const response = await call(app, jar, "GET", `/api/projects/${project.id}/usage`);
      expect(response.statusCode).toBe(200);
      const body = response.json();
      expect(body.project_id).toBe(project.id);
      expect(body.request_count).toBe(2);
      expect(body.per_model).toHaveLength(1);
      expect(body.per_model[0]).toMatchObject({ model: expect.any(String), requests: 2 });
      // Totals are exactly the fold of the per-model breakdown.
      expect(body.prompt_tokens).toBe(body.per_model[0].prompt_tokens);
      expect(body.completion_tokens).toBe(body.per_model[0].completion_tokens);
    } finally {
      await app.close();
    }
  });

  it("returns zeroed totals for a project with an empty ledger", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Empty ledger");

      const response = await call(app, jar, "GET", `/api/projects/${project.id}/usage`);
      expect(response.statusCode).toBe(200);
      expect(response.json()).toEqual({
        project_id: project.id,
        request_count: 0,
        prompt_tokens: 0,
        completion_tokens: 0,
        per_model: [],
      });
    } finally {
      await app.close();
    }
  });

  it("answers 401 unauthenticated and 404 for an unknown project", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      await seedProject(app, jar, "Scoped");

      const anonymous = await app.inject({ method: "GET", url: "/api/projects/p-1/usage" });
      expect(anonymous.statusCode).toBe(401);
      expect(anonymous.json().error.code).toBe("UNAUTHORIZED");

      const unknown = await call(
        app,
        jar,
        "GET",
        "/api/projects/00000000-0000-0000-0000-000000000000/usage",
      );
      expect(unknown.statusCode).toBe(404);
      expect(unknown.json().error.code).toBe("NOT_FOUND");
    } finally {
      await app.close();
    }
  });
});
