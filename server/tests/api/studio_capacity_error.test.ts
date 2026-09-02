import { describe, expect, it } from "vitest";
import { buildApp } from "../../src/apps/api/app.js";
import { OperationCapacityExceededError } from "../../src/contexts/studio/domain/exceptions.js";
import { withStudioErrors } from "../../src/contexts/studio/interface/http/studio_error_mapping.js";
import { AppError } from "../../src/shared/interface/http/error_envelope.js";

describe("studio operation capacity error mapping", () => {
  it("maps capacity refusal to the stable 503 envelope details and retry hint", () => {
    let mapped: unknown;

    try {
      withStudioErrors(() => {
        throw new OperationCapacityExceededError("project", 2, 2, "project-1", 5);
      });
    } catch (error) {
      mapped = error;
    }

    expect(mapped).toBeInstanceOf(AppError);
    expect(mapped).toMatchObject({
      statusCode: 503,
      code: "OPERATION_CAPACITY_EXCEEDED",
      message: "Studio operation capacity is exhausted.",
      details: {
        scope: "project",
        limit: 2,
        in_flight: 2,
        project_id: "project-1",
        retry_after_seconds: 5,
      },
      responseHeaders: { "retry-after": "5" },
    });
  });

  it("documents capacity and persistence 503 responses for every expensive workflow", async () => {
    const app = await buildApp({ logger: false });

    try {
      const document = (await app.inject({ method: "GET", url: "/openapi.json" })).json();
      type OpenApiOperation = {
        responses?: Record<string, { headers?: Record<string, unknown> }>;
      };
      const documentedCapacityOperations = Object.entries(
        document.paths as Record<string, Record<string, OpenApiOperation>>,
      )
        .flatMap(([path, methods]) =>
          Object.entries(methods).flatMap(([method, operation]) =>
            operation.responses?.["503"]?.headers?.["Retry-After"] === undefined
              ? []
              : [`${method.toUpperCase()} ${path}`],
          ),
        )
        .sort();
      expect(documentedCapacityOperations).toEqual(
        [
          "GET /api/projects/{projectId}/exports/{exportId}/download",
          "POST /api/projects/{projectId}/documents/{documentId}/ai-proposals",
          "POST /api/projects/{projectId}/documents/{documentId}/ai-proposals/stream",
          "POST /api/projects/{projectId}/exports",
          "POST /api/projects/{projectId}/jobs/{jobId}/retry",
          "POST /api/projects/{projectId}/reviews",
        ].sort(),
      );
      const operations = [
        document.paths["/api/projects/{projectId}/documents/{documentId}/ai-proposals"].post,
        document.paths["/api/projects/{projectId}/documents/{documentId}/ai-proposals/stream"].post,
        document.paths["/api/projects/{projectId}/reviews"].post,
        document.paths["/api/projects/{projectId}/exports"].post,
        document.paths["/api/projects/{projectId}/exports/{exportId}/download"].get,
        document.paths["/api/projects/{projectId}/jobs/{jobId}/retry"].post,
      ];

      for (const operation of operations) {
        const response = operation.responses["503"];
        expect(response.headers["Retry-After"].schema).toMatchObject({
          type: "integer",
          minimum: 1,
        });
        const serialized = JSON.stringify(response.content["application/json"].schema);
        expect(serialized).toContain("OPERATION_CAPACITY_EXCEEDED");
        expect(serialized).toContain("SERVICE_UNAVAILABLE");
      }
    } finally {
      await app.close();
    }
  });
});
