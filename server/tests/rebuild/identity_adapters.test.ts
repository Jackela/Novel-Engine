import { describe, expect, it } from "vitest";

import { createBcryptHasher } from "../../src/slices/identity/adapters/bcrypt_hasher.js";
import {
  createSessionTokenIssuer,
  MIN_SESSION_SECRET_LENGTH,
} from "../../src/slices/identity/adapters/hmac_tokens.js";

// Cost 4 keeps the suite fast; production uses the default 12.
const FAST_ROUNDS = 4;
const SECRET = "test-session-secret-value";

describe("bcrypt hasher", () => {
  const hasher = createBcryptHasher(FAST_ROUNDS);

  it("never returns the plaintext", async () => {
    const hashed = await hasher.hash("0123456789");
    expect(hashed).not.toBe("0123456789");
    expect(hashed.startsWith("$2")).toBe(true);
  });

  it("verifies the right password and rejects the wrong one", async () => {
    const hashed = await hasher.hash("0123456789");
    await expect(hasher.verify("0123456789", hashed)).resolves.toBe(true);
    await expect(hasher.verify("0123456780", hashed)).resolves.toBe(false);
  });

  it("salts each hash independently", async () => {
    const [a, b] = await Promise.all([hasher.hash("0123456789"), hasher.hash("0123456789")]);
    expect(a).not.toBe(b);
  });

  it("memoizes the dummy hash so the unknown-user path stays as slow, not slower", async () => {
    const [first, second] = await Promise.all([hasher.dummy(), hasher.dummy()]);
    // Same promise, same value: regenerating per call would add a second bcrypt
    // round on the unknown-user path and leak the answer by being slower.
    expect(first).toBe(second);
    expect(first.startsWith("$2")).toBe(true);
  });
});

describe("session token issuer", () => {
  const issuer = createSessionTokenIssuer(SECRET);

  it("mints three distinct values with the expected shapes", () => {
    const issued = issuer.issue();
    expect(issued.token).toMatch(/^[A-Za-z0-9_-]+$/);
    expect(issued.csrfToken).toMatch(/^[A-Za-z0-9_-]+$/);
    expect(issued.tokenHash).toMatch(/^[a-f0-9]{64}$/);
    expect(issued.token).not.toBe(issued.csrfToken);
  });

  it("derives a stable digest that matches the stored one", () => {
    const issued = issuer.issue();
    expect(issuer.derive(issued.token)).toBe(issued.tokenHash);
    expect(issuer.derive(issued.token)).toBe(issuer.derive(issued.token));
  });

  it("mints a different token every time", () => {
    const first = issuer.issue();
    const second = issuer.issue();
    expect(first.token).not.toBe(second.token);
    expect(first.tokenHash).not.toBe(second.tokenHash);
  });

  it("keys the digest with the secret", () => {
    const other = createSessionTokenIssuer("a-completely-different-secret");
    const issued = issuer.issue();
    expect(other.derive(issued.token)).not.toBe(issued.tokenHash);
  });

  it("treats an empty token as having no digest", () => {
    expect(issuer.derive("")).toBe("");
  });

  it("rejects a secret shorter than the minimum", () => {
    expect(() => createSessionTokenIssuer("x".repeat(MIN_SESSION_SECRET_LENGTH - 1))).toThrow(
      /at least/,
    );
    expect(() => createSessionTokenIssuer("x".repeat(MIN_SESSION_SECRET_LENGTH))).not.toThrow();
  });
});
