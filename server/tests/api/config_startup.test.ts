import { randomBytes } from "node:crypto";
import { existsSync } from "node:fs";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import { loadServerConfig } from "../../src/shared/infrastructure/config/server_config.js";
import { OWNER_PASSWORD, OWNER_USERNAME } from "./auth_helpers.js";

async function makeWorkspace(): Promise<string> {
  return mkdtemp(join(tmpdir(), "novel-engine-config-wiring-"));
}

function configOver(workspace: string, env: Record<string, string> = {}) {
  return loadServerConfig({ env, envFile: null, workingDirectory: workspace });
}

describe("configuration at the composition root", () => {
  it("fails fast on production misconfiguration before touching the data directory", async () => {
    const workspace = await makeWorkspace();
    const config = { ...configOver(workspace), environment: "production" as const };

    await expect(
      buildApp({
        logger: false,
        config,
      }),
    ).rejects.toThrow(/SECURITY_SECRET_KEY/);

    expect(existsSync(join(workspace, "data"))).toBe(false);
  });

  it("rejects an invalid direct workflow capacity before opening persistence", async () => {
    const workspace = await makeWorkspace();

    await expect(
      buildApp({
        logger: false,
        databasePath: join(workspace, "data", "novel-engine.sqlite3"),
        operationCapacity: { applicationLimit: 1, projectLimit: 2 },
      }),
    ).rejects.toThrow(/project.*must not exceed.*application/i);

    expect(existsSync(join(workspace, "data"))).toBe(false);
  });

  it("invalidates sessions on every non-production restart with an unset secret", async () => {
    const workspace = await makeWorkspace();
    const first = await buildApp({ logger: false, config: configOver(workspace) });

    await first.inject({
      method: "POST",
      url: "/api/setup",
      payload: { username: OWNER_USERNAME, password: OWNER_PASSWORD },
    });
    const login = await first.inject({
      method: "POST",
      url: "/api/session/login",
      payload: { username: OWNER_USERNAME, password: OWNER_PASSWORD },
    });
    expect(login.statusCode).toBe(200);
    const cookie = (login.headers["set-cookie"] ?? [""])[0]?.split(";")[0] ?? "";
    await first.close();

    const second: FastifyInstance = await buildApp({
      logger: false,
      config: configOver(workspace),
    });
    const probe = await second.inject({
      method: "GET",
      url: "/api/session",
      headers: { cookie },
    });
    expect(probe.statusCode).toBe(401);
    await second.close();
  });

  it("wires the configured authentication rate limit into the limiter", async () => {
    const workspace = await makeWorkspace();
    const app = await buildApp({
      logger: false,
      config: configOver(workspace, { SECURITY_RATE_LIMIT: "1/minute" }),
    });

    const credentials = { username: OWNER_USERNAME, password: OWNER_PASSWORD };
    const first = await app.inject({
      method: "POST",
      url: "/api/session/login",
      payload: credentials,
    });
    const second = await app.inject({
      method: "POST",
      url: "/api/session/login",
      payload: credentials,
    });

    expect(first.statusCode).toBe(422);
    expect(second.statusCode).toBe(429);
    await app.close();
  });

  it("keeps an explicit production secret stable across restarts", async () => {
    const workspace = await makeWorkspace();
    const secret = randomBytes(32).toString("base64url");
    const env = {
      APP_ENVIRONMENT: "production",
      SECURITY_SECRET_KEY: secret,
      SECURITY_CORS_ORIGINS: "https://app.example.com",
    };

    const first = await buildApp({ logger: false, config: configOver(workspace, env) });
    await first.inject({
      method: "POST",
      url: "/api/setup",
      payload: { username: OWNER_USERNAME, password: OWNER_PASSWORD },
    });
    const login = await first.inject({
      method: "POST",
      url: "/api/session/login",
      payload: { username: OWNER_USERNAME, password: OWNER_PASSWORD },
    });
    expect(login.statusCode).toBe(200);
    const cookie = (login.headers["set-cookie"] ?? [""])[0]?.split(";")[0] ?? "";
    await first.close();

    const second = await buildApp({ logger: false, config: configOver(workspace, env) });
    const probe = await second.inject({
      method: "GET",
      url: "/api/session",
      headers: { cookie },
    });
    expect(probe.statusCode).toBe(200);
    await second.close();
  });
});
