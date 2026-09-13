export function reportUnexpectedError(context: string, reason: unknown): void {
  const error = reason instanceof Error ? reason : new Error(context, { cause: reason });
  if (typeof globalThis.reportError === "function") {
    globalThis.reportError(error);
    return;
  }
  console.error(context, error);
}
