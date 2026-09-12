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
  documentIdParams,
  restoreSchema,
  revisionIdParams,
  revisionListQuerySchema,
} from "./studio_request_schemas.js";
import {
  documentResponseSchema,
  revisionConflictSchema,
  revisionListResponseSchema,
} from "./studio_schemas.js";

/** Guard failures shared by every authenticated revision surface. */
const GUARD_RESPONSES = {
  401: errorEnvelopeResponse,
  503: errorEnvelopeResponse,
} as const;

/**
 * Revision surface: paginated document history with scoped cursors, and
 * restore of a prior revision onto the current document.
 */
export const revisionRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (fastify, options) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

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
