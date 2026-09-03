import { randomUUID } from "node:crypto";
import { eq } from "drizzle-orm";
import { afterEach, describe, expect, it, vi } from "vitest";
import { projects } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import { owners } from "../../src/shared/infrastructure/db/schema.js";
import { cookieHeader } from "./auth_helpers.js";
import { authHeaders, buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

const VALIDATION_ERROR = {
  code: "VALIDATION_ERROR",
  message: "Request validation failed.",
};

afterEach(() => vi.restoreAllMocks());

describe("Project settings PATCH validation and guards", () => {
  it("rejects empty, unknown, invalid-type, normalized-empty, and bounded inputs with zero writes", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Validation authority");
      const url = `/api/projects/${project.id}`;
      const db = app.studioDb?.db;
      if (db === undefined) throw new Error("expected database");
      const before = db.select().from(projects).where(eq(projects.id, project.id)).get();
      const update = vi.spyOn(DrizzleStudioStore.prototype, "updateProject");
      const bodies: unknown[] = [
        {},
        { unknown: true },
        { title: "valid", unknown: true },
        null,
        [],
        "not an object",
        { title: 7 },
        { description: 7 },
        { settings: null },
        { settings: [] },
        { title: "   " },
        { title: "x".repeat(241) },
        { description: "x".repeat(10_001) },
      ];

      for (const body of bodies) {
        const response = await app.inject({
          method: "PATCH",
          url,
          headers: { ...authHeaders(jar), "content-type": "application/json" },
          payload: JSON.stringify(body),
        });
        expect(response.statusCode, `${JSON.stringify(body)}: ${response.body}`).toBe(422);
        const envelope = response.json();
        expect(Object.keys(envelope)).toEqual(["error"]);
        expect(Object.keys(envelope.error).sort()).toEqual(["code", "details", "message"]);
        expect(envelope.error).toMatchObject(VALIDATION_ERROR);
        expect(envelope.error.details.errors).toHaveLength(1);
      }

      expect(update).not.toHaveBeenCalled();
      expect(db.select().from(projects).where(eq(projects.id, project.id)).get()).toEqual(before);
    } finally {
      await app.close();
    }
  });

  it("runs authentication and CSRF before body validation and never enters the store", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Guard order");
      const url = `/api/projects/${project.id}`;
      const update = vi.spyOn(DrizzleStudioStore.prototype, "updateProject");

      const anonymous = await app.inject({
        method: "PATCH",
        url,
        payload: { unknown: true },
      });
      const anonymousValid = await app.inject({
        method: "PATCH",
        url,
        payload: { title: "valid" },
      });
      const missingCsrf = await app.inject({
        method: "PATCH",
        url,
        headers: { cookie: cookieHeader(jar) },
        payload: { unknown: true },
      });
      const missingCsrfValid = await app.inject({
        method: "PATCH",
        url,
        headers: { cookie: cookieHeader(jar) },
        payload: { title: "valid" },
      });
      const mismatchedCsrf = await app.inject({
        method: "PATCH",
        url,
        headers: { cookie: cookieHeader(jar), "x-csrf-token": "wrong-token" },
        payload: { unknown: true },
      });
      const mismatchedCsrfValid = await app.inject({
        method: "PATCH",
        url,
        headers: { cookie: cookieHeader(jar), "x-csrf-token": "wrong-token" },
        payload: { title: "valid" },
      });

      expect(anonymous.statusCode).toBe(401);
      expect(anonymous.json().error.code).toBe("UNAUTHORIZED");
      expect(anonymousValid.statusCode).toBe(401);
      expect(missingCsrf.statusCode).toBe(403);
      expect(missingCsrf.json().error.code).toBe("CSRF_TOKEN_MISSING");
      expect(missingCsrfValid.statusCode).toBe(403);
      expect(mismatchedCsrf.statusCode).toBe(403);
      expect(mismatchedCsrf.json().error.code).toBe("CSRF_TOKEN_INVALID");
      expect(mismatchedCsrfValid.statusCode).toBe(403);
      expect(update).not.toHaveBeenCalled();
    } finally {
      await app.close();
    }
  });

  it("returns byte-identical Project not-found envelopes for missing and foreign scope", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const db = app.studioDb?.db;
      if (db === undefined) throw new Error("expected database");
      const foreignOwnerId = randomUUID();
      const foreignProjectId = randomUUID();
      const now = new Date();
      db.insert(owners)
        .values({
          id: foreignOwnerId,
          username: `foreign-${foreignOwnerId}`,
          password_hash: "not-a-login-credential",
          created_at: now,
        })
        .run();
      db.insert(projects)
        .values({
          id: foreignProjectId,
          ownerId: foreignOwnerId,
          title: "Foreign",
          description: "",
          settingsJson: "{}",
          createdAt: now,
          updatedAt: now,
        })
        .run();

      const bodies = await Promise.all(
        [randomUUID(), foreignProjectId].map((id) =>
          call(app, jar, "PATCH", `/api/projects/${id}`, { title: "hidden" }),
        ),
      );
      expect(bodies.map((response) => response.statusCode)).toEqual([404, 404]);
      expect(new Set(bodies.map((response) => response.body)).size).toBe(1);
      expect(bodies[0]?.json().error).toEqual({
        code: "NOT_FOUND",
        message: "Project not found.",
      });
      expect(db.select().from(projects).where(eq(projects.id, foreignProjectId)).get()?.title).toBe(
        "Foreign",
      );
    } finally {
      await app.close();
    }
  });
});
