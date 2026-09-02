import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import { errorEnvelopeResponse } from "../../../../shared/interface/http/error_envelope.js";
import { jobResponseSchema } from "./job_schemas.js";
import type { JsonResponseSchema } from "./json_response_schema.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
import { writeProposalStreamResponse } from "./proposal_stream_response.js";
import { withAsyncStudioErrors, withStudioErrors } from "./studio_error_mapping.js";
import { documentIdParams, jobIdParams, proposalCreateSchema } from "./studio_request_schemas.js";
import { operationInFlightSchema } from "./studio_schemas.js";

/**
 * The stream endpoint hijacks the reply and writes raw SSE frames, so its
 * documented 200 response describes the `text/event-stream` frame stream;
 * the frame payloads are typed by `ProposalStreamFrame` and specified in the
 * OpenSpec change.
 */
const proposalStreamResponseSchema: JsonResponseSchema = {
  description: "Server-Sent Events stream of proposal frames (delta/done/error).",
  content: {
    "text/event-stream": { schema: { type: "string" } },
  },
} as const;

/** Guard + CSRF failures shared by the proposal writes; scope misses answer 404. */
const PROPOSAL_ERROR_RESPONSES = {
  401: errorEnvelopeResponse,
  403: errorEnvelopeResponse,
  404: errorEnvelopeResponse,
  422: errorEnvelopeResponse,
  503: errorEnvelopeResponse,
} as const;

/**
 * The AI proposal surface: synchronous generation that records a proposal on
 * a job (never mutating the manuscript), explicit acceptance that writes the
 * `ai-accepted` revision, and — since #308 — the SSE streaming twin of the
 * synchronous generation with identical landing semantics.
 */
export const proposalRoutes: FastifyPluginAsync<StudioRoutesOptions> = async (fastify, options) => {
  const app = fastify.withTypeProvider<TypeBoxTypeProvider>();
  const guard = principalGuard(options.authService);

  app.post(
    "/api/projects/:projectId/documents/:documentId/ai-proposals",
    {
      preHandler: [guard],
      schema: {
        params: documentIdParams,
        body: proposalCreateSchema,
        response: {
          200: jobResponseSchema,
          ...PROPOSAL_ERROR_RESPONSES,
          409: operationInFlightSchema,
        },
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
        requireServices(options).proposals.draftProposal(
          requirePrincipal(request),
          request.params.projectId,
          request.params.documentId,
          {
            operation: request.body.operation,
            instruction: request.body.instruction ?? "",
            provider: request.body.provider ?? "mock",
          },
          reportCleanupFailure,
        ),
      );
    },
  );

  app.post(
    "/api/projects/:projectId/documents/:documentId/ai-proposals/stream",
    {
      preHandler: [guard],
      schema: {
        params: documentIdParams,
        body: proposalCreateSchema,
        response: {
          200: proposalStreamResponseSchema,
          ...PROPOSAL_ERROR_RESPONSES,
          409: operationInFlightSchema,
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
      // A closed (or errored) client connection aborts the upstream provider
      // stream; nothing is persisted for an aborted proposal (#308). The TCP
      // socket is the disconnect signal: since Node 16 the IncomingMessage
      // itself emits "close" as soon as the request message is fully read,
      // which would abort every stream before it starts.
      const disconnect = new AbortController();
      const frames = requireServices(options).proposals.draftProposalStream(
        requirePrincipal(request),
        request.params.projectId,
        request.params.documentId,
        {
          operation: request.body.operation,
          instruction: request.body.instruction ?? "",
          provider: request.body.provider ?? "mock",
        },
        reportCleanupFailure,
        disconnect.signal,
      );
      await writeProposalStreamResponse({
        response: reply.raw,
        socket: request.raw.socket,
        frames,
        disconnect,
        hijack: () => reply.hijack(),
        pullFirst: () => withAsyncStudioErrors(() => frames.next()),
      });
    },
  );

  app.post(
    "/api/projects/:projectId/ai-proposals/:jobId/accept",
    {
      preHandler: [guard],
      schema: {
        params: jobIdParams,
        response: {
          200: jobResponseSchema,
          ...PROPOSAL_ERROR_RESPONSES,
        },
      },
    },
    async (request) => {
      return withStudioErrors(() =>
        requireServices(options).proposals.adoptProposal(
          requirePrincipal(request),
          request.params.projectId,
          request.params.jobId,
        ),
      );
    },
  );
};
