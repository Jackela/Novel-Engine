import { localizeError } from "@/app/localizeError";

import { reportUnexpectedError } from "./reportUnexpectedError";

/**
 * Canonical error-to-message reduction for user-facing error state (DR-021):
 * a stable envelope code (`HttpError.code`), a contract-layer shape failure,
 * or a body-size refusal resolves to a localized dictionary message through
 * `localizeError`; only reasons without a code keep their own message. When
 * the localized message withholds raw server/provider prose — provider
 * failures, unknown codes, contract shapes — that raw text is forwarded to
 * the diagnostics channel (`reportError`/console) so it stays reachable for
 * debugging while never rendering as the primary text.
 */
export function toErrorMessage(reason: unknown, fallback: string): string {
  const presentation = localizeError(reason, fallback);
  if (presentation.technical !== null) {
    reportUnexpectedError("Server error detail withheld from the localized message.", reason);
  }
  return presentation.message;
}
