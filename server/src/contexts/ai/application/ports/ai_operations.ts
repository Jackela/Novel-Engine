import type { TextGenerationExecutionOptions } from "./text_generation.js";

/** Redacted user-facing tool evidence, never raw output or secret arguments. */
export interface AgentTool {
  readonly title: string;
  readonly kind: string;
  readonly target?: string | undefined;
}
export interface AgentPermissionOption {
  readonly option_id: string;
  readonly name: string;
  readonly kind: string;
}
export interface AgentPermissionRequest {
  readonly tool: AgentTool;
  readonly options: readonly AgentPermissionOption[];
}
export type AgentEvent =
  | { readonly type: "ready"; readonly operation_id: string }
  | ({ readonly type: "tool"; readonly tool_id: string; readonly status: string } & AgentTool)
  | ({ readonly type: "permission"; readonly permission_id: string } & AgentPermissionRequest)
  | { readonly type: "completed"; readonly external_effects: "completed" | "unknown" | "none" }
  | {
      readonly type: "error";
      readonly message: string;
      readonly external_effects: "completed" | "unknown" | "none";
    };
export interface AiOperationScope {
  readonly ownerId: string;
  readonly projectId: string;
  readonly operationId: string;
}
export interface AiOperationLease {
  readonly execution: TextGenerationExecutionOptions;
  finish(failure?: unknown): void;
}
/** One app instance owns its ephemeral operations and permission decisions. */
export interface AiOperations {
  register(
    scope: AiOperationScope,
    emit: (event: AgentEvent) => void,
    close: () => void,
  ): { close(): void };
  begin(scope: AiOperationScope): AiOperationLease;
  respond(scope: AiOperationScope, permissionId: string, optionId: string): void;
  close(): void;
}

/** Durable safe tool evidence; uncertainty remains true after a submitted turn loses its outcome. */
export interface AgentExecutionEvidence {
  readonly operation_id: string;
  readonly external_effects: Array<{
    tool_id: string;
    title: string;
    kind: string;
    status: string;
    target?: string | undefined;
  }>;
  outcome_unknown: boolean;
}
