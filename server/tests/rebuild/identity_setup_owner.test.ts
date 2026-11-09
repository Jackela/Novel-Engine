import { describe, expect, it } from "vitest";

import { CredentialPolicyError } from "../../src/slices/identity/domain/credentials.js";
import type { OwnerRecord, OwnerStore } from "../../src/slices/identity/ports.js";
import {
  OwnerAlreadyConfiguredError,
  setupOwner,
} from "../../src/slices/identity/usecases/setup_owner.js";

interface Harness {
  readonly deps: Parameters<typeof setupOwner>[0];
  readonly created: OwnerRecord[];
  hashCalls: number;
}

function harness(options: { ownerExists?: boolean } = {}): Harness {
  const created: OwnerRecord[] = [];
  const state: Harness = {
    created,
    hashCalls: 0,
    deps: {
      owners: {
        ownerExists: () => options.ownerExists === true,
        findByUsername: () => null,
        findFirst: () => null,
        create: (username, passwordHash, now) => {
          const record: OwnerRecord = { id: "owner-1", username, passwordHash, createdAt: now };
          created.push(record);
          return record;
        },
      } satisfies OwnerStore,
      hasher: {
        hash: (plain) => {
          state.hashCalls += 1;
          return Promise.resolve(`hashed:${plain}`);
        },
        verify: () => Promise.resolve(true),
        dummy: () => Promise.resolve("hashed:dummy"),
      },
      now: () => 1_700_000_000_000,
    },
  };
  return state;
}

describe("setupOwner", () => {
  it("creates the owner and returns its identity", async () => {
    const h = harness();
    const result = await setupOwner(h.deps, { username: "author", password: "0123456789" });
    expect(result).toEqual({ ownerId: "owner-1", username: "author" });
    expect(h.created).toHaveLength(1);
  });

  it("persists the hash, never the plaintext", async () => {
    const h = harness();
    await setupOwner(h.deps, { username: "author", password: "0123456789" });
    expect(h.created[0]?.passwordHash).toBe("hashed:0123456789");
    expect(h.created[0]?.passwordHash).not.toBe("0123456789");
  });

  it("trims the username before persisting", async () => {
    const h = harness();
    await setupOwner(h.deps, { username: "  author  ", password: "0123456789" });
    expect(h.created[0]?.username).toBe("author");
  });

  it("rejects a short password before spending a hash round", async () => {
    const h = harness();
    await expect(
      setupOwner(h.deps, { username: "author", password: "short" }),
    ).rejects.toBeInstanceOf(CredentialPolicyError);
    expect(h.hashCalls).toBe(0);
    expect(h.created).toHaveLength(0);
  });

  it("refuses a second owner without hashing", async () => {
    const h = harness({ ownerExists: true });
    await expect(
      setupOwner(h.deps, { username: "author", password: "0123456789" }),
    ).rejects.toBeInstanceOf(OwnerAlreadyConfiguredError);
    // The refusal must be cheap: bcrypt is the only expensive step here.
    expect(h.hashCalls).toBe(0);
    expect(h.created).toHaveLength(0);
  });
});
