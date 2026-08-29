import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import type { AuthService } from "../../../../shared/application/auth_service.js";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import { AppError } from "../../../../shared/interface/http/error_envelope.js";
import type { StudioServices } from "../../application/studio_services.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import {
  projectCreateSchema,
  projectIdParams,
  projectMatchQuerySchema,
} from "./studio_request_schemas.js";
import {
  matchListResponseSchema,
  projectDetailResponseSchema,
  projectResponseSchema,
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
      code: "SERVICE_UNAVAILABLE",
      message: "The persistence layer is not configured.",
    });
  }
  return options.services;
}

const projectListResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: { projects: { type: "array", items: projectResponseSchema } },
  required: ["projects"],
} as const;

/** Project surface: create with seeding, list (updated_at DESC), detail, delete. */
export const projectRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (fastify, options) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.get(
    "/api/projects",
    { preHandler: [guard], schema: { response: { 200: projectListResponseSchema } } },
    async (request) =>
      withStudioErrors(() => ({
        projects: requireServices(options).projects.listProjects(requirePrincipal(request)),
      })),
  );

  app.post(
    "/api/projects",
    {
      preHandler: [guard],
      schema: { body: projectCreateSchema, response: { 201: projectDetailResponseSchema } },
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
      schema: { params: projectIdParams, response: { 200: projectDetailResponseSchema } },
    },
    async (request) =>
      withStudioErrors(
        () =>
          requireServices(options).projects.projectDetail(
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
        response: { 200: matchListResponseSchema },
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
      schema: { params: projectIdParams, response: { 204: { type: "null" } } },
    },
    async (request, reply) => {
      withStudioErrors(() =>
        requireServices(options).projects.removeProject(
          requirePrincipal(request),
          request.params.projectId,
        ),
      );
      reply.status(204);
      return null;
    },
  );
};
