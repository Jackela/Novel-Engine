import { mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { FastifyInstance } from "fastify";
import { expect } from "vitest";

import { type AppOptions, buildApp } from "../../src/apps/api/app.js";
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

/** Extra buildApp overrides used by the workflow tests (provider seams). */
export interface StudioAppOverrides
  extends Pick<AppOptions, "databaseQueryLogger" | "operationCapacity" | "projectArtifactCleaner"> {
  textProviderFactory?: NonNullable<Parameters<typeof buildApp>[0]>["textProviderFactory"];
  exportStoreFactory?: AppOptions["exportStoreFactory"];
  exportArtifactGateway?: AppOptions["exportArtifactGateway"];
  config?: AppOptions["config"];
  lorebookBudgetCharacters?: AppOptions["lorebookBudgetCharacters"];
  logger?: AppOptions["logger"];
}

/** Build the app with a real SQLite file and the studio surface mounted. */
export async function buildStudioApp(
  clock?: () => Date,
  overrides: StudioAppOverrides = {},
): Promise<{ app: FastifyInstance; directory: string }> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-studio-"));
  const app = await buildApp({
    logger: false,
    databasePath: join(directory, "novel-engine.sqlite3"),
    sessionSecret: TEST_SESSION_SECRET,
    clock,
    ...overrides,
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
  requestHeaders?: Record<string, string>,
): Promise<InjectedResponse> {
  const headers = { ...authHeaders(jar), ...requestHeaders };
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

export interface DocumentSummaryPayload {
  id: string;
  project_id: string;
  kind: string;
  title: string;
  position: number;
  volume_id?: string | null;
  /** The stored outline-beat reference (#313); resolved reads use GET /beat. */
  beat_ref?: string | null;
  /** Lore lifecycle status (#444); null for non-lore kinds. */
  lore_status?: string | null;
  current_revision_id: string;
  word_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentPayload extends DocumentSummaryPayload {
  content_markdown: string;
  metadata: Record<string, unknown>;
  revision_source: string;
}

export interface RevisionPayload {
  id: string;
  document_id: string;
  parent_revision_id: string | null;
  revision_number: number;
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
): Promise<{ id: string; documents: DocumentSummaryPayload[] }> {
  const response = await call(app, jar, "GET", `/api/projects/${projectId}`);
  expect(response.statusCode, response.body).toBe(200);
  return response.json();
}

export async function listDocuments(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
): Promise<DocumentSummaryPayload[]> {
  return (await getProject(app, jar, projectId)).documents;
}

/** Read one complete accepted current Document from the scoped resource. */
export async function getDocument(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  documentId: string,
): Promise<DocumentPayload> {
  const response = await call(
    app,
    jar,
    "GET",
    `/api/projects/${projectId}/documents/${documentId}`,
  );
  expect(response.statusCode, response.body).toBe(200);
  return response.json();
}
export { listRevisions } from "./revision_history_test_helper.js";

export interface JobEventPayload {
  id: string;
  status: string;
  details: Record<string, unknown>;
  created_at: string;
}

/** The synchronous job payload shared by the proposal workflow tests. */
export interface JobPayload {
  id: string;
  project_id: string;
  document_id: string | null;
  kind: string;
  operation: string;
  status: string;
  provider: string;
  model: string;
  request: Record<string, unknown>;
  result: Record<string, unknown>;
  error: string | null;
  retry_of_job_id: string | null;
  created_at: string;
  updated_at: string;
  events: JobEventPayload[];
}

/** Generate a proposal for a document's current revision; asserts 200. */
export async function draftProposal(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  documentId: string,
  body: Record<string, unknown>,
): Promise<JobPayload> {
  const response = await call(
    app,
    jar,
    "POST",
    `/api/projects/${projectId}/documents/${documentId}/ai-proposals`,
    body,
  );
  expect(response.statusCode, response.body).toBe(200);
  return response.json();
}

/** Accept a proposal; asserts 200. */
export async function admitProposal(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  jobId: string,
): Promise<JobPayload> {
  const response = await call(
    app,
    jar,
    "POST",
    `/api/projects/${projectId}/ai-proposals/${jobId}/accept`,
  );
  expect(response.statusCode, response.body).toBe(200);
  return response.json();
}

export interface VolumePayload {
  id: string;
  project_id: string;
  title: string;
  position: number;
  created_at: string;
  updated_at: string;
}

/** Create a volume through the project surface; asserts 201. */
export async function seedVolume(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  title: string,
): Promise<VolumePayload> {
  const response = await call(app, jar, "POST", `/api/projects/${projectId}/volumes`, { title });
  expect(response.statusCode, response.body).toBe(201);
  return response.json();
}

/** Volumes of a project in reading order; asserts 200. */
export async function listVolumes(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
): Promise<VolumePayload[]> {
  const response = await call(app, jar, "GET", `/api/projects/${projectId}/volumes`);
  expect(response.statusCode, response.body).toBe(200);
  return response.json().volumes;
}

/**
 * Move a document into a volume without asserting — returns the status and,
 * for accepted moves, the updated document payload (bare on success).
 */
export async function placeDocument(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  documentId: string,
  volumeId: string,
): Promise<{ status: number; document?: DocumentPayload }> {
  const response = await call(
    app,
    jar,
    "PUT",
    `/api/projects/${projectId}/documents/${documentId}/volume`,
    { volume_id: volumeId },
  );
  if (!response.statusCode.toString().startsWith("2")) {
    return { status: response.statusCode };
  }
  return { status: response.statusCode, document: response.json() as DocumentPayload };
}

/** Place with an asserted 200 (the happy path used by ordering fixtures). */
export async function moveChapterToVolume(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  documentId: string,
  volumeId: string,
): Promise<DocumentPayload> {
  const attempt = await placeDocument(app, jar, projectId, documentId, volumeId);
  expect(attempt.status, JSON.stringify(attempt)).toBe(200);
  return attempt.document as DocumentPayload;
}
