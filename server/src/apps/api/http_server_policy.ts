import type { FastifyInstance, FastifyRequest } from "fastify";

import {
  AppError,
  ERROR_CODES,
  ERROR_HTTP_STATUS,
} from "../../shared/interface/http/error_envelope.js";

/** Finite limits that cover request receipt, not route execution. */
export interface HttpServerPolicy {
  headersTimeout: number;
  requestTimeout: number;
  connectionsCheckingInterval: number;
}

export const DEFAULT_HTTP_SERVER_POLICY: Readonly<HttpServerPolicy> = Object.freeze({
  headersTimeout: 60_000,
  requestTimeout: 120_000,
  connectionsCheckingInterval: 5_000,
});

/**
 * Translate the product's receipt boundary into Fastify and Node HTTP options.
 * Handler and socket-idle timeouts stay disabled because they cover valid work
 * after the request has already been received.
 */
export function fastifyOptionsForHttpServerPolicy(policy: HttpServerPolicy) {
  return {
    http: {
      headersTimeout: policy.headersTimeout,
      connectionsCheckingInterval: policy.connectionsCheckingInterval,
    },
    requestTimeout: policy.requestTimeout,
    connectionTimeout: 0,
    handlerTimeout: 0,
    bodyLimit: 1_048_576,
  } as const;
}

const UNDECLARED_BODY_MESSAGE = "Request body is not allowed for this route.";

function advertisesNonEmptyBody(request: FastifyRequest): boolean {
  if (request.headers["transfer-encoding"] !== undefined) {
    return true;
  }
  const contentLength = request.headers["content-length"];
  return contentLength !== undefined && Number(contentLength) > 0;
}

function routeAcceptsBody(request: FastifyRequest): boolean {
  return request.routeOptions.schema?.body !== undefined;
}

/** Reject body framing that the matched route has no contract to parse. */
export function registerUndeclaredRequestBodyPolicy(app: FastifyInstance): void {
  app.addHook("onRequest", async (request, reply) => {
    if (routeAcceptsBody(request) || !advertisesNonEmptyBody(request)) {
      return;
    }

    reply.header("connection", "close");
    throw new AppError({
      statusCode: ERROR_HTTP_STATUS[ERROR_CODES.VALIDATION_ERROR],
      code: ERROR_CODES.VALIDATION_ERROR,
      message: "Request validation failed.",
      details: {
        errors: [
          {
            field: "body",
            type: "undeclared_body",
            message: UNDECLARED_BODY_MESSAGE,
          },
        ],
      },
    });
  });
}
