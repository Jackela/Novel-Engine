import { ConfigurationError } from "./configuration_error.js";
import { integerFrom, numberFrom, stringFrom } from "./env_values.js";

const LLM_PROVIDERS = ["mock", "dashscope", "openai_compatible", "acp"] as const;
const DASHSCOPE_TRANSPORT_MODES = [
  "text_generation",
  "multimodal_generation",
  "responses",
] as const;

// Mirrors DEFAULT_PROVIDER_TIMEOUT_SECONDS in ai/infrastructure/providers/
// provider_http.ts; shared never imports bounded contexts, so the value is
// kept in step deliberately.
const DEFAULT_LLM_TIMEOUT_SECONDS = 30;
const MIN_LLM_TIMEOUT_SECONDS = 5;
const MAX_LLM_TIMEOUT_SECONDS = 300;
const DEFAULT_LLM_RETRY_ATTEMPTS = 3;
const MAX_LLM_RETRY_ATTEMPTS = 3;
const DEFAULT_LLM_RETRY_DELAY_SECONDS = 1;
const MIN_LLM_RETRY_DELAY_SECONDS = 0.1;
const MAX_LLM_RETRY_DELAY_SECONDS = 10;
// Mirror DEFAULT_STREAM_FIRST_BYTE_TIMEOUT_MS and DEFAULT_STREAM_IDLE_TIMEOUT_MS
// in ai/infrastructure/providers/streaming_generation.ts; shared never imports
// bounded contexts, so the values are kept in step deliberately. The ceiling
// matches the outbound provider timeout budget (MAX_LLM_TIMEOUT_SECONDS).
const DEFAULT_LLM_STREAM_FIRST_BYTE_TIMEOUT_MS = 30_000;
const DEFAULT_LLM_STREAM_IDLE_TIMEOUT_MS = 60_000;
const MIN_LLM_STREAM_TIMEOUT_MS = 1;
const MAX_LLM_STREAM_TIMEOUT_MS = MAX_LLM_TIMEOUT_SECONDS * 1_000;
// Mirror of DEFAULT_LOREBOOK_BUDGET_CHARACTERS in studio/application/
// lore_injection.ts (#445); shared never imports bounded contexts, so the
// value is kept in step deliberately. The ceiling stays generous because the
// budget bounds a prompt section, not a transport frame.
const DEFAULT_LOREBOOK_BUDGET_CHARACTERS = 4_000;
const MIN_LOREBOOK_BUDGET_CHARACTERS = 1;
const MAX_LOREBOOK_BUDGET_CHARACTERS = 1_000_000;

export type LlmProvider = (typeof LLM_PROVIDERS)[number];
export type DashscopeTransportMode = (typeof DASHSCOPE_TRANSPORT_MODES)[number];

/** Server-only provider settings; clients select providers but never models. */
export interface LlmServerConfig {
  readonly defaultProvider: LlmProvider;
  readonly acp?:
    | {
        readonly proxyUrl: string;
        readonly tokenFile: string | undefined;
        readonly command: string;
        readonly args: readonly string[];
        readonly workspaceRoot: string | undefined;
        readonly model: string | undefined;
      }
    | undefined;
  readonly genericModel: string | undefined;
  readonly dashscopeModel: string | undefined;
  readonly dashscopeReviewModel: string | undefined;
  readonly openaiCompatibleModel: string | undefined;
  readonly dashscopeApiKey: string | undefined;
  readonly dashscopeApiBase: string | undefined;
  readonly openaiCompatibleApiKey: string | undefined;
  readonly openaiCompatibleApiBase: string | undefined;
  readonly dashscopeTransportMode: DashscopeTransportMode;
  readonly timeoutSeconds: number;
  readonly retryAttempts: number;
  readonly retryDelayMs: number;
  /** Server-wide silence ceiling (ms) before an SSE stream sends its first byte. */
  readonly streamFirstByteTimeoutMs: number;
  /** Server-wide silence ceiling (ms) between consecutive SSE stream frames. */
  readonly streamIdleTimeoutMs: number;
  /** Character budget of the lorebook prompt section (#445, ADR-0006). */
  readonly lorebookBudgetCharacters: number;
}

/**
 * Parse lower-case merged environment values into the server-owned LLM
 * configuration seam. It has no application or provider implementation
 * dependencies, and errors deliberately name the setting instead of echoing
 * it: only the numeric bounds quote the rejected value, never a string or
 * credential-shaped setting.
 */
