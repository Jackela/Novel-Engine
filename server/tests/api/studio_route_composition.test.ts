import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";

const existingStudioRoutes = [
  { method: "GET", url: "/api/projects" },
  { method: "PATCH", url: "/api/projects/project-1", payload: { title: "Updated" } },
  { method: "GET", url: "/api/projects/project-1/documents/document-1/revisions" },
  { method: "POST", url: "/api/projects/project-1/ai-proposals/job-1/accept" },
  { method: "GET", url: "/api/projects/project-1/reviews" },
] as const;

describe("Studio route composition", () => {
  it("registers each existing Studio route group on the database-free app", async () => {
    const app = await buildApp({ logger: false });
    try {
      for (const route of existingStudioRoutes) {
        const response = await app.inject(route);

        expect(response.statusCode, `${route.method} ${route.url}`).toBe(503);
        expect(response.json()).toEqual({
          error: {
            code: "SERVICE_UNAVAILABLE",
            message: "The persistence layer is not configured.",
          },
        });
      }
    } finally {
      await app.close();
    }
  });
});
