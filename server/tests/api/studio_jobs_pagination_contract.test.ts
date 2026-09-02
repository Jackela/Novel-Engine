import { describe, expect, it } from "vitest";

import {
  decodeJobCursor,
  encodeJobCursor,
} from "../../src/contexts/studio/interface/http/job_cursor.js";
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

describe("jobs pagination HTTP contract", () => {
  it("rejects invalid limits through the validation envelope", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Invalid jobs limits");
      for (const limit of ["0", "101", "1.5", "not-an-integer"]) {
        const response = await call(
          app,
          owner,
          "GET",
          `/api/projects/${project.id}/jobs?limit=${encodeURIComponent(limit)}`,
        );

        expect(response.statusCode, response.body).toBe(422);
        expect(response.json().error.code).toBe("VALIDATION_ERROR");
      }
    } finally {
      await app.close();
    }
  });

  it("round-trips only canonical project-bound cursor positions", () => {
    const token = encodeJobCursor("project-a", { createdAtMs: 1_725_000_000_123, id: "job-a" });
    expect(token).not.toBeNull();
    expect(decodeJobCursor(token ?? "", "project-a")).toEqual({
      createdAtMs: 1_725_000_000_123,
      id: "job-a",
    });

    const invalidTokens = [
      "not+base64url",
      Buffer.from('[1, "project-a", 1, "job-a"]', "utf8").toString("base64url"),
      Buffer.from('[1,"project-a",1e0,"job-a"]', "utf8").toString("base64url"),
      Buffer.from('[1,"project\\u002da",1,"job-a"]', "utf8").toString("base64url"),
      Buffer.from(JSON.stringify([2, "project-a", 1, "job-a"])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "project-a", -1, "job-a"])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "project-a", 1, ""])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "project-a", 1, "x".repeat(129)])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "project-a", 1, "job-a", "extra"])).toString("base64url"),
    ];
    for (const invalid of invalidTokens) {
      expect(() => decodeJobCursor(invalid, "project-a")).toThrowError(
        expect.objectContaining({ code: "VALIDATION_ERROR", statusCode: 422 }),
      );
    }
    expect(() => decodeJobCursor(token ?? "", "project-b")).toThrowError(
      expect.objectContaining({ code: "VALIDATION_ERROR", statusCode: 422 }),
    );
  });

  it("rejects invalid cursors before project lookup", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const routeProjectId = "00000000-0000-4000-8000-000000000099";
      const crossProject = encodeJobCursor("another-project", { createdAtMs: 1, id: "job-a" });
      const unknownVersion = Buffer.from(JSON.stringify([2, routeProjectId, 1, "job-a"])).toString(
        "base64url",
      );

      for (const cursor of [crossProject ?? "", unknownVersion, "a".repeat(1025)]) {
        const response = await call(
          app,
          owner,
          "GET",
          `/api/projects/${routeProjectId}/jobs?cursor=${encodeURIComponent(cursor)}`,
        );
        expect(response.statusCode, response.body).toBe(422);
        expect(response.json().error.code).toBe("VALIDATION_ERROR");
        expect(response.json().error.details.errors[0].field).toBe("cursor");
      }
    } finally {
      await app.close();
    }
  });

  it("returns and follows a project-bound HTTP cursor", async () => {
    const { app } = await buildStudioApp(monotonicClock());
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Jobs HTTP traversal");
      const document = firstDocument(project);
      const older = await draftProposal(app, owner, project.id, document.id, {
        operation: "continue",
        instruction: "older",
      });
      const newer = await draftProposal(app, owner, project.id, document.id, {
        operation: "rewrite",
        instruction: "newer",
      });

      const first = await call(app, owner, "GET", `/api/projects/${project.id}/jobs?limit=1`);
      expect(first.statusCode, first.body).toBe(200);
      expect(first.json().jobs.map((job: { id: string }) => job.id)).toEqual([newer.id]);
      expect(first.json().next_cursor).toEqual(expect.any(String));

      const second = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/jobs?limit=1&cursor=${encodeURIComponent(first.json().next_cursor)}`,
      );
      expect(second.statusCode, second.body).toBe(200);
      expect(second.json().jobs.map((job: { id: string }) => job.id)).toEqual([older.id]);
      expect(second.json().next_cursor).toBeNull();
    } finally {
      await app.close();
    }
  });

  it("applies the default and maximum page bounds at the authenticated HTTP seam", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Jobs HTTP bounds");
      const database = studioDatabase(app);
      database
        .insert(jobsTable)
        .values(
          Array.from({ length: 101 }, (_, index) => {
            const label = String(index).padStart(3, "0");
            const createdAt = new Date(index + 1);
            return {
              id: `job-${label}`,
              project_id: project.id,
              document_id: null,
              kind: "proposal",
              operation: "continue",
              status: "completed",
              provider: "mock",
              model: "deterministic-story-v1",
              request_json: "{}",
              result_json: "{}",
              error: null,
              retry_of_job_id: null,
              created_at: createdAt,
              updated_at: createdAt,
            };
          }),
        )
        .run();

      const defaultPage = await call(app, owner, "GET", `/api/projects/${project.id}/jobs`);
      expect(defaultPage.statusCode, defaultPage.body).toBe(200);
      expect(defaultPage.json().jobs).toHaveLength(50);
      expect(defaultPage.json().jobs[0]?.id).toBe("job-100");
      expect(defaultPage.json().jobs[49]?.id).toBe("job-051");
      expect(defaultPage.json().next_cursor).toEqual(expect.any(String));

      const maximumPage = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/jobs?limit=100`,
      );
      expect(maximumPage.statusCode, maximumPage.body).toBe(200);
      expect(maximumPage.json().jobs).toHaveLength(100);
      expect(maximumPage.json().jobs[0]?.id).toBe("job-100");
      expect(maximumPage.json().jobs[99]?.id).toBe("job-001");
      expect(maximumPage.json().next_cursor).toEqual(expect.any(String));
    } finally {
      await app.close();
    }
  });

  it("documents the bounded query and required nullable cursor response", async () => {
    const { app } = await buildStudioApp();
    try {
      const document = (await app.inject({ method: "GET", url: "/openapi.json" })).json();
      const operation = document.paths["/api/projects/{projectId}/jobs"].get;
      const parameters = Object.fromEntries(
        operation.parameters.map((parameter: { name: string; schema: object }) => [
          parameter.name,
          parameter.schema,
        ]),
      );

      expect(parameters.limit).toMatchObject({
        type: "integer",
        default: 50,
        minimum: 1,
        maximum: 100,
      });
      expect(parameters.cursor).toMatchObject({
        type: "string",
        minLength: 1,
        maxLength: 1024,
        pattern: "^[A-Za-z0-9_-]+$",
      });
      expect(operation.responses["422"]).toBeDefined();
      expect(
        operation.responses["200"].content["application/json"].schema.properties.next_cursor,
      ).toEqual({ type: "string", nullable: true });
      expect(operation.responses["200"].content["application/json"].schema.required).toContain(
        "next_cursor",
      );
    } finally {
      await app.close();
    }
  });
});
