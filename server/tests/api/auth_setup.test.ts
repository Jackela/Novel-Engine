import { readFileSync } from "node:fs";
import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import { owners } from "../../src/shared/infrastructure/db/schema.js";
import { buildAuthApp, OWNER_PASSWORD, OWNER_USERNAME, setupOwner } from "./auth_helpers.js";

const productManifest = JSON.parse(
  readFileSync(new URL("../../package.json", import.meta.url), "utf8"),
) as { productName: string; version: string };

async function ownerCount(app: FastifyInstance): Promise<number> {
  const rows = await app.studioDb?.db.select().from(owners);
  return rows?.length ?? -1;
}

describe("owner setup", () => {
  it("reports first-run status with the manifest product identity", async () => {
    const { app } = await buildAuthApp();
    try {
      const response = await app.inject({ method: "GET", url: "/api/setup" });
      expect(response.statusCode).toBe(200);
      expect(response.json()).toEqual({
        owner_configured: false,
        name: productManifest.productName,
        version: productManifest.version,
      });
    } finally {
      await app.close();
    }
  });

  it("creates the owner with valid credentials", async () => {
    const { app } = await buildAuthApp();
    try {
      const created = await setupOwner(app);
      expect(created.statusCode).toBe(201);
      const body = created.json();
      expect(typeof body.id).toBe("string");
      expect(body.username).toBe(OWNER_USERNAME);

      const status = await app.inject({ method: "GET", url: "/api/setup" });
      expect(status.json().owner_configured).toBe(true);
    } finally {
      await app.close();
    }
  });

  it("rejects a nine-character password without creating an owner", async () => {
    const { app } = await buildAuthApp();
    try {
      const response = await app.inject({
        method: "POST",
        url: "/api/setup",
        payload: { username: OWNER_USERNAME, password: "a".repeat(9) },
      });
      expect(response.statusCode).toBe(422);
      expect(response.json().error.code).toBe("INVALID_OPERATION");
      const status = await app.inject({ method: "GET", url: "/api/setup" });
      expect(status.json().owner_configured).toBe(false);
    } finally {
      await app.close();
    }
  });

  it("rejects a whitespace-only username", async () => {
    const { app } = await buildAuthApp();
    try {
      const response = await app.inject({
        method: "POST",
        url: "/api/setup",
        payload: { username: "   ", password: OWNER_PASSWORD },
      });
      expect(response.statusCode).toBe(422);
      const status = await app.inject({ method: "GET", url: "/api/setup" });
      expect(status.json().owner_configured).toBe(false);
    } finally {
      await app.close();
    }
  });

  it("rejects passwords beyond 72 UTF-8 bytes", async () => {
    const { app } = await buildAuthApp();
    try {
      const ascii = await app.inject({
        method: "POST",
        url: "/api/setup",
        payload: { username: OWNER_USERNAME, password: "b".repeat(73) },
      });
      expect(ascii.statusCode).toBe(422);

      const multibyte = await app.inject({
        method: "POST",
        url: "/api/setup",
        payload: { username: OWNER_USERNAME, password: "あ".repeat(25) },
      });
      expect(multibyte.statusCode).toBe(422);
      const status = await app.inject({ method: "GET", url: "/api/setup" });
      expect(status.json().owner_configured).toBe(false);
    } finally {
      await app.close();
    }
  });

  it("accepts a password of exactly 72 UTF-8 bytes", async () => {
    const { app } = await buildAuthApp();
    try {
      const response = await app.inject({
        method: "POST",
        url: "/api/setup",
        payload: { username: OWNER_USERNAME, password: "c".repeat(72) },
      });
      expect(response.statusCode).toBe(201);
    } finally {
      await app.close();
    }
  });

  it("rejects duplicate setup and leaves the existing owner unchanged", async () => {
    const { app } = await buildAuthApp();
    try {
      await setupOwner(app);
      const duplicate = await app.inject({
        method: "POST",
        url: "/api/setup",
        payload: { username: "other-owner", password: "another-long-password" },
      });
      expect(duplicate.statusCode).toBe(422);
      expect(duplicate.json().error.code).toBe("INVALID_OPERATION");
      expect(await ownerCount(app)).toBe(1);
    } finally {
      await app.close();
    }
  });

  it("yields exactly one owner under concurrent first-run setups", async () => {
    const { app } = await buildAuthApp();
    try {
      const [first, second] = await Promise.all([
        app.inject({
          method: "POST",
          url: "/api/setup",
          payload: { username: "racer-a", password: OWNER_PASSWORD },
        }),
        app.inject({
          method: "POST",
          url: "/api/setup",
          payload: { username: "racer-b", password: OWNER_PASSWORD },
        }),
      ]);
      const statuses = [first.statusCode, second.statusCode].sort();
      expect(statuses).toEqual([201, 422]);
      expect(await ownerCount(app)).toBe(1);
    } finally {
      await app.close();
    }
  });

  it("rejects foreign browser origins with 403 and creates no owner", async () => {
    const { app } = await buildAuthApp();
    try {
      const byOrigin = await app.inject({
        method: "POST",
        url: "/api/setup",
        headers: { origin: "https://evil.example" },
        payload: { username: OWNER_USERNAME, password: OWNER_PASSWORD },
      });
      expect(byOrigin.statusCode).toBe(403);

      const byReferer = await app.inject({
        method: "POST",
        url: "/api/setup",
        headers: { referer: "https://evil.example/attack" },
        payload: { username: OWNER_USERNAME, password: OWNER_PASSWORD },
      });
      expect(byReferer.statusCode).toBe(403);

      const status = await app.inject({ method: "GET", url: "/api/setup" });
      expect(status.json().owner_configured).toBe(false);
    } finally {
      await app.close();
    }
  });

  it("rejects null and userinfo origins", async () => {
    const { app } = await buildAuthApp();
    try {
      const nullOrigin = await app.inject({
        method: "POST",
        url: "/api/setup",
        headers: { origin: "null" },
        payload: { username: OWNER_USERNAME, password: OWNER_PASSWORD },
      });
      expect(nullOrigin.statusCode).toBe(403);

      const userinfo = await app.inject({
        method: "POST",
        url: "/api/setup",
        headers: { origin: "http://user:pass@localhost:5173" },
        payload: { username: OWNER_USERNAME, password: OWNER_PASSWORD },
      });
      expect(userinfo.statusCode).toBe(403);
    } finally {
      await app.close();
    }
  });

  it("rejects an Origin carrying a path component", async () => {
    const { app } = await buildAuthApp();
    try {
      const response = await app.inject({
        method: "POST",
        url: "/api/setup",
        headers: { origin: "http://localhost:5173/sneaky" },
        payload: { username: OWNER_USERNAME, password: OWNER_PASSWORD },
      });
      expect(response.statusCode).toBe(403);
    } finally {
      await app.close();
    }
  });

  it("allows the local development origin and origin-less bootstrap clients", async () => {
    const devOrigin = await buildAuthApp();
    try {
      const response = await devOrigin.app.inject({
        method: "POST",
        url: "/api/setup",
        headers: { origin: "http://localhost:5173" },
        payload: { username: OWNER_USERNAME, password: OWNER_PASSWORD },
      });
      expect(response.statusCode).toBe(201);
    } finally {
      await devOrigin.app.close();
    }

    const bootstrap = await buildAuthApp();
    try {
      const response = await setupOwner(bootstrap.app);
      expect(response.statusCode).toBe(201);
    } finally {
      await bootstrap.app.close();
    }
  });

  it("reports 503 when the persistence layer is not configured", async () => {
    const { buildApp } = await import("../../src/apps/api/app.js");
    const app = await buildApp({ logger: false });
    try {
      const response = await app.inject({ method: "GET", url: "/api/setup" });
      expect(response.statusCode).toBe(503);
      expect(response.json().error.code).toBe("SERVICE_UNAVAILABLE");
    } finally {
      await app.close();
    }
  });
});
