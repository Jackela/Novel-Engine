import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { authedReadResponses, authedWriteResponses } from "./route_responses.js";
import { structureCapacity422ResponseSchema } from "./structure_capacity_schemas.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import {
  documentCreateSchema,
  documentIdParams,
  documentSaveSchema,
  projectIdParams,
} from "./studio_request_schemas.js";
import {
  documentConflictSchema,
  documentResponseSchema,
  revisionConflictSchema,
  snapshotConflictSchema,
} from "./studio_schemas.js";
import { documentPlaceSchema } from "./volume_schemas.js";

/**
 * Document surface: creation with the identity uniqueness contract,
 * conflict-checked saves, volume placement, and deletion.
 */
export const documentCrudRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (
  fastify,
  options,
) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.post(
    "/api/projects/:projectId/documents",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        body: documentCreateSchema,
        response: authedWriteResponses({
          201: documentResponseSchema,
          // Document, volume-chapter, and outline-beat budgets gate the create (#461).
          422: structureCapacity422ResponseSchema,
          409: documentConflictSchema,
        }),
      },
    },
    async (request, reply) => {
      const payload = withStudioErrors(() =>
        requireServices(options).documents.newDocument(
          requirePrincipal(request),
          request.params.projectId,
          {
            kind: request.body.kind,
            title: request.body.title,
            contentMarkdown: request.body.content_markdown,
            position: request.body.position,
            metadata: request.body.metadata,
          },
        ),
      );
      reply.status(201);
      return payload;
    },
  );

  app.get(
    "/api/projects/:projectId/documents/:documentId",
    {
      // The principal is established before any scoped Studio read.
      preValidation: [guard],
      schema: {
        params: documentIdParams,
        response: authedReadResponses({ 200: documentResponseSchema }),
      },
    },
    async (request) =>
      withStudioErrors(() =>
        requireServices(options).documents.currentDocument(
          requirePrincipal(request),
          request.params.projectId,
          request.params.documentId,
        ),
      ),
  );

  app.put(
    "/api/projects/:projectId/documents/:documentId",
    {
      preHandler: [guard],
      schema: {
        params: documentIdParams,
        body: documentSaveSchema,
        response: authedWriteResponses({
          200: documentResponseSchema,
          // Metadata bytes and outline beats refuse here permanently (#461).
          422: structureCapacity422ResponseSchema,
          409: revisionConflictSchema,
        }),
      },
    },
    async (request) =>
      withStudioErrors(() =>
        requireServices(options).documents.storeDocument(
          requirePrincipal(request),
          request.params.projectId,
          request.params.documentId,
          {
            contentMarkdown: request.body.content_markdown,
            baseRevisionId: request.body.base_revision_id,
            title: request.body.title,
            metadata: request.body.metadata,
          },
        ),
      ),
  );

  app.put(
    "/api/projects/:projectId/documents/:documentId/volume",
    {
      preHandler: [guard],
      schema: {
        params: documentIdParams,
        body: documentPlaceSchema,
        response: authedWriteResponses({
          200: documentResponseSchema,
          // Placement into a full volume refuses permanently (#461).
          422: structureCapacity422ResponseSchema,
        }),
      },
    },
    async (request) =>
      withStudioErrors(() =>
        requireServices(options).volumes.placeChapter(
          requirePrincipal(request),
          request.params.projectId,
          request.params.documentId,
          { volumeId: request.body.volume_id },
        ),
      ),
  );

  app.delete(
    "/api/projects/:projectId/documents/:documentId",
    {
      preHandler: [guard],
      schema: {
        params: documentIdParams,
        response: authedWriteResponses({
          204: { type: "null" },
          409: snapshotConflictSchema,
        }),
      },
    },
    async (request, reply) => {
      withStudioErrors(() =>
        requireServices(options).documents.removeDocument(
          requirePrincipal(request),
          request.params.projectId,
          request.params.documentId,
        ),
      );
      reply.status(204);
      return null;
    },
  );
};
