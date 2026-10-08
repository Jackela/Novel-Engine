import { randomUUID } from "node:crypto";
import { client, type SessionConfigOption } from "@agentclientprotocol/sdk";
import {
  TextGenerationCancelledError,
  type TextGenerationExecutionOptions,
  TextGenerationProviderError,
} from "../../application/ports/text_generation.js";
import type { AcpTurnBudget } from "./AcpTurnBudget.js";
import type { AcpWorkspace } from "./AcpWorkspace.js";

interface Inputs {
  readonly budget: AcpTurnBudget;
  readonly execution: TextGenerationExecutionOptions;
  readonly workspace: AcpWorkspace;
  readonly sessionId: () => string | undefined;
  readonly onText: (fragment: string) => void;
  readonly onConfigOptions: (options: readonly SessionConfigOption[]) => void;
}
/** Typed ACP client handlers expose only safe tool summaries and confined material callbacks. */
export function buildAcpClient({
  budget,
  execution,
  workspace,
  sessionId,
  onText,
  onConfigOptions,
}: Inputs) {
  const tools = new Map<
    string,
    { title: string; kind: string; status: string; target?: string | undefined }
  >();
  return client({ name: "novel-engine" })
    .onNotification("session/update", ({ params: { sessionId: incoming, update } }) => {
      if (incoming !== sessionId() || budget.signal.aborted) return;
      try {
        if (update.sessionUpdate === "agent_message_chunk" && update.content.type === "text") {
          onText(update.content.text);
        } else if (update.sessionUpdate === "config_option_update")
          onConfigOptions(update.configOptions);
        else if (
          update.sessionUpdate === "tool_call" ||
          update.sessionUpdate === "tool_call_update"
        ) {
          const previous = tools.get(update.toolCallId);
          const tool = {
            title: safeToolTitle(update.title ?? previous?.title ?? "Agent tool"),
            target:
              update.locations === undefined
                ? previous?.target
                : workspace.safeTarget(update.locations?.[0]?.path),
            kind: update.kind ?? previous?.kind ?? "other",
            status: update.status ?? previous?.status ?? "pending",
          };
          tools.set(update.toolCallId, tool);
          execution.onAgentEvent?.({ type: "tool", tool_id: update.toolCallId, ...tool });
        }
      } catch (error) {
        budget.fail(error);
      }
    })
    .onRequest("session/request_permission", async ({ params: request }) => {
      if (request.sessionId !== sessionId())
        throw new TextGenerationProviderError("ACP permission names another session.");
      if (execution.requestPermission === undefined) {
        budget.fail(
          new TextGenerationProviderError(
            "ACP permission requires an active AI interaction channel.",
          ),
        );
        return { outcome: { outcome: "cancelled" } };
      }
      budget.pause();
      try {
        const selected = await budget.wait(
          execution.requestPermission({
            tool: {
              title: safeToolTitle(request.toolCall.title ?? "Agent tool"),
              target: workspace.safeTarget(request.toolCall.locations?.[0]?.path),
              kind: request.toolCall.kind ?? "other",
            },
            options: request.options.map((option) => ({
              option_id: option.optionId,
              name: safeToolTitle(option.name),
              kind: option.kind,
            })),
          }),
        );
        if (selected === null || budget.signal.aborted) {
          budget.fail(new TextGenerationCancelledError());
          return { outcome: { outcome: "cancelled" } };
        }
        if (!request.options.some((option) => option.optionId === selected))
          throw new TextGenerationProviderError("ACP permission selected an unknown option.");
        return { outcome: { outcome: "selected", optionId: selected } };
      } finally {
        budget.resume();
      }
    })
    .onRequest("fs/read_text_file", ({ params: request }) => {
      if (request.sessionId !== sessionId())
        throw new TextGenerationProviderError("ACP file request names another session.");
      if (budget.signal.aborted) throw new TextGenerationCancelledError();
      return workspace.read(request);
    })
    .onRequest("fs/write_text_file", async ({ params: request }) => {
      if (request.sessionId !== sessionId())
        throw new TextGenerationProviderError("ACP file request names another session.");
      if (budget.signal.aborted) throw new TextGenerationCancelledError();
      const effect = {
        type: "tool" as const,
        tool_id: `novel-engine:client-write:${randomUUID()}`,
        title: "Write material file",
        kind: "edit",
        target: workspace.safeTarget(request.path),
      };
      execution.onAgentEvent?.({ ...effect, status: "in_progress" });
      try {
        await workspace.write(request);
      } catch (error) {
        // A failed write may have truncated or partially changed the file.
        // Keep uncertainty even if the agent recovers and completes its prompt.
        if (!budget.signal.aborted) execution.onAgentEvent?.({ ...effect, status: "unknown" });
        throw error;
      }
      // A disconnected operation has already persisted its in-progress evidence;
      // a late filesystem completion must not relabel that captured uncertainty.
      if (budget.signal.aborted) throw new TextGenerationCancelledError();
      execution.onAgentEvent?.({ ...effect, status: "completed" });
    });
}

/** Tool labels are display evidence; credential-like fragments and control characters are removed. */
function safeToolTitle(value: string): string {
  return value
    .replace(/\p{Cc}/gu, " ")
    .replace(/\b(?:api[_ -]?key|token|password|secret|authorization)\s*[:=]\s*\S+/giu, "[redacted]")
    .replace(/\b(?:sk-|xai-)[A-Za-z0-9_-]{12,}/gu, "[redacted]")
    .slice(0, 200);
}
