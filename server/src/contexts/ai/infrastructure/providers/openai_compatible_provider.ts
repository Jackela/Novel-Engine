import { HARD_DEFAULT_MODELS } from "../../application/model_resolution.js";
import {
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationResult,
  type TextGenerationStreamOptions,
  type TextGenerationTask,
} from "../../application/ports/text_generation.js";
import { coercePayloadToSchema } from "./dashscope_payload.js";
import {
  classifyTransportRejection,
  DEFAULT_PROVIDER_RETRY_POLICY,
  effectiveTimeoutSeconds,
  httpStatusFailure,
  isJsonObject,
  isResponseLike,
  normalizedTimeoutSeconds,
  type ProviderRetryPolicy,
  type ProviderTransport,
  ProviderTransportError,
  readableResponse,
  redactCredentialAndTruncateResponseBody,
  requiredApiKey,
  runWithRetryPolicy,
} from "./provider_http.js";
import {
  type JsonObject,
  providerDispatch,
  responseJsonObject,
  structuredPayload,
  supportedStep,
} from "./provider_json.js";
import { streamProviderTextDeltas } from "./streaming_generation.js";

const DEFAULT_API_BASE = "https://api.openai.com/v1";
const DEFAULT_TEMPERATURE = 0.7;
const DEFAULT_TIMEOUT_SECONDS = 30;

export interface OpenAICompatibleTextProviderOptions {
  readonly apiKey: string;
  /** This is resolved by server composition, never by a client request. */
  readonly model?: string | undefined;
  readonly apiBase?: string | undefined;
  readonly timeoutSeconds?: number | undefined;
  readonly retry?: ProviderRetryPolicy | undefined;
  /** Injectable outbound boundary for a per-instance provider. */
  readonly transport?: ProviderTransport | undefined;
}

function modelName(value: string | undefined): string {
  const model = value?.trim();
  return model === undefined || model === "" ? HARD_DEFAULT_MODELS.openai_compatible : model;
}

function normalizedApiBase(value: string | undefined): string {
  const base = (value?.trim() || DEFAULT_API_BASE).replace(/\/+$/u, "");
  try {
    const parsed = new URL(base);
    if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
      throw new TextGenerationProviderError("OpenAI-compatible API base must use HTTP or HTTPS");
    }
    return parsed.toString().replace(/\/+$/u, "");
  } catch (error) {
    if (error instanceof TextGenerationProviderError) throw error;
    if (error instanceof TypeError) {
      throw new TextGenerationProviderError("OpenAI-compatible API base must be an absolute URL");
    }
    throw error;
  }
}

function chatCompletionPayload(model: string, task: TextGenerationTask): JsonObject {
  return {
    model,
    temperature: DEFAULT_TEMPERATURE,
    response_format: { type: "json_object" },
    messages: [
      {
        role: "system",
        content: `${task.systemPrompt}\nReturn valid JSON only. Output schema: ${JSON.stringify(task.responseSchema)}`,
      },
      {
        role: "user",
        content: `${task.userPrompt}\nTask step: ${task.step}\nMetadata: ${JSON.stringify(task.metadata)}`,
      },
    ],
  };
}

function responseContentText(data: JsonObject): string {
  const choices = data.choices;
  if (!Array.isArray(choices) || choices.length === 0) {
    throw new TextGenerationProviderError("OpenAI-compatible response missing choices");
  }
  const firstChoice = choices[0];
  if (!isJsonObject(firstChoice)) {
    throw new TextGenerationProviderError("OpenAI-compatible response choice is not an object");
  }
  const message = firstChoice.message;
  if (!isJsonObject(message)) {
    throw new TextGenerationProviderError("OpenAI-compatible response message is not an object");
  }
  if (typeof message.content !== "string" || message.content.trim() === "") {
    throw new TextGenerationProviderError("OpenAI-compatible response missing message content");
  }
  return message.content.trim();
}

function usageToken(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : null;
}

function usageTokens(data: JsonObject): readonly [number | null, number | null] {
  const usage = data.usage;
  if (!isJsonObject(usage)) return [null, null];
  return [usageToken(usage.prompt_tokens), usageToken(usage.completion_tokens)];
}

