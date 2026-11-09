/**
 * Exchange a username and password for an owner session.
 *
 * The property this use case is built around is **constant time for unknown
 * usernames**. Two paths must cost the same bcrypt round:
 * - an owner exists and the password is wrong,
 * - no owner matches at all.
 *
 * If only the first verified, response latency would answer "does this username
 * exist" for free — a username oracle on a single-owner installation, where the
 * answer is either the owner's name or nothing. So the unknown path verifies
 * against `SecretHasher.dummy()`, whose only job is to burn the same wall time.
 *
 * The byte ceiling is checked *before* any lookup: bcrypt compares the first 72
 * bytes, so accepting a longer password would authenticate anyone who knows the
 * prefix. Ordering here is security, not tidiness.
 */

import { isPasswordWithinByteCeiling } from "../domain/credentials.js";
import { ownerSessionExpiry } from "../domain/session.js";
import type { OwnerStore, SecretHasher, SessionStore, SessionTokenIssuer } from "../ports.js";

/**
 * Deliberately one error for both causes. Distinguishing "no such user" from
 * "wrong password" would restore the oracle the timing work exists to remove.
 */
export class InvalidCredentialsError extends Error {
  constructor() {
    super("Invalid username or password.");
    this.name = "InvalidCredentialsError";
  }
}

export interface LoginDeps {
  readonly owners: OwnerStore;
  readonly hasher: SecretHasher;
  readonly sessions: SessionStore;
  readonly tokens: SessionTokenIssuer;
  readonly now: () => number;
}

export interface LoginInput {
  readonly username: string;
  readonly password: string;
}

export interface LoginOutput {
  /** Bearer credential; the caller sets it as a cookie and never stores it. */
  readonly token: string;
  readonly csrfToken: string;
  readonly sessionId: string;
  readonly ownerId: string;
  readonly expiresAt: number;
}

/**
 * @throws InvalidCredentialsError for an over-long password, an unknown username,
 * and a wrong password alike — the caller maps all three to 422.
 */
export async function login(deps: LoginDeps, input: LoginInput): Promise<LoginOutput> {
  if (!isPasswordWithinByteCeiling(input.password)) {
    throw new InvalidCredentialsError();
  }
  const username = input.username.trim();
  const owner = username === "" ? null : deps.owners.findByUsername(username);

  // Always verify exactly once, against a real hash or the dummy one.
  const storedHash = owner?.passwordHash ?? (await deps.hasher.dummy());
  const matches = await deps.hasher.verify(input.password, storedHash);
  if (owner === null || !matches) {
    throw new InvalidCredentialsError();
  }

  const issued = deps.tokens.issue();
  const now = deps.now();
  const expiresAt = ownerSessionExpiry(now);
  const session = deps.sessions.create({
    ownerId: owner.id,
    tokenHash: issued.tokenHash,
    csrfToken: issued.csrfToken,
    expiresAt,
    now,
  });
  return {
    token: issued.token,
    csrfToken: issued.csrfToken,
    sessionId: session.id,
    ownerId: owner.id,
    expiresAt,
  };
}
