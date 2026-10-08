import { ApiContractError, objectValue } from "./apiContract";

export interface AgentTool {
  readonly title: string;
  readonly kind: string;
  readonly target?: string;
}
export interface AgentPermissionOption {
  readonly option_id: string;
  readonly name: string;
  readonly kind: string;
}
export type ExternalEffects = "completed" | "unknown" | "none";
export type AiOperationEvent =
  | { readonly type: "ready"; readonly operation_id: string }
  | ({ readonly type: "tool"; readonly tool_id: string; readonly status: string } & AgentTool)
  | {
      readonly type: "permission";
      readonly permission_id: string;
      readonly tool: AgentTool;
      readonly options: readonly AgentPermissionOption[];
    }
  | { readonly type: "completed"; readonly external_effects: ExternalEffects }
  | {
      readonly type: "error";
      readonly message: string;
      readonly external_effects: ExternalEffects;
    };

function field(value: Record<string, unknown>, key: string): string {
  if (typeof value[key] !== "string") throw new ApiContractError(`AI operation: ${key}`);
  return value[key];
}
function tool(value: Record<string, unknown>): AgentTool {
  return {
    title: field(value, "title"),
    kind: field(value, "kind"),
    ...(value.target === undefined ? {} : { target: field(value, "target") }),
  };
}
function effects(value: Record<string, unknown>): ExternalEffects {
  const effect = value.external_effects;
  if (effect !== "completed" && effect !== "unknown" && effect !== "none")
    throw new ApiContractError("AI operation: external_effects");
  return effect;
}

/** Parse only redacted public fields; reject unknown event types. */
export function parseAiOperationEvent(value: unknown): AiOperationEvent {
  const event = objectValue(value, "AI operation");
  switch (event.type) {
    case "ready":
      return { type: "ready", operation_id: field(event, "operation_id") };
    case "tool":
      return {
        type: "tool",
        tool_id: field(event, "tool_id"),
        status: field(event, "status"),
        ...tool(event),
      };
    case "permission": {
      if (!Array.isArray(event.options) || event.options.length === 0)
        throw new ApiContractError("AI operation: options");
      return {
        type: "permission",
        permission_id: field(event, "permission_id"),
        tool: tool(objectValue(event.tool, "permission tool")),
        options: event.options.map((value) => {
          const option = objectValue(value, "permission option");
          return {
            option_id: field(option, "option_id"),
            name: field(option, "name"),
            kind: field(option, "kind"),
          };
        }),
      };
    }
    case "completed":
      return { type: "completed", external_effects: effects(event) };
    case "error":
      return { type: "error", message: field(event, "message"), external_effects: effects(event) };
    default:
      throw new ApiContractError(`AI operation: unknown event (${String(event.type)})`);
  }
}
