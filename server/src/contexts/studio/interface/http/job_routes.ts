import type { FastifyPluginAsync } from "fastify";
import type { Principal } from "../../../../shared/application/ports/auth.js";
import { principalGuard } from "../../../../shared/interface/http/auth_guard.js";
import { jobListResponseSchema, jobResponseSchema } from "./job_schemas.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import { operationInFlightSchema } from "./studio_schemas.js";

/** `withStudioErrors` is synchronous; the retry executes asynchronously. */
async function withOutcomeErrors<T>(operation: () => Promise<T>): Promise<T> {
  try {
    return await operation();
  } catch (error) {
    return withStudioErrors<T>(() => {
      throw error;
    });
  }
}

/**
 * The synchronous jobs audit surface: the persisted listing (newest first)
 * and the retry chain, which executes synchronously and always responds with
 * the retry job's terminal state.
 */
export const jobRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (app, options) => {
  const guard = principalGuard(options.authService);
  const principal = (request: { principal?: Principal }) => request.principal as Principal;

  app.get(
    "/api/projects/:projectId/jobs",
    { preHandler: [guard], schema: { response: { 200: jobListResponseSchema } } },
    async (request) => {
      const { projectId } = request.params as { projectId: string };
      return withStudioErrors(() => ({
        jobs: requireServices(options).jobHistory.collectProjectJobs(principal(request), projectId),
      }));
    },
  );

  app.post(
    "/api/projects/:projectId/jobs/:jobId/retry",
    {
      preHandler: [guard],
      schema: { response: { 200: jobResponseSchema, 409: operationInFlightSchema } },
    },
    async (request) => {
      const { projectId, jobId } = request.params as { projectId: string; jobId: string };
      const reportCleanupFailure = (failure: unknown): void => {
        request.log.error(
          { err: failure, errorId: request.id, provider_cleanup_failed: true },
          "provider cleanup failed",
        );
      };
      return withOutcomeErrors(() =>
        requireServices(options).jobHistory.reexecuteProjectJob(
          principal(request),
          projectId,
          jobId,
          reportCleanupFailure,
        ),
      );
    },
  );
};
