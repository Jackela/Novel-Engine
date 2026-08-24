import { HARD_DEFAULT_MODELS } from "../../application/model_resolution.js";
import {
  isProviderStep,
  type ProviderStep,
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationResult,
  type TextGenerationTask,
} from "../../application/ports/text_generation.js";
import { coercePayloadToSchema, payloadFromResponseText } from "./dashscope_payload.js";
import {
  classifyTransportRejection,
  DEFAULT_PROVIDER_RETRY_POLICY,
  effectiveTimeoutSeconds,
  httpStatusFailure,
  malformedJsonFailure,
  type ProviderRetryPolicy,
  type ProviderTransport,
  ProviderTransportError,
  redactCredentialAndTruncateResponseBody,
  runWithRetryPolicy,
} from "./provider_http.js";

const DEFAULT_API_BASE = "https://api.openai.com/v1";
const DEFAULT_TEMPERATURE = 0.7;
const DEFAULT_TIMEOUT_SECONDS = 30;

type JsonObject = Record<string, unknown>;

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

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isResponseLike(value: unknown): value is Response {
  if (!isJsonObject(value)) return false;
  return (
    typeof value.ok === "boolean" &&
    typeof value.status === "number" &&
    typeof value.text === "function" &&
    typeof value.json === "function"
  );
}

function readableResponse(response: Response): Response {
  return typeof response.clone === "function" ? response.clone() : response;
}

function requiredApiKey(value: string): string {
  const apiKey = value.trim();
  if (apiKey === "") {
    throw new TextGenerationProviderError("OpenAI-compatible API key is required");
  }
  return apiKey;
}

function modelName(value: string | undefined): string {
  const model = value?.trim();
  return model === undefined || model === "" ? HARD_DEFAULT_MODELS.openai_compatible : model;
}

function normalizedTimeoutSeconds(value: number | undefined): number {
  if (value === undefined || !Number.isFinite(value) || value <= 0) {
    return DEFAULT_TIMEOUT_SECONDS;
  }
  return value;
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

function supportedStep(step: string): ProviderStep {
  if (!isProviderStep(step)) {
    throw new TextGenerationProviderError(`Unsupported generation step: ${step}`);
  }
  return step;
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

async function responseJsonObject(response: Response, context: string): Promise<JsonObject> {
  try {
    const data: unknown = await readableResponse(response).json();
    if (!isJsonObject(data)) throw malformedJsonFailure(context);
    return data;
  } catch (error) {
    if (error instanceof ProviderTransportError) throw error;
    if (error instanceof SyntaxError) throw malformedJsonFailure(context);
    throw error;
  }
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

function structuredPayload(
  contentText: string,
  responseSchema: JsonObject,
  context: string,
): JsonObject {
  try {
    return payloadFromResponseText(contentText, responseSchema);
  } catch (error) {
    if (error instanceof TextGenerationProviderError) throw malformedJsonFailure(context);
    throw error;
  }
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
    this.apiKey = requiredApiKey(options.apiKey);
    this.model = modelName(options.model);
    this.apiBase = normalizedApiBase(options.apiBase);
    this.timeoutSeconds = normalizedTimeoutSeconds(options.timeoutSeconds);
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
    if (this.transport !== undefined) return this.transport(url, init);
    if (typeof globalThis.fetch !== "function") {
      throw new ProviderTransportError("OpenAI-compatible transport is unavailable");
    }
    return globalThis.fetch(url, init);
  }
}
