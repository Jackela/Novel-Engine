/**
 * Owner credential policy.
 *
 * These are the only two rules the domain owns about credentials: what counts as
 * a usable username, and what counts as an acceptable password. Hashing is not
 * here — bcrypt is an outbound capability and lives behind a port, so this module
 * stays a total function of its inputs.
 *
 * The byte ceiling is not a style preference: bcrypt silently truncates input
 * beyond 72 bytes, so a longer password would authenticate against its first 72
 * bytes while the author believes the tail matters. Rejecting is the only honest
 * option.
 */

export const MIN_PASSWORD_CHARACTERS = 10;
export const MAX_PASSWORD_BYTES = 72;

export type CredentialPolicyViolation =
  | "username-empty"
  | "password-too-short"
  | "password-too-long";

/** Raised when supplied credentials cannot be accepted as-is. */
export class CredentialPolicyError extends Error {
  readonly violation: CredentialPolicyViolation;

  constructor(violation: CredentialPolicyViolation) {
    super(messageFor(violation));
    this.name = "CredentialPolicyError";
    this.violation = violation;
  }
}

function messageFor(violation: CredentialPolicyViolation): string {
  switch (violation) {
    case "username-empty":
      return "Username is required.";
    case "password-too-short":
      return `Password must be at least ${String(MIN_PASSWORD_CHARACTERS)} characters.`;
    case "password-too-long":
      return `Password must not exceed ${String(MAX_PASSWORD_BYTES)} UTF-8 bytes.`;
  }
}

/** UTF-8 byte length without importing a stream encoder. */
function utf8Bytes(value: string): number {
  return new TextEncoder().encode(value).length;
}

/**
 * Whether a password fits bcrypt's 72-byte window.
 *
 * Needed on the login path too, not just at setup: bcrypt compares only the
 * first 72 bytes, so a longer password would match on its prefix. Rejecting
 * before hashing keeps that from becoming an authentication bypass for anyone
 * who knows the prefix.
 */
export function isPasswordWithinByteCeiling(password: string): boolean {
  return utf8Bytes(password) <= MAX_PASSWORD_BYTES;
}

export interface OwnerCredentials {
  /** Whitespace-trimmed; the only form ever persisted or compared. */
  readonly username: string;
  /** Returned untouched — passwords keep their leading and trailing spaces. */
  readonly password: string;
}

/**
 * Validate and normalize a username/password pair.
 *
 * Trimming applies to the username only. The character minimum is measured in
 * code units while the ceiling is measured in UTF-8 bytes, which is deliberate:
 * a 24-character Chinese passphrase is 72 bytes and must pass, while a
 * 25-character one exceeds bcrypt's window and must not.
 */
export function normalizeOwnerCredentials(
  username: string,
  password: string,
): OwnerCredentials {
  const trimmed = username.trim();
  if (trimmed.length === 0) {
    throw new CredentialPolicyError("username-empty");
  }
  if (password.length < MIN_PASSWORD_CHARACTERS) {
    throw new CredentialPolicyError("password-too-short");
  }
  if (utf8Bytes(password) > MAX_PASSWORD_BYTES) {
    throw new CredentialPolicyError("password-too-long");
  }
  return { username: trimmed, password };
}