export function loadLlmServerConfig(env: ReadonlyMap<string, string>): LlmServerConfig {
  return {
    defaultProvider: enumFrom(env, "LLM_PROVIDER", LLM_PROVIDERS, "mock"),
    acp: {
      proxyUrl: nonBlankStringFrom(env, "ACP_PROXY_URL") ?? "ws://127.0.0.1:8710/acp",
      tokenFile: nonBlankStringFrom(env, "ACP_PROXY_TOKEN_FILE"),
      command: nonBlankStringFrom(env, "ACP_AGENT_COMMAND") ?? "grok",
      args: acpArgs(env),
      workspaceRoot: nonBlankStringFrom(env, "ACP_WORKSPACE_ROOT"),
      model: nonBlankStringFrom(env, "ACP_MODEL"),
    },
    genericModel: nonBlankStringFrom(env, "LLM_MODEL"),
    dashscopeModel: nonBlankStringFrom(env, "DASHSCOPE_MODEL"),
    dashscopeReviewModel: nonBlankStringFrom(env, "DASHSCOPE_REVIEW_MODEL"),
    openaiCompatibleModel: nonBlankStringFrom(env, "OPENAI_COMPATIBLE_MODEL"),
    dashscopeApiKey: nonBlankStringFrom(env, "DASHSCOPE_API_KEY"),
    dashscopeApiBase: nonBlankStringFrom(env, "DASHSCOPE_API_BASE"),
    openaiCompatibleApiKey: firstNonBlankStringFrom(env, ["LLM_API_KEY", "OPENAI_API_KEY"]),
    openaiCompatibleApiBase: firstNonBlankStringFrom(env, ["LLM_API_BASE", "OPENAI_API_BASE"]),
    dashscopeTransportMode: enumFrom(
      env,
      "DASHSCOPE_TRANSPORT_MODE",
      DASHSCOPE_TRANSPORT_MODES,
      "multimodal_generation",
    ),
    timeoutSeconds: integerFrom(
      env,
      "LLM_TIMEOUT",
      DEFAULT_LLM_TIMEOUT_SECONDS,
      MIN_LLM_TIMEOUT_SECONDS,
      MAX_LLM_TIMEOUT_SECONDS,
    ),
    retryAttempts: integerFrom(
      env,
      "LLM_RETRY_ATTEMPTS",
      DEFAULT_LLM_RETRY_ATTEMPTS,
      1,
      MAX_LLM_RETRY_ATTEMPTS,
    ),
    retryDelayMs:
      numberFrom(
        env,
        "LLM_RETRY_DELAY",
        DEFAULT_LLM_RETRY_DELAY_SECONDS,
        MIN_LLM_RETRY_DELAY_SECONDS,
        MAX_LLM_RETRY_DELAY_SECONDS,
      ) * 1_000,
    streamFirstByteTimeoutMs: integerFrom(
      env,
      "LLM_STREAM_FIRST_BYTE_TIMEOUT_MS",
      DEFAULT_LLM_STREAM_FIRST_BYTE_TIMEOUT_MS,
      MIN_LLM_STREAM_TIMEOUT_MS,
      MAX_LLM_STREAM_TIMEOUT_MS,
    ),
    streamIdleTimeoutMs: integerFrom(
      env,
      "LLM_STREAM_IDLE_TIMEOUT_MS",
      DEFAULT_LLM_STREAM_IDLE_TIMEOUT_MS,
      MIN_LLM_STREAM_TIMEOUT_MS,
      MAX_LLM_STREAM_TIMEOUT_MS,
    ),
    lorebookBudgetCharacters: integerFrom(
      env,
      "LLM_LOREBOOK_BUDGET_CHARACTERS",
      DEFAULT_LOREBOOK_BUDGET_CHARACTERS,
      MIN_LOREBOOK_BUDGET_CHARACTERS,
      MAX_LOREBOOK_BUDGET_CHARACTERS,
    ),
  };
}

function nonBlankStringFrom(env: ReadonlyMap<string, string>, key: string): string | undefined {
  const value = stringFrom(env, key)?.trim();
  return value === "" || value === undefined ? undefined : value;
}

function firstNonBlankStringFrom(
  env: ReadonlyMap<string, string>,
  keys: readonly string[],
): string | undefined {
  for (const key of keys) {
    const value = nonBlankStringFrom(env, key);
    if (value !== undefined) return value;
  }
  return undefined;
}

function enumFrom<Values extends readonly string[]>(
  env: ReadonlyMap<string, string>,
  key: string,
  values: Values,
  fallback: Values[number],
): Values[number] {
  const value = stringFrom(env, key)?.trim().toLowerCase();
  if (value === undefined || value === "") return fallback;
  if (!values.includes(value)) {
    throw new ConfigurationError(`${key} must be one of ${values.join(", ")}`);
  }
  return value as Values[number];
}

/** Parse a command argument array without a shell; values are never echoed on refusal. */
function acpArgs(env: ReadonlyMap<string, string>): readonly string[] {
  const raw = nonBlankStringFrom(env, "ACP_AGENT_ARGS");
  if (raw === undefined)
    return ["--no-auto-update", "--sandbox", "novel-engine", "agent", "--no-leader", "stdio"];
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    if (!(error instanceof SyntaxError)) throw error;
    throw new ConfigurationError("ACP_AGENT_ARGS must be a JSON string array.");
  }
  if (!Array.isArray(parsed) || parsed.some((arg) => typeof arg !== "string" || arg.includes("\0")))
    throw new ConfigurationError("ACP_AGENT_ARGS must be a JSON string array.");
  return parsed;
}
