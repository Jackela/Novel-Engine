import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import { Type } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import type { JsonResponseSchema } from "./json_response_schema.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import { documentIdParams } from "./studio_request_schemas.js";

/** The resolved association view: the live beat, or null when unlinked/vanished. */
export const chapterBeatResponseSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    beat: {
      type: "object",
      nullable: true,
      additionalProperties: false,
      properties: {
        title: { type: "string" },
        content: { type: "string" },
      },
      required: ["title", "content"],
    },
  },
  required: ["beat"],
} as const;

// A beat title links; explicit null clears the association. `nullable: true`
// keeps Fastify's coercing AJV from turning the null into "".
const chapterBeatLinkSchema = Type.Object(
  {
    beat: Type.Unsafe<string | null>({
      type: "string",
      maxLength: 240,
      nullable: true,
    }),
  },
  { additionalProperties: false },
);

/**
 * The chapter beat surface (#313): read the effective association and set or
 * clear it on a chapter. Reads never error for a vanished beat — they resolve
 * to unlinked.
 */
export const beatRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (fastify, options) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.get(
    "/api/projects/:projectId/documents/:documentId/beat",
    {
      preHandler: [guard],
      schema: { params: documentIdParams, response: { 200: chapterBeatResponseSchema } },
    },
    async (request) =>
      withStudioErrors(() =>
        requireServices(options).beats.chapterBeat(
          requirePrincipal(request),
          request.params.projectId,
          request.params.documentId,
        ),
      ),
  );

  app.put(
    "/api/projects/:projectId/documents/:documentId/beat",
    {
      preHandler: [guard],
      schema: {
        params: documentIdParams,
        body: chapterBeatLinkSchema,
        response: { 200: chapterBeatResponseSchema },
      },
    },
    async (request) =>
      withStudioErrors(() =>
        requireServices(options).beats.linkChapterBeat(
          requirePrincipal(request),
          request.params.projectId,
          request.params.documentId,
          { beat: request.body.beat },
        ),
      ),
  );
};
