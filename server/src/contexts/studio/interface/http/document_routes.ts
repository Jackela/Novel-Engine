import type { FastifyPluginAsync } from "fastify";
import type { Principal } from "../../../../shared/application/ports/auth.js";
import { principalGuard } from "../../../../shared/interface/http/auth_guard.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import {
  documentConflictSchema,
  documentCreateSchema,
  documentResponseSchema,
  documentSaveSchema,
  reorderSchema,
  restoreSchema,
  revisionConflictSchema,
  revisionResponseSchema,
} from "./studio_schemas.js";

const documentListResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: { documents: { type: "array", items: documentResponseSchema } },
  required: ["documents"],
} as const;

const revisionListResponseSchema = {
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
export const documentRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (app, options) => {
  const guard = principalGuard(options.authService);
  const principal = (request: { principal?: Principal }) => request.principal as Principal;

  app.post(
    "/api/projects/:projectId/documents",
    { preHandler: [guard], schema: { body: documentCreateSchema, response: CREATE_RESPONSES } },
    async (request, reply) => {
      const { projectId } = request.params as { projectId: string };
      const body = request.body as {
        kind: string;
        title: string;
        content_markdown?: string;
        position?: number | null;
        metadata?: Record<string, unknown>;
      };
      const payload = withStudioErrors(() =>
        requireServices(options).documents.newDocument(principal(request), projectId, {
          kind: body.kind,
          title: body.title,
          contentMarkdown: body.content_markdown,
          position: body.position,
          metadata: body.metadata,
        }),
      );
      reply.status(201);
      return payload;
    },
  );

  app.put(
    "/api/projects/:projectId/documents/reorder",
    {
      preHandler: [guard],
      schema: { body: reorderSchema, response: { 200: documentListResponseSchema } },
    },
    async (request) => {
      const { projectId } = request.params as { projectId: string };
      const body = request.body as { document_ids: string[] };
      return withStudioErrors(() => ({
        documents: requireServices(options).documents.reorderProjectDocuments(
          principal(request),
          projectId,
          body.document_ids,
        ),
      }));
    },
  );

  app.get(
    "/api/projects/:projectId/documents/:documentId",
    { preHandler: [guard], schema: { response: { 200: documentResponseSchema } } },
    async (request) => {
      const { projectId, documentId } = request.params as {
        projectId: string;
        documentId: string;
      };
      return withStudioErrors(() =>
        requireServices(options).documents.documentById(principal(request), projectId, documentId),
      );
    },
  );

  app.put(
    "/api/projects/:projectId/documents/:documentId",
    { preHandler: [guard], schema: { body: documentSaveSchema, response: SAVE_RESPONSES } },
    async (request) => {
      const { projectId, documentId } = request.params as {
        projectId: string;
        documentId: string;
      };
      const body = request.body as {
        content_markdown: string;
        base_revision_id: string | null;
        title?: string;
        metadata?: Record<string, unknown>;
      };
      return withStudioErrors(() =>
        requireServices(options).documents.storeDocument(
          principal(request),
          projectId,
          documentId,
          {
            contentMarkdown: body.content_markdown,
            baseRevisionId: body.base_revision_id,
            title: body.title,
            metadata: body.metadata,
          },
        ),
      );
    },
  );

  app.delete(
    "/api/projects/:projectId/documents/:documentId",
    { preHandler: [guard], schema: { response: { 204: { type: "null" } } } },
    async (request, reply) => {
      const { projectId, documentId } = request.params as {
        projectId: string;
        documentId: string;
      };
      withStudioErrors(() =>
        requireServices(options).documents.removeDocument(
          principal(request),
          projectId,
          documentId,
        ),
      );
      reply.status(204);
      return null;
    },
  );

  app.get(
    "/api/projects/:projectId/documents/:documentId/revisions",
    { preHandler: [guard], schema: { response: { 200: revisionListResponseSchema } } },
    async (request) => {
      const { projectId, documentId } = request.params as {
        projectId: string;
        documentId: string;
      };
      return withStudioErrors(() => ({
        revisions: requireServices(options).revisions.documentRevisions(
          principal(request),
          projectId,
          documentId,
        ),
      }));
    },
  );

  app.post(
    "/api/projects/:projectId/documents/:documentId/revisions/:revisionId/restore",
    {
      preHandler: [guard],
      schema: {
        body: restoreSchema,
        response: { 200: documentResponseSchema, 409: revisionConflictSchema },
      },
    },
    async (request) => {
      const { projectId, documentId, revisionId } = request.params as {
        projectId: string;
        documentId: string;
        revisionId: string;
      };
      const body = request.body as { base_revision_id: string | null };
      return withStudioErrors(() =>
        requireServices(options).revisions.replayRevision(
          principal(request),
          projectId,
          documentId,
          revisionId,
          body.base_revision_id,
        ),
      );
    },
  );
};
