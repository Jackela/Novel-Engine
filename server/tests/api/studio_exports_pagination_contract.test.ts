import { describe, expect, it } from "vitest";
import {
  exports as exportsTable,
  projectSnapshots,
} from "../../src/contexts/studio/infrastructure/db/schema.js";
import {
  decodeExportCursor,
  encodeExportCursor,
} from "../../src/contexts/studio/interface/http/export_cursor.js";
import { studioDatabase } from "./job_test_helpers.js";
import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

function seedCatalogArtifacts(
  app: Parameters<typeof call>[0],
  projectId: string,
  count: number,
): void {
  const database = studioDatabase(app);
  const snapshotId = `snapshot-${projectId}`;
  database
    .insert(projectSnapshots)
    .values({ id: snapshotId, projectId, reason: "export", createdAt: new Date(1) })
    .run();
  database
    .insert(exportsTable)
    .values(
      Array.from({ length: count }, (_, index) => ({
        id: `artifact-${String(index + 1).padStart(3, "0")}`,
        projectId,
        snapshotId,
        format: "markdown",
        relativePath: `exports/${projectId}/artifact-${String(index + 1).padStart(3, "0")}.md`,
        sizeBytes: index + 1,
        checksumSha256: "a".repeat(64),
        createdAt: new Date(index + 1),
      })),
    )
    .run();
}

