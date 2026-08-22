import { randomBytes } from "node:crypto";
import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { FastifyInstance } from "fastify";

import { buildApp } from "../../src/apps/api/app.js";

/** Stable secret so tests can prove rotation by choosing different values. */
export const TEST_SESSION_SECRET = "test-session-secret-265-0123456789abcdef";

export const OWNER_USERNAME = "owner";

/**
 * The owner password is generated per run (never a usable literal in source);
 * it only needs to satisfy the 10–72 UTF-8 byte policy.
 */
export const OWNER_PASSWORD =
  process.env.TEST_OWNER_PASSWORD ?? randomBytes(24).toString("base64url");

export async function makeDataDirectory(): Promise<string> {
  return mkdtemp(join(tmpdir(), "novel-engine-auth-"));
}

export interface BuildAuthAppOptions {
  directory?: string;
  environment?: string;
  sessionSecret?: string;
  corsOrigins?: string[];
  trustedProxies?: string[];
  authRateLimitPerMinute?: number;
  clock?: () => Date;
}

export interface AuthTestApp {
  app: FastifyInstance;
  directory: string;
}

/** Build the app over a real SQLite file in a temp directory (the auth seam). */
export async function buildAuthApp(options: BuildAuthAppOptions = {}): Promise<AuthTestApp> {
  const directory = options.directory ?? (await makeDataDirectory());
  const app = await buildApp({
    logger: false,
    dataDirectory: directory,
    environment: options.environment,
    sessionSecret: options.sessionSecret ?? TEST_SESSION_SECRET,
    corsOrigins: options.corsOrigins,
    trustedProxies: options.trustedProxies,
    authRateLimitPerMinute: options.authRateLimitPerMinute,
    clock: options.clock,
  });
  return { app, directory };
}

/** The full light-my-request response of app.inject(): json(), headers, body. */
export type InjectedResponse = Awaited<ReturnType<FastifyInstance["inject"]>>;

/** set-cookie arrives as string[] (single values are normalized into an array). */
export function setCookieHeaders(response: InjectedResponse): string[] {
  const value = response.headers["set-cookie"];
  if (value === undefined) {
    return [];
  }
  return Array.isArray(value) ? value.map(String) : [String(value)];
}

/** Parse Set-Cookie entries into a name→value jar for follow-up requests. */
export function cookieJar(response: InjectedResponse): Map<string, string> {
  const jar = new Map<string, string>();
  for (const header of setCookieHeaders(response)) {
    const pair = header.split(";")[0];
    if (pair === undefined) {
      continue;
    }
    const separator = pair.indexOf("=");
    if (separator > 0) {
      jar.set(pair.slice(0, separator), pair.slice(separator + 1));
    }
  }
  return jar;
}

export function cookieHeader(jar: Map<string, string>): string {
  return [...jar.entries()].map(([name, value]) => `${name}=${value}`).join("; ");
}

export async function setupOwner(
  app: FastifyInstance,
  username: string = OWNER_USERNAME,
  password: string = OWNER_PASSWORD,
): Promise<InjectedResponse> {
  const response = await app.inject({
    method: "POST",
    url: "/api/setup",
    payload: { username, password },
  });
  return response;
}

export async function loginOwner(
  app: FastifyInstance,
  username: string = OWNER_USERNAME,
  password: string = OWNER_PASSWORD,
): Promise<InjectedResponse> {
  return app.inject({
    method: "POST",
    url: "/api/session/login",
    payload: { username, password },
  });
}
