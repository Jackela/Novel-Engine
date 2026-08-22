import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { FastifyInstance } from "fastify";
import { expect } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import {
  cookieHeader,
  cookieJar,
  type InjectedResponse,
  loginOwner,
  setupOwner,
  TEST_SESSION_SECRET,
} from "./auth_helpers.js";

/** Parsed name→value cookie jar reused across authenticated injections. */
export type CookieJar = Map<string, string>;

/**
 * Strictly increasing time source: every call advances by 1 ms so ordering
 * assertions (updated_at DESC, revision monotonicity) never collide on a
 * coarse real clock.
 */
export function monotonicClock(): () => Date {
  let current = Date.now();
  return () => {
    current += 1;
    return new Date(current);
  };
}

export interface StudioTestApp {
  app: FastifyInstance;
  directory: string;
}

/** Build the app with a real SQLite file and the studio surface mounted. */
export async function buildStudioApp(clock?: () => Date): Promise<StudioTestApp> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-studio-"));
  const app = await buildApp({
    logger: false,
    dataDirectory: directory,
    sessionSecret: TEST_SESSION_SECRET,
    clock,
  });
  return { app, directory };
}

/** Set up the owner and log in, returning the authenticated cookie jar. */
export async function ownerJar(app: FastifyInstance): Promise<CookieJar> {
  await setupOwner(app);
  const login = await loginOwner(app);
  expect(login.statusCode).toBe(200);
  return cookieJar(login);
}

/** Create a guest sandbox session, returning its cookie jar. */
export async function guestJar(app: FastifyInstance): Promise<CookieJar> {
  const response = await app.inject({ method: "POST", url: "/api/session/guest" });
  expect(response.statusCode).toBe(201);
  return cookieJar(response);
}

/** Session cookie plus the matching CSRF header (double-submit pair). */
export function authHeaders(jar: CookieJar): Record<string, string> {
  const csrf = jar.get("novel_engine_csrf");
  expect(csrf, "expected a csrf cookie in the jar").toBeDefined();
  return { cookie: cookieHeader(jar), "x-csrf-token": csrf ?? "" };
}

/** The inject-able verb subset used by the studio contract tests. */
export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | "HEAD" | "OPTIONS";

/** Inject an authenticated (and CSRF-carrying, for writes) API call. */
export async function call(
  app: FastifyInstance,
  jar: CookieJar,
  method: HttpMethod,
  url: string,
  payload?: Record<string, unknown>,
): Promise<InjectedResponse> {
  const headers = authHeaders(jar);
  return payload === undefined
    ? app.inject({ method, url, headers })
    : app.inject({ method, url, payload, headers });
}

/** Inject a call with no credentials at all. */
export async function anonymousCall(
  app: FastifyInstance,
  method: HttpMethod,
  url: string,
  payload?: Record<string, unknown>,
): Promise<InjectedResponse> {
  return payload === undefined ? app.inject({ method, url }) : app.inject({ method, url, payload });
}

/** Create a project through the API and return its payload. */
export async function seedProject(
  app: FastifyInstance,
  jar: CookieJar,
  title: string,
): Promise<{
  id: string;
  documents: Array<{ id: string; kind: string; title: string; position: number }>;
}> {
  const response = await call(app, jar, "POST", "/api/projects", { title });
  expect(response.statusCode, response.body).toBe(201);
  return response.json();
}

export interface DocumentPayload {
  id: string;
  project_id: string;
  kind: string;
  title: string;
  position: number;
  current_revision_id: string;
  content_markdown: string;
  metadata: Record<string, unknown>;
  revision_source: string;
  word_count: number;
  created_at: string;
  updated_at: string;
}

export interface RevisionPayload {
  id: string;
  document_id: string;
  parent_revision_id: string | null;
  revision_number: number;
  content_markdown: string;
  metadata: Record<string, unknown>;
  source: string;
  word_count: number;
  created_at: string;
}

export async function seedDocument(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  body: { kind: string; title: string; content_markdown?: string; position?: number },
): Promise<DocumentPayload> {
  const response = await call(app, jar, "POST", `/api/projects/${projectId}/documents`, body);
  expect(response.statusCode, response.body).toBe(201);
  return response.json();
}

/** Project detail payload — documents arrive ordered (kind, position, created). */
export async function getProject(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
): Promise<{ id: string; documents: DocumentPayload[] }> {
  const response = await call(app, jar, "GET", `/api/projects/${projectId}`);
  expect(response.statusCode, response.body).toBe(200);
  return response.json();
}

export async function listDocuments(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
): Promise<DocumentPayload[]> {
  return (await getProject(app, jar, projectId)).documents;
}

export async function listRevisions(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  documentId: string,
): Promise<RevisionPayload[]> {
  const response = await call(
    app,
    jar,
    "GET",
    `/api/projects/${projectId}/documents/${documentId}/revisions`,
  );
  expect(response.statusCode, response.body).toBe(200);
  return response.json().revisions;
}
