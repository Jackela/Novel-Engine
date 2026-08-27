import type { FastifyPluginAsync } from "fastify";
import type { Principal } from "../../../../shared/application/ports/auth.js";
import { principalGuard } from "../../../../shared/interface/http/auth_guard.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withStudioErrors } from "./studio_error_mapping.js";

/** The resolved association view: the live beat, or null when unlinked/vanished. */
export const chapterBeatResponseSchema = {
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

const chapterBeatLinkSchema = {
  type: "object",
  properties: {
    // A beat title links; explicit null clears the association.
    beat: { type: "string", maxLength: 240, nullable: true },
  },
  required: ["beat"],
  additionalProperties: false,
} as const;

/**
 * The chapter beat surface (#313): read the effective association and set or
 * clear it on a chapter. Reads never error for a vanished beat — they resolve
 * to unlinked.
 */
export const beatRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (app, options) => {
  const guard = principalGuard(options.authService);
  const principal = (request: { principal?: Principal }) => request.principal as Principal;

  app.get(
    "/api/projects/:projectId/documents/:documentId/beat",
    { preHandler: [guard], schema: { response: { 200: chapterBeatResponseSchema } } },
    async (request) => {
      const { projectId, documentId } = request.params as {
        projectId: string;
        documentId: string;
      };
      return withStudioErrors(() =>
        requireServices(options).beats.chapterBeat(principal(request), projectId, documentId),
      );
    },
  );

  app.put(
    "/api/projects/:projectId/documents/:documentId/beat",
    {
      preHandler: [guard],
      schema: {
        body: chapterBeatLinkSchema,
        response: { 200: chapterBeatResponseSchema },
      },
    },
    async (request) => {
      const { projectId, documentId } = request.params as {
        projectId: string;
        documentId: string;
      };
      const body = request.body as { beat: string | null };
      return withStudioErrors(() =>
        requireServices(options).beats.linkChapterBeat(principal(request), projectId, documentId, {
          beat: body.beat,
        }),
      );
    },
  );
};
