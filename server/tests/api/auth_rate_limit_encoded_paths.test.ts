import { readFileSync } from "node:fs";
import { rm } from "node:fs/promises";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import { owners, sessions } from "../../src/shared/infrastructure/db/schema.js";
import {
  buildAuthApp,
  type InjectedResponse,
  OWNER_PASSWORD,
  OWNER_USERNAME,
  setupOwner,
} from "./auth_helpers.js";

/** Freeze the limiter's monotonic clock so a slow runner cannot replenish a burst. */
beforeEach(() => {
  vi.spyOn(performance, "now").mockReturnValue(0);
});

afterEach(() => {
  vi.restoreAllMocks();
});

function expectRateLimited(response: InjectedResponse): void {
  expect(response.statusCode).toBe(429);
  const retryAfter = Number(response.headers["retry-after"]);
  expect(Number.isInteger(retryAfter)).toBe(true);
  expect(retryAfter).toBeGreaterThanOrEqual(1);
  expect(response.json().error).toMatchObject({
    code: "RATE_LIMIT_EXCEEDED",
    details: { retry_after_seconds: retryAfter },
  });
  expect(response.headers["set-cookie"]).toBeUndefined();
}

describe("authentication limits use the matched route", () => {
  it("shares the setup bucket across encoded aliases before verifying the setup token", async () => {
    const { app, directory } = await buildAuthApp();
    const payload = { username: OWNER_USERNAME, password: OWNER_PASSWORD };
    const remoteAddress = "203.0.113.7";
    try {
      for (const url of [
        "/api/setup",
        "/%61pi/setup",
        "/api/%73etup",
        "/api/s%65tup?attempt=4",
        "/api/setup?attempt=5",
      ]) {
        const rejected = await app.inject({ method: "POST", url, remoteAddress, payload });
        expect(rejected.statusCode).toBe(403);
        expect(rejected.json().error.code).toBe("SETUP_TOKEN_INVALID");
      }
      const setupToken = readFileSync(join(directory, ".setup-token"), "utf8").trim();
      for (const url of ["/api/setup", "/api/%73etup", "/%61pi/setup?attempt=7"]) {
        expectRateLimited(
          await app.inject({
            method: "POST",
            url,
            remoteAddress,
            headers: { "x-setup-token": setupToken },
            payload,
          }),
        );
      }
      expect(await app.studioDb?.db.select().from(owners)).toHaveLength(0);

      /** GET and another peer keep their own buckets after this POST burst. */
      const status = await app.inject({ method: "GET", url: "/api/%73etup", remoteAddress });
      expect(status.statusCode).toBe(200);
      expect(status.json().owner_configured).toBe(false);
      const otherPeer = await app.inject({
        method: "POST",
        url: "/api/%73etup",
        remoteAddress: "203.0.113.8",
        payload,
      });
      expect(otherPeer.statusCode).toBe(403);
    } finally {
      await app.close();
      await rm(directory, { recursive: true, force: true });
    }
  });

  it("shares the login bucket across encoded aliases and cannot issue a session when spent", async () => {
    const { app, directory } = await buildAuthApp();
    try {
      expect((await setupOwner(app)).statusCode).toBe(201);
      for (const url of [
        "/api/session/login",
        "/api/session/%6cogin",
        "/api/session/%6Cogin",
        "/%61pi/session/login?attempt=4",
        "/api/session/login?attempt=5",
      ]) {
        const rejected = await app.inject({
          method: "POST",
          url,
          payload: { username: OWNER_USERNAME, password: "a-wrong-password" },
        });
        expect(rejected.statusCode).toBe(422);
      }
      for (const url of ["/api/session/login", "/api/session/%6Cogin"]) {
        expectRateLimited(
          await app.inject({
            method: "POST",
            url,
            payload: { username: OWNER_USERNAME, password: OWNER_PASSWORD },
          }),
        );
      }
      expect(await app.studioDb?.db.select().from(sessions)).toHaveLength(0);
    } finally {
      await app.close();
      await rm(directory, { recursive: true, force: true });
    }
  });

  it("limits encoded setup probes without a database while keeping readiness available", async () => {
    const app = await buildApp({ logger: false });
    try {
      for (let attempt = 0; attempt < 5; attempt += 1) {
        const response = await app.inject({
          method: "GET",
          url: attempt % 2 === 0 ? "/api/setup" : "/api/%73etup",
        });
        expect(response.statusCode).toBe(503);
        expect(response.json().error.code).toBe("SERVICE_UNAVAILABLE");
      }
      expectRateLimited(await app.inject({ method: "GET", url: "/api/%73etup" }));
      expect((await app.inject({ method: "GET", url: "/health/ready" })).statusCode).toBe(200);
    } finally {
      await app.close();
    }
  });
});
