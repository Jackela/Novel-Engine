export function isJsonObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** A provider-reported failure payload embedded in a 200 SSE stream (DR-026). */
export interface ProviderStreamFailure {
  readonly message: string;
  readonly code: string;
}

function errorPayloadCode(error: Record<string, unknown>): string {
  for (const candidate of [error.code, error.type]) {
    if (typeof candidate === "string" && candidate.trim() !== "") return candidate.trim();
    if (typeof candidate === "number" && Number.isFinite(candidate)) return String(candidate);
  }
  return "unknown";
}

function errorPayloadFailure(error: unknown): ProviderStreamFailure | undefined {
  if (!isJsonObject(error)) return undefined;
  const message = typeof error.message === "string" ? error.message.trim() : "";
  return message === "" ? undefined : { message, code: errorPayloadCode(error) };
}

/**
 * Recognize compatible error payloads and failed/incomplete Responses events.
 * An adverse Responses event fails immediately, even without readable error
 * detail; a later DONE marker cannot turn that outcome into success.
 */
export function openAiCompatibleStreamFailure(
  data: Record<string, unknown>,
): ProviderStreamFailure | undefined {
  if (data.type !== "response.failed" && data.type !== "response.incomplete") {
    return errorPayloadFailure(data.error);
  }
  const response = isJsonObject(data.response) ? data.response : {};
  const failure = errorPayloadFailure(response.error);
  if (failure !== undefined) return failure;
  const details = response.incomplete_details;
  const reason =
    isJsonObject(details) && typeof details.reason === "string" ? details.reason.trim() : "";
  return {
    code: data.type,
    message:
      data.type === "response.failed"
        ? "response failed"
        : `response incomplete${reason === "" ? "" : `: ${reason}`}`,
  };
}
