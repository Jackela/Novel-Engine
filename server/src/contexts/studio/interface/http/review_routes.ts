import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import { AppError } from "../../../../shared/interface/http/error_envelope.js";
import type { EditorialAssessment } from "../../application/review_service.js";
import { jobResponseSchema } from "./job_schemas.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { reviewCreateSchema, reviewListResponseSchema } from "./review_schemas.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import { projectIdParams } from "./studio_request_schemas.js";

function reviewPayload(assessment: EditorialAssessment) {
  return {
    id: assessment.id,
    project_id: assessment.projectId,
    snapshot_id: assessment.snapshotId,
    provider: assessment.provider,
    model: assessment.model,
    summary: assessment.summary,
    created_at: assessment.createdAt.toISOString(),
    issues: assessment.issues.map((issue) => ({
      id: issue.id,
      document_id: issue.documentId,
      severity: issue.severity,
      code: issue.code,
      message: issue.message,
      suggestion: issue.suggestion,
      evidence: { ...issue.evidence },
    })),
  };
}

/** `withStudioErrors` is synchronous; review generation runs asynchronously. */
async function withOutcomeErrors<T>(operation: () => Promise<T>): Promise<T> {
  try {
    return await operation();
  } catch (error) {
    return withStudioErrors<T>(() => {
      throw error;
    });
  }
}

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
            code: "VALIDATION_ERROR",
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
        response: { 201: jobResponseSchema },
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
      const payload = await withOutcomeErrors(() =>
        requireServices(options).jobHistory.recordReviewJob(
          requirePrincipal(request),
          request.params.projectId,
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
      schema: { params: projectIdParams, response: { 200: reviewListResponseSchema } },
    },
    async (request) =>
      withStudioErrors(() => ({
        reviews: requireServices(options)
          .reviewAssessments.listEditorialAssessments(
            requirePrincipal(request),
            request.params.projectId,
          )
          .map(reviewPayload),
      })),
  );
};
