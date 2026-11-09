/**
 * Resolve the authenticated principal for a presented token.
 *
 * Expiry is enforced here, lazily, on every read: an expired session is deleted
 * and reported as absent. That makes "expired" and "never existed" identical to
 * the caller, which is the correct answer — neither authenticates, and telling
 * them apart would reveal that a token was once valid.
 *
 * `lastSeenAt` is refreshed on success for diagnostics only. It does **not**
 * extend the expiry: sessions have a fixed 30-day life regardless of activity.
 * If that ever changes, it changes in `domain/session.ts`, not here.
 */

import { isSessionExpired } from "../domain/session.js";
import type { SessionStore, SessionTokenIssuer } from "../ports.js";

export interface Principal {
  readonly sessionId: string;
  readonly ownerId: string;
  /** Epoch millis; the caller may of course still find it expired later. */
  readonly expiresAt: number;
}

export interface ResolvePrincipalDeps {
  readonly sessions: SessionStore;
  readonly tokens: SessionTokenIssuer;
  readonly now: () => number;
}

/** @returns the principal, or null when the token is absent, unknown, or expired. */
export function resolvePrincipal(
  deps: ResolvePrincipalDeps,
  token: string | undefined,
): Principal | null {
  if (token === undefined || token === "") return null;
  const digest = deps.tokens.derive(token);
  if (digest === "") return null;

  const record = deps.sessions.findByTokenHash(digest);
  if (record === null) return null;

  const now = deps.now();
  if (isSessionExpired(record.expiresAt, now)) {
    // Delete on sight rather than leave a dead row behind: nothing else sweeps.
    deps.sessions.delete(record.id);
    return null;
  }
  deps.sessions.touch(record.id, now);
  return { sessionId: record.id, ownerId: record.ownerId, expiresAt: record.expiresAt };
}
