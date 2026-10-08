import { randomUUID } from "node:crypto";
import type { FastifyReply, FastifyRequest } from "fastify";
import { InvalidOperationError } from "../../../../shared/domain/exceptions.js";
import { requirePrincipal } from "../../../../shared/interface/http/auth_guard.js";
import { AppError, ERROR_CODES } from "../../../../shared/interface/http/error_envelope.js";
import type {
  AgentExecutionEvidence,
  AiOperationLease,
} from "../../../ai/application/ports/ai_operations.js";
import {
  type TextGenerationExecutionOptions,
  TextGenerationProviderError,
} from "../../../ai/application/ports/text_generation.js";
import type { StudioRoutesOptions } from "./project_routes.js";

/** Bind a request to its pre-opened owner/project channel; client disconnect aborts every provider step. */
export async function withAiExecution<T>(
  request: FastifyRequest,
  reply: FastifyReply,
  options: StudioRoutesOptions,
  projectId: string,
  work: (execution: TextGenerationExecutionOptions) => Promise<T>,
): Promise<T> {
  const header = request.headers["x-ai-operation-id"];
  if (
    header !== undefined &&
    (typeof header !== "string" ||
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/iu.test(header))
  )
    throw new AppError({
      statusCode: 422,
      code: ERROR_CODES.VALIDATION_ERROR,
      message: "Request validation failed.",
      details: {
        errors: [{ field: "X-AI-Operation-Id", type: "format", message: "must be a UUID" }],
      },
    });
  const principal = requirePrincipal(request);
  const disconnect = new AbortController();
  const close = (): void => {
    if (!reply.raw.writableFinished) disconnect.abort();
  };
  reply.raw.on("close", close);
  let lease: AiOperationLease | undefined;
  try {
    if (typeof header === "string") {
      if (principal.ownerId === null || options.aiOperations === undefined)
        throw new InvalidOperationError("AI operation channel unavailable.");
      lease = options.aiOperations.begin({
        ownerId: principal.ownerId,
        projectId,
        operationId: header,
      });
    }
    const execution: TextGenerationExecutionOptions = {
      ...lease?.execution,
      operationId: typeof header === "string" ? header : randomUUID(),
      signal:
        lease?.execution.signal === undefined
          ? disconnect.signal
          : AbortSignal.any([disconnect.signal, lease.execution.signal]),
    };
    const evidence: AgentExecutionEvidence = lease?.execution.agentExecution ?? {
      operation_id: execution.operationId ?? randomUUID(),
      external_effects: [],
      outcome_unknown: false,
    };
    const emit = execution.onAgentEvent;
    const observed: TextGenerationExecutionOptions = {
      ...execution,
      agentExecution: evidence,
      onAgentEvent: (event) => {
        if (event.type === "tool") {
          const entry = {
            tool_id: event.tool_id,
            title: event.title.slice(0, 200),
            kind: event.kind,
            status: event.status,
            ...(event.target === undefined ? {} : { target: event.target }),
          };
          const index = evidence.external_effects.findIndex(
            (previous) => previous.tool_id === event.tool_id,
          );
          if (index >= 0) evidence.external_effects[index] = entry;
          else if (evidence.external_effects.length < 100) evidence.external_effects.push(entry);
          else {
            evidence.outcome_unknown = true;
            throw new TextGenerationProviderError(
              "ACP tool evidence limit reached; external effects may be unknown.",
            );
          }
        }
        emit?.(event);
      },
    };
    const result = await work(observed);
    const terminalFailure =
      result !== null &&
      typeof result === "object" &&
      "status" in result &&
      result.status === "failed";
    lease?.finish(
      terminalFailure || execution.signal?.aborted
        ? new Error("Provider operation failed.")
        : undefined,
    );
    return result;
  } catch (error) {
    lease?.finish(error);
    throw error;
  } finally {
    reply.raw.off("close", close);
  }
}
