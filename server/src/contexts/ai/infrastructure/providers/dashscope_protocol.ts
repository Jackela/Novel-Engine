import {
  TextGenerationProviderError,
  type TextGenerationTask,
} from "../../application/ports/text_generation.js";

const DASHSCOPE_API_PATH_SEGMENTS = {
  root: "api",
  nativeVersion: "v1",
  compatibleVersion: "v2",
  applications: "apps",
  protocols: "protocols",
  compatibleMode: "compatible-mode",
} as const;

function apiPath(...segments: readonly string[]): string {
  return `/${segments.join("/")}`;
}

const NATIVE_API_PATH = apiPath(
  DASHSCOPE_API_PATH_SEGMENTS.root,
  DASHSCOPE_API_PATH_SEGMENTS.nativeVersion,
);
const COMPATIBLE_MODE_PATH = apiPath(
  DASHSCOPE_API_PATH_SEGMENTS.root,
  DASHSCOPE_API_PATH_SEGMENTS.compatibleVersion,
  DASHSCOPE_API_PATH_SEGMENTS.applications,
  DASHSCOPE_API_PATH_SEGMENTS.protocols,
  DASHSCOPE_API_PATH_SEGMENTS.compatibleMode,
  DASHSCOPE_API_PATH_SEGMENTS.nativeVersion,
);
const DEFAULT_DASHSCOPE_API_BASE = `https://dashscope.aliyuncs.com${NATIVE_API_PATH}`;
const DEFAULT_DASHSCOPE_RESPONSES_API_BASE = `https://dashscope.aliyuncs.com${COMPATIBLE_MODE_PATH}`;
const DEFAULT_DASHSCOPE_TEXT_ENDPOINT = "/services/aigc/text-generation/generation";
const DEFAULT_DASHSCOPE_MULTIMODAL_ENDPOINT = "/services/aigc/multimodal-generation/generation";
const DEFAULT_DASHSCOPE_RESPONSES_ENDPOINT = "/responses";
const DEFAULT_TEMPERATURE = 0.7;

type JsonObject = Record<string, unknown>;

export type DashscopeTransportMode = "text_generation" | "multimodal_generation" | "responses";

export interface DashscopeGenerationRequest {
  readonly model: string;
  readonly input: {
    readonly messages: readonly {
      readonly role: "system" | "user";
      readonly content: string | readonly { readonly text: string }[];
    }[];
  };
  readonly parameters: {
    readonly temperature: number;
    readonly enable_thinking: boolean;
    readonly result_format: "message";
    readonly response_format: { readonly type: "json_object" };
  };
}

export interface DashscopeResponsesRequest {
  readonly model: string;
  readonly input: string;
  readonly temperature: number;
}

type RequestForMode<Mode extends DashscopeTransportMode> = Mode extends "responses"
  ? DashscopeResponsesRequest
  : DashscopeGenerationRequest;

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizedBase(apiBase: string | undefined, fallback: string): string {
  const candidate = apiBase?.trim();
  return (candidate === "" || candidate === undefined ? fallback : candidate).replace(/\/+$/u, "");
}

function parseBaseUrl(base: string): URL {
  try {
    return new URL(base);
  } catch {
    throw new TextGenerationProviderError("DashScope API base must be an absolute URL");
  }
}

function normalizeGenerationBase(apiBase: string | undefined): string {
  const base = normalizedBase(apiBase, DEFAULT_DASHSCOPE_API_BASE);
  const parsed = parseBaseUrl(base);
  return parsed.pathname.includes("compatible-mode") ? `${parsed.origin}${NATIVE_API_PATH}` : base;
}

function normalizeResponsesBase(apiBase: string | undefined): string {
  const base = normalizedBase(apiBase, DEFAULT_DASHSCOPE_RESPONSES_API_BASE);
  const parsed = parseBaseUrl(base);
  return parsed.pathname === COMPATIBLE_MODE_PATH
    ? base
    : `${parsed.origin}${COMPATIBLE_MODE_PATH}`;
}

function buildSystemContent(task: TextGenerationTask): string {
  return `${task.systemPrompt}\nReturn valid JSON only. Output schema: ${JSON.stringify(task.responseSchema)}`;
}

function buildUserContent(task: TextGenerationTask): string {
  return `${task.userPrompt}\nTask step: ${task.step}\nMetadata: ${JSON.stringify(task.metadata)}`;
}

function textFromContent(content: unknown): string | undefined {
  if (typeof content === "string") {
    const text = content.trim();
    return text === "" ? undefined : text;
  }
  if (!Array.isArray(content)) return undefined;
  const text = content
    .filter(
      (part): part is JsonObject =>
        isJsonObject(part) && typeof part.text === "string" && part.text.trim() !== "",
    )
    .map((part) => part.text as string)
    .join("")
    .trim();
  return text === "" ? undefined : text;
}

