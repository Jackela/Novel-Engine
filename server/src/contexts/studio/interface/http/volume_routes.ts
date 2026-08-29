import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import type { JsonResponseSchema } from "./json_response_schema.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import { projectIdParams, volumeIdParams } from "./studio_request_schemas.js";
import {
  volumeCreateSchema,
  volumeListResponseSchema,
  volumeReorderSchema,
  volumeResponseSchema,
  volumeRetitleSchema,
} from "./volume_schemas.js";

/** The 409 envelope when a title collides with an existing project volume. */
export const volumeConflictSchema: JsonResponseSchema = {
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
export const volumeRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (fastify, options) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.get(
    "/api/projects/:projectId/volumes",
    {
      preHandler: [guard],
      schema: { params: projectIdParams, response: { 200: volumeListResponseSchema } },
    },
    async (request) =>
      withStudioErrors(() => ({
        volumes: requireServices(options).volumes.listVolumes(
          requirePrincipal(request),
          request.params.projectId,
        ),
      })),
  );

  app.post(
    "/api/projects/:projectId/volumes",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        body: volumeCreateSchema,
        response: CREATE_RESPONSES,
      },
    },
    async (request, reply) => {
      const payload = withStudioErrors(() =>
        requireServices(options).volumes.newVolume(
          requirePrincipal(request),
          request.params.projectId,
          {
            title: request.body.title,
          },
        ),
      );
      reply.status(201);
      return payload;
    },
  );

  app.put(
    "/api/projects/:projectId/volumes/reorder",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        body: volumeReorderSchema,
        response: { 200: volumeListResponseSchema },
      },
    },
    async (request) =>
      withStudioErrors(() => ({
        volumes: requireServices(options).volumes.applyVolumeOrder(
          requirePrincipal(request),
          request.params.projectId,
          request.body.volume_ids,
        ),
      })),
  );

  app.put(
    "/api/projects/:projectId/volumes/:volumeId",
    {
      preHandler: [guard],
      schema: {
        params: volumeIdParams,
        body: volumeRetitleSchema,
        response: RETITLE_RESPONSES,
      },
    },
    async (request) =>
      withStudioErrors(() =>
        requireServices(options).volumes.retitleVolume(
          requirePrincipal(request),
          request.params.projectId,
          request.params.volumeId,
          {
            title: request.body.title,
          },
        ),
      ),
  );

  app.delete(
    "/api/projects/:projectId/volumes/:volumeId",
    {
      preHandler: [guard],
      schema: { params: volumeIdParams, response: { 204: { type: "null" } } },
    },
    async (request, reply) => {
      withStudioErrors(() =>
        requireServices(options).volumes.removeVolume(
          requirePrincipal(request),
          request.params.projectId,
          request.params.volumeId,
        ),
      );
      reply.status(204);
      return null;
    },
  );
};
