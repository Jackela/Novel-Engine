/**
 * Text generation contract used by narrative workflows (TS twin of the
 * Python authority's text_generation_port). The step vocabulary is CLOSED:
 * the application layer maps frontend operations to provider steps at this
 * boundary, and providers reject every other step instead of echoing it.
 */

/** The closed provider-step vocabulary at the port boundary. */
export const PROVIDER_STEPS = ["chapter_draft", "chapter_revision", "editorial_review"] as const;

export type ProviderStep = (typeof PROVIDER_STEPS)[number];

export function isProviderStep(value: string): value is ProviderStep {
  return (PROVIDER_STEPS as readonly string[]).includes(value);
}

/** The provider names clients may choose from; models are never client input. */
export const PROVIDER_NAMES = ["mock", "dashscope", "openai_compatible"] as const;

export type TextProviderName = (typeof PROVIDER_NAMES)[number];

export function isTextProviderName(value: string): value is TextProviderName {
  return (PROVIDER_NAMES as readonly string[]).includes(value);
}

/** Raised when a provider cannot complete a request; job persistence records it. */
export class TextGenerationProviderError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TextGenerationProviderError";
  }
}

/** Internal control-flow signal for an application-owned stream cancellation. */
export class TextGenerationCancelledError extends Error {
  constructor() {
    super("Text generation was cancelled.");
    this.name = "TextGenerationCancelledError";
  }
}

/** Structured generation task handed to provider adapters. */
export interface TextGenerationTask {
  readonly step: string;
  readonly systemPrompt: string;
  readonly userPrompt: string;
  readonly responseSchema: Record<string, unknown>;
  readonly metadata: Record<string, unknown>;
}

/** Structured response produced by a generation provider. */
export interface TextGenerationResult {
  readonly step: string;
  readonly provider: TextProviderName;
  readonly model: string;
  readonly rawText: string;
  readonly content: Record<string, unknown>;
  readonly promptTokens: number | null;
  readonly completionTokens: number | null;
}

/** Identity and usage of a completed generation stream (#308). */
export interface TextGenerationStreamOutcome {
  readonly model: string;
  readonly promptTokens: number | null;
  readonly completionTokens: number | null;
}

export interface TextGenerationStreamOptions {
  /**
   * Aborts the upstream request and stops the stream; deltas already yielded
   * stay valid, but the stream outcome is never reported after an abort.
   */
  readonly signal?: AbortSignal | undefined;
  /**
   * Invoked exactly once when the stream completes, carrying the provider
   * model and the usage read from the final stream chunk when present
   * (absent tokens stay null). Never invoked after an abort or failure.
   */
  readonly onOutcome?: ((outcome: TextGenerationStreamOutcome) => void) | undefined;
}

export interface TextGenerationProvider {
  generateStructured(task: TextGenerationTask): Promise<TextGenerationResult>;
  /**
   * Optional streaming capability (#308): yields raw chapter_markdown deltas
   * as the provider produces them — the concatenation of every delta is the
   * full proposal markdown. Providers without streaming support simply omit
   * the method; the streaming proposal service rejects such providers before
   * any stream starts instead of silently buffering.
   */
  generateStructuredStreaming?(
    task: TextGenerationTask,
    options?: TextGenerationStreamOptions,
  ): AsyncGenerator<string, void, void>;
  /** Optional request-scoped cleanup for providers that hold transport resources. */
  dispose?(): Promise<void>;
}

/**
 * Constructs one provider per request. Factories are injected by the
 * composition root; nothing constructs providers at import time.
 */
export type TextGenerationProviderFactory = (provider: TextProviderName) => TextGenerationProvider;