/** Extract the first structured message text from a native generation response. */
export function extractDashscopeGenerationText(data: JsonObject): string {
  const output = data.output;
  if (!isJsonObject(output))
    throw new TextGenerationProviderError("DashScope response missing output");

  const choices = output.choices;
  if (Array.isArray(choices) && choices.length > 0) {
    const firstChoice = choices[0];
    if (!isJsonObject(firstChoice)) {
      throw new TextGenerationProviderError("DashScope response choice is not an object");
    }
    const message = firstChoice.message;
    if (!isJsonObject(message)) {
      throw new TextGenerationProviderError("DashScope response message is not an object");
    }
    const text = textFromContent(message.content);
    if (text !== undefined) return text;
  }

  const outputText = output.text;
  if (typeof outputText === "string" && outputText.trim() !== "") return outputText.trim();
  throw new TextGenerationProviderError("DashScope response missing structured message content");
}

/** Extract a message item from the compatible Responses API shape. */
export function extractDashscopeResponsesText(data: JsonObject): string {
  const output = data.output;
  if (!Array.isArray(output)) {
    throw new TextGenerationProviderError("DashScope responses output is invalid");
  }
  for (const item of output) {
    if (!isJsonObject(item) || item.type !== "message") continue;
    const text = textFromContent(item.content);
    if (text !== undefined) return text;
  }
  throw new TextGenerationProviderError("DashScope responses output missing message text");
}

function usageToken(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : null;
}

/** Read provider usage structurally; callers fall back to the shared word count when absent. */
export function extractDashscopeUsageTokens(
  data: JsonObject,
): readonly [number | null, number | null] {
  const usage = data.usage;
  if (!isJsonObject(usage)) return [null, null];
  return [
    usageToken(usage.prompt_tokens) ?? usageToken(usage.input_tokens),
    usageToken(usage.completion_tokens) ?? usageToken(usage.output_tokens),
  ];
}

/** Pure transport descriptor; the later adapter owns fetch, timeout, retry, and lifecycle. */
export class DashscopeTransport<Mode extends DashscopeTransportMode> {
  constructor(
    readonly mode: Mode,
    private readonly endpoint: string,
    private readonly responsesApi = false,
    private readonly multimodalContent = false,
  ) {}

  normalizeApiBase(apiBase: string | undefined): string {
    return this.responsesApi ? normalizeResponsesBase(apiBase) : normalizeGenerationBase(apiBase);
  }

  endpointPath(): string {
    return this.endpoint;
  }

  buildRequestPayload(model: string, task: TextGenerationTask): RequestForMode<Mode> {
    if (this.responsesApi) {
      return {
        model,
        input: `System:\n${buildSystemContent(task)}\n\nUser:\n${buildUserContent(task)}`,
        temperature: DEFAULT_TEMPERATURE,
      } as RequestForMode<Mode>;
    }
    const systemContent = buildSystemContent(task);
    const userContent = buildUserContent(task);
    const messageContent = (content: string) =>
      this.multimodalContent ? [{ text: content }] : content;
    return {
      model,
      input: {
        messages: [
          { role: "system", content: messageContent(systemContent) },
          { role: "user", content: messageContent(userContent) },
        ],
      },
      parameters: {
        temperature: DEFAULT_TEMPERATURE,
        enable_thinking: false,
        result_format: "message",
        response_format: { type: "json_object" },
      },
    } as unknown as RequestForMode<Mode>;
  }

  extractResponseText(data: JsonObject): string {
    return this.responsesApi
      ? extractDashscopeResponsesText(data)
      : extractDashscopeGenerationText(data);
  }
}

const RESPONSES_TRANSPORT = new DashscopeTransport(
  "responses",
  DEFAULT_DASHSCOPE_RESPONSES_ENDPOINT,
  true,
);

const TRANSPORTS = {
  text_generation: new DashscopeTransport("text_generation", DEFAULT_DASHSCOPE_TEXT_ENDPOINT),
  multimodal_generation: new DashscopeTransport(
    "multimodal_generation",
    DEFAULT_DASHSCOPE_MULTIMODAL_ENDPOINT,
    false,
    true,
  ),
  responses: RESPONSES_TRANSPORT,
} as const;

/** Resolve a native transport mode; an invalid operational mode falls back to Responses compatibility. */
export function resolveDashscopeTransport<Mode extends DashscopeTransportMode>(
  mode: Mode,
): DashscopeTransport<Mode>;
export function resolveDashscopeTransport(mode: string): DashscopeTransport<DashscopeTransportMode>;
export function resolveDashscopeTransport(
  mode: string,
): DashscopeTransport<DashscopeTransportMode> {
  return TRANSPORTS[mode as DashscopeTransportMode] ?? RESPONSES_TRANSPORT;
}
