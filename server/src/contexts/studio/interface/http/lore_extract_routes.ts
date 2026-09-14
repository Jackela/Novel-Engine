import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import { Type } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import {
  PROVIDER_NAMES,
  type TextProviderName,
} from "../../../ai/application/ports/text_generation.js";
import { loreExtraction422ResponseSchema } from "./generation_capacity_schemas.js";
import { jobResponseSchema } from "./job_schemas.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { authedWriteResponses } from "./route_responses.js";
import { withAsyncStudioErrors } from "./studio_error_mapping.js";
import { projectIdParams } from "./studio_request_schemas.js";

/**
 * The wizard's segment-extraction request (#614): one segment and the named
 * provider — models are resolved server-side, never sent. The segment is
 * deliberately left without a schema `maxLength`: its refusal authority is
 * the service's 100,000-code-point cap, whose stable
 * `GENERATION_CAPACITY_EXCEEDED` envelope must own every over-budget refusal
 * regardless of the input's UTF-16 code-unit width.
 */
const loreExtractCreateSchema = Type.Object(
  {
    segment: Type.String({ minLength: 1 }),
    provider: Type.Optional(
      Type.Unsafe<TextProviderName | undefined>({
        type: "string",
        enum: [...PROVIDER_NAMES],
        default: "mock",
      }),
    ),
  },
  { additionalProperties: false },
);

/**
 * The lorebook initialization wizard's extraction surface (#614): each
 * submitted segment executes synchronously as its own `lore-extract` Job —
 * the terminal job rides the response, exactly like proposal generation, and
 * retry runs through the shared jobs retry chain.
 */
export const loreExtractRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (
  fastify,
  options,
) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.post(
    "/api/projects/:projectId/lore-extractions",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        body: loreExtractCreateSchema,
        response: authedWriteResponses({
          200: jobResponseSchema,
          422: loreExtraction422ResponseSchema,
        }),
      },
    },
    async (request) => {
      const reportCleanupFailure = (failure: unknown): void => {
        request.log.error(
          { err: failure, errorId: request.id, provider_cleanup_failed: true },
          "provider cleanup failed",
        );
      };
      return withAsyncStudioErrors(() =>
        requireServices(options).loreExtractions.extractSegment(
          requirePrincipal(request),
          request.params.projectId,
          {
            provider: request.body.provider ?? "mock",
            segment: request.body.segment,
          },
          reportCleanupFailure,
        ),
      );
    },
  );
};
