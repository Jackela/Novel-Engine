import { ApiContractError, objectValue } from "./apiContract";
import { type AiOperationEvent, parseAiOperationEvent } from "./parseAiOperationEvent";

export interface AgentExecution {
  readonly operation_id: string;
  readonly external_effects: readonly Extract<AiOperationEvent, { type: "tool" }>[];
  readonly outcome_unknown: boolean;
}

/** Durable redacted file actions stay readable after observation closes. */
export function parseAgentExecution(value: unknown): AgentExecution | undefined {
  if (value === undefined) return undefined;
  const execution = objectValue(value, "agent execution");
  if (
    typeof execution.operation_id !== "string" ||
    typeof execution.outcome_unknown !== "boolean" ||
    !Array.isArray(execution.external_effects)
  )
    throw new ApiContractError("agent execution");
  return {
    operation_id: execution.operation_id,
    outcome_unknown: execution.outcome_unknown,
    external_effects: execution.external_effects.map((value) => {
      const effect = objectValue(value, "agent effect");
      const event = parseAiOperationEvent({ ...effect, type: "tool" });
      if (event.type !== "tool") throw new ApiContractError("agent effect");
      return event;
    }),
  };
}
