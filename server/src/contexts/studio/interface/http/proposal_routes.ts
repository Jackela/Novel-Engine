import type { TypeBoxTypeProvider } from "@fastify/type-provider-typebox";
import type { FastifyPluginAsync, FastifyReply } from "fastify";
import { principalGuard, requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import { errorEnvelopeResponse } from "../../../../shared/interface/http/error_envelope.js";
import type { ProposalStreamFrame } from "../../application/proposal_streaming.js";
import { jobResponseSchema } from "./job_schemas.js";
import type { JsonResponseSchema } from "./json_response_schema.js";
import { requireServices, type StudioRoutesOptions } from "./project_routes.js";
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

/** One SSE event: a single JSON frame per `data:` field, blank-line ended. */
function sseFrame(frame: ProposalStreamFrame): string {
  return `data: ${JSON.stringify(frame)}\n\n`;
}

/** SSE response headers: disable proxy buffering so deltas arrive immediately. */
const SSE_HEADERS = {
  "content-type": "text/event-stream; charset=utf-8",
  "cache-control": "no-cache",
  connection: "keep-alive",
  "x-accel-buffering": "no",
} as const;

/**
 * Drive the proposal stream: validation (and every envelope error) resolves
 * before the first frame, then the reply is hijacked and frames are written
 * as they arrive. The disconnect signal aborts the upstream generator; a
 * provider failure arrives as the stream's error frame.
 */
async function writeProposalStream(
  reply: FastifyReply,
  frames: AsyncGenerator<ProposalStreamFrame, void, void>,
  disconnect: AbortController,
): Promise<void> {
  let current = await withAsyncStudioErrors(() => frames.next());
  reply.hijack();
  reply.raw.writeHead(200, SSE_HEADERS);
  const write = (frame: ProposalStreamFrame): void => {
    if (!disconnect.signal.aborted) reply.raw.write(sseFrame(frame));
  };
  while (!current.done) {
    write(current.value);
    current = await frames.next();
  }
  reply.raw.end();
}

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
      const abort = (): void => disconnect.abort();
      const socket = request.raw.socket;
      socket?.on("close", abort);
      reply.raw.on("close", abort);
      reply.raw.on("error", abort);
      let streamFailure: unknown;
      try {
        await writeProposalStream(reply, frames, disconnect);
      } catch (error) {
        streamFailure = error;
      }
      disconnect.abort();
      socket?.off("close", abort);
      reply.raw.off("close", abort);
      reply.raw.off("error", abort);
      let cleanupFailure: unknown;
      try {
        await frames.return();
      } catch (error) {
        cleanupFailure = error;
      }
      if (streamFailure !== undefined && cleanupFailure !== undefined) {
        throw new AggregateError(
          [streamFailure, cleanupFailure],
          "Proposal stream and generator cleanup both failed.",
        );
      }
      if (streamFailure !== undefined) throw streamFailure;
      if (cleanupFailure !== undefined) throw cleanupFailure;
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
