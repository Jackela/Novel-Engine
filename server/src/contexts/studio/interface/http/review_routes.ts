import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import {
  AppError,
  ERROR_CODES,
  errorEnvelopeResponse,
} from "../../../../shared/interface/http/error_envelope.js";
import { reviewPayload, reviewSummaryPayload } from "../../application/payloads.js";
import { reviewPageLimit } from "../../application/ports/review_outcome_store.js";
import { jobResponseSchema } from "./job_schemas.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { decodeReviewCursor, encodeReviewCursor } from "./review_cursor.js";
import {
  reviewCreateSchema,
  reviewListQuerySchema,
  reviewListResponseSchema,
  reviewResponseSchema,
} from "./review_schemas.js";
import { withAsyncStudioErrors, withStudioErrors } from "./studio_error_mapping.js";
import { projectIdParams, reviewIdParams } from "./studio_request_schemas.js";
import { operationCapacityResponseSchema, operationInFlightSchema } from "./studio_schemas.js";

/** Snapshot-bound editorial assessments, with server-owned provider provenance. */
export const reviewRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (fastify, options) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.post(
    "/api/projects/:projectId/reviews",
    {
      preValidation: async (request) => {
        if (request.body === undefined) {
          request.body = {};
          return;
        }
        if (
          request.body !== null &&
          typeof request.body === "object" &&
          !Array.isArray(request.body) &&
          Object.keys(request.body).length > 0
        ) {
          throw new AppError({
            statusCode: 422,
            code: ERROR_CODES.VALIDATION_ERROR,
            message: "Request validation failed.",
            details: {
              errors: [
                {
                  field: "(root)",
                  message: "must not contain client-controlled review fields",
                  type: "additionalProperties",
                },
              ],
            },
          });
        }
      },
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        body: reviewCreateSchema,
        response: {
          201: jobResponseSchema,
          401: errorEnvelopeResponse,
          403: errorEnvelopeResponse,
          404: errorEnvelopeResponse,
          409: operationInFlightSchema,
          422: errorEnvelopeResponse,
          503: operationCapacityResponseSchema,
        },
      },
      config: {
        swaggerTransform: ({ schema, url }) => {
          const documentationSchema = { ...schema };
          delete documentationSchema.body;
          return { schema: documentationSchema, url };
        },
      },
    },
    async (request, reply) => {
      const reportCleanupFailure = (failure: unknown): void => {
        request.log.error(
          { err: failure, errorId: request.id, provider_cleanup_failed: true },
          "provider cleanup failed",
        );
      };
      const payload = await withAsyncStudioErrors(() =>
        requireServices(options).jobHistory.recordReviewJob(
          requirePrincipal(request),
          request.params.projectId,
          reportCleanupFailure,
        ),
      );
      reply.status(201);
      return payload;
    },
  );

  app.get(
    "/api/projects/:projectId/reviews",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        querystring: reviewListQuerySchema,
        response: {
          200: reviewListResponseSchema,
          401: errorEnvelopeResponse,
          404: errorEnvelopeResponse,
          422: errorEnvelopeResponse,
          503: errorEnvelopeResponse,
        },
      },
    },
    async (request) => {
      const cursor =
        request.query.cursor === undefined
          ? undefined
          : decodeReviewCursor(request.query.cursor, request.params.projectId);
      return withStudioErrors(() => {
        const page = requireServices(options).reviewAssessments.collectProjectReviewSummaries(
          requirePrincipal(request),
          request.params.projectId,
          {
            limit: reviewPageLimit(request.query.limit ?? 50),
            ...(cursor === undefined ? {} : { cursor }),
          },
        );
        return {
          reviews: page.reviews.map(reviewSummaryPayload),
          next_cursor: encodeReviewCursor(request.params.projectId, page.nextCursor),
        };
      });
    },
  );

  app.get(
    "/api/projects/:projectId/reviews/:reviewId",
    {
      preHandler: [guard],
      schema: {
        params: reviewIdParams,
        response: {
          200: reviewResponseSchema,
          401: errorEnvelopeResponse,
          404: errorEnvelopeResponse,
          503: errorEnvelopeResponse,
        },
      },
    },
    async (request) =>
      withStudioErrors(() =>
        reviewPayload(
          requireServices(options).reviewAssessments.findEditorialAssessment(
            requirePrincipal(request),
            request.params.projectId,
            request.params.reviewId,
          ),
        ),
      ),
  );
};
