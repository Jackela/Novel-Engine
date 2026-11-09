/**
 * Owner session lifetime and expiry.
 *
 * Two decisions live here, both inherited from the previous implementation
 * because changing either would silently alter observed behaviour:
 *
 * 1. Thirty days, fixed. There is no sliding renewal — `lastSeenAt` is updated
 *    for diagnostics, not to extend the window. A session that keeps being used
 *    still dies at its original expiry.
 * 2. Expiry is inclusive: a session whose `expiresAt` equals now is already
 *    over. The boundary is observable (a token minted at T with a TTL is valid
 *    strictly before T + TTL), so it is pinned by a test rather than left to the
 *    reader's intuition about `<=` versus `<`.
 *
 * Expiry is evaluated lazily at read time, not by a sweeper: the row is deleted
 * when a request presents the token. That keeps a single-process server free of
 * timers while making "expired" indistinguishable from "never existed" to the
 * caller — which is the correct answer, since neither authenticates.
 */

export const OWNER_SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000;

/** Epoch millis at which a session created at `nowMs` stops being valid. */
export function ownerSessionExpiry(nowMs: number): number {
  return nowMs + OWNER_SESSION_TTL_MS;
}

/**
 * Whether a session has expired at `nowMs`.
 *
 * `null` means "no expiry recorded" and never expires; the single-owner build
 * always records one, but the column is nullable because sessions predating the
 * owner-only model may not carry it.
 */
export function isSessionExpired(expiresAtMs: number | null, nowMs: number): boolean {
  return expiresAtMs !== null && expiresAtMs <= nowMs;
}
