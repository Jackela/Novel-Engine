import type { FastifyPluginAsync } from "fastify";
import type { Principal } from "../../../../shared/application/ports/auth.js";
import { principalGuard } from "../../../../shared/interface/http/auth_guard.js";
import { AppError } from "../../../../shared/interface/http/error_envelope.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withStudioErrors } from "./studio_error_mapping.js";

const legacyPreviewRequestSchema = {
  type: "object",
  properties: {
    source: {
      type: "string",
      minLength: 1,
      maxLength: 240,
      description: "Workspace directory name under data/imports.",
    },
  },
  required: ["source"],
  additionalProperties: false,
} as const;

const legacyPreviewResponseSchema = {
  type: "object",
  properties: {
    source: { type: "string" },
    source_hash: { type: "string" },
    title: { type: "string" },
    description: { type: "string" },
    chapter_count: { type: "integer" },
    chapters: {
      type: "array",
      items: {
        type: "object",
        properties: { filename: { type: "string" }, bytes: { type: "integer" } },
        required: ["filename", "bytes"],
        additionalProperties: false,
      },
    },
  },
  required: ["source", "source_hash", "title", "description", "chapter_count", "chapters"],
  additionalProperties: false,
} as const;

function requireLocalOwner(principal: Principal): void {
  if (principal.kind !== "owner") {
    throw new AppError({
      statusCode: 403,
      code: "FORBIDDEN",
      message: "This operation requires the local Owner.",
    });
  }
}

/**
 * The web legacy-import surface is preview-only: importing happens through
 * the CLI. The untrusted source name is confined to one real directory under
 * the application-owned data/imports root before any content is read.
 */
export const importRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (app, options) => {
  const guard = principalGuard(options.authService);

  app.post(
    "/api/imports/preview",
    {
      preHandler: [
        guard,
        async (request) => {
          requireLocalOwner(request.principal as Principal);
        },
      ],
      schema: {
        body: legacyPreviewRequestSchema,
        response: { 200: legacyPreviewResponseSchema },
      },
    },
    async (request) => {
      const { source } = request.body as { source: string };
      const dataDirectory = options.dataDirectory;
      if (dataDirectory === undefined) {
        throw new AppError({
          statusCode: 503,
          code: "SERVICE_UNAVAILABLE",
          message: "The persistence layer is not configured.",
        });
      }
      return withStudioErrors(() =>
        requireServices(options).imports.previewConfinedLegacyWorkspace(dataDirectory, source),
      );
    },
  );
};
