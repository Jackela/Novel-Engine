import type { FastifyPluginAsync } from "fastify";
import type { AuthService } from "../../../../shared/application/auth_service.js";
import type { Principal } from "../../../../shared/application/ports/auth.js";
import { InvalidOperationError } from "../../../../shared/domain/exceptions.js";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import {
  AppError,
  ERROR_CODES,
  errorEnvelopeResponse,
} from "../../../../shared/interface/http/error_envelope.js";
import type { AiOperations } from "../../application/ports/ai_operations.js";

interface Options {
  authService?: AuthService | undefined;
  operations: AiOperations;
  authorize(principal: Principal, projectId: string): void;
}
const uuid = { type: "string", format: "uuid" } as const;
const params = {
  type: "object",
  required: ["projectId", "operationId"],
  properties: { projectId: uuid, operationId: uuid },
  additionalProperties: false,
} as const;
/** Owner-scoped ephemeral SSE channels and one-shot permission decisions. */
export const aiOperationRoutes: FastifyPluginAsync<Options> = async (app, options) => {
  const guard = principalGuard(options.authService);
  const scope = (principal: Principal, projectId: string, operationId: string) => {
    if (principal.ownerId === null || principal.kind !== "owner")
      throw new AppError({
        statusCode: 403,
        code: ERROR_CODES.FORBIDDEN,
        message: "Owner session required.",
      });
    options.authorize(principal, projectId);
    return { ownerId: principal.ownerId, projectId, operationId };
  };
  app.get<{ Params: { projectId: string; operationId: string } }>(
    "/api/projects/:projectId/ai-operations/:operationId/events",
    {
      preValidation: [guard],
      schema: {
        params,
        response: {
          200: {
            description: "AI operation events (ready/tool/permission/completed/error)",
            content: { "text/event-stream": { schema: { type: "string" } } },
          },
          401: errorEnvelopeResponse,
          403: errorEnvelopeResponse,
          404: errorEnvelopeResponse,
          422: errorEnvelopeResponse,
        },
      },
    },
    async (request, reply) => {
      const identity = scope(
        requirePrincipal(request),
        request.params.projectId,
        request.params.operationId,
      );
      let heartbeat: ReturnType<typeof setInterval> | undefined;
      try {
        const channel = options.operations.register(
          identity,
          (event) => {
            // A closed observer is an expected transport state; terminal
            // landing still owns cleanup and must not become a second failure.
            if (reply.raw.destroyed || reply.raw.writableEnded) return;
            if (!reply.sent) {
              reply.hijack();
              reply.raw.writeHead(200, {
                "content-type": "text/event-stream; charset=utf-8",
                "cache-control": "no-cache",
                "x-accel-buffering": "no",
                connection: "keep-alive",
              });
            }
            if (!reply.raw.write(`data: ${JSON.stringify(event)}\n\n`))
              throw new AppError({
                statusCode: 503,
                code: ERROR_CODES.SERVICE_UNAVAILABLE,
                message: "AI interaction client is not reading events.",
              });
          },
          () => {
            if (heartbeat !== undefined) clearInterval(heartbeat);
            reply.raw.end();
          },
        );
        heartbeat = setInterval(() => {
          if (!reply.raw.destroyed) reply.raw.write(": heartbeat\n\n");
        }, 15_000);
        heartbeat.unref();
        reply.raw.once("close", () => {
          if (heartbeat !== undefined) clearInterval(heartbeat);
          channel.close();
        });
      } catch (error) {
        if (error instanceof InvalidOperationError)
          throw new AppError({
            statusCode: 422,
            code: ERROR_CODES.VALIDATION_ERROR,
            message: error.message,
          });
        throw error;
      }
    },
  );
  app.post<{
    Params: { projectId: string; operationId: string; permissionId: string };
    Body: { option_id: string };
  }>(
    "/api/projects/:projectId/ai-operations/:operationId/permissions/:permissionId",
    {
      preValidation: [guard],
      schema: {
        params: {
          ...params,
          required: [...params.required, "permissionId"],
          properties: { ...params.properties, permissionId: uuid },
        },
        body: {
          type: "object",
          required: ["option_id"],
          properties: { option_id: { type: "string", minLength: 1, maxLength: 200 } },
          additionalProperties: false,
        },
        response: {
          204: { type: "null" },
          401: errorEnvelopeResponse,
          403: errorEnvelopeResponse,
          404: errorEnvelopeResponse,
          422: errorEnvelopeResponse,
        },
      },
    },
    async (request, reply) => {
      const identity = scope(
        requirePrincipal(request),
        request.params.projectId,
        request.params.operationId,
      );
      try {
        options.operations.respond(identity, request.params.permissionId, request.body.option_id);
      } catch (error) {
        if (error instanceof InvalidOperationError)
          throw new AppError({
            statusCode: 422,
            code: ERROR_CODES.VALIDATION_ERROR,
            message: error.message,
          });
        throw error;
      }
      reply.status(204).send();
    },
  );
};
