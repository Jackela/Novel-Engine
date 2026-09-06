import { HttpError } from "@/app/httpClient";

const STRUCTURE_CAPACITY_EXCEEDED_CODE = "STRUCTURE_CAPACITY_EXCEEDED";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * The permanent structure-capacity refusal (#461) reports a fixed message, so
 * its envelope details carry the only actionable evidence: which bounded
 * resource refused the write and its inclusive limit. Append exactly that;
 * every other error keeps its own message semantics.
 */
function structureCapacitySuffix(reason: Error): string {
  if (!(reason instanceof HttpError) || reason.code !== STRUCTURE_CAPACITY_EXCEEDED_CODE) {
    return "";
  }
  if (!isRecord(reason.detail)) return "";
  const { resource, limit } = reason.detail;
  if (typeof resource !== "string" || resource === "") return "";
  if (typeof limit !== "number" || !Number.isSafeInteger(limit) || limit < 0) return "";
  return ` ${resource} limit is ${limit}.`;
}

/**
 * Canonical error-to-message reduction for user-facing error state: prefer
 * the error's own message, fall back to a caller-supplied readable string.
 */
export function toErrorMessage(reason: unknown, fallback: string): string {
  if (!(reason instanceof Error)) return fallback;
  return `${reason.message}${structureCapacitySuffix(reason)}`;
}
