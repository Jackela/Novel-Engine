import { describe, expect, it } from "vitest";

import { buildStudioApp } from "./studio_helpers.js";

const PROJECT_SCALAR_FIELDS = [
  "created_at",
  "description",
  "id",
  "import_hash",
  "settings",
  "title",
  "updated_at",
];

describe("Project settings PATCH OpenAPI contract", () => {
  it("publishes one closed partial request and strict scalar response", async () => {
    const { app } = await buildStudioApp();
    try {
      const openapi = (await app.inject({ method: "GET", url: "/openapi.json" })).json();
      const patch = openapi.paths["/api/projects/{projectId}"].patch;
      const request = patch.requestBody.content["application/json"].schema;
      expect(Object.keys(request.properties).sort()).toEqual(["description", "settings", "title"]);
      expect(request.additionalProperties).toBe(false);
      expect(request.minProperties).toBe(1);
      expect(request.required ?? []).toEqual([]);
      expect(request.properties.title).toMatchObject({
        type: "string",
        minLength: 1,
        maxLength: 240,
      });
      expect(request.properties.description).toMatchObject({
        type: "string",
        maxLength: 10_000,
      });
      expect(request.properties.settings).toEqual({
        type: "object",
        additionalProperties: true,
      });

      const success = patch.responses["200"].content["application/json"].schema;
      expect(Object.keys(success.properties).sort()).toEqual(PROJECT_SCALAR_FIELDS);
      expect(success.required.slice().sort()).toEqual(PROJECT_SCALAR_FIELDS);
      expect(success.additionalProperties).toBe(false);
      expect(success.properties).not.toHaveProperty("documents");
      expect(success.properties).not.toHaveProperty("volumes");
      expect(Object.keys(patch.responses).sort()).toEqual([
        "200",
        "401",
        "403",
        "404",
        "422",
        "500",
        "503",
      ]);
    } finally {
      await app.close();
    }
  });
});
