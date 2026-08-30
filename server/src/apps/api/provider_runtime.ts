import { resolveReviewModel } from "../../contexts/ai/application/model_resolution.js";
import type { TextGenerationProviderFactory } from "../../contexts/ai/application/ports/text_generation.js";
import { textProviderFactory } from "../../contexts/ai/infrastructure/providers/text_provider_factory.js";
import type { LlmProvider } from "../../shared/infrastructure/config/provider_config.js";
import type { ServerConfig } from "../../shared/infrastructure/config/server_config.js";

/** Credentials for the HTTP providers; absent keys leave them unconfigured. */
export interface ProviderApiKeys {
  dashscope?: string | undefined;
  openaiCompatible?: string | undefined;
}

/** Provider identity and model settings shared by generation and catalog routes. */
export interface ProviderRuntime {
  providerFactory: TextGenerationProviderFactory;
  providerApiKeys: ProviderApiKeys;
  providerModelSettings: {
    genericModel: string | undefined;
    dashscopeModel: string | undefined;
    dashscopeReviewModel: string | undefined;
    openaiCompatibleModel: string | undefined;
  };
  defaultProvider: LlmProvider;
  /** Review model resolved from the default provider and model settings. */
  reviewModel: string;
}

export interface ProviderRuntimeInputs {
  /**
   * Per-request AI provider factory override (tests inject capturing
   * providers). The default builds providers from `providerApiKeys`; HTTP
   * providers without a key fail explicitly — the mock is never a fallback.
   */
  textProviderFactory?: TextGenerationProviderFactory | undefined;
  providerApiKeys?: ProviderApiKeys | undefined;
}

/**
 * Private assembly of the AI provider runtime for the composition root:
 * resolve the injected-or-default factory, the configured credentials, model
 * settings, and the default provider used for review provenance.
 */
export function buildProviderRuntime(
  config: ServerConfig | undefined,
  inputs: ProviderRuntimeInputs,
): ProviderRuntime {
  const llm = config?.llm;
  const providerApiKeys = inputs.providerApiKeys ?? {
    dashscope: llm?.dashscopeApiKey,
    openaiCompatible: llm?.openaiCompatibleApiKey,
  };
  const providerModelSettings = {
    genericModel: llm?.genericModel,
    dashscopeModel: llm?.dashscopeModel,
    dashscopeReviewModel: llm?.dashscopeReviewModel,
    openaiCompatibleModel: llm?.openaiCompatibleModel,
  };
  const defaultProvider = llm?.defaultProvider ?? "mock";
  const providerFactory: TextGenerationProviderFactory =
    inputs.textProviderFactory ??
    textProviderFactory(providerApiKeys, {
      modelSettings: providerModelSettings,
      ...(llm === undefined
        ? {}
        : {
            adapterOptions: {
              dashscope: {
                apiBase: llm.dashscopeApiBase,
                transportMode: llm.dashscopeTransportMode,
                timeoutSeconds: llm.timeoutSeconds,
                retry: { maxAttempts: llm.retryAttempts, delayMs: llm.retryDelayMs },
                firstByteTimeoutMs: llm.streamFirstByteTimeoutMs,
                idleTimeoutMs: llm.streamIdleTimeoutMs,
              },
              openaiCompatible: {
                apiBase: llm.openaiCompatibleApiBase,
                timeoutSeconds: llm.timeoutSeconds,
                retry: { maxAttempts: llm.retryAttempts, delayMs: llm.retryDelayMs },
                firstByteTimeoutMs: llm.streamFirstByteTimeoutMs,
                idleTimeoutMs: llm.streamIdleTimeoutMs,
              },
            },
          }),
    });
  return {
    providerFactory,
    providerApiKeys,
    providerModelSettings,
    defaultProvider,
    reviewModel: resolveReviewModel(defaultProvider, providerModelSettings),
  };
}
