import { HttpError } from "@/app/httpClient";

import { toErrorMessage } from "./toErrorMessage";

/** Server code for the first-boot token refusal on `POST /api/setup` (403). */
const SETUP_TOKEN_INVALID_CODE = "SETUP_TOKEN_INVALID";

/** Server code the constant-time wrong-credential login refusal uses (422). */
const INVALID_OPERATION_CODE = "INVALID_OPERATION";

/** The submit step that failed; only the login step can name credentials. */
export type EntrySubmitPhase = "setup" | "login";

type EntryMessageKey =
  | "entry.error.unableToContinue"
  | "entry.error.setupTokenInvalid"
  | "entry.error.invalidCredentials";

/**
 * Reduce a failed entry submission to the message the form shows. The
 * first-boot token refusal carries a server-side English explanation whose
 * actionable form is localized, so it is replaced by the `t`-resolved hint;
 * a failed login is the server's constant-time 422 refusal, which the form
 * names as wrong credentials instead of the shared state-refusal wording;
 * every other failure keeps its own message semantics through the shared
 * `toErrorMessage` reduction (DR-021). Failure semantics: an unknown reason
 * still yields the caller's fallback, never an empty string.
 */
export function entrySubmitMessage(
  reason: unknown,
  t: (key: EntryMessageKey) => string,
  phase: EntrySubmitPhase = "setup",
): string {
  if (reason instanceof HttpError && reason.code === SETUP_TOKEN_INVALID_CODE) {
    return t("entry.error.setupTokenInvalid");
  }
  if (phase === "login" && reason instanceof HttpError && reason.code === INVALID_OPERATION_CODE) {
    return t("entry.error.invalidCredentials");
  }
  return toErrorMessage(reason, t("entry.error.unableToContinue"));
}
