import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import { sessions } from "../../src/shared/infrastructure/db/schema.js";
import { buildAuthApp, type InjectedResponse } from "./auth_helpers.js";

async function sessionCount(app: FastifyInstance): Promise<number> {
  const rows = await app.studioDb?.db.select().from(sessions);
  return rows?.length ?? -1;
}

async function createGuest(app: FastifyInstance, forwardedFor?: string): Promise<InjectedResponse> {
  const headers = forwardedFor === undefined ? {} : { "x-forwarded-for": forwardedFor };
  return app.inject({ method: "POST", url: "/api/session/guest", headers });
}

describe("auth endpoint rate limiting", () => {
  it("returns 429 with Retry-After once the five-per-minute burst is spent", async () => {
    const { app } = await buildAuthApp();
    try {
      for (let index = 0; index < 5; index += 1) {
        const response = await createGuest(app);
        expect(response.statusCode).toBe(201);
      }

      const sixth = await createGuest(app);
      expect(sixth.statusCode).toBe(429);
      const retryAfter = Number(sixth.headers["retry-after"]);
      expect(Number.isInteger(retryAfter)).toBe(true);
      expect(retryAfter).toBeGreaterThanOrEqual(1);
      const body = sixth.json();
      expect(body.error.code).toBe("RATE_LIMIT_EXCEEDED");
      expect(body).not.toHaveProperty("detail");
      // The rejected request must not create a session.
      expect(await sessionCount(app)).toBe(5);
    } finally {
      await app.close();
    }
  });

  it("keeps a separate bucket per protected endpoint", async () => {
    const { app } = await buildAuthApp();
    try {
      for (let index = 0; index < 5; index += 1) {
        const response = await createGuest(app);
        expect(response.statusCode).toBe(201);
      }
      const blocked = await createGuest(app);
      expect(blocked.statusCode).toBe(429);

      // The login bucket is untouched even though the guest bucket is spent.
      const login = await app.inject({
        method: "POST",
        url: "/api/session/login",
        payload: { username: "anyone", password: "any-failing-attempt" },
      });
      expect(login.statusCode).toBe(422);
    } finally {
      await app.close();
    }
  });

  it("drops rate-limited setup attempts without creating an owner", async () => {
    const { app } = await buildAuthApp();
    try {
      // Five invalid setups consume the bucket without ever creating an owner.
      for (let index = 0; index < 5; index += 1) {
        const response = await app.inject({
          method: "POST",
          url: "/api/setup",
          payload: { username: "owner", password: "short" },
        });
        expect(response.statusCode).toBe(422);
      }
      const blocked = await app.inject({
        method: "POST",
        url: "/api/setup",
        payload: { username: "owner", password: "a-valid-long-password" },
      });
      expect(blocked.statusCode).toBe(429);

      const status = await app.inject({ method: "GET", url: "/api/setup" });
      expect(status.json().owner_configured).toBe(false);
    } finally {
      await app.close();
    }
  });

  it("exempts preflight OPTIONS requests", async () => {
    const { app } = await buildAuthApp();
    try {
      for (let index = 0; index < 5; index += 1) {
        await createGuest(app);
      }
      // The CORS contract (#275) answers preflights with 204 — the point is
      // that the exhausted rate limiter never answers instead.
      const preflight = await app.inject({
        method: "OPTIONS",
        url: "/api/session/guest",
        headers: { origin: "http://localhost:5173", "access-control-request-method": "POST" },
      });
      expect(preflight.statusCode).toBe(204);
    } finally {
      await app.close();
    }
  });

  it("keys the bucket by the peer address when no proxy is trusted", async () => {
    const { app } = await buildAuthApp();
    try {
      for (let index = 0; index < 5; index += 1) {
        const response = await createGuest(app, `198.51.100.${index}`);
        expect(response.statusCode).toBe(201);
      }
      // Forged X-Forwarded-For values cannot shuffle identity: all requests
      // share the single bucket of the actual peer.
      const shuffled = await createGuest(app, "203.0.113.77");
      expect(shuffled.statusCode).toBe(429);
    } finally {
      await app.close();
    }
  });

  it("honors the first X-Forwarded-For entry from a trusted proxy", async () => {
    const { app } = await buildAuthApp({ trustedProxies: ["127.0.0.1"] });
    try {
      for (let index = 0; index < 5; index += 1) {
        const response = await createGuest(app, "198.51.100.7");
        expect(response.statusCode).toBe(201);
      }
      const sameIdentity = await createGuest(app, "198.51.100.7");
      expect(sameIdentity.statusCode).toBe(429);

      const otherIdentity = await createGuest(app, "198.51.100.8");
      expect(otherIdentity.statusCode).toBe(201);
    } finally {
      await app.close();
    }
  });

  it("supports CIDR trusted proxy networks", async () => {
    const { app } = await buildAuthApp({ trustedProxies: ["127.0.0.0/8"] });
    try {
      for (let index = 0; index < 5; index += 1) {
        const response = await createGuest(app, "198.51.100.7");
        expect(response.statusCode).toBe(201);
      }
      const sameIdentity = await createGuest(app, "198.51.100.7");
      expect(sameIdentity.statusCode).toBe(429);

      const otherIdentity = await createGuest(app, "198.51.100.8");
      expect(otherIdentity.statusCode).toBe(201);
    } finally {
      await app.close();
    }
  });
});
