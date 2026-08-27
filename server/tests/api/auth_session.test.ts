import { randomBytes } from "node:crypto";
import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import { sessions } from "../../src/shared/infrastructure/db/schema.js";
import {
  buildAuthApp,
  cookieHeader,
  cookieJar,
  type InjectedResponse,
  loginOwner,
  makeDataDirectory,
  OWNER_USERNAME,
  setCookieHeaders,
  setupOwner,
} from "./auth_helpers.js";

const OWNER_MAX_AGE = 60 * 60 * 24 * 30;

function cookieEntry(response: InjectedResponse, name: string): string {
  const entry = setCookieHeaders(response).find((header) => header.startsWith(`${name}=`));
  expect(entry, `expected a Set-Cookie entry for ${name}`).toBeDefined();
  return entry ?? "";
}

async function sessionRows(
  app: FastifyInstance,
): Promise<Array<{ id: string; last_seen_at: Date; expires_at: Date | null }>> {
  const rows = await app.studioDb?.db.select().from(sessions);
  return (rows ?? []) as Array<{ id: string; last_seen_at: Date; expires_at: Date | null }>;
}

describe("owner and guest sessions", () => {
  it("keeps failed logins indistinguishable in payload and hash timing", async () => {
    const { app } = await buildAuthApp();
    try {
      await setupOwner(app);
      const wrongPassword = `wrong-${randomBytes(12).toString("hex")}`;

      const unknownStart = performance.now();
      const unknown = await app.inject({
        method: "POST",
        url: "/api/session/login",
        payload: { username: "ghost-user", password: wrongPassword },
      });
      const unknownMs = performance.now() - unknownStart;

      const wrongStart = performance.now();
      const wrong = await app.inject({
        method: "POST",
        url: "/api/session/login",
        payload: { username: OWNER_USERNAME, password: wrongPassword },
      });
      const wrongMs = performance.now() - wrongStart;

      expect(unknown.statusCode).toBe(422);
      expect(wrong.statusCode).toBe(422);
      expect(unknown.json().error.code).toBe(wrong.json().error.code);
      expect(unknown.json().error.message).toBe(wrong.json().error.message);
      // Both paths must run a real bcrypt comparison: the dummy-hash hedge
      // costs the same tens of milliseconds as the real-hash check.
      expect(unknownMs).toBeGreaterThan(15);
      expect(wrongMs).toBeGreaterThan(15);
      expect(setCookieHeaders(unknown)).toHaveLength(0);
    } finally {
      await app.close();
    }
  });

  it("logs in the owner and sets the adjudicated cookies", async () => {
    const { app } = await buildAuthApp();
    try {
      const setup = await setupOwner(app);
      const ownerId = setup.json().id;

      const response = await loginOwner(app);
      expect(response.statusCode).toBe(200);
      const body = response.json();
      expect(body.kind).toBe("owner");
      expect(body.session_id).toEqual(expect.any(String));
      expect(body.owner_id).toBe(ownerId);
      expect(body.expires_at).toEqual(expect.any(String));

      const sessionCookie = cookieEntry(response, "novel_engine_session");
      expect(sessionCookie).toContain("HttpOnly");
      expect(sessionCookie).toContain("SameSite=Lax");
      expect(sessionCookie).toContain("Path=/");
      expect(sessionCookie).toContain(`Max-Age=${OWNER_MAX_AGE}`);
      expect(sessionCookie).not.toContain("Secure");

      const csrfCookie = cookieEntry(response, "novel_engine_csrf");
      expect(csrfCookie).not.toContain("HttpOnly");
      expect(csrfCookie).toContain("SameSite=Lax");
      expect(csrfCookie).toContain(`Max-Age=${OWNER_MAX_AGE}`);
    } finally {
      await app.close();
    }
  });

  it("issues owner sessions with the thirty-day expiry", async () => {
    const start = new Date("2026-08-22T08:00:00.000Z");
    const { app } = await buildAuthApp({ clock: () => start });
    try {
      await setupOwner(app);
      const response = await loginOwner(app);
      expect(response.statusCode).toBe(200);
      const body = response.json();
      const expectedExpiry = new Date(start.getTime() + OWNER_MAX_AGE * 1000).toISOString();
      expect(body.expires_at).toBe(expectedExpiry);

      const sessionCookie = cookieEntry(response, "novel_engine_session");
      expect(sessionCookie).toContain(`Max-Age=${OWNER_MAX_AGE}`);
      const csrfCookie = cookieEntry(response, "novel_engine_csrf");
      expect(csrfCookie).toContain(`Max-Age=${OWNER_MAX_AGE}`);
    } finally {
      await app.close();
    }
  });

  it("returns the principal for a presented session and 401 otherwise", async () => {
    const { app } = await buildAuthApp();
    try {
      const anonymous = await app.inject({ method: "GET", url: "/api/session" });
      expect(anonymous.statusCode).toBe(401);
      expect(anonymous.json().error.code).toBe("UNAUTHORIZED");

      await setupOwner(app);
      const login = await loginOwner(app);
      const jar = cookieJar(login);
      const authenticated = await app.inject({
        method: "GET",
        url: "/api/session",
        headers: { cookie: cookieHeader(jar) },
      });
      expect(authenticated.statusCode).toBe(200);
      expect(authenticated.json().session_id).toBe(login.json().session_id);
    } finally {
      await app.close();
    }
  });

  it("lazily deletes an expired owner session on next use", async () => {
    const start = new Date("2026-08-22T08:00:00.000Z");
    let current = start;
    const { app } = await buildAuthApp({ clock: () => current });
    try {
      await setupOwner(app);
      const login = await loginOwner(app);
      const jar = cookieJar(login);
      expect(await sessionRows(app)).toHaveLength(1);

      current = new Date(start.getTime() + (OWNER_MAX_AGE + 60) * 1000);
      const response = await app.inject({
        method: "GET",
        url: "/api/session",
        headers: { cookie: cookieHeader(jar) },
      });
      expect(response.statusCode).toBe(401);
      expect(await sessionRows(app)).toHaveLength(0);
    } finally {
      await app.close();
    }
  });

  it("refreshes last_seen on each successful validation", async () => {
    const start = new Date("2026-08-22T08:00:00.000Z");
    let current = start;
    const { app } = await buildAuthApp({ clock: () => current });
    try {
      await setupOwner(app);
      const login = await loginOwner(app);
      const jar = cookieJar(login);
      const afterLogin = await sessionRows(app);
      expect(afterLogin).toHaveLength(1);
      expect(afterLogin[0]?.last_seen_at.getTime()).toBe(start.getTime());

      current = new Date(start.getTime() + 10 * 60 * 1000);
      const response = await app.inject({
        method: "GET",
        url: "/api/session",
        headers: { cookie: cookieHeader(jar) },
      });
      expect(response.statusCode).toBe(200);
      const refreshed = await sessionRows(app);
      expect(refreshed).toHaveLength(1);
      expect(refreshed[0]?.last_seen_at.getTime()).toBe(current.getTime());
    } finally {
      await app.close();
    }
  });

  it("terminates the session on logout, clearing both cookies", async () => {
    const { app } = await buildAuthApp();
    try {
      await setupOwner(app);
      const login = await loginOwner(app);
      const jar = cookieJar(login);

      const response = await app.inject({
        method: "DELETE",
        url: "/api/session",
        headers: {
          cookie: cookieHeader(jar),
          "x-csrf-token": jar.get("novel_engine_csrf") ?? "",
        },
      });
      expect(response.statusCode).toBe(204);
      expect(response.body).toBe("");

      const clearedSession = cookieEntry(response, "novel_engine_session");
      const clearedCsrf = cookieEntry(response, "novel_engine_csrf");
      expect(clearedSession).toMatch(/Max-Age=0|Expires=Thu, 01 Jan 1970/);
      expect(clearedCsrf).toMatch(/Max-Age=0|Expires=Thu, 01 Jan 1970/);

      expect(await sessionRows(app)).toHaveLength(0);
      const after = await app.inject({
        method: "GET",
        url: "/api/session",
        headers: { cookie: cookieHeader(jar) },
      });
      expect(after.statusCode).toBe(401);
    } finally {
      await app.close();
    }
  });

  it("invalidates every session when the secret rotates", async () => {
    const first = await buildAuthApp({ sessionSecret: "rotation-secret-alpha" });
    const directory = first.directory;
    await setupOwner(first.app);
    const login = await loginOwner(first.app);
    const jar = cookieJar(login);
    await first.app.close();

    const rotated = await buildAuthApp({ directory, sessionSecret: "rotation-secret-beta" });
    try {
      const rejected = await rotated.app.inject({
        method: "GET",
        url: "/api/session",
        headers: { cookie: cookieHeader(jar) },
      });
      expect(rejected.statusCode).toBe(401);
    } finally {
      await rotated.app.close();
    }

    const restored = await buildAuthApp({ directory, sessionSecret: "rotation-secret-alpha" });
    try {
      const accepted = await restored.app.inject({
        method: "GET",
        url: "/api/session",
        headers: { cookie: cookieHeader(jar) },
      });
      expect(accepted.statusCode).toBe(200);
    } finally {
      await restored.app.close();
    }
  });

  it("replaces an unset secret with a fresh random value on every start", async () => {
    const directory = await makeDataDirectory();

    const issued = await buildApp({ logger: false, dataDirectory: directory });
    let jar: Map<string, string>;
    try {
      await setupOwner(issued);
      jar = cookieJar(await loginOwner(issued));
    } finally {
      await issued.close();
    }

    const restarted = await buildApp({ logger: false, dataDirectory: directory });
    try {
      const response = await restarted.inject({
        method: "GET",
        url: "/api/session",
        headers: { cookie: cookieHeader(jar) },
      });
      expect(response.statusCode).toBe(401);
    } finally {
      await restarted.close();
    }
  });

  it("marks cookies Secure only in production and staging", async () => {
    for (const environment of ["production", "staging"] as const) {
      const { app } = await buildAuthApp({ environment });
      try {
        await setupOwner(app);
        const login = await loginOwner(app);
        expect(cookieEntry(login, "novel_engine_session")).toContain("Secure");
        expect(cookieEntry(login, "novel_engine_csrf")).toContain("Secure");
      } finally {
        await app.close();
      }
    }
  });
});
