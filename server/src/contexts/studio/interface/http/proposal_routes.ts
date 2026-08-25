import type { FastifyPluginAsync } from "fastify";
import type { Principal } from "../../../../shared/application/ports/auth.js";
import { principalGuard } from "../../../../shared/interface/http/auth_guard.js";
import { jobResponseSchema } from "./job_schemas.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { withStudioErrors } from "./studio_error_mapping.js";
import { proposalCreateSchema } from "./studio_schemas.js";

/**
 * The AI proposal surface: synchronous generation that records a proposal on
 * a job (never mutating the manuscript), and explicit acceptance that writes
 * the `ai-accepted` revision.
 */
export const proposalRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (app, options) => {
  const guard = principalGuard(options.authService);
  const principal = (request: { principal?: Principal }) => request.principal as Principal;

  app.post(
    "/api/projects/:projectId/documents/:documentId/ai-proposals",
    {
      preHandler: [guard],
      schema: { body: proposalCreateSchema, response: { 200: jobResponseSchema } },
    },
    async (request) => {
      const { projectId, documentId } = request.params as {
        projectId: string;
        documentId: string;
      };
      const body = request.body as { operation: string; instruction?: string; provider?: string };
      const reportCleanupFailure = (failure: unknown): void => {
        request.log.error(
          { err: failure, errorId: request.id, provider_cleanup_failed: true },
          "provider cleanup failed",
        );
      };
      return withStudioErrors(() =>
        requireServices(options).proposals.draftProposal(
          principal(request),
          projectId,
          documentId,
          {
            operation: body.operation,
            instruction: body.instruction ?? "",
            provider: body.provider ?? "mock",
          },
          reportCleanupFailure,
        ),
      );
    },
  );

  app.post(
    "/api/projects/:projectId/ai-proposals/:jobId/accept",
    { preHandler: [guard], schema: { response: { 200: jobResponseSchema } } },
    async (request) => {
      const { projectId, jobId } = request.params as { projectId: string; jobId: string };
      return withStudioErrors(() =>
        requireServices(options).proposals.adoptProposal(principal(request), projectId, jobId),
      );
    },
  );
};
