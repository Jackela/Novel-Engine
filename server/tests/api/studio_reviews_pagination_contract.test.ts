import { describe, expect, it } from "vitest";
import { reviews as reviewsTable } from "../../src/contexts/studio/infrastructure/db/schema.js";
import {
  decodeReviewCursor,
  encodeReviewCursor,
} from "../../src/contexts/studio/interface/http/review_cursor.js";
import { studioDatabase } from "./job_test_helpers.js";
import { buildStudioApp, call, ownerJar, seedProject } from "./studio_helpers.js";

describe("review history pagination HTTP contract", () => {
  it("returns strict bounded summaries without issues", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Review summary contract");
      const created = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      expect(created.statusCode, created.body).toBe(201);
      const snapshotId = created.json().result.snapshot_id as string;
      const database = studioDatabase(app);
      database
        .insert(reviewsTable)
        .values(
          Array.from({ length: 51 }, (_, index) => ({
            id: `synthetic-${String(index).padStart(2, "0")}`,
            projectId: project.id,
            snapshotId,
            provider: "mock",
            model: "deterministic-story-v1",
            summary: "synthetic",
            createdAt: new Date(Date.parse("2026-09-05T00:00:00.000Z") + index * 1000),
          })),
        )
        .run();

      const response = await call(app, owner, "GET", `/api/projects/${project.id}/reviews`);
      expect(response.statusCode, response.body).toBe(200);
      const body = response.json();
      expect(Object.keys(body).sort()).toEqual(["next_cursor", "reviews"]);
      expect(body.reviews).toHaveLength(50);
      expect(body.reviews[0]?.id).toBe(created.json().result.review_id);
      expect(body.reviews[1]?.id).toBe("synthetic-50");
      expect(body.reviews[49]?.id).toBe("synthetic-02");
      expect(body.next_cursor).toEqual(expect.any(String));
      const summary = body.reviews[0] as Record<string, unknown>;
      expect(Object.keys(summary).sort()).toEqual(
        [
          "created_at",
          "id",
          "issue_count",
          "model",
          "project_id",
          "provider",
          "snapshot_id",
          "summary",
        ].sort(),
      );
      expect(summary).not.toHaveProperty("issues");
      const synthetic = body.reviews.find((review: { id: string }) => review.id === "synthetic-50");
      expect(synthetic?.issue_count).toBe(0);

      const maximum = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/reviews?limit=100`,
      );
      expect(maximum.statusCode, maximum.body).toBe(200);
      expect(maximum.json().reviews).toHaveLength(52);
      expect(maximum.json().reviews[0]?.id).toBe(created.json().result.review_id);
      expect(maximum.json().next_cursor).toBeNull();
    } finally {
      await app.close();
    }
  });

  it("rejects invalid limits through the validation envelope", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Invalid review limits");
      for (const limit of ["0", "101", "1.5", "not-an-integer"]) {
        const response = await call(
          app,
          owner,
          "GET",
          `/api/projects/${project.id}/reviews?limit=${encodeURIComponent(limit)}`,
        );

        expect(response.statusCode, response.body).toBe(422);
        expect(response.json().error.code).toBe("VALIDATION_ERROR");
      }
    } finally {
      await app.close();
    }
  });

  it("round-trips only canonical project-bound cursor positions", () => {
    const token = encodeReviewCursor("project-a", {
      createdAtMs: 1_725_000_000_123,
      id: "review-a",
    });
    expect(token).toBe("WzEsInByb2plY3QtYSIsMTcyNTAwMDAwMDEyMywicmV2aWV3LWEiXQ");
    expect(decodeReviewCursor(token ?? "", "project-a")).toEqual({
      createdAtMs: 1_725_000_000_123,
      id: "review-a",
    });

    const invalidTokens = [
      "not+base64url",
      Buffer.from('[1, "project-a", 1, "review-a"]', "utf8").toString("base64url"),
      Buffer.from('[1,"project-a",1e0,"review-a"]', "utf8").toString("base64url"),
      Buffer.from('[1,"project\\u002da",1,"review-a"]', "utf8").toString("base64url"),
      Buffer.from(JSON.stringify([2, "project-a", 1, "review-a"])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "project-a", -1, "review-a"])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "project-a", 1, ""])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "project-a", 1, "x".repeat(129)])).toString("base64url"),
      Buffer.from(JSON.stringify([1, "project-a", 1, "review-a", "extra"])).toString("base64url"),
    ];
    for (const invalid of invalidTokens) {
      expect(() => decodeReviewCursor(invalid, "project-a")).toThrowError(
        expect.objectContaining({ code: "VALIDATION_ERROR", statusCode: 422 }),
      );
    }
    expect(() => decodeReviewCursor(token ?? "", "project-b")).toThrowError(
      expect.objectContaining({ code: "VALIDATION_ERROR", statusCode: 422 }),
    );
  });

  it("rejects invalid cursors before project lookup", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const routeProjectId = "00000000-0000-4000-8000-000000000099";
      const crossProject = encodeReviewCursor("another-project", {
        createdAtMs: 1,
        id: "review-a",
      });
      const unknownVersion = Buffer.from(
        JSON.stringify([2, routeProjectId, 1, "review-a"]),
      ).toString("base64url");

      for (const cursor of [crossProject ?? "", unknownVersion, "a".repeat(1025)]) {
        const response = await call(
          app,
          owner,
          "GET",
          `/api/projects/${routeProjectId}/reviews?cursor=${encodeURIComponent(cursor)}`,
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
      const firstProject = await seedProject(app, owner, "Review HTTP traversal");
      const older = await call(app, owner, "POST", `/api/projects/${firstProject.id}/reviews`);
      expect(older.statusCode, older.body).toBe(201);
      const newer = await call(app, owner, "POST", `/api/projects/${firstProject.id}/reviews`);
      expect(newer.statusCode, newer.body).toBe(201);
      const secondProject = await seedProject(app, owner, "Review HTTP other project");
      await call(app, owner, "POST", `/api/projects/${secondProject.id}/reviews`);

      const first = await call(
        app,
        owner,
        "GET",
        `/api/projects/${firstProject.id}/reviews?limit=1`,
      );
      expect(first.statusCode, first.body).toBe(200);
      expect(first.json().reviews.map((review: { id: string }) => review.id)).toEqual([
        newer.json().result.review_id,
      ]);
      expect(first.json().next_cursor).toEqual(expect.any(String));

      const second = await call(
        app,
        owner,
        "GET",
        `/api/projects/${firstProject.id}/reviews?limit=1&cursor=${encodeURIComponent(first.json().next_cursor)}`,
      );
      expect(second.statusCode, second.body).toBe(200);
      expect(second.json().reviews.map((review: { id: string }) => review.id)).toEqual([
        older.json().result.review_id,
      ]);
      expect(second.json().next_cursor).toBeNull();
    } finally {
      await app.close();
    }
  });

  it("serves the scoped detail read with ordered issues and closes scope misses", async () => {
    const { app } = await buildStudioApp();
    try {
      const owner = await ownerJar(app);
      const project = await seedProject(app, owner, "Review detail contract");
      const otherProject = await seedProject(app, owner, "Review detail other");
      const created = await call(app, owner, "POST", `/api/projects/${project.id}/reviews`);
      expect(created.statusCode, created.body).toBe(201);
      const reviewId = created.json().result.review_id as string;

      const detail = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/reviews/${reviewId}`,
      );
      expect(detail.statusCode, detail.body).toBe(200);
      const detailBody = detail.json();
      expect(Object.keys(detailBody).sort()).toEqual(
        [
          "created_at",
          "id",
          "issues",
          "model",
          "project_id",
          "provider",
          "snapshot_id",
          "summary",
        ].sort(),
      );
      expect(detailBody.id).toBe(reviewId);
      expect(detailBody.issues.length).toBeGreaterThan(0);
      const summaryPage = await call(app, owner, "GET", `/api/projects/${project.id}/reviews`);
      expect(summaryPage.json().reviews[0]?.issue_count).toBe(detailBody.issues.length);

      const foreign = await call(
        app,
        owner,
        "GET",
        `/api/projects/${otherProject.id}/reviews/${reviewId}`,
      );
      expect(foreign.statusCode).toBe(404);
      expect(foreign.json().error.code).toBe("NOT_FOUND");

      const missing = await call(
        app,
        owner,
        "GET",
        `/api/projects/${project.id}/reviews/missing-review`,
      );
      expect(missing.statusCode).toBe(404);
      expect(missing.json().error.code).toBe("NOT_FOUND");
    } finally {
      await app.close();
    }
  });
});
