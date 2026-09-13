import { connect } from "node:net";

import type { FastifyInstance } from "fastify";
import { describe, expect, it } from "vitest";

import { buildApp } from "../../../src/apps/api/app.js";

const SHORT_RECEIPT_POLICY = {
  headersTimeout: 40,
  requestTimeout: 80,
  connectionsCheckingInterval: 10,
} as const;

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function rawRequest(app: FastifyInstance, fragment: string): Promise<string> {
  const address = app.server.address();
  if (address === null || typeof address === "string") {
    throw new Error("Expected the test app to listen on a TCP port.");
  }

  return new Promise((resolve, reject) => {
    let response = "";
    let socketError: Error | undefined;
    const socket = connect({ host: "127.0.0.1", port: address.port }, () => {
      socket.write(fragment);
    });
    const timeout = setTimeout(() => {
      socket.destroy();
      reject(new Error("Timed out waiting for the HTTP server to close the connection."));
    }, 2_000);

    socket.on("data", (chunk: Buffer) => {
      response += chunk.toString("utf8");
    });
    socket.once("error", (error) => {
      socketError = error;
    });
    socket.once("close", () => {
      clearTimeout(timeout);
      if (response === "" && socketError !== undefined) {
        reject(socketError);
        return;
      }
      resolve(response);
    });
  });
}

