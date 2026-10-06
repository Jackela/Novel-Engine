import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";

/**
 * DR-027 header contract: both proposal-generation routes document the
 * optional `Idempotency-Key`; the retry route keeps its required key, and the
 * accept route needs no key at all (a duplicate acceptance is already safe on
 * the job row).
 */
describe("proposal generation request-key OpenAPI contract", () => {
  it("documents the optional generation key and keeps the retry key required", async () => {
    const app = await buildApp({ logger: false });
    try {
      const document = (await app.inject({ method: "GET", url: "/openapi.json" })).json();
      const expected = {
        in: "header",
        name: "idempotency-key",
        schema: {
          type: "string",
          minLength: 16,
          maxLength: 128,
          pattern: "^[A-Za-z0-9._~-]+$",
        },
      };
      const generationPaths = [
        "/api/projects/{projectId}/documents/{documentId}/ai-proposals",
        "/api/projects/{projectId}/documents/{documentId}/ai-proposals/stream",
      ];
      for (const path of generationPaths) {
        const post = document.paths[path].post;
        const parameter = (post.parameters as Array<Record<string, unknown>>).find(
          (candidate) => candidate.name === "idempotency-key",
        );
        expect(parameter, path).toMatchObject(expected);
        expect(parameter?.required, path).not.toBe(true);
      }

      const retry = document.paths["/api/projects/{projectId}/jobs/{jobId}/retry"].post;
      expect(retry.parameters).toContainEqual({ ...expected, required: true });

      const accept = document.paths["/api/projects/{projectId}/ai-proposals/{jobId}/accept"].post;
      const acceptKey = (accept.parameters as Array<Record<string, unknown>>).find(
        (candidate) => candidate.name === "idempotency-key",
      );
      expect(acceptKey).toBeUndefined();
    } finally {
      await app.close();
    }
  });
});
