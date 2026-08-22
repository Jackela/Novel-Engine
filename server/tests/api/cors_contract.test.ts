import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import { loadServerConfig } from "../../src/shared/infrastructure/config/server_config.js";

/** The app under a throwaway data directory; tests never touch the real data/. */
async function buildCorsApp(corsEnv?: Record<string, string>): Promise<FastifyInstance> {
  const workspace = await mkdtemp(join(tmpdir(), "novel-engine-cors-"));
  return buildApp({
    logger: false,
    config: loadServerConfig({
      env: corsEnv ?? {},
      envFile: null,
      workingDirectory: workspace,
    }),
  });
}

describe("CORS origin contract", () => {
  it("answers a credentialed preflight from the dev origin with the CSRF header allowed", async () => {
    const app = await buildCorsApp();

    const response = await app.inject({
      method: "OPTIONS",
      url: "/api/session/login",
      headers: {
        origin: "http://localhost:5173",
        "access-control-request-method": "POST",
        "access-control-request-headers": "content-type,x-csrf-token",
      },
    });

    expect(response.statusCode).toBe(204);
    expect(response.headers["access-control-allow-origin"]).toBe("http://localhost:5173");
    expect(response.headers["access-control-allow-credentials"]).toBe("true");
    expect(String(response.headers["access-control-allow-headers"])).toContain("x-csrf-token");
    await app.close();
  });

  it("echoes the dev origin on actual credentialed requests", async () => {
    const app = await buildCorsApp();

    const response = await app.inject({
      method: "GET",
      url: "/health",
      headers: { origin: "http://localhost:4173" },
    });

    expect(response.statusCode).toBe(200);
    expect(response.headers["access-control-allow-origin"]).toBe("http://localhost:4173");
    expect(response.headers["access-control-allow-credentials"]).toBe("true");
    await app.close();
  });

  it("does not allow an unconfigured origin", async () => {
    const app = await buildCorsApp();

    const response = await app.inject({
      method: "GET",
      url: "/health",
      headers: { origin: "https://evil.example" },
    });

    expect(response.statusCode).toBe(200);
    expect(response.headers["access-control-allow-origin"]).toBeUndefined();
    await app.close();
  });

  it("expands a localhost wildcard to exactly the development ports", async () => {
    const app = await buildCorsApp({ SECURITY_CORS_ORIGINS: "http://localhost:*" });

    for (const port of [5173, 4173, 8000]) {
      const response = await app.inject({
        method: "GET",
        url: "/health",
        headers: { origin: `http://localhost:${port}` },
      });
      expect(response.headers["access-control-allow-origin"]).toBe(`http://localhost:${port}`);
    }

    const rejected = await app.inject({
      method: "GET",
      url: "/health",
      headers: { origin: "http://localhost:9999" },
    });
    expect(rejected.headers["access-control-allow-origin"]).toBeUndefined();
    await app.close();
  });
});
