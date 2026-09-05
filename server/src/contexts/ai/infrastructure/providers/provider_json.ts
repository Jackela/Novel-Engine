import {
  isProviderStep,
  type ProviderStep,
  TextGenerationProviderError,
  type TextGenerationTask,
} from "../../application/ports/text_generation.js";
import { payloadFromResponseText } from "./dashscope_payload.js";
import {
  isJsonObject,
  malformedJsonFailure,
  type ProviderTransport,
  ProviderTransportError,
} from "./provider_http.js";
import {
  boundedProviderResponseText,
  type ProviderResponseDeadline,
} from "./provider_response_lifecycle.js";

/** Shared system prompt channel: the JSON-only schema contract, verbatim. */
export function buildSystemContent(task: TextGenerationTask): string {
  return `${task.systemPrompt}\nReturn valid JSON only. Output schema: ${JSON.stringify(task.responseSchema)}`;
}

/** Shared user prompt channel: step and metadata suffixes, verbatim. */
export function buildUserContent(task: TextGenerationTask): string {
  return `${task.userPrompt}\nTask step: ${task.step}\nMetadata: ${JSON.stringify(task.metadata)}`;
}

/** JSON-object payload shape shared by provider request/response helpers. */
export type JsonObject = Record<string, unknown>;

export function supportedStep(step: string): ProviderStep {
  if (!isProviderStep(step)) {
    throw new TextGenerationProviderError(`Unsupported generation step: ${step}`);
  }
  return step;
}

export async function responseJsonObject(
  response: Response,
  context: string,
  deadline?: ProviderResponseDeadline | undefined,
): Promise<JsonObject> {
  try {
    const text = await boundedProviderResponseText(response, context, deadline);
    const data: unknown = JSON.parse(text);
    if (!isJsonObject(data)) throw malformedJsonFailure(context);
    return data;
  } catch (error) {
    if (error instanceof ProviderTransportError) throw error;
    if (error instanceof SyntaxError) throw malformedJsonFailure(context);
    throw error;
  }
}

export function structuredPayload(
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
 * Shared outbound dispatch: use the injected transport when present, else
 * global fetch. The provider label keeps each availability message verbatim.
 */
export function providerDispatch(
  url: string,
  init: RequestInit,
  transport: ProviderTransport | undefined,
  providerLabel: string,
): Promise<Response | undefined> {
  if (transport !== undefined) return transport(url, init);
  if (typeof globalThis.fetch !== "function") {
    throw new ProviderTransportError(`${providerLabel} transport is unavailable`);
  }
  return globalThis.fetch(url, init);
}
