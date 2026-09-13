/**
 * Extract the string `code` property from a Node-style errno error.
 *
 * Returns `undefined` when the thrown value is not an object, carries no
 * `code` property, or carries a non-string `code` (for example a numeric
 * code). Callers therefore match specific codes such as `"ENOENT"` without
 * accidental string coercion and must treat `undefined` as "unknown error",
 * never as a matched code.
 */
export function errorCode(error: unknown): string | undefined {
  if (typeof error !== "object" || error === null || !("code" in error)) return undefined;
  return typeof error.code === "string" ? error.code : undefined;
}
