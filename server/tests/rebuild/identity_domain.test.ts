import { describe, expect, it } from "vitest";

import {
  CredentialPolicyError,
  MAX_PASSWORD_BYTES,
  MIN_PASSWORD_CHARACTERS,
  normalizeOwnerCredentials,
} from "../../src/slices/identity/domain/credentials.js";
import {
  isSessionExpired,
  OWNER_SESSION_TTL_MS,
  ownerSessionExpiry,
} from "../../src/slices/identity/domain/session.js";

function violationOf(fn: () => unknown): string {
  try {
    fn();
  } catch (error) {
    expect(error).toBeInstanceOf(CredentialPolicyError);
    return (error as CredentialPolicyError).violation;
  }
  throw new Error("expected a credential policy failure");
}

describe("owner credentials", () => {
  it("accepts a ten-character password and rejects nine", () => {
    expect(normalizeOwnerCredentials("author", "0123456789").password).toBe("0123456789");
    expect(violationOf(() => normalizeOwnerCredentials("author", "012345678"))).toBe(
      "password-too-short",
    );
  });

  it("trims the username but never the password", () => {
    const credentials = normalizeOwnerCredentials("  author  ", "  spaced pw  ");
    expect(credentials.username).toBe("author");
    expect(credentials.password).toBe("  spaced pw  ");
  });

  it("rejects a username that is empty after trimming", () => {
    expect(violationOf(() => normalizeOwnerCredentials("   ", "0123456789"))).toBe(
      "username-empty",
    );
  });

  it("measures the minimum in characters and the ceiling in UTF-8 bytes", () => {
    // 24 Chinese characters = 72 bytes: passes the byte ceiling.
    const atCeiling = "作".repeat(24);
    expect(new TextEncoder().encode(atCeiling).length).toBe(MAX_PASSWORD_BYTES);
    expect(normalizeOwnerCredentials("author", atCeiling).password).toBe(atCeiling);

    // 25 characters = 75 bytes: over bcrypt's 72-byte window, so rejected.
    expect(violationOf(() => normalizeOwnerCredentials("author", "作".repeat(25)))).toBe(
      "password-too-long",
    );
  });

  it("accepts a short multi-byte password that still clears ten characters", () => {
    // 10 characters, 30 bytes: the character minimum is what gates it.
    expect(normalizeOwnerCredentials("author", "密码".repeat(5)).password).toHaveLength(10);
  });
});

describe("owner session lifetime", () => {
  it("is thirty days from creation", () => {
    expect(OWNER_SESSION_TTL_MS).toBe(30 * 24 * 60 * 60 * 1000);
    expect(ownerSessionExpiry(1_000)).toBe(1_000 + OWNER_SESSION_TTL_MS);
  });

  it("treats the expiry instant itself as expired", () => {
    const now = 1_700_000_000_000;
    expect(isSessionExpired(now, now)).toBe(true);
    expect(isSessionExpired(now + 1, now)).toBe(false);
    expect(isSessionExpired(now - 1, now)).toBe(true);
  });

  it("never expires a session with no recorded expiry", () => {
    expect(isSessionExpired(null, 1_700_000_000_000)).toBe(false);
  });
});
