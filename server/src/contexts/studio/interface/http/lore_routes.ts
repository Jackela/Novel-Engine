import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import { loreAliasResponseSchema, loreAliasWriteSchema } from "./lore_schemas.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import { documentIdParams } from "./studio_request_schemas.js";

/**
 * The lorebook alias surface (#315): read and replace the extra prompt keys
 * (beyond the title) of a character or world document. Writes to other kinds
 * answer 422; reads default to an empty list.
 */
export const loreRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (fastify, options) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.get(
    "/api/projects/:projectId/documents/:documentId/aliases",
    {
      preHandler: [guard],
      schema: { params: documentIdParams, response: { 200: loreAliasResponseSchema } },
    },
    async (request) =>
      withStudioErrors(() => ({
        aliases: requireServices(options).lore.listDocumentLoreAliases(
          requirePrincipal(request),
          request.params.projectId,
          request.params.documentId,
        ),
      })),
  );

  app.put(
    "/api/projects/:projectId/documents/:documentId/aliases",
    {
      preHandler: [guard],
      schema: {
        params: documentIdParams,
        body: loreAliasWriteSchema,
        response: { 200: loreAliasResponseSchema },
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
};
