import { HARD_DEFAULT_MODELS } from "../../application/model_resolution.js";
import type {
  TextGenerationProvider,
  TextGenerationResult,
  TextGenerationStreamOptions,
  TextGenerationTask,
} from "../../application/ports/text_generation.js";
import { coercePayloadToSchema } from "./dashscope_payload.js";
import {
  type DashscopeTransport,
  type DashscopeTransportMode,
  extractDashscopeIncrementalText,
  extractDashscopeUsageTokens,
  resolveDashscopeTransport,
} from "./dashscope_protocol.js";
import {
  DEFAULT_PROVIDER_RETRY_POLICY,
  DEFAULT_PROVIDER_TIMEOUT_SECONDS,
  discardHttpFailureResponse,
  effectiveTimeoutSeconds,
  isResponseLike,
  normalizedTimeoutSeconds,
  type ProviderRetryPolicy,
  type ProviderTransport,
  ProviderTransportError,
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
import {
  dispatchProviderResponse,
  startProviderResponseDeadline,
} from "./provider_response_lifecycle.js";
import { streamProviderTextDeltas } from "./streaming_generation.js";

const DEFAULT_TRANSPORT_MODE: DashscopeTransportMode = "multimodal_generation";

export interface DashScopeTextProviderOptions {
  readonly apiKey: string;
  readonly model?: string | undefined;
  readonly apiBase?: string | undefined;
  readonly transportMode?: DashscopeTransportMode | undefined;
  readonly timeoutSeconds?: number | undefined;
  readonly retry?: ProviderRetryPolicy | undefined;
  readonly transport?: ProviderTransport | undefined;
  /** Server-configured silence ceiling before the stream's first byte. */
  readonly firstByteTimeoutMs?: number | undefined;
  /** Server-configured silence ceiling between consecutive stream frames. */
  readonly idleTimeoutMs?: number | undefined;
}

function modelName(value: string | undefined): string {
  const model = value?.trim();
  return model === undefined || model === "" ? HARD_DEFAULT_MODELS.dashscope : model;
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
  private readonly firstByteTimeoutMs: number | undefined;
  private readonly idleTimeoutMs: number | undefined;

  constructor(options: DashScopeTextProviderOptions) {
    this.apiKey = requiredApiKey(options.apiKey, "DashScope");
    this.model = modelName(options.model);
    this.apiBase = options.apiBase;
    this.protocol = resolveDashscopeTransport(options.transportMode ?? DEFAULT_TRANSPORT_MODE);
    this.timeoutSeconds = normalizedTimeoutSeconds(
      options.timeoutSeconds,
      DEFAULT_PROVIDER_TIMEOUT_SECONDS,
    );
    this.retry = options.retry ?? DEFAULT_PROVIDER_RETRY_POLICY;
    this.transport = options.transport;
    this.firstByteTimeoutMs = options.firstByteTimeoutMs;
    this.idleTimeoutMs = options.idleTimeoutMs;
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
        timeoutSeconds: effectiveTimeoutSeconds(this.timeoutSeconds, step),
        model: this.model,
        firstByteTimeoutMs: this.firstByteTimeoutMs,
        idleTimeoutMs: this.idleTimeoutMs,
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
    const deadline = startProviderResponseDeadline(context, timeoutSeconds);
    try {
      const response = await dispatchProviderResponse(
        (target, init) => this.dispatch(target, init ?? {}),
        url,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${this.apiKey}`,
            "Content-Type": "application/json",
          },
          body,
        },
        context,
        deadline,
      );
      if (!isResponseLike(response)) {
        throw new ProviderTransportError(`${context}: transport returned no response`);
      }
      if (!response.ok) {
        throw await discardHttpFailureResponse(context, response, deadline.interrupt);
      }

      const data = await responseJsonObject(response, context, deadline);
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
      deadline.finish();
    }
  }

  private dispatch(url: string, init: RequestInit): Promise<Response | undefined> {
    return providerDispatch(url, init, this.transport, "DashScope");
  }
}
