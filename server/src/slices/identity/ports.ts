/**
 * Ports the identity slice needs from the outside world.
 *
 * Three capabilities, deliberately separate:
 * - `OwnerStore` / `SessionStore`: persistence. Split because they have
 *   different lifetimes — an owner survives every session it ever created.
 * - `SecretHasher`: bcrypt, which is slow by design and must not be called
 *   inside a transaction. Keeping it a port lets the use case hash first and
 *   write second.
 * - `SessionTokenIssuer`: minting and digesting bearer tokens. It owns the
 *   deployment key, so rotating that key invalidates every session at once —
 *   which is the intended blast radius, not an accident.
 *
 * All timestamps are epoch milliseconds. The legacy build used `Date`; passing
 * plain numbers keeps the domain free of a mutable time type and makes
 * boundaries testable without freezing a clock object.
 */

export interface OwnerRecord {
  readonly id: string;
  readonly username: string;
  readonly passwordHash: string;
  readonly createdAt: number;
}

export interface SessionRecord {
  readonly id: string;
  readonly ownerId: string;
  /** HMAC digest of the bearer token; the token itself is never stored. */
  readonly tokenHash: string;
  /** Double-submit secret the client must echo in `x-csrf-token`. */
  readonly csrfToken: string;
  readonly expiresAt: number;
  readonly lastSeenAt: number;
  readonly createdAt: number;
}

export interface NewSession {
  readonly ownerId: string;
  readonly tokenHash: string;
  readonly csrfToken: string;
  readonly expiresAt: number;
  readonly now: number;
}

export interface OwnerStore {
  ownerExists(): boolean;
  /**
   * Username lookup. Callers must not branch on null to decide the error: the
   * use case verifies a dummy hash in that case so response timing does not
   * reveal whether a username exists.
   */
  findByUsername(username: string): OwnerRecord | null;
  /** The installation's single owner, for the CLI's operational principal. */
  findFirst(): OwnerRecord | null;
  /** Throws when the single-owner invariant would break. */
  create(username: string, passwordHash: string, now: number): OwnerRecord;
}

export interface SessionStore {
  create(input: NewSession): SessionRecord;
  findByTokenHash(tokenHash: string): SessionRecord | null;
  delete(sessionId: string): void;
  /** Diagnostics only: this never extends a session's expiry. */
  touch(sessionId: string, now: number): void;
}

export interface SecretHasher {
  hash(plain: string): Promise<string>;
  verify(plain: string, stored: string): Promise<boolean>;
  /**
   * A hash to verify against when no owner matched. Its only job is to spend the
   * same bcrypt time as a real comparison. Implementations must memoize it: it
   * contains a random salt generated at runtime, never a literal password.
   */
  dummy(): Promise<string>;
}

export interface IssuedSessionTokens {
  /** Bearer credential handed to the client. Never persisted. */
  readonly token: string;
  /** Deployment-keyed digest that is persisted. */
  readonly tokenHash: string;
  readonly csrfToken: string;
}

export interface SessionTokenIssuer {
  /** Mints a fresh token, its digest, and the paired CSRF secret. */
  issue(): IssuedSessionTokens;
  /** Digests a presented token; returns "" for an empty input. */
  derive(token: string): string;
}
