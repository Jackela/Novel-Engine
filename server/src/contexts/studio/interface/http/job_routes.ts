import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import { errorEnvelopeResponse } from "../../../../shared/interface/http/error_envelope.js";
import { jobListResponseSchema, jobResponseSchema, usageResponseSchema } from "./job_schemas.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withAsyncStudioErrors, withStudioErrors } from "./studio_error_mapping.js";
import { jobIdParams, projectIdParams } from "./studio_request_schemas.js";
import { operationCapacityResponseSchema, operationInFlightSchema } from "./studio_schemas.js";

/** Guard + scope failures shared by the project-scoped job reads. */
const JOB_READ_ERROR_RESPONSES = {
  401: errorEnvelopeResponse,
  404: errorEnvelopeResponse,
  503: errorEnvelopeResponse,
} as const;

/**
 * The synchronous jobs audit surface: the persisted listing (newest first)
 * and the retry chain, which executes synchronously and always responds with
 * the retry job's terminal state.
 */
export const jobRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (fastify, options) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.get(
    "/api/projects/:projectId/jobs",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        response: { 200: jobListResponseSchema, ...JOB_READ_ERROR_RESPONSES },
      },
    },
    async (request) =>
      withStudioErrors(() => ({
        jobs: requireServices(options).jobHistory.collectProjectJobs(
          requirePrincipal(request),
          request.params.projectId,
        ),
      })),
  );

  app.post(
    "/api/projects/:projectId/jobs/:jobId/retry",
    {
      preHandler: [guard],
      schema: {
        params: jobIdParams,
        response: {
          200: jobResponseSchema,
          ...JOB_READ_ERROR_RESPONSES,
          403: errorEnvelopeResponse,
          // Non-retryable terminal states answer 422 INVALID_OPERATION.
          422: errorEnvelopeResponse,
          409: operationInFlightSchema,
          503: operationCapacityResponseSchema,
        },
      },
    },
    async (request) => {
      const reportCleanupFailure = (failure: unknown): void => {
        request.log.error(
          {
            err: failure,
            errorId: request.id,
            request_cleanup_failed: true,
            // Preserve the established retry-cleanup diagnostic consumed by
            // provider lifecycle monitoring while export retries share this seam.
            provider_cleanup_failed: true,
          },
          "provider cleanup failed",
        );
      };
      return withAsyncStudioErrors(() =>
        requireServices(options).jobHistory.reexecuteProjectJob(
          requirePrincipal(request),
          request.params.projectId,
          request.params.jobId,
          reportCleanupFailure,
        ),
      );
    },
  );

  app.get(
    "/api/projects/:projectId/usage",
    {
      preHandler: [guard],
      schema: {
        params: projectIdParams,
        response: { 200: usageResponseSchema, ...JOB_READ_ERROR_RESPONSES },
      },
    },
    async (request) => {
      return withStudioErrors(() => {
        const usage = requireServices(options).jobHistory.aggregateProjectUsage(
          requirePrincipal(request),
          request.params.projectId,
        );
        return {
          project_id: usage.projectId,
          request_count: usage.requestCount,
          prompt_tokens: usage.promptTokens,
          completion_tokens: usage.completionTokens,
          per_model: usage.perModel.map((entry) => ({
            model: entry.model,
            requests: entry.requests,
            prompt_tokens: entry.promptTokens,
            completion_tokens: entry.completionTokens,
          })),
          daily: usage.daily.map((bucket) => ({
            date: bucket.date,
            request_count: bucket.requestCount,
            prompt_tokens: bucket.promptTokens,
            completion_tokens: bucket.completionTokens,
          })),
        };
      });
    },
  );
};
