import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { eq } from "drizzle-orm";
import { afterEach, describe, expect, expectTypeOf, it } from "vitest";

import type { ProjectUpdateInput } from "../../src/contexts/studio/application/ports/project_update_store.js";
import type {
  ProjectRecord,
  StudioStore,
} from "../../src/contexts/studio/application/ports/studio_store.js";
import {
  ProjectService,
  type ProjectUpdateCommand,
} from "../../src/contexts/studio/application/project_service.js";
import {
  InvalidProjectUpdateError,
  NotFoundError,
} from "../../src/contexts/studio/domain/exceptions.js";
import { projects } from "../../src/contexts/studio/infrastructure/db/schema.js";
import { DrizzleStudioStore } from "../../src/contexts/studio/infrastructure/drizzle_studio_store.js";
import type { Principal } from "../../src/shared/application/ports/auth.js";
import { owners } from "../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const PRINCIPAL: Principal = {
  sessionId: "session-1",
  kind: "owner",
  ownerId: "owner-1",
  expiresAt: null,
};

const directories: string[] = [];

afterEach(async () => {
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true })));
});

async function openHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-project-update-"));
  directories.push(directory);
  const queries: Array<{ query: string; params: unknown[] }> = [];
  const studio = await openStudioDatabase(join(directory, "novel-engine.sqlite3"), {
    queryLogger: { logQuery: (query, params) => queries.push({ query, params }) },
  });
  studio.db
    .insert(owners)
    .values({
      id: "owner-1",
      username: "owner-1",
      password_hash: "not-a-login-credential",
      created_at: new Date(0),
    })
    .run();
  const store = new DrizzleStudioStore({ database: studio.db });
  const seeded = store.addProject(
    { ownerId: "owner-1" },
    {
      title: "Initial",
      description: "Description",
      settingsJson: '{"provider":"mock","remove":true}',
      seed: null,
      now: new Date("2026-09-03T12:00:00.000Z"),
    },
  ).project;
  queries.length = 0;
  return { queries, seeded, store, studio };
}

describe("Project settings application boundary", () => {
  it("normalizes and serializes before one Owner-scoped store command", () => {
    let nowCalls = 0;
    let captured:
      | { scope: { ownerId: string }; projectId: string; input: ProjectUpdateInput }
      | undefined;
    const row: ProjectRecord = {
      id: "project-1",
      ownerId: "owner-1",
      title: "Updated",
      description: "Description",
      settingsJson: '{"provider":"dashscope"}',
      importHash: null,
      createdAt: new Date(0),
      updatedAt: new Date(1),
    };
    const store = {
      updateProject: (scope: { ownerId: string }, projectId: string, input: ProjectUpdateInput) => {
        captured = { scope, projectId, input };
        return row;
      },
    } as unknown as StudioStore;
    const service = new ProjectService(store, () => {
      nowCalls += 1;
      return new Date(1);
    });

    const payload = service.updateProject(PRINCIPAL, "project-1", {
      title: "  Updated  ",
      settings: { provider: "dashscope" },
    });

    expect(captured).toEqual({
      scope: { ownerId: "owner-1" },
      projectId: "project-1",
      input: {
        title: "Updated",
        settingsJson: '{"provider":"dashscope"}',
        now: new Date(1),
      },
    });
    expect(Object.hasOwn(captured?.input ?? {}, "description")).toBe(false);
    expect(nowCalls).toBe(1);
    expect(payload).toMatchObject({ id: "project-1", title: "Updated" });
  });

  it("rejects a blank normalized title before consulting persistence", () => {
    let storeCalls = 0;
    let nowCalls = 0;
    const store = {
      updateProject: () => {
        storeCalls += 1;
        throw new Error("store must not be called");
      },
    } as unknown as StudioStore;
    const service = new ProjectService(store, () => {
      nowCalls += 1;
      return new Date();
    });

    expectTypeOf<Record<string, never>>().not.toMatchTypeOf<ProjectUpdateCommand>();
    expect(() => service.updateProject(PRINCIPAL, "project-1", {} as ProjectUpdateCommand)).toThrow(
      InvalidProjectUpdateError,
    );
    expect(() => service.updateProject(PRINCIPAL, "project-1", { title: "   " })).toThrow(
      InvalidProjectUpdateError,
    );
    expect(storeCalls).toBe(0);
    expect(nowCalls).toBe(0);
  });
});

describe("Project settings store boundary", () => {
  it("uses one Owner-scoped atomic UPDATE and strictly advances a stale clock", async () => {
    const { queries, seeded, store, studio } = await openHarness();
    try {
      const updated = store.updateProject({ ownerId: "owner-1" }, seeded.id, {
        title: "Updated",
        settingsJson: "{}",
        now: new Date(0),
      });

      expect(updated.updatedAt.getTime()).toBe(seeded.updatedAt.getTime() + 1);
      expect(updated).toMatchObject({
        title: "Updated",
        description: "Description",
        settingsJson: "{}",
        importHash: seeded.importHash,
        createdAt: seeded.createdAt,
      });
      const updates = queries.filter((entry) => entry.query.startsWith('update "projects"'));
      expect(updates).toHaveLength(1);
      expect(updates[0]?.query).toContain('"id" = ?');
      expect(updates[0]?.query).toContain('"owner_id" = ?');
      expect(updates[0]?.query).toContain("max(");
      expect(updates[0]?.params).toContain(seeded.id);
      expect(updates[0]?.params).toContain("owner-1");
    } finally {
      studio.close();
    }
  });

  it("normalizes missing and foreign Project ids to one not-found error", async () => {
    const { seeded, store, studio } = await openHarness();
    try {
      const update = (ownerId: string, projectId: string) =>
        store.updateProject({ ownerId }, projectId, { title: "Hidden", now: new Date() });
      for (const operation of [
        () => update("owner-1", "missing"),
        () => update("foreign-owner", seeded.id),
      ]) {
        expect(operation).toThrowError(new NotFoundError("Project not found."));
      }
      expect(store.findProject({ ownerId: "owner-1" }, seeded.id).title).toBe("Initial");
    } finally {
      studio.close();
    }
  });

  it("rejects a runtime empty store command before issuing SQL", async () => {
    const { queries, seeded, store, studio } = await openHarness();
    try {
      expectTypeOf<{ now: Date }>().not.toMatchTypeOf<ProjectUpdateInput>();
      expect(() =>
        store.updateProject({ ownerId: "owner-1" }, seeded.id, {
          now: new Date(),
        } as ProjectUpdateInput),
      ).toThrow(RangeError);
      expect(queries).toEqual([]);
    } finally {
      studio.close();
    }
  });

  it("rolls back every scalar and timestamp when an after-update trigger aborts", async () => {
    const { seeded, store, studio } = await openHarness();
    try {
      const before = studio.db.select().from(projects).where(eq(projects.id, seeded.id)).get();
      studio.raw.exec(`
        CREATE TRIGGER reject_atomic_project_update
        AFTER UPDATE OF title, description, settings_json, updated_at ON projects
        BEGIN
          SELECT RAISE(ABORT, 'injected failure after row mutation');
        END;
      `);

      expect(() =>
        store.updateProject({ ownerId: "owner-1" }, seeded.id, {
          title: "No",
          description: "No",
          settingsJson: '{"no":true}',
          now: new Date("2030-01-01T00:00:00.000Z"),
        }),
      ).toThrow("injected failure after row mutation");
      expect(studio.db.select().from(projects).where(eq(projects.id, seeded.id)).get()).toEqual(
        before,
      );
    } finally {
      studio.close();
    }
  });
});
