import type {
  TextGenerationProvider,
  TextGenerationResult,
  TextGenerationStreamOptions,
  TextGenerationTask,
} from "../../application/ports/text_generation.js";
import { ProviderNotConfiguredError } from "../../application/ports/text_generation.js";

/**
 * A stream that fails on its first pull: the generator contract requires the
 * shape, but the credential failure must surface before any delta, so no
 * frame is ever emitted (the empty delegation keeps the generator valid).
 */
async function* failingTextStream(message: string): AsyncGenerator<string, void, void> {
  yield* [] as readonly string[];
  throw new ProviderNotConfiguredError(message);
}

/**
 * Explicit provider used when runtime configuration is incomplete (or the
 * HTTP adapter has not landed yet): the first generation — synchronous or
 * streamed — fails with that provider's credential error. The streaming
 * method exists on purpose (DR-022): the pipeline must report the missing
 * credential instead of misreading the absent capability as "does not
 * support streaming generation". There is never a silent fallback to the
 * mock.
 */
export class UnconfiguredTextProvider implements TextGenerationProvider {
  private readonly message: string;

  constructor(message: string) {
    this.message = message;
  }

  generateStructured(_task: TextGenerationTask): Promise<TextGenerationResult> {
    return Promise.reject(new ProviderNotConfiguredError(this.message));
  }

  /** Fails on the first pull, before any delta, with the credential error. */
  generateStructuredStreaming(
    _task: TextGenerationTask,
    _options?: TextGenerationStreamOptions,
  ): AsyncGenerator<string, void, void> {
    return failingTextStream(this.message);
  }
}
