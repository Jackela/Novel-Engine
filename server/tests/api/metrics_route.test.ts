import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import { SESSION_SECRET_FILE_NAME } from "../../src/shared/infrastructure/config/session_secret.js";
import {
  cookieHeader,
  cookieJar,
  loginOwner,
  makeDataDirectory,
  setupOwner,
} from "./auth_helpers.js";

/**
 * DR-041 internal metrics surface: `GET /metrics` renders Prometheus text to
 * the loopback peer or an authenticated owner session, and stays out of the
 * unauthenticated surface (401 envelope) everywhere else. The body carries
 * counters only — never the session secret.
 */
const NON_LOOPBACK_PEER = "203.0.113.7";

async function openApp(directory: string) {
  return buildApp({
    logger: false,
    environment: "development",
    databasePath: join(directory, "novel-engine.sqlite3"),
  });
}

describe("internal metrics surface (DR-041)", () => {
  it("serves Prometheus text to the loopback peer without leaking the secret", async () => {
    const directory = await makeDataDirectory();
    const app = await openApp(directory);
    try {
      const response = await app.inject({ method: "GET", url: "/metrics" });
      expect(response.statusCode, response.body).toBe(200);
      expect(response.headers["content-type"]).toContain("text/plain");
      expect(response.headers["content-type"]).toContain("version=0.0.4");

      const body = response.body;
      for (const metric of [
        "novel_engine_info",
        "novel_engine_uptime_seconds",
        "novel_engine_process_resident_memory_bytes",
        "novel_engine_nodejs_heap_used_bytes",
        "novel_engine_documents",
        "novel_engine_revisions",
        "novel_engine_usage_requests_total",
        "novel_engine_usage_prompt_tokens_total",
        "novel_engine_usage_completion_tokens_total",
      ]) {
        expect(body, `expected ${metric} in the scrape`).toContain(`\n${metric}`);
      }
      // A store-counter read that reached the migrated database renders
      // numbers, and no NaN can reach a scraper.
      expect(body).toContain("novel_engine_documents 0");
      expect(body).not.toContain("NaN");

      const secret = readFileSync(join(directory, SESSION_SECRET_FILE_NAME), "utf8").trim();
      expect(secret).not.toBe("");
      expect(body).not.toContain(secret);
    } finally {
      await app.close();
    }
  });

  it("accepts IPv4-mapped and IPv6 loopback peers", async () => {
    const directory = await makeDataDirectory();
    const app = await openApp(directory);
    try {
      for (const remoteAddress of ["127.0.0.1", "::1", "::ffff:127.0.0.1"]) {
        const response = await app.inject({ method: "GET", url: "/metrics", remoteAddress });
        expect(response.statusCode, `${remoteAddress}: ${response.body}`).toBe(200);
      }
    } finally {
      await app.close();
    }
  });

  it("answers 401 without figures to a non-loopback anonymous scrape", async () => {
    const directory = await makeDataDirectory();
    const app = await openApp(directory);
    try {
      const response = await app.inject({
        method: "GET",
        url: "/metrics",
        remoteAddress: NON_LOOPBACK_PEER,
      });
      expect(response.statusCode).toBe(401);
      expect(response.json().error.code).toBe("UNAUTHORIZED");
      expect(response.body).not.toContain("novel_engine_uptime_seconds");
    } finally {
      await app.close();
    }
  });

  it("serves a non-loopback scrape to an authenticated owner session", async () => {
    const directory = await makeDataDirectory();
    const app = await openApp(directory);
    try {
      await setupOwner(app);
      const jar = cookieJar(await loginOwner(app));
      const response = await app.inject({
        method: "GET",
        url: "/metrics",
        remoteAddress: NON_LOOPBACK_PEER,
        headers: { cookie: cookieHeader(jar) },
      });
      expect(response.statusCode, response.body).toBe(200);
      expect(response.body).toContain("novel_engine_uptime_seconds");
    } finally {
      await app.close();
    }
  });
});
