import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import {
  ImportCapacityExceededError,
  type ImportCapacityResource,
} from "../../src/contexts/studio/domain/exceptions.js";
import { withAsyncStudioErrors } from "../../src/contexts/studio/interface/http/studio_error_mapping.js";
import { AppError } from "../../src/shared/interface/http/error_envelope.js";
import { anonymousCall, buildStudioApp, call, monotonicClock, ownerJar } from "./studio_helpers.js";

const RESOURCES: readonly ImportCapacityResource[] = [
  "story_bytes",
  "chapter_bytes",
  "workspace_bytes",
  "chapter_count",
  "directory_entries",
];

describe("legacy import capacity HTTP contract", () => {
  it.each(RESOURCES)("maps %s to the stable bounded 422 envelope", async (resource) => {
    let mapped: unknown;

    try {
      await withAsyncStudioErrors(async () => {
        throw new ImportCapacityExceededError(resource, 10, 11);
      });
    } catch (error) {
      mapped = error;
    }

    expect(mapped).toBeInstanceOf(AppError);
    expect(mapped).toMatchObject({
      statusCode: 422,
      code: "IMPORT_CAPACITY_EXCEEDED",
      message: "Legacy import capacity exceeded.",
      details: { resource, limit: 10, observed: 11 },
    });
    expect(Object.keys((mapped as AppError).details ?? {}).sort()).toEqual([
      "limit",
      "observed",
      "resource",
    ]);
  });

  it("keeps authentication ahead of filesystem capacity and returns no partial preview", async () => {
    const { app, directory } = await buildStudioApp(monotonicClock());
    const workspace = join(directory, "imports", "oversized-story");
    await mkdir(workspace, { recursive: true });
    await writeFile(join(workspace, "story.yaml"), Buffer.alloc(262_145, 0x61));

    try {
      const jar = await ownerJar(app);
      const anonymous = await anonymousCall(app, "POST", "/api/imports/preview", {
        source: "oversized-story",
      });
      expect(anonymous.statusCode, anonymous.body).toBe(401);
      expect(anonymous.json().error.code).toBe("UNAUTHORIZED");

      const rejected = await call(app, jar, "POST", "/api/imports/preview", {
        source: "oversized-story",
      });
      expect(rejected.statusCode, rejected.body).toBe(422);
      expect(rejected.json()).toEqual({
        error: {
          code: "IMPORT_CAPACITY_EXCEEDED",
          message: "Legacy import capacity exceeded.",
          details: { resource: "story_bytes", limit: 262_144, observed: 262_145 },
        },
      });
      expect(rejected.json()).not.toHaveProperty("source");
      expect(rejected.json()).not.toHaveProperty("chapters");

      const projects = await call(app, jar, "GET", "/api/projects");
      expect(projects.statusCode, projects.body).toBe(200);
      expect(projects.json().projects).toEqual([]);
    } finally {
      await app.close();
    }
  });

  it("documents the capacity code without changing the preview success schema", async () => {
    const app = await buildApp({ logger: false });
    try {
      const document = (await app.inject({ method: "GET", url: "/openapi.json" })).json();
      const operation = document.paths["/api/imports/preview"].post;
      const response = operation.responses["422"];
      expect(response.description).toContain("IMPORT_CAPACITY_EXCEEDED");
      expect(response.content["application/json"].schema).toEqual({
        $ref: "#/components/schemas/ErrorEnvelope",
      });
      expect(operation.responses["200"].content["application/json"].schema.required).toEqual([
        "source",
        "source_hash",
        "title",
        "description",
        "chapter_count",
        "chapters",
      ]);
      for (const status of ["401", "403", "404", "422", "503"]) {
        expect(operation.responses).toHaveProperty(status);
      }
    } finally {
      await app.close();
    }
  });
});
