import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import { deferredReviewFactory, firstDocument, flakyProviderFactory } from "./job_test_helpers.js";
import {
  authHeaders,
  buildStudioApp,
  call,
  draftProposal,
  type JobPayload,
  monotonicClock,
  ownerJar,
  seedProject,
} from "./studio_helpers.js";

const VALID_KEY = "retry-attempt-00000001";

describe("job retry idempotency HTTP contract", () => {
  it("validates the required header before authentication and without creating evidence", async () => {
    const failures = { count: 1 };
    const { app } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: flakyProviderFactory(failures),
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Retry key validation");
      const source = await failedProposal(app, owner, project);
      const before = retryEvidence(app);
      const url = `/api/projects/${project.id}/jobs/${source.id}/retry`;
      const invalidHeaders: Array<[string, string | string[] | undefined]> = [
        ["missing", undefined],
        ["empty", ""],
        ["short", "a".repeat(15)],
        ["overlong", "a".repeat(129)],
        ["whitespace", "valid-key-000001 "],
        ["non-ASCII", "retry-attempt-测试-0001"],
        ["invalid character", "valid-prefix-0001/"],
        ["duplicate", ["duplicate-key-0001", "duplicate-key-0002"]],
      ];

      for (const [label, key] of invalidHeaders) {
        const response = await retry(app, owner, url, key);
        expect(response.statusCode, `${label}: ${response.body}`).toBe(422);
        expect(response.json().error.code).toBe("VALIDATION_ERROR");
        expect(retryEvidence(app)).toEqual(before);
      }

      const anonymousMissing = await app.inject({ method: "POST", url });
      expect(anonymousMissing.statusCode, anonymousMissing.body).toBe(422);
      expect(anonymousMissing.json().error.code).toBe("VALIDATION_ERROR");
      expect(retryEvidence(app)).toEqual(before);

      const bodyOnly = await app.inject({
        method: "POST",
        url,
        headers: authHeaders(owner),
        payload: { idempotency_key: VALID_KEY },
      });
      expect(bodyOnly.statusCode, bodyOnly.body).toBe(422);
      expect(bodyOnly.json().error.code).toBe("VALIDATION_ERROR");
      expect(retryEvidence(app)).toEqual(before);

      const anonymousValid = await app.inject({
        method: "POST",
        url,
        headers: { "idempotency-key": VALID_KEY },
      });
      expect(anonymousValid.statusCode, anonymousValid.body).toBe(401);
      expect(retryEvidence(app)).toEqual(before);
    } finally {
      await app.close();
    }
  });

  it("returns the keyed running conflict with Retry-After without duplicate execution", async () => {
    const deferred = deferredReviewFactory(1);
    const { app } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: deferred.factory,
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Running keyed retry");
      const sourceResponse = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      const source = sourceResponse.json<JobPayload>();
      expect(source.status).toBe("failed");
      const url = `/api/projects/${project.id}/jobs/${source.id}/retry`;

      const creator = retry(app, owner, url, VALID_KEY);
      await deferred.started;
      const replay = await retry(app, owner, url, VALID_KEY);
      deferred.succeed();
      const completed = await creator;

      expect(replay.statusCode, replay.body).toBe(409);
      expect(replay.json().error.code).toBe("OPERATION_IN_FLIGHT");
      expect(replay.headers["retry-after"]).toBe("1");
      expect(completed.statusCode, completed.body).toBe(200);
      expect(retryEvidence(app)).toMatchObject({ jobs: 2, events: 3 });
    } finally {
      deferred.succeed();
      await app.close();
    }
  });

  it("replays the exact terminal Job without adding any evidence", async () => {
    const failures = { count: 1 };
    const { app } = await buildStudioApp(monotonicClock(), {
      textProviderFactory: flakyProviderFactory(failures),
    });
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Terminal keyed retry");
      const source = await failedProposal(app, owner, project);
      const url = `/api/projects/${project.id}/jobs/${source.id}/retry`;

      const first = await retry(app, owner, url, VALID_KEY);
      expect(first.statusCode, first.body).toBe(200);
      const afterFirst = retryEvidence(app);
      const replay = await retry(app, owner, url, VALID_KEY);

      expect(replay.statusCode, replay.body).toBe(200);
      expect(replay.json<JobPayload>()).toEqual(first.json<JobPayload>());
      expect(retryEvidence(app)).toEqual(afterFirst);
    } finally {
      await app.close();
    }
  });

  it("allows the header through CORS and documents the complete OpenAPI contract", async () => {
    const app = await buildApp({ logger: false });
    try {
      const preflight = await app.inject({
        method: "OPTIONS",
        url: "/api/projects/project-1/jobs/job-1/retry",
        headers: {
          origin: "http://localhost:5173",
          "access-control-request-method": "POST",
          "access-control-request-headers": "idempotency-key,x-csrf-token",
        },
      });
      expect(preflight.statusCode).toBe(204);
      expect(String(preflight.headers["access-control-allow-headers"])).toContain(
        "idempotency-key",
      );

      const document = (await app.inject({ method: "GET", url: "/openapi.json" })).json();
      const operation = document.paths["/api/projects/{projectId}/jobs/{jobId}/retry"].post;
      expect(operation.parameters).toContainEqual({
        in: "header",
        name: "idempotency-key",
        required: true,
        schema: {
          type: "string",
          minLength: 16,
          maxLength: 128,
          pattern: "^[A-Za-z0-9._~-]+$",
        },
      });
      expect(operation.requestBody).toBeUndefined();
      expect(operation.responses["409"].headers["Retry-After"].schema).toMatchObject({
        type: "integer",
        const: 1,
      });
    } finally {
      await app.close();
    }
  });
});

async function failedProposal(
  app: FastifyInstance,
  owner: Awaited<ReturnType<typeof ownerJar>>,
  project: Awaited<ReturnType<typeof seedProject>>,
): Promise<JobPayload> {
  const source = await draftProposal(app, owner, project.id, firstDocument(project).id, {
    operation: "continue",
    instruction: "fail once for retry",
  });
  expect(source.status).toBe("failed");
  return source;
}

function retry(
  app: FastifyInstance,
  owner: Awaited<ReturnType<typeof ownerJar>>,
  url: string,
  key: string | string[] | undefined,
) {
  return app.inject({
    method: "POST",
    url,
    headers: {
      ...authHeaders(owner),
      ...(key === undefined ? {} : { "idempotency-key": key }),
    },
  });
}

function retryEvidence(app: FastifyInstance): {
  jobs: number;
  events: number;
  usage: number;
} {
  const database = app.studioDb?.raw;
  if (database === undefined) throw new Error("Expected the real Studio database.");
  const row = database
    .prepare(
      `SELECT
         (SELECT count(*) FROM jobs) AS jobs,
         (SELECT count(*) FROM job_events) AS events,
         (SELECT count(*) FROM usage_events) AS usage`,
    )
    .get();
  if (!isEvidence(row)) throw new Error("Expected numeric retry evidence counts.");
  return row;
}

function isEvidence(value: unknown): value is { jobs: number; events: number; usage: number } {
  if (value === null || typeof value !== "object") return false;
  const row = value as Record<string, unknown>;
  return (
    typeof row.jobs === "number" && typeof row.events === "number" && typeof row.usage === "number"
  );
}
