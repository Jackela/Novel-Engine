import type { FastifyPluginAsync } from "fastify";
import type { AuthService } from "../../../../shared/application/auth_service.js";
import type { Principal } from "../../../../shared/application/ports/auth.js";
import { principalGuard } from "../../../../shared/interface/http/auth_guard.js";
import { AppError } from "../../../../shared/interface/http/error_envelope.js";
import type { StudioServices } from "../../application/studio_services.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import {
  projectCreateSchema,
  projectDetailResponseSchema,
  projectResponseSchema,
} from "./studio_schemas.js";

export interface StudioRoutesOptions {
  /** Absent while the app is database-free; studio surfaces then answer 503. */
  authService?: AuthService | undefined;
  services?: StudioServices | undefined;
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
export const projectRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (app, options) => {
  const guard = principalGuard(options.authService);

  app.get(
    "/api/projects",
    { preHandler: [guard], schema: { response: { 200: projectListResponseSchema } } },
    async (request) =>
      withStudioErrors(() => ({
        projects: requireServices(options).projects.listProjects(request.principal as Principal),
      })),
  );

  app.post(
    "/api/projects",
    {
      preHandler: [guard],
      schema: { body: projectCreateSchema, response: { 201: projectDetailResponseSchema } },
    },
    async (request, reply) => {
      const body = request.body as { title: string; description?: string };
      const payload = withStudioErrors(() =>
        requireServices(options).projects.newProject(request.principal as Principal, {
          title: body.title,
          description: body.description,
        }),
      );
      reply.status(201);
      return payload;
    },
  );

  app.get(
    "/api/projects/:projectId",
    { preHandler: [guard], schema: { response: { 200: projectDetailResponseSchema } } },
    async (request) => {
      const { projectId } = request.params as { projectId: string };
      return withStudioErrors(
        () =>
          requireServices(options).projects.projectDetail(request.principal as Principal, projectId)
            .payload,
      );
    },
  );

  app.delete(
    "/api/projects/:projectId",
    { preHandler: [guard], schema: { response: { 204: { type: "null" } } } },
    async (request, reply) => {
      const { projectId } = request.params as { projectId: string };
      withStudioErrors(() =>
        requireServices(options).projects.removeProject(request.principal as Principal, projectId),
      );
      reply.status(204);
      return null;
    },
  );
};