describe("inbound HTTP request lifetime", () => {
  it("uses finite receipt deadlines without handler or idle-connection deadlines", async () => {
    const app = await buildApp({ logger: false });
    try {
      const server = app.server as typeof app.server & { connectionsCheckingInterval: number };
      const initialConfig = app.initialConfig as typeof app.initialConfig & {
        handlerTimeout: number;
      };
      expect(server.headersTimeout).toBe(60_000);
      expect(server.requestTimeout).toBe(120_000);
      expect(server.connectionsCheckingInterval).toBeLessThanOrEqual(5_000);
      expect(server.timeout).toBe(0);
      expect(initialConfig.handlerTimeout).toBe(0);
      expect(app.initialConfig.bodyLimit).toBe(1_048_576);
    } finally {
      await app.close();
    }
  });

  it("applies injectable receipt thresholds before the listener starts", async () => {
    const app = await buildApp({ logger: false, httpServerPolicy: SHORT_RECEIPT_POLICY });
    try {
      const server = app.server as typeof app.server & { connectionsCheckingInterval: number };
      expect(server.headersTimeout).toBe(40);
      expect(server.requestTimeout).toBe(80);
      expect(server.connectionsCheckingInterval).toBe(10);
    } finally {
      await app.close();
    }
  });

  it("expires partial headers before Fastify hooks or handlers run", async () => {
    const app = await buildApp({ logger: false, httpServerPolicy: SHORT_RECEIPT_POLICY });
    let enteredFastify = false;
    app.addHook("onRequest", async () => {
      enteredFastify = true;
    });
    try {
      await app.listen({ host: "127.0.0.1", port: 0 });
      const response = await rawRequest(
        app,
        "GET /health/live HTTP/1.1\r\nHost: 127.0.0.1\r\nX-Pending:",
      );

      expect(response).toMatch(/^HTTP\/1\.1 408 Request Timeout\r\n/);
      expect(enteredFastify).toBe(false);
    } finally {
      await app.close();
    }
  });

  it("expires a partial declared body before validation, authorization, or handler work", async () => {
    const app = await buildApp({ logger: false, httpServerPolicy: SHORT_RECEIPT_POLICY });
    const phases: string[] = [];
    app.addHook("onRequest", async () => {
      phases.push("onRequest");
    });
    app.addHook("preParsing", async (_request, _reply, payload) => {
      phases.push("preParsing");
      return payload;
    });
    app.addHook("preValidation", async () => {
      phases.push("preValidation");
    });
    app.addHook("preHandler", async () => {
      phases.push("preHandler");
    });
    app.post(
      "/test/slow-body",
      {
        schema: {
          body: {
            type: "object",
            additionalProperties: false,
            properties: { title: { type: "string" } },
            required: ["title"],
          },
        },
      },
      async () => {
        phases.push("handler");
        return { ok: true };
      },
    );
    try {
      await app.listen({ host: "127.0.0.1", port: 0 });
      const response = await rawRequest(
        app,
        [
          "POST /test/slow-body HTTP/1.1",
          "Host: 127.0.0.1",
          "Content-Type: application/json",
          "Content-Length: 32",
          "Connection: close",
          "",
          "{",
        ].join("\r\n"),
      );

      expect(response).toMatch(/^HTTP\/1\.1 408 Request Timeout\r\n/);
      expect(phases).toEqual(["onRequest", "preParsing"]);
    } finally {
      await app.close();
    }
  });

  it("rejects an advertised body on a bodyless route before its handler runs", async () => {
    const app = await buildApp({ logger: false, httpServerPolicy: SHORT_RECEIPT_POLICY });
    let handlerRuns = 0;
    app.get("/test/bodyless", async () => {
      handlerRuns += 1;
      return { ok: true };
    });
    try {
      await app.listen({ host: "127.0.0.1", port: 0 });
      for (const framingHeader of ["Content-Length: 32", "Transfer-Encoding: chunked"]) {
        const response = await rawRequest(
          app,
          [
            "GET /test/bodyless HTTP/1.1",
            "Host: 127.0.0.1",
            framingHeader,
            "X-Request-Id: inbound-bodyless-test",
            "",
            "",
          ].join("\r\n"),
        );
        const [, body = ""] = response.split("\r\n\r\n", 2);

        expect(response).toMatch(/^HTTP\/1\.1 422 Unprocessable Entity\r\n/);
        expect(response.toLowerCase()).toContain("connection: close");
        expect(response.toLowerCase()).toContain("x-request-id: inbound-bodyless-test");
        expect(JSON.parse(body)).toEqual({
          error: {
            code: "VALIDATION_ERROR",
            message: "Request validation failed.",
            details: {
              errors: [
                {
                  field: "body",
                  type: "undeclared_body",
                  message: "Request body is not allowed for this route.",
                },
              ],
            },
          },
        });
      }
      expect(handlerRuns).toBe(0);
    } finally {
      await app.close();
    }
  });

  it("does not apply the receipt deadline to a fully received long handler", async () => {
    const app = await buildApp({ logger: false, httpServerPolicy: SHORT_RECEIPT_POLICY });
    app.get("/test/slow-handler", async () => {
      await delay(160);
      return { completed: true };
    });
    try {
      const address = await app.listen({ host: "127.0.0.1", port: 0 });
      const response = await fetch(`${address}/test/slow-handler`);

      expect(response.status).toBe(200);
      expect(await response.json()).toEqual({ completed: true });
    } finally {
      await app.close();
    }
  });

  it("does not apply the receipt deadline to later SSE frames", async () => {
    const app = await buildApp({ logger: false, httpServerPolicy: SHORT_RECEIPT_POLICY });
    app.get("/test/slow-stream", async (_request, reply) => {
      reply.hijack();
      reply.raw.writeHead(200, {
        "content-type": "text/event-stream; charset=utf-8",
        "cache-control": "no-cache",
      });
      await delay(120);
      reply.raw.write("data: first\n\n");
      await delay(120);
      reply.raw.end("data: second\n\n");
    });
    try {
      const address = await app.listen({ host: "127.0.0.1", port: 0 });
      const response = await fetch(`${address}/test/slow-stream`);

      expect(response.status).toBe(200);
      expect(await response.text()).toBe("data: first\n\ndata: second\n\n");
    } finally {
      await app.close();
    }
  });

  it("keeps the one MiB body limit in force", async () => {
    const app = await buildApp({ logger: false });
    let handlerRuns = 0;
    app.post(
      "/test/body-limit",
      {
        schema: {
          body: {
            type: "object",
            properties: { content: { type: "string" } },
            required: ["content"],
          },
        },
      },
      async () => {
        handlerRuns += 1;
        return { ok: true };
      },
    );
    try {
      const response = await app.inject({
        method: "POST",
        url: "/test/body-limit",
        payload: { content: "x".repeat(1_048_576) },
      });

      expect(response.statusCode).toBe(413);
      expect(response.json().error.code).toBe("FST_ERR_CTP_BODY_TOO_LARGE");
      expect(handlerRuns).toBe(0);
    } finally {
      await app.close();
    }
  });
});
