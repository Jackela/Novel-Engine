import { randomUUID } from "node:crypto";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type {
  AgentEvent,
  AgentExecutionEvidence,
  AgentPermissionRequest,
  AiOperationLease,
  AiOperationScope,
  AiOperations,
} from "../application/ports/ai_operations.js";
import { TextGenerationCancelledError } from "../application/ports/text_generation.js";

interface Channel {
  scope: AiOperationScope;
  emit: (event: AgentEvent) => void;
  close: () => void;
  abort: AbortController;
  active: boolean;
  timer: ReturnType<typeof setTimeout>;
  pending: Map<
    string,
    {
      options: Set<string>;
      resolve: (value: string | null) => void;
      timer: ReturnType<typeof setTimeout>;
    }
  >;
  effects: "completed" | "unknown" | "none";
}
/** Bounded app-owned channels; disconnected, expired and consumed decisions refuse reuse. */
export class AiOperationRegistry implements AiOperations {
  private readonly channels = new Map<string, Channel>();
  constructor(
    private readonly waitingMs = 60_000,
    private readonly permissionMs = 120_000,
  ) {}
  register(
    scope: AiOperationScope,
    emit: (event: AgentEvent) => void,
    close: () => void,
  ): { close(): void } {
    if (this.channels.has(scope.operationId))
      throw new InvalidOperationError("AI operation already exists.");
    const channel: Channel = {
      scope,
      emit,
      close,
      abort: new AbortController(),
      active: false,
      timer: setTimeout(() => this.remove(scope.operationId), this.waitingMs),
      pending: new Map(),
      effects: "none",
    };
    channel.timer.unref();
    this.channels.set(scope.operationId, channel);
    try {
      emit({ type: "ready", operation_id: scope.operationId });
    } catch (error) {
      this.remove(scope.operationId);
      throw error;
    }
    return { close: () => this.remove(scope.operationId) };
  }
  begin(scope: AiOperationScope): AiOperationLease {
    const channel = this.find(scope);
    if (channel.active) throw new InvalidOperationError("AI operation already started.");
    channel.active = true;
    clearTimeout(channel.timer);
    let finished = false;
    const evidence: AgentExecutionEvidence = {
      operation_id: scope.operationId,
      external_effects: [],
      outcome_unknown: false,
    };
    return {
      execution: {
        agentExecution: evidence,
        operationId: scope.operationId,
        signal: channel.abort.signal,
        onAgentEvent: (event) => {
          if (channel.abort.signal.aborted) throw new TextGenerationCancelledError();
          if (event.type === "tool")
            channel.effects = event.status === "completed" ? "completed" : "unknown";
          channel.emit(event);
        },
        requestPermission: (request) => this.permission(channel, request),
      },
      finish: (failure) => {
        if (finished) return;
        finished = true;
        if (this.channels.get(scope.operationId) !== channel) return;
        try {
          channel.emit(
            failure === undefined
              ? {
                  type: "completed",
                  external_effects: evidence.outcome_unknown ? "unknown" : channel.effects,
                }
              : {
                  type: "error",
                  message: "AI operation failed or was cancelled.",
                  external_effects: evidence.outcome_unknown ? "unknown" : channel.effects,
                },
          );
        } finally {
          this.remove(scope.operationId);
        }
      },
    };
  }
  respond(scope: AiOperationScope, permissionId: string, optionId: string): void {
    const channel = this.find(scope);
    const pending = channel.pending.get(permissionId);
    if (!channel.active || pending === undefined || !pending.options.has(optionId)) {
      throw new InvalidOperationError("Permission is expired, consumed, or has an invalid option.");
    }
    clearTimeout(pending.timer);
    channel.pending.delete(permissionId);
    pending.resolve(optionId);
  }
  private permission(channel: Channel, request: AgentPermissionRequest): Promise<string | null> {
    if (channel.abort.signal.aborted) return Promise.reject(new TextGenerationCancelledError());
    const permissionId = randomUUID();
    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        channel.pending.delete(permissionId);
        resolve(null);
      }, this.permissionMs);
      timer.unref();
      channel.pending.set(permissionId, {
        options: new Set(request.options.map((option) => option.option_id)),
        resolve,
        timer,
      });
      channel.emit({ type: "permission", permission_id: permissionId, ...request });
    });
  }
  private find(scope: AiOperationScope): Channel {
    const channel = this.channels.get(scope.operationId);
    if (
      channel === undefined ||
      channel.scope.ownerId !== scope.ownerId ||
      channel.scope.projectId !== scope.projectId ||
      channel.abort.signal.aborted
    ) {
      throw new InvalidOperationError(
        "AI operation channel is unavailable for this project and owner.",
      );
    }
    return channel;
  }
  private remove(operationId: string): void {
    const channel = this.channels.get(operationId);
    if (channel === undefined) return;
    this.channels.delete(operationId);
    clearTimeout(channel.timer);
    channel.abort.abort();
    for (const pending of channel.pending.values()) {
      clearTimeout(pending.timer);
      pending.resolve(null);
    }
    channel.pending.clear();
    channel.close();
  }
  close(): void {
    for (const id of this.channels.keys()) this.remove(id);
  }
}
