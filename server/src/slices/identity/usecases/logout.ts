/**
 * Terminate the session behind a presented token.
 *
 * Idempotent by design: an absent, unknown, or already-deleted token is a no-op.
 * Logout must not fail for a caller whose session is already gone — and it must
 * not answer "was this token ever valid", which a 401 would.
 *
 * "Logout terminates the session" is a product requirement, not a courtesy: the
 * bearer token is the only credential, so deleting the row is the whole of
 * revocation. There is no denylist to keep, and nothing to expire later.
 */

import type { SessionStore, SessionTokenIssuer } from "../ports.js";

export interface LogoutDeps {
  readonly sessions: SessionStore;
  readonly tokens: SessionTokenIssuer;
}

/** Deletes the matching session when one exists; otherwise does nothing. */
export function logout(deps: LogoutDeps, token: string | undefined): void {
  if (token === undefined) return;
  const digest = deps.tokens.derive(token);
  if (digest === "") return;
  const record = deps.sessions.findByTokenHash(digest);
  if (record !== null) {
    deps.sessions.delete(record.id);
  }
}
