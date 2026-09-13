import { describe, expect, it } from "vitest";

import { buildStudioApp } from "./studio_helpers.js";

const SUMMARY_FIELDS = [
  "beat_ref",
  "created_at",
  "current_revision_id",
  "id",
  "kind",
  "lore_status",
  "position",
  "project_id",
  "revision_source",
  "title",
  "updated_at",
  "volume_id",
  "word_count",
];

describe("project shell OpenAPI contract", () => {
  it("uses one closed body-free summary for create, detail, and reorder", async () => {
    const { app } = await buildStudioApp();
    try {
      const openapi = (await app.inject({ method: "GET", url: "/openapi.json" })).json();
      const summaries = [
        openapi.paths["/api/projects"].post.responses["201"].content["application/json"].schema
          .properties.documents.items,
        openapi.paths["/api/projects/{projectId}"].get.responses["200"].content["application/json"]
          .schema.properties.documents.items,
        openapi.paths["/api/projects/{projectId}/documents/reorder"].put.responses["200"].content[
          "application/json"
        ].schema.properties.documents.items,
      ];

      for (const summary of summaries) {
        expect(Object.keys(summary.properties).sort()).toEqual(SUMMARY_FIELDS);
        expect(summary.required.slice().sort()).toEqual(SUMMARY_FIELDS);
        expect(summary.additionalProperties).toBe(false);
        expect(summary.properties.revision_source).toEqual({
          type: "string",
          enum: ["author", "ai-accepted", "restore"],
        });
        expect(summary.properties).not.toHaveProperty("content_markdown");
        expect(summary.properties).not.toHaveProperty("metadata");
      }
    } finally {
      await app.close();
    }
  });
});
