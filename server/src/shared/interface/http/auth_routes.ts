import type { FastifyPluginAsync, FastifyReply, FastifyRequest } from "fastify";

import type { AuthService, IssuedSession } from "../../application/auth_service.js";
import type { Principal } from "../../application/ports/auth.js";
import type { RateLimiter } from "../../application/ports/rate_limit.js";
import { FIRST_CONTACT_PATHS, principalGuard } from "./auth_guard.js";
import { AppError } from "./error_envelope.js";
import { isSameOriginRequest } from "./origin_validation.js";
import {
  clearSessionCookies,
  issueSessionCookies,
  principalPayload,
  SESSION_COOKIE,
} from "./session_cookies.js";

export type ClientIdentityResolver = (request: {
  socket?: { remoteAddress?: string | undefined } | undefined;
  headers: Record<string, unknown>;
}) => string;

export interface AuthRoutesOptions {
  /** Absent while the app is database-free; auth surfaces then answer 503. */
  authService?: AuthService | undefined;
  limiter: RateLimiter;
  version: string;
  environment: string;
  corsOrigins: string[];
  resolveClientIdentity: ClientIdentityResolver;
}

const principalResponseSchema = {
  type: "object",
  properties: {
    session_id: { type: "string" },
    kind: { type: "string", enum: ["owner", "guest"] },
    owner_id: { type: "string", nullable: true },
    expires_at: { type: "string", nullable: true },
  },
  required: ["session_id", "kind", "owner_id", "expires_at"],
};

const credentialsBodySchema = {
  type: "object",
  properties: { username: { type: "string" }, password: { type: "string" } },
  required: ["username", "password"],
  additionalProperties: false,
};

function requireService(options: AuthRoutesOptions): AuthService {
  if (options.authService === undefined) {
    throw new AppError({
      statusCode: 503,
      code: "SERVICE_UNAVAILABLE",
      message: "The persistence layer is not configured.",
    });
  }
  return options.authService;
}

function respondWithSession(
  reply: FastifyReply,
  issued: IssuedSession,
  environment: string,
): ReturnType<typeof principalPayload> {
  issueSessionCookies(reply, issued.token, issued.csrfToken, issued.principal.kind, environment);
  return principalPayload(issued.principal);
}

/**
 * The auth and session spine: owner setup with same-origin validation and the
 * password policy, constant-time login, guest sandboxes, session probe and
 * logout, plus per-IP rate limiting of the unauthenticated endpoints.
 */
export const authRoutes: FastifyPluginAsync<AuthRoutesOptions> = async (app, options) => {
  const guard = principalGuard(options.authService);

  app.addHook("onRequest", async (request: FastifyRequest, reply: FastifyReply) => {
    if (request.method === "OPTIONS") {
      return;
    }
    const path = request.url.split("?")[0] ?? request.url;
    if (!FIRST_CONTACT_PATHS.has(path)) {
      return;
    }
    const key = `${options.resolveClientIdentity(request)}:${request.method}:${path}`;
    const decision = options.limiter.check(key);
    if (!decision.allowed) {
      reply.header("retry-after", String(decision.retryAfterSeconds));
      throw new AppError({
        statusCode: 429,
        code: "RATE_LIMIT_EXCEEDED",
        message: "Rate limit exceeded.",
        details: { retry_after_seconds: decision.retryAfterSeconds },
      });
    }
  });

  app.get(
    "/api/setup",
    {
      schema: {
        response: {
          200: {
            type: "object",
            properties: {
              owner_configured: { type: "boolean" },
              version: { type: "string" },
            },
            required: ["owner_configured", "version"],
          },
        },
      },
    },
    async () => ({
      owner_configured: requireService(options).ownerExists(),
      version: options.version,
    }),
  );

  app.post(
    "/api/setup",
    {
      schema: {
        body: credentialsBodySchema,
        response: {
          201: {
            type: "object",
            properties: { id: { type: "string" }, username: { type: "string" } },
            required: ["id", "username"],
          },
        },
      },
    },
    async (request, reply) => {
      const service = requireService(options);
      if (!isSameOriginRequest(request, options.corsOrigins)) {
        throw new AppError({
          statusCode: 403,
          code: "FORBIDDEN",
          message: "Setup requests must be same-origin.",
        });
      }
      const body = request.body as { username: string; password: string };
      const owner = await service.configureOwner(body.username, body.password);
      reply.status(201);
      return owner;
    },
  );

  app.post(
    "/api/session/login",
    { schema: { body: credentialsBodySchema, response: { 200: principalResponseSchema } } },
    async (request, reply) => {
      const body = request.body as { username: string; password: string };
      const issued = await requireService(options).createOwnerSession(body.username, body.password);
      return respondWithSession(reply, issued, options.environment);
    },
  );

  app.post(
    "/api/session/guest",
    { schema: { response: { 201: principalResponseSchema } } },
    async (_request, reply) => {
      const issued = requireService(options).createGuestSession();
      reply.status(201);
      return respondWithSession(reply, issued, options.environment);
    },
  );

  app.get(
    "/api/session",
    {
      preHandler: [guard],
      schema: { response: { 200: principalResponseSchema } },
    },
    // The guard has already resolved and attached the principal.
    async (request) => principalPayload(request.principal as Principal),
  );

  app.delete(
    "/api/session",
    {
      preHandler: [guard],
      schema: { response: { 204: { type: "null" } } },
    },
    async (request, reply) => {
      requireService(options).terminateSession(request.cookies[SESSION_COOKIE]);
      clearSessionCookies(reply);
      return reply.code(204).send();
    },
  );
};
