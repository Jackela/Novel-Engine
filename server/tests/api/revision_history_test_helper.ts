import type { FastifyInstance } from "fastify";
import { expect } from "vitest";

import { cookieHeader } from "./auth_helpers.js";
import type { CookieJar, RevisionPayload } from "./studio_helpers.js";

/** Follow every bounded History cursor so callers named `listRevisions` get the complete list. */
export async function listRevisions(
  app: FastifyInstance,
  jar: CookieJar,
  projectId: string,
  documentId: string,
): Promise<RevisionPayload[]> {
  const revisions: RevisionPayload[] = [];
  const seenCursors = new Set<string>();
  let cursor: string | null = null;
  do {
    const response = await app.inject({
      method: "GET",
      url: `/api/projects/${projectId}/documents/${documentId}/revisions?limit=100${
        cursor === null ? "" : `&cursor=${encodeURIComponent(cursor)}`
      }`,
      headers: { cookie: cookieHeader(jar) },
    });
    expect(response.statusCode, response.body).toBe(200);
    const page = response.json() as {
      revisions: RevisionPayload[];
      next_cursor: string | null;
    };
    revisions.push(...page.revisions);
    if (page.next_cursor !== null && seenCursors.has(page.next_cursor)) {
      throw new Error("Revision history repeated a continuation cursor.");
    }
    if (page.next_cursor !== null) seenCursors.add(page.next_cursor);
    cursor = page.next_cursor;
  } while (cursor !== null);
  return revisions;
}
