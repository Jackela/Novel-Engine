import type { FastifyPluginAsync } from "fastify";
import type { Principal } from "../../../../shared/application/ports/auth.js";
import { principalGuard } from "../../../../shared/interface/http/auth_guard.js";
import { loreAliasResponseSchema, loreAliasWriteSchema } from "./lore_schemas.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withStudioErrors } from "./studio_error_mapping.js";

/**
 * The lorebook alias surface (#315): read and replace the extra prompt keys
 * (beyond the title) of a character or world document. Writes to other kinds
 * answer 422; reads default to an empty list.
 */
export const loreRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (app, options) => {
  const guard = principalGuard(options.authService);
  const principal = (request: { principal?: Principal }) => request.principal as Principal;

  app.get(
    "/api/projects/:projectId/documents/:documentId/aliases",
    { preHandler: [guard], schema: { response: { 200: loreAliasResponseSchema } } },
    async (request) => {
      const { projectId, documentId } = request.params as {
        projectId: string;
        documentId: string;
      };
      return withStudioErrors(() => ({
        aliases: requireServices(options).lore.documentAliases(
          principal(request),
          projectId,
          documentId,
        ),
      }));
    },
  );

  app.put(
    "/api/projects/:projectId/documents/:documentId/aliases",
    {
      preHandler: [guard],
      schema: { body: loreAliasWriteSchema, response: { 200: loreAliasResponseSchema } },
    },
    async (request) => {
      const { projectId, documentId } = request.params as {
        projectId: string;
        documentId: string;
      };
      const body = request.body as { aliases: string[] };
      return withStudioErrors(() =>
        requireServices(options).lore.setDocumentAliases(
          principal(request),
          projectId,
          documentId,
          {
            aliases: body.aliases,
          },
        ),
      );
    },
  );
};
