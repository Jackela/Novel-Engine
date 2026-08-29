/**
 * Canonical error-to-message reduction for user-facing error state: prefer
 * the error's own message, fall back to a caller-supplied readable string.
 */
export function toErrorMessage(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}
