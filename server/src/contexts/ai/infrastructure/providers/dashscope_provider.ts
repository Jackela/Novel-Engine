import { HARD_DEFAULT_MODELS } from "../../application/model_resolution.js";
import {
  isProviderStep,
  type ProviderStep,
  type TextGenerationProvider,
  TextGenerationProviderError,
  type TextGenerationResult,
  type TextGenerationStreamOptions,
  type TextGenerationTask,
} from "../../application/ports/text_generation.js";
import { coercePayloadToSchema, payloadFromResponseText } from "./dashscope_payload.js";
import {
  type DashscopeTransport,
  type DashscopeTransportMode,
  extractDashscopeIncrementalText,
  extractDashscopeUsageTokens,
  resolveDashscopeTransport,
} from "./dashscope_protocol.js";
import {
  classifyTransportRejection,
  DEFAULT_PROVIDER_RETRY_POLICY,
  effectiveTimeoutSeconds,
  httpStatusFailure,
  isJsonObject,
  isResponseLike,
  malformedJsonFailure,
  normalizedTimeoutSeconds,
  type ProviderRetryPolicy,
  type ProviderTransport,
  ProviderTransportError,
  readableResponse,
  redactCredentialAndTruncateResponseBody,
  requiredApiKey,
  runWithRetryPolicy,
} from "./provider_http.js";
import { streamProviderTextDeltas } from "./streaming_generation.js";

const DEFAULT_TIMEOUT_SECONDS = 30;
const DEFAULT_TRANSPORT_MODE: DashscopeTransportMode = "multimodal_generation";

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

function modelName(value: string | undefined): string {
  const model = value?.trim();
  return model === undefined || model === "" ? HARD_DEFAULT_MODELS.dashscope : model;
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
 * Stream variant of the protocol payload: native modes read incremental
 * output so each chunk carries a text piece instead of the whole message;
 * payloads without a parameters object pass through unchanged.
 */
function streamingPayload(payload: object): JsonObject {
  const source = payload as JsonObject;
  const parameters = source.parameters;
  if (typeof parameters !== "object" || parameters === null || Array.isArray(parameters)) {
    return source;
  }
  return {
    ...source,
    parameters: { ...(parameters as JsonObject), incremental_output: true },
  };
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
    this.apiKey = requiredApiKey(options.apiKey, "DashScope");
    this.model = modelName(options.model);
    this.apiBase = options.apiBase;
    this.protocol = resolveDashscopeTransport(options.transportMode ?? DEFAULT_TRANSPORT_MODE);
    this.timeoutSeconds = normalizedTimeoutSeconds(options.timeoutSeconds, DEFAULT_TIMEOUT_SECONDS);
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

  /**
   * #308 SSE passthrough: native modes request `incremental_output` chunks
   * and compatible mode relays OpenAI-style deltas; every text piece is
   * yielded as a raw chapter-markdown delta. Usage comes from the final
   * chunk when the provider includes it; absent tokens stay null.
   */
  async *generateStructuredStreaming(
    task: TextGenerationTask,
    options?: TextGenerationStreamOptions,
  ): AsyncGenerator<string, void, void> {
    const step = supportedStep(task.step);
    const apiBase = this.protocol.normalizeApiBase(this.apiBase);
    yield* streamProviderTextDeltas(
      {
        url: `${apiBase}${this.protocol.endpointPath()}`,
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          "X-DashScope-SSE": "enable",
        },
        body: JSON.stringify(streamingPayload(this.protocol.buildRequestPayload(this.model, task))),
        signal: options?.signal,
        context: `DashScope generation failed for step '${step}'`,
        timeoutSeconds: this.timeoutSeconds,
        credential: this.apiKey,
        model: this.model,
      },
      (url, init) => this.dispatch(url, init ?? {}),
      extractDashscopeIncrementalText,
      extractDashscopeUsageTokens,
      options,
    );
  }

  private async generateOnce(
    task: TextGenerationTask,
    timeoutSeconds: number,
    context: string,
    url: string,
  ): Promise<TextGenerationResult> {
    const body = JSON.stringify(this.protocol.buildRequestPayload(this.model, task));
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
