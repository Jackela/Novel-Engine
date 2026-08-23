import type {
  TextGenerationProvider,
  TextGenerationResult,
  TextGenerationTask,
} from "../../application/ports/text_generation.js";
import { TextGenerationProviderError } from "../../application/ports/text_generation.js";

/**
 * Explicit provider used when runtime configuration is incomplete (or the
 * HTTP adapter has not landed yet): the first generation fails with that
 * provider's error. There is never a silent fallback to the mock.
 */
export class UnconfiguredTextProvider implements TextGenerationProvider {
  private readonly message: string;

  constructor(message: string) {
    this.message = message;
  }

  generateStructured(_task: TextGenerationTask): Promise<TextGenerationResult> {
    return Promise.reject(new TextGenerationProviderError(this.message));
  }
}
