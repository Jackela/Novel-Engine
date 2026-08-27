import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import { sessions } from "../../src/shared/infrastructure/db/schema.js";
import {
  buildAuthApp,
  cookieHeader,
  cookieJar,
  loginOwner,
  OWNER_PASSWORD,
  setupOwner,
} from "./auth_helpers.js";

async function sessionCount(app: FastifyInstance): Promise<number> {
  const rows = await app.studioDb?.db.select().from(sessions);
  return rows?.length ?? -1;
}

describe("CSRF double-submit protection", () => {
  it("rejects authenticated writes without a token and keeps the session", async () => {
    const { app } = await buildAuthApp();
    try {
      await setupOwner(app);
      const login = await loginOwner(app);
      const jar = cookieJar(login);

      const response = await app.inject({
        method: "DELETE",
        url: "/api/session",
        headers: { cookie: cookieHeader(jar) },
      });
      expect(response.statusCode).toBe(403);
      expect(response.json().error.code).toBe("CSRF_TOKEN_MISSING");

      const stillValid = await app.inject({
        method: "GET",
        url: "/api/session",
        headers: { cookie: cookieHeader(jar) },
      });
      expect(stillValid.statusCode).toBe(200);
    } finally {
      await app.close();
    }
  });

  it("rejects mismatched tokens under constant-time comparison", async () => {
    const { app } = await buildAuthApp();
    try {
      await setupOwner(app);
      const jar = cookieJar(await loginOwner(app));

      const response = await app.inject({
        method: "DELETE",
        url: "/api/session",
        headers: {
          cookie: cookieHeader(jar),
          "x-csrf-token": "mismatched-csrf-token-value",
        },
      });
      expect(response.statusCode).toBe(403);
      expect(response.json().error.code).toBe("CSRF_TOKEN_INVALID");
      expect(await sessionCount(app)).toBe(1);
    } finally {
      await app.close();
    }
  });

  it("accepts the write when header and cookie match", async () => {
    const { app } = await buildAuthApp();
    try {
      await setupOwner(app);
      const jar = cookieJar(await loginOwner(app));

      const response = await app.inject({
        method: "DELETE",
        url: "/api/session",
        headers: {
          cookie: cookieHeader(jar),
          "x-csrf-token": jar.get("novel_engine_csrf") ?? "",
        },
      });
      expect(response.statusCode).toBe(204);
    } finally {
      await app.close();
    }
  });

  it("lets first-contact endpoints proceed without CSRF tokens", async () => {
    const { app } = await buildAuthApp();
    try {
      await setupOwner(app);
      const login = await app.inject({
        method: "POST",
        url: "/api/session/login",
        payload: { username: "owner", password: OWNER_PASSWORD },
      });
      expect(login.statusCode).toBe(200);
    } finally {
      await app.close();
    }
  });
});
