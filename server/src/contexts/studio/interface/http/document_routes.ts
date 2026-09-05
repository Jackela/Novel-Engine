import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import { errorEnvelopeResponse } from "../../../../shared/interface/http/error_envelope.js";
import { revisionPageLimit } from "../../application/ports/studio_store.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { decodeRevisionCursor, encodeRevisionCursor } from "./revision_cursor.js";
import { structureCapacity422ResponseSchema } from "./structure_capacity_schemas.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import {
  documentCreateSchema,
  documentIdParams,
  documentSaveSchema,
  projectIdParams,
  reorderSchema,
  restoreSchema,
  revisionIdParams,
  revisionListQuerySchema,
} from "./studio_request_schemas.js";
import {
  documentConflictSchema,
  documentListResponseSchema,
  documentResponseSchema,
  revisionConflictSchema,
  revisionListResponseSchema,
  snapshotConflictSchema,
} from "./studio_schemas.js";
import { documentPlaceSchema } from "./volume_schemas.js";

const SAVE_RESPONSES = {
  200: documentResponseSchema,
  401: errorEnvelopeResponse,
  403: errorEnvelopeResponse,
  404: errorEnvelopeResponse,
  // Metadata bytes and outline beats refuse here permanently (#461).
  422: structureCapacity422ResponseSchema,
  409: revisionConflictSchema,
  503: errorEnvelopeResponse,
} as const;

const CREATE_RESPONSES = {
  201: documentResponseSchema,
  401: errorEnvelopeResponse,
  403: errorEnvelopeResponse,
  // The parent project is scoped first: a foreign or missing project 404s.
  404: errorEnvelopeResponse,
  // Document, volume-chapter, and outline-beat budgets gate the create (#461).
  422: structureCapacity422ResponseSchema,
  409: documentConflictSchema,
  503: errorEnvelopeResponse,
} as const;

/** Guard failures shared by every authenticated document surface. */
const GUARD_RESPONSES = {
  401: errorEnvelopeResponse,
  503: errorEnvelopeResponse,
} as const;

/** Guard + CSRF double-submit failures shared by authenticated writes. */
const WRITE_RESPONSES = {
  ...GUARD_RESPONSES,
  403: errorEnvelopeResponse,
  422: errorEnvelopeResponse,
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
        response: {
          200: documentListResponseSchema,
          ...WRITE_RESPONSES,
          404: errorEnvelopeResponse,
        },
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

  app.get(
    "/api/projects/:projectId/documents/:documentId",
    {
      // The principal is established before any scoped Studio read.
      preValidation: [guard],
      schema: {
        params: documentIdParams,
        response: {
          200: documentResponseSchema,
          ...GUARD_RESPONSES,
          404: errorEnvelopeResponse,
        },
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
        response: {
          200: documentResponseSchema,
          ...GUARD_RESPONSES,
          403: errorEnvelopeResponse,
          404: errorEnvelopeResponse,
          // Placement into a full volume refuses permanently (#461).
          422: structureCapacity422ResponseSchema,
        },
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
        response: {
          204: { type: "null" },
          ...GUARD_RESPONSES,
          403: errorEnvelopeResponse,
          404: errorEnvelopeResponse,
          409: snapshotConflictSchema,
        },
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
      // Authentication deliberately precedes schema/cursor validation so an
      // anonymous malformed query cannot probe this scoped surface.
      preValidation: [guard],
      schema: {
        params: documentIdParams,
        querystring: revisionListQuerySchema,
        response: {
          200: revisionListResponseSchema,
          ...GUARD_RESPONSES,
          404: errorEnvelopeResponse,
          422: errorEnvelopeResponse,
        },
      },
    },
    async (request) => {
      const cursor =
        request.query.cursor === undefined
          ? undefined
          : decodeRevisionCursor(
              request.query.cursor,
              request.params.projectId,
              request.params.documentId,
            );
      return withStudioErrors(() => {
        const page = requireServices(options).revisions.documentRevisions(
          requirePrincipal(request),
          request.params.projectId,
          request.params.documentId,
          {
            limit: revisionPageLimit(request.query.limit ?? 50),
            ...(cursor === undefined ? {} : { cursor }),
          },
        );
        return {
          revisions: page.revisions,
          next_cursor: encodeRevisionCursor(
            request.params.projectId,
            request.params.documentId,
            page.nextCursor,
          ),
        };
      });
    },
  );

  app.post(
    "/api/projects/:projectId/documents/:documentId/revisions/:revisionId/restore",
    {
      preHandler: [guard],
      schema: {
        params: revisionIdParams,
        body: restoreSchema,
        response: {
          200: documentResponseSchema,
          ...GUARD_RESPONSES,
          403: errorEnvelopeResponse,
          404: errorEnvelopeResponse,
          // Restoring an over-budget outline revision refuses permanently (#461).
          422: structureCapacity422ResponseSchema,
          409: revisionConflictSchema,
        },
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
