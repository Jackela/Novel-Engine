/**
 * Session token minting and digesting.
 *
 * Two properties carry the design:
 *
 * 1. **The token is never stored.** Only its HMAC-SHA256 digest, keyed by the
 *    deployment secret, reaches the database. A stolen database therefore yields
 *    no usable session — and rotating the secret invalidates every existing
 *    session at once, which is the intended blast radius.
 * 2. **The digest is keyed, not a plain hash.** A bare SHA-256 of a 36-byte
 *    random token would be fine against preimage attacks, but keying it means the
 *    digest is useless without the deployment secret, so a leaked backup cannot
 *    even be checked offline.
 *
 * Sizes match the previous build (36-byte token, 32-byte CSRF secret) so the
 * cookie payload size and entropy do not change under the migration.
 */

import { createHmac, randomBytes } from "node:crypto";

import type { IssuedSessionTokens, SessionTokenIssuer } from "../ports.js";

/** Minimum deployment secret length; shorter secrets are rejected at wiring time. */
export const MIN_SESSION_SECRET_LENGTH = 16;

const TOKEN_BYTES = 36;
const CSRF_BYTES = 32;

export function createSessionTokenIssuer(secret: string): SessionTokenIssuer {
  if (secret.length < MIN_SESSION_SECRET_LENGTH) {
    // Fail at composition, not at the first login: a short secret is a
    // configuration error, and discovering it during a request would look like
    // an authentication bug.
    throw new Error(
      `The session secret must be at least ${String(MIN_SESSION_SECRET_LENGTH)} characters.`,
    );
  }

  function digest(token: string): string {
    return createHmac("sha256", secret).update(token, "utf8").digest("hex");
  }

  return {
    issue: (): IssuedSessionTokens => {
      const token = randomBytes(TOKEN_BYTES).toString("base64url");
      return {
        token,
        tokenHash: digest(token),
        csrfToken: randomBytes(CSRF_BYTES).toString("base64url"),
      };
    },
    // An empty token has no digest; returning "" lets callers treat it as absent
    // without a second branch.
    derive: (token: string) => (token === "" ? "" : digest(token)),
  };
}
