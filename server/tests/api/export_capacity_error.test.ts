import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import {
  EXPORT_CAPACITY_LIMITS,
  EXPORT_CAPACITY_RESOURCES,
  ExportCapacityExceededError,
  type ExportCapacityResource,
} from "../../src/contexts/studio/domain/exceptions.js";
import {
  exports,
  projectSnapshots,
  snapshotDocuments,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import { ExportStorePart } from "../../src/contexts/studio/infrastructure/export_store_part.js";
import { withAsyncStudioErrors } from "../../src/contexts/studio/interface/http/studio_error_mapping.js";
import { jobEvents, jobs } from "../../src/shared/infrastructure/db/schema.js";
import { AppError } from "../../src/shared/interface/http/error_envelope.js";
import { seedProjectWithChapter, studioDatabase } from "./job_test_helpers.js";
import { buildStudioApp, call, monotonicClock, ownerJar } from "./studio_helpers.js";

const SOURCE_CAPACITY_RESOURCES = ["source_documents", "source_bytes"] as const;

class CapacityExportStore extends ExportStorePart {
  constructor(
    database: ConstructorParameters<typeof ExportStorePart>[0],
    private readonly resource: ExportCapacityResource,
  ) {
    super(database);
  }

  override readExportSource(): never {
    const limit = EXPORT_CAPACITY_LIMITS[this.resource];
    throw new ExportCapacityExceededError(this.resource, limit, limit + 999);
  }
}

describe("export capacity contract", () => {
  it("keeps the resource vocabulary and fixed limits closed", () => {
    expect(EXPORT_CAPACITY_RESOURCES).toEqual([
      "source_documents",
      "source_bytes",
      "artifact_bytes",
      "manifest_bytes",
    ]);
    expect(EXPORT_CAPACITY_LIMITS).toEqual({
      source_documents: 65_536,
      source_bytes: 16_777_216,
      artifact_bytes: 67_108_864,
      manifest_bytes: 16_384,
    });
    expect(Object.isFrozen(EXPORT_CAPACITY_RESOURCES)).toBe(true);
    expect(Object.isFrozen(EXPORT_CAPACITY_LIMITS)).toBe(true);
    expect(() => new ExportCapacityExceededError("source_bytes", 10, 10)).toThrow(RangeError);
    expect(() => new ExportCapacityExceededError("source_bytes", 10, 1.5)).toThrow(RangeError);
    expect(() => new ExportCapacityExceededError("source_bytes", -1, 1)).toThrow(RangeError);
    expect(
      () => new ExportCapacityExceededError("source_bytes", 10, Number.POSITIVE_INFINITY),
    ).toThrow(RangeError);
    expect(
      () => new ExportCapacityExceededError("unknown" as ExportCapacityResource, 10, 11),
    ).toThrow(RangeError);
  });

  it.each(EXPORT_CAPACITY_RESOURCES)("maps %s to one bounded 422 envelope", async (resource) => {
    let mapped: unknown;
    try {
      await withAsyncStudioErrors(async () => {
        throw new ExportCapacityExceededError(resource, 10, 999);
      });
    } catch (error) {
      mapped = error;
    }

    expect(mapped).toBeInstanceOf(AppError);
    expect(mapped).toMatchObject({
      statusCode: 422,
      code: "EXPORT_CAPACITY_EXCEEDED",
      message: "Export capacity exceeded.",
      details: { resource, limit: 10, observed: 11 },
    });
    expect(Object.keys((mapped as AppError).details ?? {}).sort()).toEqual([
      "limit",
      "observed",
      "resource",
    ]);
  });

  it.each(SOURCE_CAPACITY_RESOURCES)(
    "returns fresh-export 422 for %s with no durable evidence",
    async (resource) => {
      const { app } = await buildStudioApp(monotonicClock(), {
        exportStoreFactory: (database) => new CapacityExportStore(database, resource),
      });
      try {
        const owner = await ownerJar(app);
        const projectId = await seedProjectWithChapter(app, owner, `Capacity ${resource}`);

        const response = await call(app, owner, "POST", `/api/projects/${projectId}/exports`, {
          format: "markdown",
        });
        expect(response.statusCode, response.body).toBe(422);
        expect(response.json()).toEqual({
          error: {
            code: "EXPORT_CAPACITY_EXCEEDED",
            message: "Export capacity exceeded.",
            details: {
              resource,
              limit: EXPORT_CAPACITY_LIMITS[resource],
              observed: EXPORT_CAPACITY_LIMITS[resource] + 1,
            },
          },
        });
        const database = studioDatabase(app);
        expect(database.select().from(jobs).all()).toEqual([]);
        expect(database.select().from(jobEvents).all()).toEqual([]);
        expect(database.select().from(projectSnapshots).all()).toEqual([]);
        expect(database.select().from(snapshotDocuments).all()).toEqual([]);
        expect(database.select().from(exports).all()).toEqual([]);
      } finally {
        await app.close();
      }
    },
  );

  it("documents the stable envelope on fresh export only", async () => {
    const app = await buildApp({ logger: false });
    try {
      const document = (await app.inject({ method: "GET", url: "/openapi.json" })).json();
      const fresh = document.paths["/api/projects/{projectId}/exports"].post;
      expect(fresh.responses["422"].description).toContain("EXPORT_CAPACITY_EXCEEDED");
      expect(fresh.responses["422"].description).toContain("source_documents");
      expect(fresh.responses["422"].content["application/json"].schema).toEqual({
        $ref: "#/components/schemas/ErrorEnvelope",
      });
      const retry = document.paths["/api/projects/{projectId}/jobs/{jobId}/retry"].post;
      expect(JSON.stringify(retry.responses["422"])).not.toContain("EXPORT_CAPACITY_EXCEEDED");
      const download = document.paths["/api/projects/{projectId}/exports/{exportId}/download"].get;
      expect(download.responses).not.toHaveProperty("422");
    } finally {
      await app.close();
    }
  });
});