/** The incremental content piece of one chat-completions stream chunk. */
function streamDeltaContent(data: JsonObject): string | undefined {
  const choices = data.choices;
  if (!Array.isArray(choices) || choices.length === 0) return undefined;
  const firstChoice = choices[0];
  if (!isJsonObject(firstChoice)) return undefined;
  const delta = firstChoice.delta;
  if (!isJsonObject(delta)) return undefined;
  const content = delta.content;
  return typeof content === "string" && content !== "" ? content : undefined;
}

/**
 * Per-request OpenAI-compatible chat-completions adapter. It owns no imported
 * client or shared mutable state; composition constructs an instance per use.
 */
export class OpenAICompatibleTextProvider implements TextGenerationProvider {
  private readonly apiKey: string;
  private readonly model: string;
  private readonly apiBase: string;
  private readonly timeoutSeconds: number;
  private readonly retry: ProviderRetryPolicy;
  private readonly transport: ProviderTransport | undefined;

  constructor(options: OpenAICompatibleTextProviderOptions) {
    this.apiKey = requiredApiKey(options.apiKey, "OpenAI-compatible");
    this.model = modelName(options.model);
    this.apiBase = normalizedApiBase(options.apiBase);
    this.timeoutSeconds = normalizedTimeoutSeconds(options.timeoutSeconds, DEFAULT_TIMEOUT_SECONDS);
    this.retry = options.retry ?? DEFAULT_PROVIDER_RETRY_POLICY;
    this.transport = options.transport;
  }

  async generateStructured(task: TextGenerationTask): Promise<TextGenerationResult> {
    const step = supportedStep(task.step);
    const timeoutSeconds = effectiveTimeoutSeconds(this.timeoutSeconds, step);
    const context = `OpenAI-compatible generation failed for step '${step}'`;
    const url = `${this.apiBase}/chat/completions`;

    return runWithRetryPolicy(this.retry, () =>
      this.generateOnce(task, timeoutSeconds, context, url),
    );
  }

  /**
   * #308 SSE passthrough: `stream=true` chat completions relayed as raw
   * chapter-markdown deltas. Usage comes from the final chunk when the
   * provider includes it (`stream_options.include_usage`); absent tokens
   * stay null so the caller's word-count fallback applies.
   */
  async *generateStructuredStreaming(
    task: TextGenerationTask,
    options?: TextGenerationStreamOptions,
  ): AsyncGenerator<string, void, void> {
    const step = supportedStep(task.step);
    yield* streamProviderTextDeltas(
      {
        url: `${this.apiBase}/chat/completions`,
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({
          ...chatCompletionPayload(this.model, task),
          stream: true,
          stream_options: { include_usage: true },
        }),
        signal: options?.signal,
        context: `OpenAI-compatible generation failed for step '${step}'`,
        timeoutSeconds: this.timeoutSeconds,
        credential: this.apiKey,
        model: this.model,
      },
      (url, init) => this.dispatch(url, init ?? {}),
      streamDeltaContent,
      usageTokens,
      options,
    );
  }

  private async generateOnce(
    task: TextGenerationTask,
    timeoutSeconds: number,
    context: string,
    url: string,
  ): Promise<TextGenerationResult> {
    const body = JSON.stringify(chatCompletionPayload(this.model, task));
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutSeconds * 1_000);
    try {
      let response: Response | undefined;
      try {
        response = await this.dispatch(url, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${this.apiKey}`,
            "Content-Type": "application/json",
          },
          body,
          signal: controller.signal,
        });
      } catch (error) {
        throw classifyTransportRejection(error, context, timeoutSeconds);
      }
      if (!isResponseLike(response)) {
        throw new ProviderTransportError(`${context}: transport returned no response`);
      }
      if (!response.ok) {
        const responseBody = await readableResponse(response).text();
        throw httpStatusFailure(
          context,
          response.status,
          redactCredentialAndTruncateResponseBody(responseBody, this.apiKey),
        );
      }

      const data = await responseJsonObject(response, context);
      const contentText = responseContentText(data);
      const content = coercePayloadToSchema(
        structuredPayload(contentText, task.responseSchema, context),
        task.responseSchema,
      );
      const [promptTokens, completionTokens] = usageTokens(data);
      return {
        step: task.step,
        provider: "openai_compatible",
        model: this.model,
        rawText: JSON.stringify(content),
        content,
        promptTokens,
        completionTokens,
      };
    } finally {
      clearTimeout(timeout);
    }
  }

  private dispatch(url: string, init: RequestInit): Promise<Response | undefined> {
    return providerDispatch(url, init, this.transport, "OpenAI-compatible");
  }
}
