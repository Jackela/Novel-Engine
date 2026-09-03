import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import type { AuthService } from "../../../../shared/application/auth_service.js";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import {
  AppError,
  ERROR_CODES,
  errorEnvelopeResponse,
} from "../../../../shared/interface/http/error_envelope.js";
import { projectUpdateCommand } from "../../application/project_service.js";
import type { StudioServices } from "../../application/studio_services.js";
import { projectUpdateRawKeyGuard } from "./project_update_raw_keys.js";
import { withAsyncStudioErrors, withStudioErrors } from "./studio_error_mapping.js";
import {
  projectCreateSchema,
  projectIdParams,
  projectMatchQuerySchema,
  projectUpdateSchema,
} from "./studio_request_schemas.js";
import {
  matchListResponseSchema,
  operationInFlightSchema,
  projectListResponseSchema,
  projectResponseSchema,
  projectShellResponseSchema,
} from "./studio_schemas.js";

export interface StudioRoutesOptions {
  /** Absent while the app is database-free; studio surfaces then answer 503. */
  authService?: AuthService | undefined;
  services?: StudioServices | undefined;
  /** Data directory owning the confined data/imports web-import root. */
  dataDirectory?: string | undefined;
}

export function requireServices(options: StudioRoutesOptions): StudioServices {
  if (options.services === undefined) {
    throw new AppError({
      statusCode: 503,
      code: ERROR_CODES.SERVICE_UNAVAILABLE,
      message: "The persistence layer is not configured.",
    });
  }
  return options.services;
}

/** Project surface: create with seeding, list (updated_at DESC), detail, delete. */
export const projectRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (fastify, options) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.get(
    "/api/projects",
    {
      preHandler: [guard],
      schema: {
        response: {
          200: projectListResponseSchema,
          401: errorEnvelopeResponse,
          503: errorEnvelopeResponse,
        },
      },
    },
    async (request) =>
      withStudioErrors(() => ({
        projects: requireServices(options).projects.listProjects(requirePrincipal(request)),
      })),
  );

  app.patch(
    "/api/projects/:projectId",
    {
      preValidation: [guard, projectUpdateRawKeyGuard],
      schema: {
        params: projectIdParams,
        body: projectUpdateSchema,
        response: {
          200: projectResponseSchema,
          401: errorEnvelopeResponse,
          403: errorEnvelopeResponse,
          404: errorEnvelopeResponse,
          422: errorEnvelopeResponse,
          500: errorEnvelopeResponse,
          503: errorEnvelopeResponse,
        },
      },
    },
    async (request) =>
      withStudioErrors(() =>
        requireServices(options).projects.updateProject(
          requirePrincipal(request),
          request.params.projectId,
          projectUpdateCommand(request.body),
        ),
      ),
  );

  app.post(
    "/api/projects",
    {
      preHandler: [guard],
      schema: {
        body: projectCreateSchema,
        response: {
          201: projectShellResponseSchema,
          401: errorEnvelopeResponse,
          403: errorEnvelopeResponse,
          422: errorEnvelopeResponse,
          503: errorEnvelopeResponse,
        },
      },
    },
    async (request, reply) => {
      const payload = withStudioErrors(() =>
        requireServices(options).projects.newProject(requirePrincipal(request), {
          title: request.body.title,
          description: request.body.description,
        }),
      );
      reply.status(201);
      return payload;
    },
  );

  app.get(
    "/api/projects/:projectId",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        response: {
          200: projectShellResponseSchema,
          401: errorEnvelopeResponse,
          404: errorEnvelopeResponse,
          503: errorEnvelopeResponse,
        },
      },
    },
    async (request) =>
      withStudioErrors(
        () =>
          requireServices(options).projects.projectShell(
            requirePrincipal(request),
            request.params.projectId,
          ).payload,
      ),
  );

  app.get(
    "/api/projects/:projectId/search",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        querystring: projectMatchQuerySchema,
        response: {
          200: matchListResponseSchema,
          401: errorEnvelopeResponse,
          404: errorEnvelopeResponse,
          422: errorEnvelopeResponse,
          503: errorEnvelopeResponse,
        },
      },
    },
    async (request) =>
      withStudioErrors(() => ({
        results: requireServices(options).documents.queryProjectDocuments(
          requirePrincipal(request),
          request.params.projectId,
          request.query.q,
        ),
      })),
  );

  app.delete(
    "/api/projects/:projectId",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        response: {
          204: { type: "null" },
          401: errorEnvelopeResponse,
          403: errorEnvelopeResponse,
          404: errorEnvelopeResponse,
          409: operationInFlightSchema,
          503: errorEnvelopeResponse,
        },
      },
    },
    async (request, reply) => {
      const reportCleanupFailure = (failure: unknown): void => {
        request.log.error(
          { err: failure, errorId: request.id, project_artifact_cleanup_failed: true },
          "project artifact cleanup failed",
        );
      };
      await withAsyncStudioErrors(() =>
        requireServices(options).projects.removeProject(
          requirePrincipal(request),
          request.params.projectId,
          reportCleanupFailure,
        ),
      );
      reply.status(204);
      return null;
    },
  );
};