describe("exports pagination HTTP contract", () => {
  it("round-trips only canonical project-bound cursor positions", () => {
    const token = encodeExportCursor("project-a", {
      createdAtMs: 1_725_000_000_123,
      id: "artifact-a",
    });
    expect(token).toBe("WzEsInByb2plY3QtYSIsMTcyNTAwMDAwMDEyMywiYXJ0aWZhY3QtYSJd");
    expect(decodeExportCursor(token ?? "", "project-a")).toEqual({
      createdAtMs: 1_725_000_000_123,
      id: "artifact-a",
    });

    const invalidTokens = [
      "not+base64url",
      Buffer.from('[1, "project-a", 1, "artifact-a"]', "utf8").toString("base64url"),
      Buffer.from('[1,"project-a",1e0,"artifact-a"]', "utf8").toString("base64url"),
      Buffer.from('[1,"project\\u002da",1,"artifact-a"]', "utf8").toString("base64url"),
      Buffer.from(JSON.stringify([2, "project-a", 1, "artifact-a"])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "project-a", -1, "artifact-a"])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "project-a", 1, ""])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "project-a", 1, "x".repeat(129)])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "project-a", 1, "artifact-a", "extra"])).toString("base64url"),
    ];
    for (const invalid of invalidTokens) {
      expect(() => decodeExportCursor(invalid, "project-a")).toThrowError(
        expect.objectContaining({ code: "VALIDATION_ERROR", statusCode: 422 }),
      );
    }
    expect(() => decodeExportCursor(token ?? "", "project-b")).toThrowError(
      expect.objectContaining({ code: "VALIDATION_ERROR", statusCode: 422 }),
    );
  });

  it("rejects invalid limits and cursors through the validation envelope", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Invalid export page inputs");
      for (const limit of ["0", "101", "1.5", "not-an-integer"]) {
        const response = await call(
          app,
          owner,
          "GET",
          `/api/projects/${project.id}/exports?limit=${encodeURIComponent(limit)}`,
        );
        expect(response.statusCode, response.body).toBe(422);
        expect(response.json().error.code).toBe("VALIDATION_ERROR");
      }

      const routeProjectId = "00000000-0000-4000-8000-000000000099";
      const crossProject = encodeExportCursor("another-project", { createdAtMs: 1, id: "a" });
      const unknownVersion = Buffer.from(
        JSON.stringify([2, routeProjectId, 1, "artifact-a"]),
      ).toString("base64url");
      for (const cursor of [crossProject ?? "", unknownVersion, "a".repeat(1025)]) {
        const response = await call(
          app,
          owner,
          "GET",
          `/api/projects/${routeProjectId}/exports?cursor=${encodeURIComponent(cursor)}`,
        );
        expect(response.statusCode, response.body).toBe(422);
        expect(response.json().error.code).toBe("VALIDATION_ERROR");
        expect(response.json().error.details.errors[0].field).toBe("cursor");
      }
    } finally {
      await app.close();
    }
  });

  it("returns and follows a project-bound HTTP cursor", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Exports HTTP traversal");
      seedCatalogArtifacts(app, project.id, 3);

      const first = await call(app, owner, "GET", `/api/projects/${project.id}/exports?limit=2`);
      expect(first.statusCode, first.body).toBe(200);
      expect(first.json().exports.map((item: { id: string }) => item.id)).toEqual([
        "artifact-003",
        "artifact-002",
      ]);
      expect(first.json().next_cursor).toEqual(expect.any(String));

      const second = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/exports?limit=2&cursor=${encodeURIComponent(first.json().next_cursor)}`,
      );
      expect(second.statusCode, second.body).toBe(200);
      expect(second.json().exports.map((item: { id: string }) => item.id)).toEqual([
        "artifact-001",
      ]);
      expect(second.json().next_cursor).toBeNull();
    } finally {
      await app.close();
    }
  });

  it("applies the default and maximum page bounds and keeps summary fields", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Exports HTTP bounds");
      seedCatalogArtifacts(app, project.id, 101);

      const defaultPage = await call(app, owner, "GET", `/api/projects/${project.id}/exports`);
      expect(defaultPage.statusCode, defaultPage.body).toBe(200);
      expect(defaultPage.json().exports).toHaveLength(50);
      expect(defaultPage.json().exports[0]?.id).toBe("artifact-101");
      expect(defaultPage.json().exports[49]?.id).toBe("artifact-052");
      expect(defaultPage.json().next_cursor).toEqual(expect.any(String));
      expect(Object.keys(defaultPage.json().exports[0]).sort()).toEqual(
        [
          "checksum_sha256",
          "created_at",
          "download_url",
          "format",
          "id",
          "project_id",
          "size_bytes",
          "snapshot_id",
        ].sort(),
      );

      const maximumPage = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/exports?limit=100`,
      );
      expect(maximumPage.statusCode, maximumPage.body).toBe(200);
      expect(maximumPage.json().exports).toHaveLength(100);
      expect(maximumPage.json().exports[0]?.id).toBe("artifact-101");
      expect(maximumPage.json().exports[99]?.id).toBe("artifact-002");
      expect(maximumPage.json().next_cursor).toEqual(expect.any(String));
    } finally {
      await app.close();
    }
  });

  it("documents the bounded query and required nullable cursor response", async () => {
    const { app } = await buildStudioApp();
    try {
      const document = (await app.inject({ method: "GET", url: "/openapi.json" })).json();
      const operation = document.paths["/api/projects/{projectId}/exports"].get;
      const parameters = Object.fromEntries(
        operation.parameters.map((parameter: { name: string; schema: object }) => [
          parameter.name,
          parameter.schema,
        ]),
      );

      expect(parameters.limit).toMatchObject({
        type: "integer",
        default: 50,
        minimum: 1,
        maximum: 100,
      });
      expect(parameters.cursor).toMatchObject({
        type: "string",
        minLength: 1,
        maxLength: 1024,
        pattern: "^[A-Za-z0-9_-]+$",
      });
      expect(operation.responses["422"]).toBeDefined();
      const schema = operation.responses["200"].content["application/json"].schema;
      expect(schema.properties.next_cursor).toEqual({ type: "string", nullable: true });
      expect(schema.required).toContain("next_cursor");
      expect(Object.keys(schema.properties.exports.items.properties).sort()).toEqual(
        [
          "checksum_sha256",
          "created_at",
          "download_url",
          "format",
          "id",
          "project_id",
          "size_bytes",
          "snapshot_id",
        ].sort(),
      );
    } finally {
      await app.close();
    }
  });
});
