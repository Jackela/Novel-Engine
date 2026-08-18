import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";

describe("GET /api/hello", () => {
  it("answers with a greeting through inject()", async () => {
    const app = await buildApp();

    try {
      const response = await app.inject({ method: "GET", url: "/api/hello" });

      expect(response.statusCode).toBe(200);
      expect(response.json()).toEqual({ message: "hello from novel-engine server" });
    } finally {
      await app.close();
    }
  });
});
