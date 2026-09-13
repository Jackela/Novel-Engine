import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import { errorEnvelopeResponse } from "../../../../shared/interface/http/error_envelope.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { authedWriteResponses } from "./route_responses.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import { projectIdParams, reorderSchema } from "./studio_request_schemas.js";
import { documentListResponseSchema } from "./studio_schemas.js";

/** Document surface: whole-set reorder of a project's documents. */
export const documentOrderRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (
  fastify,
  options,
) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.put(
    "/api/projects/:projectId/documents/reorder",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        body: reorderSchema,
        response: authedWriteResponses({
          200: documentListResponseSchema,
          404: errorEnvelopeResponse,
          422: errorEnvelopeResponse,
        }),
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
};
