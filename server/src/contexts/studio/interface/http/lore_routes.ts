import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import { errorEnvelopeResponse } from "../../../../shared/interface/http/error_envelope.js";
import { loreAliasPayload } from "../../application/payloads.js";
import {
  loreAliasResponseSchema,
  loreAliasWriteSchema,
  loreStatusResponseSchema,
  loreStatusWriteSchema,
} from "./lore_schemas.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import { documentIdParams } from "./studio_request_schemas.js";

/**
 * The lorebook surface: alias prompt keys (#315) and the lifecycle status
 * (#444) of a character or world document. Writes to other kinds answer 422;
 * alias reads default to an empty list; the status write mints no revision —
 * it flips injection gating only (ADR-0006).
 */
export const loreRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (fastify, options) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.get(
    "/api/projects/:projectId/documents/:documentId/aliases",
    {
      preHandler: [guard],
      schema: {
        params: documentIdParams,
        response: {
          200: loreAliasResponseSchema,
          401: errorEnvelopeResponse,
          404: errorEnvelopeResponse,
          503: errorEnvelopeResponse,
        },
      },
    },
    async (request) =>
      withStudioErrors(() =>
        loreAliasPayload(
          requireServices(options).lore.listDocumentLoreAliases(
            requirePrincipal(request),
            request.params.projectId,
            request.params.documentId,
          ),
        ),
      ),
  );

  app.put(
    "/api/projects/:projectId/documents/:documentId/aliases",
    {
      preHandler: [guard],
      schema: {
        params: documentIdParams,
        body: loreAliasWriteSchema,
        response: {
          200: loreAliasResponseSchema,
          // Non-lore document kinds answer 422 INVALID_OPERATION.
          401: errorEnvelopeResponse,
          403: errorEnvelopeResponse,
          404: errorEnvelopeResponse,
          422: errorEnvelopeResponse,
          503: errorEnvelopeResponse,
        },
      },
    },
    async (request) =>
      withStudioErrors(() =>
        requireServices(options).lore.overwriteDocumentAliases(
          requirePrincipal(request),
          request.params.projectId,
          request.params.documentId,
          {
            aliases: request.body.aliases,
          },
        ),
      ),
  );

  app.put(
    "/api/projects/:projectId/documents/:documentId/lore-status",
    {
      preHandler: [guard],
      schema: {
        params: documentIdParams,
        body: loreStatusWriteSchema,
        response: {
          200: loreStatusResponseSchema,
          // Non-lore kinds and enum misses answer 422.
          401: errorEnvelopeResponse,
          403: errorEnvelopeResponse,
          404: errorEnvelopeResponse,
          422: errorEnvelopeResponse,
          503: errorEnvelopeResponse,
        },
      },
    },
    async (request) =>
      withStudioErrors(() =>
        requireServices(options).lore.changeDocumentLoreStatus(
          requirePrincipal(request),
          request.params.projectId,
          request.params.documentId,
          {
            status: request.body.lore_status,
          },
        ),
      ),
  );
};
