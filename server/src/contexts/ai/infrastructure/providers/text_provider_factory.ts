import type {
  TextGenerationProvider,
  TextGenerationProviderFactory,
  TextProviderName,
} from "../../application/ports/text_generation.js";
import { DeterministicStoryProvider } from "./deterministic_story_provider.js";
import { UnconfiguredTextProvider } from "./unconfigured_provider.js";

/** Hard default models of the server-side resolution chain (per-provider overrides land with the HTTP adapters). */
const HARD_DEFAULT_MODELS: Record<TextProviderName, string> = {
  mock: "deterministic-story-v1",
  dashscope: "qwen3.5-flash",
  openai_compatible: "gpt-4o-mini",
};

export interface ProviderCredentials {
  readonly dashscope?: string | undefined;
  readonly openaiCompatible?: string | undefined;
}

export interface TextProviderFactoryOptions {
  readonly provider: TextProviderName;
  readonly apiKeys: ProviderCredentials;
}

/** The message family for an HTTP provider selected without credentials. */
export function missingCredentialMessage(provider: TextProviderName): string {
  return provider === "dashscope"
    ? "DASHSCOPE_API_KEY is required when provider is dashscope"
    : "LLM_API_KEY is required when provider is openai_compatible";
}

/**
 * Build one provider for one request. Unconfigured HTTP providers fail
 * explicitly on first use — the mock is never a fallback — and a configured
 * provider whose HTTP adapter has not landed says so honestly.
 */
export function createTextGenerationProvider(
  options: TextProviderFactoryOptions,
): TextGenerationProvider {
  const { provider, apiKeys } = options;
  if (provider === "mock") {
    return new DeterministicStoryProvider("mock", HARD_DEFAULT_MODELS.mock);
  }
  const apiKey = provider === "dashscope" ? apiKeys.dashscope : apiKeys.openaiCompatible;
  if (apiKey === undefined || apiKey === "") {
    return new UnconfiguredTextProvider(missingCredentialMessage(provider));
  }
  return new UnconfiguredTextProvider(
    `The ${provider} adapter is not implemented yet; it lands with the HTTP provider adapters`,
  );
}

/** Curry the credentials into the per-request factory the composition root injects. */
export function textProviderFactory(apiKeys: ProviderCredentials): TextGenerationProviderFactory {
  return (provider) => createTextGenerationProvider({ provider, apiKeys });
}

export { HARD_DEFAULT_MODELS };
