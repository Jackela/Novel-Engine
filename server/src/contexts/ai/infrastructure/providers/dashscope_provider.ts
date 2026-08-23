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
  type DashscopeTransport,
  type DashscopeTransportMode,
  extractDashscopeUsageTokens,
  resolveDashscopeTransport,
} from "./dashscope_protocol.js";
import {
  classifyTransportRejection,
  DEFAULT_PROVIDER_RETRY_POLICY,
  effectiveTimeoutSeconds,
  httpStatusFailure,
  malformedJsonFailure,
  type ProviderRetryPolicy,
  type ProviderTransport,
  ProviderTransportError,
  runWithRetryPolicy,
} from "./provider_http.js";

const DEFAULT_MODEL = "qwen3.5-flash";
const DEFAULT_TIMEOUT_SECONDS = 30;
const DEFAULT_TRANSPORT_MODE: DashscopeTransportMode = "multimodal_generation";
const MAX_ERROR_BODY_LENGTH = 1_000;

type JsonObject = Record<string, unknown>;

export interface DashScopeTextProviderOptions {
  readonly apiKey: string;
  readonly model?: string | undefined;
  readonly apiBase?: string | undefined;
  readonly transportMode?: DashscopeTransportMode | undefined;
  readonly timeoutSeconds?: number | undefined;
  readonly retry?: ProviderRetryPolicy | undefined;
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
  if (apiKey === "") throw new TextGenerationProviderError("DashScope API key is required");
  return apiKey;
}

function modelName(value: string | undefined): string {
  const model = value?.trim();
  return model === undefined || model === "" ? DEFAULT_MODEL : model;
}

function normalizedTimeoutSeconds(value: number | undefined): number {
  if (value === undefined || !Number.isFinite(value) || value <= 0) {
    return DEFAULT_TIMEOUT_SECONDS;
  }
  return value;
}

function errorBodyWithoutCredential(body: string, apiKey: string): string {
  return body.slice(0, MAX_ERROR_BODY_LENGTH).split(apiKey).join("[REDACTED]");
}

function supportedStep(step: string): ProviderStep {
  if (!isProviderStep(step)) {
    throw new TextGenerationProviderError(`Unsupported generation step: ${step}`);
  }
  return step;
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
 * Per-request DashScope adapter. It owns no import-time client or mutable
 * state; the composition root constructs an instance for each provider use.
 */
export class DashScopeTextProvider implements TextGenerationProvider {
  private readonly apiKey: string;
  private readonly model: string;
  private readonly apiBase: string | undefined;
  private readonly protocol: DashscopeTransport<DashscopeTransportMode>;
  private readonly timeoutSeconds: number;
  private readonly retry: ProviderRetryPolicy;
  private readonly transport: ProviderTransport | undefined;

  constructor(options: DashScopeTextProviderOptions) {
    this.apiKey = requiredApiKey(options.apiKey);
    this.model = modelName(options.model);
    this.apiBase = options.apiBase;
    this.protocol = resolveDashscopeTransport(options.transportMode ?? DEFAULT_TRANSPORT_MODE);
    this.timeoutSeconds = normalizedTimeoutSeconds(options.timeoutSeconds);
    this.retry = options.retry ?? DEFAULT_PROVIDER_RETRY_POLICY;
    this.transport = options.transport;
  }

  async generateStructured(task: TextGenerationTask): Promise<TextGenerationResult> {
    const step = supportedStep(task.step);
    const timeoutSeconds = effectiveTimeoutSeconds(this.timeoutSeconds, step);
    const context = `DashScope generation failed for step '${step}'`;
    const apiBase = this.protocol.normalizeApiBase(this.apiBase);
    const url = `${apiBase}${this.protocol.endpointPath()}`;

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
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutSeconds * 1_000);
    try {
      const response = await this.dispatch(url, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(this.protocol.buildRequestPayload(this.model, task)),
        signal: controller.signal,
      });
      if (!isResponseLike(response)) {
        throw new ProviderTransportError(`${context}: transport returned no response`);
      }
      if (!response.ok) {
        const responseBody = await readableResponse(response).text();
        throw httpStatusFailure(
          context,
          response.status,
          errorBodyWithoutCredential(responseBody, this.apiKey),
        );
      }

      const data = await responseJsonObject(response, context);
      const contentText = this.protocol.extractResponseText(data);
      const [promptTokens, completionTokens] = extractDashscopeUsageTokens(data);
      const parsed = structuredPayload(contentText, task.responseSchema, context);
      const content = coercePayloadToSchema(parsed, task.responseSchema);
      return {
        step: task.step,
        provider: "dashscope",
        model: this.model,
        rawText: JSON.stringify(content),
        content,
        promptTokens,
        completionTokens,
      };
    } catch (error) {
      throw classifyTransportRejection(error, context, timeoutSeconds);
    } finally {
      clearTimeout(timeout);
    }
  }

  private dispatch(url: string, init: RequestInit): Promise<Response | undefined> {
    if (this.transport !== undefined) return this.transport(url, init);
    if (typeof globalThis.fetch !== "function") {
      throw new ProviderTransportError("DashScope transport is unavailable");
    }
    return globalThis.fetch(url, init);
  }
}
