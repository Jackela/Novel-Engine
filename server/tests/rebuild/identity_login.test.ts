import { describe, expect, it } from "vitest";

import { OWNER_SESSION_TTL_MS } from "../../src/slices/identity/domain/session.js";
import type {
  NewSession,
  OwnerStore,
  SessionRecord,
  SessionStore,
} from "../../src/slices/identity/ports.js";
import { InvalidCredentialsError, login } from "../../src/slices/identity/usecases/login.js";

const NOW = 1_700_000_000_000;
const PASSWORD = "0123456789";

interface Harness {
  readonly deps: Parameters<typeof login>[0];
  readonly verifyCalls: () => number;
  readonly sessions: () => SessionRecord[];
  readonly lookups: () => number;
}

function harness(options: { owner?: { username: string; passwordHash: string } } = {}): Harness {
  let verifyCalls = 0;
  let lookups = 0;
  const sessions: SessionRecord[] = [];
  const owner = options.owner;

  const deps: Parameters<typeof login>[0] = {
    owners: {
      ownerExists: () => owner !== undefined,
      findByUsername: (username) => {
        lookups += 1;
        if (owner === undefined || owner.username !== username) return null;
        return {
          id: "owner-1",
          username: owner.username,
          passwordHash: owner.passwordHash,
          createdAt: NOW,
        };
      },
      findFirst: () => null,
      create: () => {
        throw new Error("login never creates an owner");
      },
    } satisfies OwnerStore,
    hasher: {
      hash: () => Promise.resolve("hash:unused"),
      verify: (plain, stored) => {
        verifyCalls += 1;
        return Promise.resolve(stored === `hash:${plain}`);
      },
      dummy: () => Promise.resolve("hash:dummy-only"),
    },
    sessions: {
      create: (input: NewSession) => {
        const record: SessionRecord = {
          id: "session-1",
          ownerId: input.ownerId,
          tokenHash: input.tokenHash,
          csrfToken: input.csrfToken,
          expiresAt: input.expiresAt,
          lastSeenAt: input.now,
          createdAt: input.now,
        };
        sessions.push(record);
        return record;
      },
      findByTokenHash: () => null,
      delete: () => undefined,
      touch: () => undefined,
    } satisfies SessionStore,
    tokens: {
      issue: () => ({ token: "token-1", tokenHash: "digest-1", csrfToken: "csrf-1" }),
      derive: (token) => `digest:${token}`,
    },
    now: () => NOW,
  };

  return {
    deps,
    verifyCalls: () => verifyCalls,
    sessions: () => sessions,
    lookups: () => lookups,
  };
}

/** A fresh harness per test: sessions and call counters must not leak across. */
function configured(): Harness {
  return harness({ owner: { username: "author", passwordHash: `hash:${PASSWORD}` } });
}

describe("login", () => {
  it("issues a session thirty days out", async () => {
    const h = configured();
    const result = await login(h.deps, { username: "author", password: PASSWORD });
    expect(result.token).toBe("token-1");
    expect(result.csrfToken).toBe("csrf-1");
    expect(result.expiresAt).toBe(NOW + OWNER_SESSION_TTL_MS);
    expect(h.sessions()).toHaveLength(1);
    expect(h.sessions()[0]?.tokenHash).toBe("digest-1");
  });

  it("rejects a wrong password and writes no session", async () => {
    const h = configured();
    await expect(
      login(h.deps, { username: "author", password: "wrong-password" }),
    ).rejects.toBeInstanceOf(InvalidCredentialsError);
    expect(h.sessions()).toHaveLength(0);
  });

  it("spends one verify even when the username does not exist", async () => {
    // The count is the point: zero here would make latency answer "does this
    // user exist", and on a single-owner install that answer is everything.
    const h = configured();
    const before = h.verifyCalls();
    await expect(login(h.deps, { username: "nobody", password: PASSWORD })).rejects.toBeInstanceOf(
      InvalidCredentialsError,
    );
    expect(h.verifyCalls() - before).toBe(1);
    expect(h.sessions()).toHaveLength(0);
  });

  it("rejects an over-long password before any lookup or hash", async () => {
    const h = configured();
    const lookupsBefore = h.lookups();
    const verifiesBefore = h.verifyCalls();
    await expect(
      login(h.deps, { username: "author", password: "a".repeat(73) }),
    ).rejects.toBeInstanceOf(InvalidCredentialsError);
    expect(h.lookups()).toBe(lookupsBefore);
    expect(h.verifyCalls()).toBe(verifiesBefore);
  });

  it("treats a blank username as unknown without querying the store", async () => {
    const h = configured();
    const lookupsBefore = h.lookups();
    await expect(login(h.deps, { username: "   ", password: PASSWORD })).rejects.toBeInstanceOf(
      InvalidCredentialsError,
    );
    expect(h.lookups()).toBe(lookupsBefore);
    expect(h.verifyCalls()).toBeGreaterThan(0);
  });
});
