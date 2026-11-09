import cookie from "@fastify/cookie";
import Fastify, { type FastifyInstance } from "fastify";
import { afterEach, describe, expect, it } from "vitest";

import { openDatabase, type DatabaseHandle } from "../../src/platform/db/connection.js";
import { registerErrorEnvelope } from "../../src/platform/http/error_envelope.js";
import { createBcryptHasher } from "../../src/slices/identity/adapters/bcrypt_hasher.js";
import { createSessionTokenIssuer } from "../../src/slices/identity/adapters/hmac_tokens.js";
import { createSqliteOwnerStore } from "../../src/slices/identity/adapters/sqlite_owner_store.js";
import { createSqliteSessionStore } from "../../src/slices/identity/adapters/sqlite_session_store.js";
import { registerIdentityRoutes, SESSION_COOKIE } from "../../src/slices/identity/routes.js";

const NOW = 1_700_000_000_000;
const PASSWORD = "0123456789";

const OWNERS_DDL = `CREATE TABLE owners (
  id TEXT PRIMARY KEY NOT NULL,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL
)`;

const SESSIONS_DDL = `CREATE TABLE sessions (
  id TEXT PRIMARY KEY NOT NULL,
  owner_id TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  csrf_token TEXT NOT NULL,
  expires_at INTEGER NOT NULL,
  last_seen_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL
)`;

const handles: DatabaseHandle[] = [];

async function buildApp(): Promise<FastifyInstance> {
  const handle = openDatabase({ path: ":memory:" });
  handles.push(handle);
  handle.raw.exec(OWNERS_DDL);
  handle.raw.exec(SESSIONS_DDL);

  const app = Fastify();
  await app.register(cookie);
  registerErrorEnvelope(app);
  registerIdentityRoutes(app, {
    owners: createSqliteOwnerStore(handle),
    hasher: createBcryptHasher(4),
    sessions: createSqliteSessionStore(handle),
    tokens: createSessionTokenIssuer("test-session-secret-16"),
    now: () => NOW,
    secureCookies: false,
  });
  await app.ready();
  return app;
}

afterEach(() => {
  for (const handle of handles.splice(0)) handle.close();
});

function sessionCookie(response: { headers: Record<string, unknown> }): string {
  const raw = response.headers["set-cookie"];
  const list = Array.isArray(raw) ? raw : [String(raw ?? "")];
  const found = list
    .map((entry) => entry.split(";")[0] ?? "")
    .find((pair) => pair.startsWith(`${SESSION_COOKIE}=`));
  if (found === undefined) throw new Error("session cookie missing from response");
  return found;
}

describe("identity routes", () => {
  it("creates the owner and answers 201 with identity only", async () => {
    const app = await buildApp();
    const response = await app.inject({
      method: "POST",
      url: "/api/setup",
      payload: { username: "  author  ", password: PASSWORD },
    });
    expect(response.statusCode).toBe(201);
    expect(response.json()).toEqual({ ownerId: expect.any(String), username: "author" });
    await app.close();
  });

  it("answers 422 for a second owner and for a short password", async () => {
    const app = await buildApp();
    await app.inject({ method: "POST", url: "/api/setup", payload: { username: "author", password: PASSWORD } });

    const second = await app.inject({
      method: "POST",
      url: "/api/setup",
      payload: { username: "intruder", password: PASSWORD },
    });
    expect(second.statusCode).toBe(422);
    expect(second.json()).toMatchObject({ error: { code: "INVALID_OPERATION" } });

    const short = await app.inject({
      method: "POST",
      url: "/api/setup",
      payload: { username: "author", password: "short" },
    });
    expect(short.statusCode).toBe(422);
    expect(short.json()).toMatchObject({ error: { code: "INVALID_OPERATION" } });
    await app.close();
  });

  it("logs in, sets both cookies, and probes as authenticated", async () => {
    const app = await buildApp();
    await app.inject({ method: "POST", url: "/api/setup", payload: { username: "author", password: PASSWORD } });

    const login = await app.inject({
      method: "POST",
      url: "/api/session",
      payload: { username: "author", password: PASSWORD },
    });
    expect(login.statusCode).toBe(200);
    expect(login.json()).toEqual({ ownerId: expect.any(String), expiresAt: NOW + 30 * 24 * 60 * 60 * 1000 });

    const setCookie = login.headers["set-cookie"];
    const list = Array.isArray(setCookie) ? setCookie : [String(setCookie)];
    const sessionEntry = list.find((entry) => entry.startsWith(`${SESSION_COOKIE}=`)) ?? "";
    const csrfEntry = list.find((entry) => entry.startsWith("novel_engine_csrf=")) ?? "";
    expect(sessionEntry).not.toBe("");
    expect(csrfEntry).not.toBe("");
    // Checked per cookie, not on a joined string: joining crosses the boundary
    // and would match HttpOnly from the neighbouring entry.
    expect(sessionEntry).toMatch(/HttpOnly/i);
    expect(csrfEntry).not.toMatch(/HttpOnly/i);

    const probe = await app.inject({
      method: "GET",
      url: "/api/session",
      headers: { cookie: sessionCookie(login) },
    });
    expect(probe.json()).toMatchObject({ authenticated: true });
    await app.close();
  });

  it("answers 422 for a wrong password without revealing why", async () => {
    const app = await buildApp();
    await app.inject({ method: "POST", url: "/api/setup", payload: { username: "author", password: PASSWORD } });

    const response = await app.inject({
      method: "POST",
      url: "/api/session",
      payload: { username: "author", password: "wrong-password" },
    });
    expect(response.statusCode).toBe(422);
    expect(response.json()).toMatchObject({
      error: { code: "INVALID_OPERATION", message: "Invalid username or password." },
    });
    await app.close();
  });

  it("probes as unauthenticated without a cookie, and after logout", async () => {
    const app = await buildApp();
    await app.inject({ method: "POST", url: "/api/setup", payload: { username: "author", password: PASSWORD } });
    const login = await app.inject({
      method: "POST",
      url: "/api/session",
      payload: { username: "author", password: PASSWORD },
    });
    const cookieHeader = { cookie: sessionCookie(login) };

    const anonymous = await app.inject({ method: "GET", url: "/api/session" });
    expect(anonymous.statusCode).toBe(200);
    expect(anonymous.json()).toEqual({ authenticated: false });

    const out = await app.inject({ method: "DELETE", url: "/api/session", headers: cookieHeader });
    expect(out.statusCode).toBe(204);

    const after = await app.inject({ method: "GET", url: "/api/session", headers: cookieHeader });
    expect(after.json()).toEqual({ authenticated: false });
    await app.close();
  });
});
