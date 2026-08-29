import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import { jobListResponseSchema, jobResponseSchema, usageResponseSchema } from "./job_schemas.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withAsyncStudioErrors, withStudioErrors } from "./studio_error_mapping.js";
import { jobIdParams, projectIdParams } from "./studio_request_schemas.js";
import { operationInFlightSchema } from "./studio_schemas.js";

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
      schema: { params: projectIdParams, response: { 200: jobListResponseSchema } },
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
        response: { 200: jobResponseSchema, 409: operationInFlightSchema },
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
      schema: { params: projectIdParams, response: { 200: usageResponseSchema } },
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
