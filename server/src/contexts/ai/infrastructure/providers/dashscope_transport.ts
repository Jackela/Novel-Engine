import {
  TextGenerationProviderError,
  type TextGenerationTask,
} from "../../application/ports/text_generation.js";
import {
  extractDashscopeGenerationText,
  extractDashscopeResponsesText,
  type JsonObject,
} from "./dashscope_extractors.js";
import { buildSystemContent, buildUserContent } from "./provider_json.js";

const DASHSCOPE_API_PATH_SEGMENTS = {
  root: "api",
  nativeVersion: "v1",
  compatibleMode: "compatible-mode",
} as const;

function apiPath(...segments: readonly string[]): string {
  return `/${segments.join("/")}`;
}

const NATIVE_API_PATH = apiPath(
  DASHSCOPE_API_PATH_SEGMENTS.root,
  DASHSCOPE_API_PATH_SEGMENTS.nativeVersion,
);
/**
 * Official OpenAI-compatible Responses path (#502): the legacy `api`-rooted
 * segment chain is no longer maintained upstream, so the default now targets
 * `compatible-mode` + native version. Explicit bases pass through unrewritten.
 */
const RESPONSES_COMPATIBLE_MODE_PATH = apiPath(
  DASHSCOPE_API_PATH_SEGMENTS.compatibleMode,
  DASHSCOPE_API_PATH_SEGMENTS.nativeVersion,
);
const DEFAULT_DASHSCOPE_API_BASE = `https://dashscope.aliyuncs.com${NATIVE_API_PATH}`;
const DEFAULT_DASHSCOPE_RESPONSES_API_BASE = `https://dashscope.aliyuncs.com${RESPONSES_COMPATIBLE_MODE_PATH}`;
const DEFAULT_DASHSCOPE_TEXT_ENDPOINT = "/services/aigc/text-generation/generation";
const DEFAULT_DASHSCOPE_MULTIMODAL_ENDPOINT = "/services/aigc/multimodal-generation/generation";
const DEFAULT_DASHSCOPE_RESPONSES_ENDPOINT = "/responses";
const DEFAULT_TEMPERATURE = 0.7;

export type DashscopeTransportMode = "text_generation" | "multimodal_generation" | "responses";

interface DashscopeGenerationRequest {
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

interface DashscopeResponsesRequest {
  readonly model: string;
  readonly input: string;
  readonly temperature: number;
  readonly response_format: { readonly type: "json_object" };
}

type RequestForMode<Mode extends DashscopeTransportMode> = Mode extends "responses"
  ? DashscopeResponsesRequest
  : DashscopeGenerationRequest;

function normalizedBase(apiBase: string | undefined, fallback: string): string {
  const candidate = apiBase?.trim();
  return (candidate === "" || candidate === undefined ? fallback : candidate).replace(/\/+$/u, "");
}

function parseBaseUrl(base: string): URL {
  try {
    return new URL(base);
  } catch (error) {
    if (error instanceof TypeError) {
      throw new TextGenerationProviderError("DashScope API base must be an absolute URL");
    }
    throw error;
  }
}

function normalizeGenerationBase(apiBase: string | undefined): string {
  const base = normalizedBase(apiBase, DEFAULT_DASHSCOPE_API_BASE);
  const parsed = parseBaseUrl(base);
  return parsed.pathname.includes("compatible-mode") ? `${parsed.origin}${NATIVE_API_PATH}` : base;
}

/**
 * Responses base resolution (#502): the no-config default is the official
 * compatible-mode path; an explicitly configured base is validated as an
 * absolute URL and passed through verbatim (only whitespace and trailing
 * slashes are trimmed) instead of being rewritten to a canonical path.
 */
function normalizeResponsesBase(apiBase: string | undefined): string {
  const base = normalizedBase(apiBase, DEFAULT_DASHSCOPE_RESPONSES_API_BASE);
  parseBaseUrl(base);
  return base;
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
        response_format: { type: "json_object" },
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
