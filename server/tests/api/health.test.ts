import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import type { HealthProbe } from "../../src/shared/application/ports/health.js";

const healthyDatabaseProbe: HealthProbe = async () => ({
  components: [{ name: "database", status: "healthy", message: "SQLite ready" }],
});

const failingDatabaseProbe: HealthProbe = async () => ({
  components: [{ name: "database", status: "unhealthy", error: "database health check failed" }],
});

const throwingProbe: HealthProbe = async () => {
  throw new Error("probe transport exploded");
};

describe("health surface", () => {
  it("reports a live process on /health/live without touching probes", async () => {
    const app = await buildApp({ logger: false, healthProbe: throwingProbe });

    try {
      const response = await app.inject({ method: "GET", url: "/health/live" });

      expect(response.statusCode).toBe(200);
      expect(response.json()).toEqual({ status: "alive" });
    } finally {
      await app.close();
    }
  });

  it("serves /health with the injected database component", async () => {
    const app = await buildApp({ logger: false, healthProbe: healthyDatabaseProbe });

    try {
      const response = await app.inject({ method: "GET", url: "/health" });

      expect(response.statusCode).toBe(200);
      const body = response.json();
      expect(body.overall_status).toBe("healthy");
      expect(body.components.database).toMatchObject({
        status: "healthy",
        message: "SQLite ready",
      });
      expect(typeof body.timestamp).toBe("string");
    } finally {
      await app.close();
    }
  });

  it("marks /health unhealthy when the probe reports a down component", async () => {
    const app = await buildApp({ logger: false, healthProbe: failingDatabaseProbe });

    try {
      const response = await app.inject({ method: "GET", url: "/health" });

      expect(response.statusCode).toBe(200);
      const body = response.json();
      expect(body.overall_status).toBe("unhealthy");
      expect(body.components.database).toMatchObject({
        status: "unhealthy",
        error: "database health check failed",
      });
    } finally {
      await app.close();
    }
  });

  it("returns 503 from /health/ready when the database probe reports failure", async () => {
    const app = await buildApp({ logger: false, healthProbe: failingDatabaseProbe });

    try {
      const response = await app.inject({ method: "GET", url: "/health/ready" });

      expect(response.statusCode).toBe(503);
      expect(response.json()).toEqual({
        status: "not_ready",
        reason: "database health check failed",
      });
    } finally {
      await app.close();
    }
  });

  it("returns 503 from /health/ready when the probe itself throws", async () => {
    const app = await buildApp({ logger: false, healthProbe: throwingProbe });

    try {
      const response = await app.inject({ method: "GET", url: "/health/ready" });

      expect(response.statusCode).toBe(503);
      const body = response.json();
      expect(body.status).toBe("not_ready");
      expect(body.reason).toContain("probe transport exploded");
    } finally {
      await app.close();
    }
  });

  it("returns 200 from /health/ready when every probed component is healthy", async () => {
    const app = await buildApp({ logger: false, healthProbe: healthyDatabaseProbe });

    try {
      const response = await app.inject({ method: "GET", url: "/health/ready" });

      expect(response.statusCode).toBe(200);
      expect(response.json()).toEqual({ status: "ready" });
    } finally {
      await app.close();
    }
  });

  it("treats the walking skeleton without a probe as ready with no components", async () => {
    const app = await buildApp({ logger: false });

    try {
      const detailed = await app.inject({ method: "GET", url: "/health" });
      const ready = await app.inject({ method: "GET", url: "/health/ready" });

      expect(detailed.statusCode).toBe(200);
      expect(detailed.json().components).toEqual({});
      expect(ready.statusCode).toBe(200);
      expect(ready.json()).toEqual({ status: "ready" });
    } finally {
      await app.close();
    }
  });

  it("uses the live application database handle for readiness", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-health-db-"));
    const app = await buildApp({
      logger: false,
      databasePath: join(directory, "novel-engine.sqlite3"),
    });
    app.studioDb?.raw.close();

    try {
      const ready = await app.inject({ method: "GET", url: "/health/ready" });
      const live = await app.inject({ method: "GET", url: "/health/live" });

      expect(ready.statusCode).toBe(503);
      expect(ready.json()).toEqual({
        status: "not_ready",
        reason: "database health check failed",
      });
      expect(live.statusCode).toBe(200);
      expect(live.json()).toEqual({ status: "alive" });
    } finally {
      await app.close();
    }
  });

  it("keeps an explicit injected probe above the database default", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-health-override-"));
    const app = await buildApp({
      logger: false,
      databasePath: join(directory, "novel-engine.sqlite3"),
      healthProbe: healthyDatabaseProbe,
    });
    app.studioDb?.raw.close();

    try {
      const ready = await app.inject({ method: "GET", url: "/health/ready" });
      expect(ready.statusCode).toBe(200);
      expect(ready.json()).toEqual({ status: "ready" });
    } finally {
      await app.close();
    }
  });
});
