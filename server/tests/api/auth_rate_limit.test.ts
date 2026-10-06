import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import { sessions } from "../../src/shared/infrastructure/db/schema.js";
import { buildAuthApp, type InjectedResponse } from "./auth_helpers.js";

async function sessionCount(app: FastifyInstance): Promise<number> {
  const rows = await app.studioDb?.db.select().from(sessions);
  return rows?.length ?? -1;
}

async function createContact(
  app: FastifyInstance,
  forwardedFor?: string,
): Promise<InjectedResponse> {
  const headers = forwardedFor === undefined ? {} : { "x-forwarded-for": forwardedFor };
  return app.inject({
    method: "POST",
    url: "/api/session/login",
    headers,
    payload: { username: "owner", password: "a-wrong-password" },
  });
}

describe("auth endpoint rate limiting", () => {
  it("returns 429 with Retry-After once the five-per-minute burst is spent", async () => {
    const { app } = await buildAuthApp();
    try {
      for (let index = 0; index < 5; index += 1) {
        const response = await createContact(app);
        expect(response.statusCode).toBe(422);
      }

      const sixth = await createContact(app);
      expect(sixth.statusCode).toBe(429);
      const retryAfter = Number(sixth.headers["retry-after"]);
      expect(Number.isInteger(retryAfter)).toBe(true);
      expect(retryAfter).toBeGreaterThanOrEqual(1);
      const body = sixth.json();
      expect(body.error.code).toBe("RATE_LIMIT_EXCEEDED");
      expect(body).not.toHaveProperty("detail");
      // The rejected request must not create a session.
      expect(await sessionCount(app)).toBe(0);
    } finally {
      await app.close();
    }
  });

  it("keeps a separate bucket per protected endpoint", async () => {
    const { app } = await buildAuthApp();
    try {
      for (let index = 0; index < 5; index += 1) {
        const response = await createContact(app);
        expect(response.statusCode).toBe(422);
      }
      const blocked = await createContact(app);
      expect(blocked.statusCode).toBe(429);

      // The setup bucket is untouched even though the login bucket is spent.
      const setup = await app.inject({
        method: "POST",
        url: "/api/setup",
        payload: { username: "owner", password: "short" },
      });
      expect(setup.statusCode).toBe(422);
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
        await createContact(app);
      }
      // The CORS contract (#275) answers preflights with 204 — the point is
      // that the exhausted rate limiter never answers instead.
      const preflight = await app.inject({
        method: "OPTIONS",
        url: "/api/session/login",
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
        const response = await createContact(app, `198.51.100.${index}`);
        expect(response.statusCode).toBe(422);
      }
      // Forged X-Forwarded-For values cannot shuffle identity: all requests
      // share the single bucket of the actual peer.
      const shuffled = await createContact(app, "203.0.113.77");
      expect(shuffled.statusCode).toBe(429);
    } finally {
      await app.close();
    }
  });

  it("keys the bucket by the forwarded hops behind a trusted proxy", async () => {
    const { app } = await buildAuthApp({ trustedProxies: ["127.0.0.1"] });
    try {
      for (let index = 0; index < 5; index += 1) {
        const response = await createContact(app, "198.51.100.7");
        expect(response.statusCode).toBe(422);
      }
      const sameIdentity = await createContact(app, "198.51.100.7");
      expect(sameIdentity.statusCode).toBe(429);

      const otherIdentity = await createContact(app, "198.51.100.8");
      expect(otherIdentity.statusCode).toBe(422);
    } finally {
      await app.close();
    }
  });

  it("keeps one bucket when a trusted proxy forwards forged leading X-Forwarded-For segments", async () => {
    const { app } = await buildAuthApp({ trustedProxies: ["127.0.0.1"] });
    try {
      const statuses: number[] = [];
      for (let index = 0; index < 16; index += 1) {
        // A proxy appends the address it actually saw at the right end of the
        // chain; the leading segment is whatever the client sent and rotates.
        const response = await createContact(app, `198.51.100.${index}, 203.0.113.50`);
        statuses.push(response.statusCode);
      }

      expect(statuses.slice(0, 5)).toEqual([422, 422, 422, 422, 422]);
      expect(statuses.slice(5)).toEqual(Array.from({ length: 11 }, () => 429));
    } finally {
      await app.close();
    }
  });

  it("resolves the rightmost untrusted hop instead of a forged leading segment", async () => {
    const { app } = await buildAuthApp({ trustedProxies: ["127.0.0.1", "10.0.0.1"] });
    try {
      for (let index = 0; index < 5; index += 1) {
        const response = await createContact(app, `192.0.2.${index}, 198.51.100.23, 10.0.0.1`);
        expect(response.statusCode).toBe(422);
      }
      const blocked = await createContact(app, "192.0.2.99, 198.51.100.23, 10.0.0.1");
      expect(blocked.statusCode).toBe(429);

      const otherClient = await createContact(app, "203.0.113.9, 10.0.0.1");
      expect(otherClient.statusCode).toBe(422);
    } finally {
      await app.close();
    }
  });

  it("never lets a network range trust entry mint forwarded identities", async () => {
    const { app } = await buildAuthApp({ trustedProxies: ["127.0.0.0/8"] });
    try {
      for (let index = 0; index < 5; index += 1) {
        const response = await createContact(app, `198.51.100.${index}, 203.0.113.50`);
        expect(response.statusCode).toBe(422);
      }
      // A range can cover clients, so it must not make the peer a trusted
      // proxy: every request keeps sharing the peer's single bucket.
      const blocked = await createContact(app, "198.51.100.99, 203.0.113.50");
      expect(blocked.statusCode).toBe(429);
    } finally {
      await app.close();
    }
  });
});
