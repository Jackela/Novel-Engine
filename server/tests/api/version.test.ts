import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";

describe("GET /version", () => {
  it("reports the workspace manifest version, Node runtime, environment, and build SHA", async () => {
    const app = await buildApp({
      logger: false,
      environment: "testing",
      buildSha: "deadbeef",
    });

    try {
      const response = await app.inject({ method: "GET", url: "/version" });

      expect(response.statusCode).toBe(200);
      expect(response.json()).toEqual({
        version: "0.3.1",
        name: "Novel Engine",
        runtime: { name: "node", version: process.versions.node },
        environment: "testing",
        build: "deadbeef",
      });
    } finally {
      await app.close();
    }
  });

  it("falls back to unknown build SHA when none is provided", async () => {
    const app = await buildApp({ logger: false, buildSha: undefined });

    try {
      const response = await app.inject({ method: "GET", url: "/version" });

      expect(response.statusCode).toBe(200);
      expect(response.json().build).toBe("unknown");
    } finally {
      await app.close();
    }
  });

  it("echoes a stable correlation id header on responses", async () => {
    const app = await buildApp({ logger: false });

    try {
      const withHeader = await app.inject({
        method: "GET",
        url: "/version",
        headers: { "x-request-id": "corr-abc" },
      });
      const withoutHeader = await app.inject({ method: "GET", url: "/version" });
      const withHostileHeader = await app.inject({
        method: "GET",
        url: "/version",
        headers: { "x-request-id": "drop table logs; <script>" },
      });

      expect(withHeader.headers["x-request-id"]).toBe("corr-abc");
      expect(withoutHeader.headers["x-request-id"]).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
      );
      expect(withHostileHeader.headers["x-request-id"]).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/,
      );
    } finally {
      await app.close();
    }
  });
});
