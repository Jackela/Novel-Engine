import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import { AppError } from "../../src/shared/interface/http/error_envelope.js";

const titleBodySchema = {
  type: "object",
  properties: { title: { type: "string", maxLength: 3 } },
  required: ["title"],
  additionalProperties: false,
};

async function buildQuietApp() {
  return buildApp({ logger: false });
}

describe("unified error envelope", () => {
  it("maps schema violations to 422 VALIDATION_ERROR with per-field details", async () => {
    const app = await buildQuietApp();

    try {
      app.post("/test/validated", { schema: { body: titleBodySchema } }, async () => ({
        ok: true,
      }));

      const response = await app.inject({
        method: "POST",
        url: "/test/validated",
        payload: { title: "too-long-title" },
      });

      expect(response.statusCode).toBe(422);
      const body = response.json();
      expect(body.error.code).toBe("VALIDATION_ERROR");
      expect(typeof body.error.message).toBe("string");
      const errors = body.error.details.errors as Array<{
        field: string;
        message: string;
        type: string;
      }>;
      expect(errors).toHaveLength(1);
      expect(errors[0]?.field).toBe("title");
      expect(errors[0]?.type).toBe("maxLength");
      expect(typeof errors[0]?.message).toBe("string");
      expect(body).not.toHaveProperty("detail");
    } finally {
      await app.close();
    }
  });

  it("serializes AppError conflicts as 409 with details.current_revision_id", async () => {
    const app = await buildQuietApp();

    try {
      app.get("/test/conflict", async () => {
        throw new AppError({
          statusCode: 409,
          code: "REVISION_CONFLICT",
          message: "Document was updated by another writer.",
          details: { current_revision_id: "rev-0002" },
        });
      });

      const response = await app.inject({ method: "GET", url: "/test/conflict" });

      expect(response.statusCode).toBe(409);
      expect(response.json()).toEqual({
        error: {
          code: "REVISION_CONFLICT",
          message: "Document was updated by another writer.",
          details: { current_revision_id: "rev-0002" },
        },
      });
    } finally {
      await app.close();
    }
  });

  it("hides unhandled failures behind an opaque 500 with an error_id", async () => {
    const app = await buildQuietApp();

    try {
      app.get("/test/boom", async () => {
        throw new Error("secret-token-leaked-in-stack");
      });

      const response = await app.inject({ method: "GET", url: "/test/boom" });

      expect(response.statusCode).toBe(500);
      const body = response.json();
      expect(body.error.code).toBe("INTERNAL_ERROR");
      expect(typeof body.error.details.error_id).toBe("string");
      expect(body.error.details.error_id.length).toBeGreaterThan(0);
      expect(response.body).not.toContain("secret-token-leaked-in-stack");
      expect(response.body).not.toContain("at /");
    } finally {
      await app.close();
    }
  });

  it("ties the opaque error_id to the request correlation id", async () => {
    const app = await buildQuietApp();

    try {
      app.get("/test/boom", async () => {
        throw new Error("boom");
      });

      const response = await app.inject({
        method: "GET",
        url: "/test/boom",
        headers: { "x-request-id": "corr-263" },
      });

      expect(response.statusCode).toBe(500);
      expect(response.json().error.details.error_id).toBe("corr-263");
      expect(response.headers["x-request-id"]).toBe("corr-263");
    } finally {
      await app.close();
    }
  });

  it("wraps unknown API routes in the envelope", async () => {
    const app = await buildQuietApp();

    try {
      const response = await app.inject({ method: "GET", url: "/api/test/nowhere" });

      expect(response.statusCode).toBe(404);
      const body = response.json();
      expect(body.error.code).toBe("NOT_FOUND");
      expect(body).not.toHaveProperty("detail");
    } finally {
      await app.close();
    }
  });

  it("wraps malformed JSON bodies without leaking parser internals", async () => {
    const app = await buildQuietApp();

    try {
      app.post("/test/validated", { schema: { body: titleBodySchema } }, async () => ({
        ok: true,
      }));

      const response = await app.inject({
        method: "POST",
        url: "/test/validated",
        headers: { "content-type": "application/json" },
        payload: "{not-json",
      });

      expect([400, 422]).toContain(response.statusCode);
      const body = response.json();
      expect(body.error.code).toBeTypeOf("string");
      expect(body.error).not.toHaveProperty("detail");
    } finally {
      await app.close();
    }
  });
});
