import Fastify, { type FastifyInstance } from "fastify";
import { afterEach, describe, expect, it } from "vitest";

import { AppError, registerErrorEnvelope } from "../../src/platform/http/error_envelope.js";

let instance: FastifyInstance | undefined;

afterEach(async () => {
  await instance?.close();
  instance = undefined;
});

function app(): FastifyInstance {
  instance = Fastify({ logger: false });
  registerErrorEnvelope(instance);
  return instance;
}

interface Envelope {
  error: { code: string; message: string; details?: Record<string, unknown> };
}

describe("registerErrorEnvelope", () => {
  it("derives the status from the catalog and forwards details", async () => {
    const server = app();
    server.get("/invalid", async () => {
      throw new AppError("INVALID_OPERATION", {
        message: "The volume is already at that position.",
        details: { volumeId: "vol-1" },
      });
    });

    const response = await server.inject({ method: "GET", url: "/invalid" });
    expect(response.statusCode).toBe(422);
    expect(response.json<Envelope>().error).toEqual({
      code: "INVALID_OPERATION",
      message: "The volume is already at that position.",
      details: { volumeId: "vol-1" },
    });
  });

  it("falls back to the catalog sentence when the throw site supplies none", async () => {
    const server = app();
    server.get("/unauthorized", async () => {
      throw new AppError("UNAUTHORIZED");
    });

    const response = await server.inject({ method: "GET", url: "/unauthorized" });
    expect(response.statusCode).toBe(401);
    expect(response.json<Envelope>().error).toEqual({
      code: "UNAUTHORIZED",
      message: "Owner session required.",
    });
  });

  it("sets Retry-After on the statuses the retry route uses", async () => {
    const server = app();
    server.get("/rate-limited", async () => {
      throw AppError.afterDelay("RATE_LIMIT_EXCEEDED", 30);
    });
    server.get("/keyed-retry", async () => {
      throw AppError.afterDelay("OPERATION_IN_FLIGHT", 5, {
        message: "An import is already running.",
      });
    });

    const limited = await server.inject({ method: "GET", url: "/rate-limited" });
    expect(limited.statusCode).toBe(429);
    expect(limited.headers["retry-after"]).toBe("30");
    expect(limited.json<Envelope>().error.code).toBe("RATE_LIMIT_EXCEEDED");

    const keyed = await server.inject({ method: "GET", url: "/keyed-retry" });
    expect(keyed.statusCode).toBe(409);
    expect(keyed.headers["retry-after"]).toBe("5");
    expect(keyed.json<Envelope>().error.message).toBe("An import is already running.");
  });

  it("renders a schema failure as VALIDATION_ERROR with per-field details", async () => {
    const server = app();
    server.get("/validated", async () => {
      const error = new Error("body/title must NOT have fewer than 1 characters") as Error & {
        validation: unknown;
      };
      error.validation = [
        {
          instancePath: "/title",
          keyword: "minLength",
          message: "must NOT have fewer than 1 characters",
        },
        {},
      ];
      throw error;
    });

    const response = await server.inject({ method: "GET", url: "/validated" });
    expect(response.statusCode).toBe(422);
    const envelope = response.json<Envelope>();
    expect(envelope.error.code).toBe("VALIDATION_ERROR");
    expect(envelope.error.message).toBe("Request validation failed.");
    expect(envelope.error.details).toEqual({
      errors: [
        {
          field: "title",
          message: "must NOT have fewer than 1 characters",
          type: "minLength",
        },
        { field: "(root)", message: "value is invalid", type: "invalid" },
      ],
    });
  });

  it("forwards Fastify transport errors verbatim", async () => {
    const server = app();
    server.get("/too-large", async () => {
      const error = new Error("Request body is too large") as Error & {
        statusCode: number;
        code: string;
      };
      error.statusCode = 413;
      error.code = "FST_ERR_CTP_BODY_TOO_LARGE";
      throw error;
    });

    const response = await server.inject({ method: "GET", url: "/too-large" });
    expect(response.statusCode).toBe(413);
    expect(response.json<Envelope>().error).toEqual({
      code: "FST_ERR_CTP_BODY_TOO_LARGE",
      message: "Request body is too large",
    });
  });

  it("buries an unknown failure behind INTERNAL_ERROR and an error id", async () => {
    const server = app();
    server.get("/boom", async () => {
      throw new Error("connection string leaked here");
    });

    const response = await server.inject({ method: "GET", url: "/boom" });
    expect(response.statusCode).toBe(500);
    const envelope = response.json<Envelope>();
    expect(envelope.error.code).toBe("INTERNAL_ERROR");
    expect(envelope.error.message).toBe("An internal error occurred.");
    expect(envelope.error.message).not.toContain("connection string");
    expect(typeof envelope.error.details?.error_id).toBe("string");
  });

  it("answers an unknown route with the method and path, not the default 404", async () => {
    const server = app();
    const response = await server.inject({ method: "GET", url: "/missing" });
    expect(response.statusCode).toBe(404);
    expect(response.json<Envelope>().error).toEqual({
      code: "NOT_FOUND",
      message: "Route GET /missing is not known to this API.",
    });
  });
});
