import { readFile } from "node:fs/promises";
import {
  type ClientConnection,
  type PromptRequest,
  RequestError,
  type SessionConfigOption,
} from "@agentclientprotocol/sdk";
import { createWebSocketStream } from "@agentclientprotocol/sdk/experimental/ws-client";
import WebSocket from "ws";
import {
  isSafeUsageToken,
  ProviderNotConfiguredError,
  TextGenerationCancelledError,
  type TextGenerationExecutionOptions,
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationResult,
  type TextGenerationStreamOptions,
  type TextGenerationTask,
} from "../../application/ports/text_generation.js";
import { AcpJsonResponse } from "./AcpJsonResponse.js";
import { AcpTurnBudget } from "./AcpTurnBudget.js";
import { AcpWorkspace } from "./AcpWorkspace.js";
import { buildAcpClient } from "./buildAcpClient.js";
import { buildAcpSystemContent } from "./buildAcpSystemContent.js";
import { openAcpSession } from "./openAcpSession.js";
import { buildUserContent, structuredPayload, supportedStep } from "./provider_json.js";
import { createChapterMarkdownUnwrapper } from "./stream_json_unwrap.js";

export interface AcpProviderOptions {
  readonly proxyUrl: string;
  readonly tokenFile?: string | undefined;
  readonly command: string;
  readonly args: readonly string[];
  readonly workspaceRoot?: string | undefined;
  readonly model?: string | undefined;
  readonly handshakeMs?: number | undefined;
  readonly executionMs?: number | undefined;
  readonly overallMs?: number | undefined;
}
interface TurnResult {
  readonly text: string;
  readonly model: string;
  readonly promptTokens: number | null;
  readonly completionTokens: number | null;
}
function modelFact(options: readonly SessionConfigOption[] | null | undefined): string | undefined {
  const model = options?.find((option) => option.category === "model" && option.type === "select");
  return model?.type === "select" && model.currentValue.trim() !== ""
    ? model.currentValue
    : undefined;
}
/** One request owns one authenticated ACP connection and session; prompts never replay automatically. */
export class AcpTextProvider implements TextGenerationProvider {
  private connection: ClientConnection | undefined;
  private activeBudget: AcpTurnBudget | undefined;
  constructor(private readonly options: AcpProviderOptions) {
    let url: URL;
    try {
      url = new URL(options.proxyUrl);
    } catch (error) {
      if (!(error instanceof TypeError)) throw error;
      throw new ProviderNotConfiguredError("ACP_PROXY_URL must be an absolute WebSocket URL.");
    }
    if (
      (url.protocol !== "ws:" && url.protocol !== "wss:") ||
      url.username !== "" ||
      url.password !== ""
    )
      throw new ProviderNotConfiguredError(
        "ACP_PROXY_URL must use WebSocket transport without URL credentials.",
      );
  }
  async generateStructured(
    task: TextGenerationTask,
    execution: TextGenerationExecutionOptions = {},
  ): Promise<TextGenerationResult> {
    supportedStep(task.step);
    const result = await this.turn(task, execution, () => {});
    return {
      step: task.step,
      provider: "acp",
      model: result.model,
      rawText: result.text,
      content: structuredPayload(result.text, task.responseSchema, "ACP response"),
      promptTokens: result.promptTokens,
      completionTokens: result.completionTokens,
    };
  }
  async *generateStructuredStreaming(
    task: TextGenerationTask,
    execution: TextGenerationStreamOptions = {},
  ): AsyncGenerator<string, void, void> {
    const step = supportedStep(task.step);
    if (step !== "chapter_draft" && step !== "chapter_revision")
      throw new TextGenerationProviderError("ACP streaming requires a chapter step.");
    const unwrapper = createChapterMarkdownUnwrapper();
    const queue: string[] = [];
    let wake = (): void => {};
    let done = false;
    let failure: unknown;
    let result: TurnResult | undefined;
    const pending = this.turn(task, execution, (fragment) => {
      const delta = unwrapper.feed(fragment);
      if (delta !== undefined) {
        queue.push(delta);
        wake();
      }
    })
      .then((value) => {
        result = value;
      })
      .catch((error: unknown) => {
        failure = error;
      })
      .finally(() => {
        done = true;
        wake();
      });
    try {
      while (!done || queue.length > 0) {
        if (queue.length > 0) {
          yield queue.shift() ?? "";
          continue;
        }
        await new Promise<void>((resolve) => {
          wake = resolve;
        });
      }
      if (failure !== undefined) throw failure;
      if (execution.signal?.aborted) throw new TextGenerationCancelledError();
      unwrapper.finish();
      if (result === undefined)
        throw new TextGenerationProviderError("ACP completed without outcome evidence.");
      structuredPayload(result.text, task.responseSchema, "ACP response");
      execution.onOutcome?.({
        model: result.model,
        promptTokens: result.promptTokens,
        completionTokens: result.completionTokens,
      });
    } finally {
      await this.dispose();
      await pending;
    }
  }
  private async turn(
    task: TextGenerationTask,
    execution: TextGenerationExecutionOptions,
    onText: (fragment: string) => void,
  ): Promise<TurnResult> {
    if (this.options.tokenFile === undefined || this.options.workspaceRoot === undefined)
      throw new ProviderNotConfiguredError(
        "ACP requires ACP_PROXY_TOKEN_FILE and ACP_WORKSPACE_ROOT.",
      );
    const prompt: PromptRequest["prompt"] = [
      {
        type: "text",
        text: `${buildAcpSystemContent(task)}\n\n${buildUserContent(task)}`,
      },
    ];
    // Leave room for the JSON-RPC envelope/session identity inside the gateway frame.
    if (Buffer.byteLength(JSON.stringify(prompt), "utf8") > 1024 * 1024 - 4096)
      throw new TextGenerationProviderError(
        "ACP prompt exceeds the 1 MiB transport budget; shorten the input.",
      );
    const workspace = await AcpWorkspace.open(this.options.workspaceRoot);
    let token: string;
    try {
      token = (await readFile(this.options.tokenFile, "utf8")).trim();
    } catch (error) {
      if (error instanceof Error && "code" in error)
        throw new ProviderNotConfiguredError("ACP proxy token file is unavailable.");
      throw error;
    }
    if (token === "") throw new ProviderNotConfiguredError("ACP proxy token file is empty.");
    const budget = new AcpTurnBudget(
      this.options.handshakeMs ?? 30_000,
      this.options.overallMs ?? 600_000,
      execution.signal,
    );
    this.activeBudget = budget;
    let sessionId: string | undefined;
    let model: string | undefined;
    let text = "";
    const response = new AcpJsonResponse(task.responseSchema);
    const handlers = buildAcpClient({
      budget,
      execution,
      workspace,
      sessionId: () => sessionId,
      onConfigOptions: (options) => {
        model = modelFact(options) ?? model;
      },
      onText: (fragment) => {
        const structured = response.feed(fragment);
        if (structured !== undefined) {
          text += structured;
          onText(structured);
        }
      },
    });
    const stream = createWebSocketStream(this.options.proxyUrl, {
      WebSocket,
      headers: { Authorization: `Bearer ${token}` },
      cookies: "omit",
    });
    const connection = handlers.connect(stream);
    this.connection = connection;
    const cancel = (): void => {
      if (sessionId !== undefined)
        void connection.agent.notify("session/cancel", { sessionId }).catch(() => {});
      connection.close();
    };
    budget.signal.addEventListener("abort", cancel, { once: true });
    try {
      const session = await openAcpSession(connection, this.options, workspace.root, task, budget);
      sessionId = session.sessionId;
      model = modelFact(session.configOptions);
      budget.startExecution(this.options.executionMs ?? 180_000);
      if (execution.agentExecution !== undefined) execution.agentExecution.outcome_unknown = true;
      const outcome = await budget.wait(
        connection.agent.request<"session/prompt">("session/prompt", {
          sessionId,
          prompt,
        }),
      );
      if (budget.signal.aborted || outcome.stopReason === "cancelled")
        throw new TextGenerationCancelledError();
      if (outcome.stopReason !== "end_turn")
        throw new TextGenerationProviderError(
          `ACP prompt stopped with ${outcome.stopReason}; no successful outcome.`,
        );
      if (model === undefined)
        throw new TextGenerationProviderError("ACP completed without an actual model identity.");
      if (execution.agentExecution !== undefined)
        execution.agentExecution.outcome_unknown = execution.agentExecution.external_effects.some(
          (tool) => tool.status !== "completed" && tool.status !== "failed",
        );
      text = response.finish();
      return {
        text,
        model,
        promptTokens: isSafeUsageToken(outcome.usage?.inputTokens)
          ? outcome.usage.inputTokens
          : null,
        completionTokens: isSafeUsageToken(outcome.usage?.outputTokens)
          ? outcome.usage.outputTokens
          : null,
      };
    } catch (error) {
      if (budget.signal.aborted) {
        if (
          budget.failure instanceof TextGenerationCancelledError &&
          execution.agentExecution?.outcome_unknown
        )
          throw new TextGenerationProviderError(
            "ACP turn cancelled after submission; external effects may be unknown.",
          );
        throw budget.failure;
      }
      if (connection.signal.aborted)
        throw new TextGenerationProviderError("ACP connection closed before a complete outcome.");
      if (error instanceof RequestError)
        throw new TextGenerationProviderError(`ACP protocol failed (${error.code}).`);
      throw error;
    } finally {
      budget.signal.removeEventListener("abort", cancel);
      budget.close();
      connection.close();
      this.connection = undefined;
      this.activeBudget = undefined;
    }
  }
  async dispose(): Promise<void> {
    this.activeBudget?.fail(new TextGenerationCancelledError());
    this.connection?.close();
  }
}
