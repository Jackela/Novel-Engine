import { type LlmModelSettings, resolveProviderModel } from "../../application/model_resolution.js";
import type {
  TextGenerationProvider,
  TextGenerationProviderFactory,
  TextProviderName,
} from "../../application/ports/text_generation.js";
import { DashScopeTextProvider, type DashScopeTextProviderOptions } from "./dashscope_provider.js";
import { DeterministicStoryProvider } from "./deterministic_story_provider.js";
import {
  OpenAICompatibleTextProvider,
  type OpenAICompatibleTextProviderOptions,
} from "./openai_compatible_provider.js";
import { UnconfiguredTextProvider } from "./unconfigured_provider.js";

export interface ProviderCredentials {
  readonly dashscope?: string | undefined;
  readonly openaiCompatible?: string | undefined;
}

/** Server-owned HTTP adapter settings; credentials and models stay outside request payloads. */
export interface ProviderAdapterOptions {
  readonly dashscope?: Omit<DashScopeTextProviderOptions, "apiKey" | "model"> | undefined;
  readonly openaiCompatible?:
    | Omit<OpenAICompatibleTextProviderOptions, "apiKey" | "model">
    | undefined;
}

export interface TextProviderFactoryConfiguration {
  readonly modelSettings?: LlmModelSettings | undefined;
  readonly adapterOptions?: ProviderAdapterOptions | undefined;
}

export interface TextProviderFactoryOptions extends TextProviderFactoryConfiguration {
  readonly provider: TextProviderName;
  readonly apiKeys: ProviderCredentials;
}

/** The message family for an HTTP provider selected without credentials. */
export function missingCredentialMessage(provider: TextProviderName): string {
  return provider === "dashscope"
    ? "DASHSCOPE_API_KEY is required when provider is dashscope"
    : "LLM_API_KEY is required when provider is openai_compatible";
}

function nonBlankCredential(value: string | undefined): string | undefined {
  const credential = value?.trim();
  return credential === "" ? undefined : credential;
}

/**
 * Build one provider for one request. Unconfigured HTTP providers fail
 * explicitly on first use — the mock is never a fallback. HTTP adapter
 * models always come from the server-side resolution chain.
 */
export function createTextGenerationProvider(
  options: TextProviderFactoryOptions,
): TextGenerationProvider {
  const { adapterOptions, apiKeys, modelSettings, provider } = options;
  if (provider === "mock") {
    return new DeterministicStoryProvider("mock", resolveProviderModel("mock", modelSettings));
  }
  const apiKey = nonBlankCredential(
    provider === "dashscope" ? apiKeys.dashscope : apiKeys.openaiCompatible,
  );
  if (apiKey === undefined) {
    return new UnconfiguredTextProvider(missingCredentialMessage(provider));
  }
  const model = resolveProviderModel(provider, modelSettings);
  if (provider === "dashscope") {
    return new DashScopeTextProvider({
      ...adapterOptions?.dashscope,
      apiKey,
      model,
    });
  }
  return new OpenAICompatibleTextProvider({
    ...adapterOptions?.openaiCompatible,
    apiKey,
    model,
  });
}

/** Curry server configuration into the per-request factory the composition root injects. */
export function textProviderFactory(
  apiKeys: ProviderCredentials,
  configuration: TextProviderFactoryConfiguration = {},
): TextGenerationProviderFactory {
  return (provider) => createTextGenerationProvider({ provider, apiKeys, ...configuration });
}
