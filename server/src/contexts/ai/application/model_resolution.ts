import { PROVIDER_NAMES, type TextProviderName } from "./ports/text_generation.js";

/** Server-owned fallback models; proposal requests never carry a model value. */
export const HARD_DEFAULT_MODELS = {
  mock: "deterministic-story-v1",
  dashscope: "qwen3.5-flash",
  openai_compatible: "gpt-4o-mini",
} as const satisfies Record<TextProviderName, string>;

/** Optional server configuration for the provider-model resolution chain. */
export interface LlmModelSettings {
  readonly genericModel?: string | undefined;
  readonly dashscopeModel?: string | undefined;
  readonly openaiCompatibleModel?: string | undefined;
  readonly dashscopeReviewModel?: string | undefined;
}

interface ProviderCredentials {
  readonly dashscope?: string | undefined;
  readonly openaiCompatible?: string | undefined;
}

export interface ProviderCatalogOptions {
  readonly defaultProvider: TextProviderName;
  readonly settings: LlmModelSettings;
  readonly credentials: ProviderCredentials;
}

export interface ProviderCatalogEntry {
  readonly provider: TextProviderName;
  readonly configured: boolean;
  readonly model: string;
  readonly is_default: boolean;
}

function nonBlank(value: string | undefined): string | undefined {
  const normalized = value?.trim();
  return normalized === "" ? undefined : normalized;
}

function providerOverride(
  provider: TextProviderName,
  settings: LlmModelSettings,
): string | undefined {
  if (provider === "dashscope") return nonBlank(settings.dashscopeModel);
  if (provider === "openai_compatible") return nonBlank(settings.openaiCompatibleModel);
  return undefined;
}

/** Resolve a model from server configuration, never from a client request. */
export function resolveProviderModel(
  provider: TextProviderName,
  settings: LlmModelSettings = {},
): string {
  return (
    providerOverride(provider, settings) ??
    nonBlank(settings.genericModel) ??
    HARD_DEFAULT_MODELS[provider]
  );
}

/** Reviews use the DashScope-specific reviewer override before the normal chain. */
export function resolveReviewModel(
  provider: TextProviderName,
  settings: LlmModelSettings = {},
): string {
  if (provider === "dashscope") {
    return nonBlank(settings.dashscopeReviewModel) ?? resolveProviderModel(provider, settings);
  }
  return resolveProviderModel(provider, settings);
}

function isConfigured(provider: TextProviderName, credentials: ProviderCredentials): boolean {
  if (provider === "mock") return true;
  const credential =
    provider === "dashscope" ? credentials.dashscope : credentials.openaiCompatible;
  return nonBlank(credential) !== undefined;
}

/** Build the server-owned provider facts exposed by the provider catalog endpoint. */
export function buildProviderCatalog(options: ProviderCatalogOptions): ProviderCatalogEntry[] {
  return PROVIDER_NAMES.map((provider) => ({
    provider,
    configured: isConfigured(provider, options.credentials),
    model: resolveProviderModel(provider, options.settings),
    is_default: provider === options.defaultProvider,
  }));
}
