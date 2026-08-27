import type { FastifyPluginAsync } from "fastify";
import type { Principal } from "../../../../shared/application/ports/auth.js";
import { principalGuard } from "../../../../shared/interface/http/auth_guard.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import {
  volumeCreateSchema,
  volumeListResponseSchema,
  volumeReorderSchema,
  volumeResponseSchema,
  volumeRetitleSchema,
} from "./volume_schemas.js";

/** The 409 envelope when a title collides with an existing project volume. */
export const volumeConflictSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: ["VOLUME_CONFLICT"] },
        message: { type: "string" },
      },
      required: ["code", "message"],
    },
  },
  required: ["error"],
} as const;

const CREATE_RESPONSES = { 201: volumeResponseSchema, 409: volumeConflictSchema } as const;
const RETITLE_RESPONSES = { 200: volumeResponseSchema, 409: volumeConflictSchema } as const;

/**
 * Volume surface on the project path (ADR-0005): list in reading order,
 * create with tail placement, retitle, reorder the whole set, and delete
 * with the at-least-one-volume guard.
 */
export const volumeRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (app, options) => {
  const guard = principalGuard(options.authService);
  const principal = (request: { principal?: Principal }) => request.principal as Principal;

  app.get(
    "/api/projects/:projectId/volumes",
    { preHandler: [guard], schema: { response: { 200: volumeListResponseSchema } } },
    async (request) => {
      const { projectId } = request.params as { projectId: string };
      return withStudioErrors(() => ({
        volumes: requireServices(options).volumes.listVolumes(principal(request), projectId),
      }));
    },
  );

  app.post(
    "/api/projects/:projectId/volumes",
    {
      preHandler: [guard],
      schema: { body: volumeCreateSchema, response: CREATE_RESPONSES },
    },
    async (request, reply) => {
      const { projectId } = request.params as { projectId: string };
      const body = request.body as { title: string };
      const payload = withStudioErrors(() =>
        requireServices(options).volumes.newVolume(principal(request), projectId, {
          title: body.title,
        }),
      );
      reply.status(201);
      return payload;
    },
  );

  app.put(
    "/api/projects/:projectId/volumes/reorder",
    {
      preHandler: [guard],
      schema: { body: volumeReorderSchema, response: { 200: volumeListResponseSchema } },
    },
    async (request) => {
      const { projectId } = request.params as { projectId: string };
      const body = request.body as { volume_ids: string[] };
      return withStudioErrors(() => ({
        volumes: requireServices(options).volumes.applyVolumeOrder(
          principal(request),
          projectId,
          body.volume_ids,
        ),
      }));
    },
  );

  app.put(
    "/api/projects/:projectId/volumes/:volumeId",
    { preHandler: [guard], schema: { body: volumeRetitleSchema, response: RETITLE_RESPONSES } },
    async (request) => {
      const { projectId, volumeId } = request.params as { projectId: string; volumeId: string };
      const body = request.body as { title: string };
      return withStudioErrors(() =>
        requireServices(options).volumes.retitleVolume(principal(request), projectId, volumeId, {
          title: body.title,
        }),
      );
    },
  );

  app.delete(
    "/api/projects/:projectId/volumes/:volumeId",
    { preHandler: [guard], schema: { response: { 204: { type: "null" } } } },
    async (request, reply) => {
      const { projectId, volumeId } = request.params as { projectId: string; volumeId: string };
      withStudioErrors(() =>
        requireServices(options).volumes.removeVolume(principal(request), projectId, volumeId),
      );
      reply.status(204);
      return null;
    },
  );
};
