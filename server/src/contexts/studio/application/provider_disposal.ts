import type { TextGenerationProvider } from "../../../contexts/ai/application/ports/text_generation.js";

/** Observer for provider cleanup failures; reporting never alters outcomes. */
export type ProviderCleanupFailureReporter = (failure: unknown) => void;

function reportCleanupFailureBestEffort(
  reportCleanupFailure: ProviderCleanupFailureReporter | undefined,
  failure: unknown,
): void {
  if (reportCleanupFailure === undefined) {
    return;
  }
  try {
    reportCleanupFailure(failure);
  } catch (reporterFailure) {
    // This observer has no recovery path, so its own failure is intentionally
    // suppressed and cannot replace the job/HTTP outcome already selected.
    void reporterFailure;
  }
}

/** Request-scoped provider cleanup; never replaces the selected job outcome. */
export async function disposeProvider(
  provider: TextGenerationProvider,
  reportCleanupFailure?: ProviderCleanupFailureReporter,
): Promise<void> {
  try {
    await provider.dispose?.();
  } catch (failure) {
    reportCleanupFailureBestEffort(reportCleanupFailure, failure);
  }
}
