import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";

const productManifest = JSON.parse(
  readFileSync(new URL("../../package.json", import.meta.url), "utf8"),
) as { productName: string; version: string };

describe("GET /version", () => {
  it("reports the workspace manifest version, Node runtime, environment, and build SHA", async () => {
    const app = await buildApp({
      logger: false,
      environment: "testing",
      buildSha: "deadbeef",
    });

    try {
      const response = await app.inject({ method: "GET", url: "/version" });
      const openapiResponse = await app.inject({ method: "GET", url: "/openapi.json" });

      expect(response.statusCode).toBe(200);
      expect(response.json()).toEqual({
        version: productManifest.version,
        name: productManifest.productName,
        runtime: { name: "node", version: process.versions.node },
        environment: "testing",
        build: "deadbeef",
      });
      expect(openapiResponse.statusCode).toBe(200);
      expect(openapiResponse.json().info).toMatchObject({
        title: `${productManifest.productName} API`,
        version: productManifest.version,
      });
    } finally {
      await app.close();
    }
  });

  it("binds every structured log record to the manifest product identity", async () => {
    const lines: string[] = [];
    const app = await buildApp({
      logger: {
        level: "info",
        base: {
          deployment: "test",
          product_name: "forged-name",
          product_version: "9.9.9",
        },
        stream: { write: (line) => lines.push(line) },
      },
    });

    try {
      await app.inject({ method: "GET", url: "/version" });
    } finally {
      await app.close();
    }

    const records = lines.flatMap((line) =>
      line
        .split("\n")
        .filter(Boolean)
        .map((entry) => JSON.parse(entry) as Record<string, unknown>),
    );
    expect(records.length).toBeGreaterThan(0);
    for (const record of records) {
      expect(record).toMatchObject({
        deployment: "test",
        product_name: productManifest.productName,
        product_version: productManifest.version,
      });
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
