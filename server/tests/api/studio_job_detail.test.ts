import { eq } from "drizzle-orm";
import { describe, expect, it } from "vitest";

import { jobs as jobsTable } from "../../src/shared/infrastructure/db/schema.js";
import { firstDocument, studioDatabase } from "./job_test_helpers.js";
import {
  buildStudioApp,
  call,
  draftProposal,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

describe("project-scoped job detail", () => {
  it("returns the existing complete Job with oldest-first events", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Complete job detail");
      const document = firstDocument(project);
      const original = await draftProposal(app, owner, project.id, document.id, {
        operation: "continue",
        instruction: "retry source",
      });
      studioDatabase(app)
        .update(jobsTable)
        .set({ status: "interrupted" })
        .where(eq(jobsTable.id, original.id))
        .run();
      const retried = await call(
        app,
        owner,
        "POST",
        `/api/projects/${project.id}/jobs/${original.id}/retry`,
      );
      expect(retried.statusCode, retried.body).toBe(200);

      const detail = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/jobs/${retried.json().id}`,
      );
      expect(detail.statusCode, detail.body).toBe(200);
      expect(detail.json()).toEqual(retried.json());
      expect(detail.json().events.map((event: { status: string }) => event.status)).toEqual([
        "running",
        "completed",
      ]);
      expect(detail.json()).toMatchObject({
        request: expect.any(Object),
        result: expect.any(Object),
      });
    } finally {
      await app.close();
    }
  });

  it("validates matched path parameters before authentication", async () => {
    const { app } = await buildStudioApp();
    try {
      const response = await app.inject({
        method: "GET",
        url: `/api/projects/${"p".repeat(65)}/jobs/${"j".repeat(65)}`,
      });
      expect(response.statusCode, response.body).toBe(422);
      expect(response.json().error.code).toBe("VALIDATION_ERROR");
    } finally {
      await app.close();
    }
  });

  it("requires authentication for validly shaped detail parameters", async () => {
    const { app } = await buildStudioApp();
    try {
      const response = await app.inject({
        method: "GET",
        url: "/api/projects/project-a/jobs/job-a",
      });
      expect(response.statusCode, response.body).toBe(401);
    } finally {
      await app.close();
    }
  });

  it("normalizes every known scoped miss to the same complete 404 envelope", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const firstProject = await seedProject(app, owner, "Detail scope A");
      const secondProject = await seedProject(app, owner, "Detail scope B");
      const secondDocument = firstDocument(secondProject);
      const foreignJob = await draftProposal(app, owner, secondProject.id, secondDocument.id, {
        operation: "continue",
        instruction: "foreign project job",
      });

      const missingJob = await call(
        app,
        owner,
        "GET",
        `/api/projects/${firstProject.id}/jobs/missing-job`,
      );
      const crossProject = await call(
        app,
        owner,
        "GET",
        `/api/projects/${firstProject.id}/jobs/${foreignJob.id}`,
      );
      const missingProject = await call(
        app,
        owner,
        "GET",
        "/api/projects/missing-project/jobs/missing-job",
      );

      for (const response of [missingJob, crossProject, missingProject]) {
        expect(response.statusCode, response.body).toBe(404);
        expect(response.json()).toEqual({
          error: { code: "NOT_FOUND", message: "Job not found." },
        });
      }
    } finally {
      await app.close();
    }
  });

  it("validates a trailing empty detail segment before authentication", async () => {
    const { app } = await buildStudioApp();
    try {
      const response = await app.inject({
        method: "GET",
        url: "/api/projects/project-a/jobs/",
      });
      expect(response.statusCode, response.body).toBe(422);
      expect(response.json().error.code).toBe("VALIDATION_ERROR");
    } finally {
      await app.close();
    }
  });

  it("documents bounded parameters, stable read errors, and the complete Job response", async () => {
    const { app } = await buildStudioApp();
    try {
      const document = (await app.inject({ method: "GET", url: "/openapi.json" })).json();
      const operation = document.paths["/api/projects/{projectId}/jobs/{jobId}"].get;
      const pathParameters = Object.fromEntries(
        operation.parameters.map((parameter: { name: string; schema: object }) => [
          parameter.name,
          parameter.schema,
        ]),
      );

      expect(pathParameters).toEqual({
        projectId: { type: "string", minLength: 1, maxLength: 64 },
        jobId: { type: "string", minLength: 1, maxLength: 64 },
      });
      expect(Object.keys(operation.responses).sort()).toEqual(["200", "401", "404", "422", "503"]);
      const payload = operation.responses["200"].content["application/json"].schema;
      expect(payload.required).toEqual(
        expect.arrayContaining(["request", "result", "events", "created_at", "updated_at"]),
      );
      expect(payload.properties.events.description).toContain("oldest first");
    } finally {
      await app.close();
    }
  });
});
