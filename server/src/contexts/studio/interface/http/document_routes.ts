import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import type { JsonResponseSchema } from "./json_response_schema.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import {
  documentCreateSchema,
  documentIdParams,
  documentSaveSchema,
  projectIdParams,
  reorderSchema,
  restoreSchema,
  revisionIdParams,
} from "./studio_request_schemas.js";
import {
  documentConflictSchema,
  documentResponseSchema,
  revisionConflictSchema,
  revisionResponseSchema,
  snapshotConflictSchema,
} from "./studio_schemas.js";
import { documentPlaceSchema } from "./volume_schemas.js";

const documentListResponseSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: { documents: { type: "array", items: documentResponseSchema } },
  required: ["documents"],
} as const;

const revisionListResponseSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: { revisions: { type: "array", items: revisionResponseSchema } },
  required: ["revisions"],
} as const;

const SAVE_RESPONSES = {
  200: documentResponseSchema,
  409: revisionConflictSchema,
} as const;

const CREATE_RESPONSES = {
  201: documentResponseSchema,
  409: documentConflictSchema,
} as const;

/**
 * Document and revision surface: creation with the identity uniqueness
 * contract, conflict-checked saves, whole-set reorder, deletion, history,
 * and restore.
 */
export const documentRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (fastify, options) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.post(
    "/api/projects/:projectId/documents",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        body: documentCreateSchema,
        response: CREATE_RESPONSES,
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

  app.put(
    "/api/projects/:projectId/documents/reorder",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        body: reorderSchema,
        response: { 200: documentListResponseSchema },
      },
    },
    async (request) =>
      withStudioErrors(() => ({
        documents: requireServices(options).documents.reorderProjectDocuments(
          requirePrincipal(request),
          request.params.projectId,
          request.body.document_ids,
        ),
      })),
  );

  app.put(
    "/api/projects/:projectId/documents/:documentId",
    {
      preHandler: [guard],
      schema: {
        params: documentIdParams,
        body: documentSaveSchema,
        response: SAVE_RESPONSES,
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
        response: { 200: documentResponseSchema },
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
        response: { 204: { type: "null" }, 409: snapshotConflictSchema },
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

  app.get(
    "/api/projects/:projectId/documents/:documentId/revisions",
    {
      preHandler: [guard],
      schema: {
        params: documentIdParams,
        response: { 200: revisionListResponseSchema },
      },
    },
    async (request) =>
      withStudioErrors(() => ({
        revisions: requireServices(options).revisions.documentRevisions(
          requirePrincipal(request),
          request.params.projectId,
          request.params.documentId,
        ),
      })),
  );

  app.post(
    "/api/projects/:projectId/documents/:documentId/revisions/:revisionId/restore",
    {
      preHandler: [guard],
      schema: {
        params: revisionIdParams,
        body: restoreSchema,
        response: { 200: documentResponseSchema, 409: revisionConflictSchema },
      },
    },
    async (request) =>
      withStudioErrors(() =>
        requireServices(options).revisions.replayRevision(
          requirePrincipal(request),
          request.params.projectId,
          request.params.documentId,
          request.params.revisionId,
          request.body.base_revision_id,
        ),
      ),
  );
};
