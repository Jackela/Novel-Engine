import { join } from "node:path";
import Database from "better-sqlite3";
import { describe, expect, it } from "vitest";

import { capturingFactory } from "./proposal_test_helpers.js";
import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

function insertRawUsage(
  directory: string,
  projectId: string,
  rows: ReadonlyArray<{
    id: string;
    model: string;
    promptTokens: number;
    completionTokens: number;
    createdAt?: number;
  }>,
  ignoreConstraints = false,
): void {
  const raw = new Database(join(directory, "novel-engine.sqlite3"));
  try {
    if (ignoreConstraints) raw.pragma("ignore_check_constraints = ON");
    const insert = raw.prepare(
      `INSERT INTO usage_events
        (id, project_id, provider, model, prompt_tokens, completion_tokens,
         request_evidence_json, created_at)
       VALUES (?, ?, 'mock', ?, ?, ?, '{}', ?)`,
    );
    const now = Date.now();
    raw.transaction(() => {
      for (const row of rows) {
        insert.run(
          row.id,
          projectId,
          row.model,
          row.promptTokens,
          row.completionTokens,
          row.createdAt ?? now,
        );
      }
    })();
  } finally {
    raw.close();
  }
}

describe("project usage surface (#317)", () => {
  it("aggregates recorded events into totals and a per-model breakdown", async () => {
    const capture = capturingFactory({});
    const { app } = await buildStudioApp(undefined, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Counted");
      const document = project.documents[0];
      if (document === undefined) throw new Error("expected seeded document");
      const propose = () =>
        call(
          app,
          jar,
          "POST",
          `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
          { operation: "continue" },
        );

      await propose();
      await propose();

      const response = await call(app, jar, "GET", `/api/projects/${project.id}/usage`);
      expect(response.statusCode).toBe(200);
      const body = response.json();
      expect(body.project_id).toBe(project.id);
      expect(body.request_count).toBe(2);
      expect(body.per_model).toHaveLength(1);
      expect(body.per_model[0]).toMatchObject({ model: expect.any(String), requests: 2 });
      // Totals are exactly the fold of the per-model breakdown.
      expect(body.prompt_tokens).toBe(body.per_model[0].prompt_tokens);
      expect(body.completion_tokens).toBe(body.per_model[0].completion_tokens);
      // #384: 30 zero-filled daily buckets ending today; today holds the calls.
      expect(body.daily).toHaveLength(30);
      const today = new Date().toISOString().slice(0, 10);
      expect(body.daily.at(-1)).toEqual({
        date: today,
        request_count: 2,
        prompt_tokens: body.prompt_tokens,
        completion_tokens: body.completion_tokens,
      });
      expect(body.daily.at(-2)?.request_count).toBe(0);
    } finally {
      await app.close();
    }
  });

  it("zero-fills the trailing 30 UTC days for a project with an empty ledger", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Empty ledger");

      const response = await call(app, jar, "GET", `/api/projects/${project.id}/usage`);
      expect(response.statusCode).toBe(200);
      const body = response.json();
      expect(body).toEqual({
        project_id: project.id,
        request_count: 0,
        prompt_tokens: 0,
        completion_tokens: 0,
        per_model: [],
        daily: expect.any(Array),
      });
      expect(body.daily).toHaveLength(30);
      const today = new Date().toISOString().slice(0, 10);
      expect(body.daily.map((bucket: { date: string }) => bucket.date)).toEqual(
        Array.from({ length: 30 }, (_, index) =>
          new Date(Date.parse(`${today}T00:00:00Z`) - (29 - index) * 86_400_000)
            .toISOString()
            .slice(0, 10),
        ),
      );
      for (const bucket of body.daily) {
        expect(bucket).toEqual({
          date: bucket.date,
          request_count: 0,
          prompt_tokens: 0,
          completion_tokens: 0,
        });
      }
    } finally {
      await app.close();
    }
  });

  it("buckets usage into the UTC day of an injected fixed clock (#384)", async () => {
    const fixed = new Date("2026-03-15T23:30:00Z");
    let current = fixed.getTime();
    const clock = () => {
      current += 1;
      return new Date(current);
    };
    const capture = capturingFactory({});
    const { app } = await buildStudioApp(clock, { textProviderFactory: capture.factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Fixed clock");
      const document = project.documents[0];
      if (document === undefined) throw new Error("expected seeded document");
      const propose = () =>
        call(
          app,
          jar,
          "POST",
          `/api/projects/${project.id}/documents/${document.id}/ai-proposals`,
          { operation: "continue" },
        );
      await propose();
      await propose();

      const response = await call(app, jar, "GET", `/api/projects/${project.id}/usage`);
      expect(response.statusCode).toBe(200);
      const body = response.json();
      expect(body.daily.at(-1)).toEqual({
        date: "2026-03-15",
        request_count: 2,
        prompt_tokens: body.prompt_tokens,
        completion_tokens: body.completion_tokens,
      });
      // Only the fixed-clock day and zero-filled predecessors, never a future day.
      expect(body.daily.at(0).date).toBe("2026-02-14");
      expect(body.daily.some((bucket: { date: string }) => bucket.date > "2026-03-15")).toBe(false);
    } finally {
      await app.close();
    }
  });

  it("answers 401 unauthenticated and 404 for an unknown project", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      await seedProject(app, jar, "Scoped");

      const anonymous = await app.inject({ method: "GET", url: "/api/projects/p-1/usage" });
      expect(anonymous.statusCode).toBe(401);
      expect(anonymous.json().error.code).toBe("UNAUTHORIZED");

      const unknown = await call(
        app,
        jar,
        "GET",
        "/api/projects/00000000-0000-0000-0000-000000000000/usage",
      );
      expect(unknown.statusCode).toBe(404);
      expect(unknown.json().error.code).toBe("NOT_FOUND");
    } finally {
      await app.close();
    }
  });

  it("returns exact safe-boundary project, model, and daily totals", async () => {
    const { app, directory } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Exact ledger");
      insertRawUsage(directory, project.id, [
        {
          id: "usage-a",
          model: "alpha",
          promptTokens: Number.MAX_SAFE_INTEGER - 3,
          completionTokens: Number.MAX_SAFE_INTEGER - 5,
        },
        { id: "usage-b", model: "beta", promptTokens: 3, completionTokens: 5 },
      ]);

      const response = await call(app, jar, "GET", `/api/projects/${project.id}/usage`);
      expect(response.statusCode).toBe(200);
      expect(response.json()).toMatchObject({
        request_count: 2,
        prompt_tokens: Number.MAX_SAFE_INTEGER,
        completion_tokens: Number.MAX_SAFE_INTEGER,
        per_model: [
          { model: "alpha", prompt_tokens: Number.MAX_SAFE_INTEGER - 3 },
          { model: "beta", prompt_tokens: 3 },
        ],
      });
      expect(response.json().daily.at(-1)).toMatchObject({
        request_count: 2,
        prompt_tokens: Number.MAX_SAFE_INTEGER,
        completion_tokens: Number.MAX_SAFE_INTEGER,
      });
    } finally {
      await app.close();
    }
  });

  it("fails opaquely when individually safe rows have an unsafe total", async () => {
    const { app, directory } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Unsafe total");
      insertRawUsage(directory, project.id, [
        {
          id: "usage-max",
          model: "alpha",
          promptTokens: Number.MAX_SAFE_INTEGER,
          completionTokens: 0,
        },
        { id: "usage-one", model: "beta", promptTokens: 1, completionTokens: 0 },
      ]);

      const response = await call(app, jar, "GET", `/api/projects/${project.id}/usage`);
      expect(response.statusCode).toBe(500);
      expect(response.json()).toEqual({
        error: {
          code: "INTERNAL_ERROR",
          message: "An internal error occurred.",
          details: { error_id: expect.any(String) },
        },
      });
    } finally {
      await app.close();
    }
  });

  it.each([
    ["negative", -1],
    ["fractional", 1.5],
    ["unsafe", Number.MAX_SAFE_INTEGER + 1],
    ["non-finite", Number.POSITIVE_INFINITY],
  ])("fails opaquely for a corrupt %s stored count", async (_label, promptTokens) => {
    const { app, directory } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Corrupt ledger");
      insertRawUsage(
        directory,
        project.id,
        [{ id: "usage-corrupt", model: "alpha", promptTokens, completionTokens: 0 }],
        true,
      );

      const response = await call(app, jar, "GET", `/api/projects/${project.id}/usage`);
      expect(response.statusCode).toBe(500);
      expect(response.json()).toMatchObject({
        error: {
          code: "INTERNAL_ERROR",
          message: "An internal error occurred.",
          details: { error_id: expect.any(String) },
        },
      });
    } finally {
      await app.close();
    }
  });
});
