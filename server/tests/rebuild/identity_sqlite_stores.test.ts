import { describe, expect, it } from "vitest";

import { openDatabase, type DatabaseHandle } from "../../src/platform/db/connection.js";
import { createSqliteOwnerStore } from "../../src/slices/identity/adapters/sqlite_owner_store.js";
import { createSqliteSessionStore } from "../../src/slices/identity/adapters/sqlite_session_store.js";
import { OwnerAlreadyConfiguredError } from "../../src/slices/identity/domain/errors.js";

/**
 * Hand-written DDL for the two tables these adapters touch.
 *
 * Stage 2 replaces this with generated migrations. Until then the adapters are
 * otherwise unverifiable, and "the SQL is probably fine" is how column drift
 * starts. The column names mirror `platform/db/schema/identity.ts` exactly; if
 * they diverge, these tests fail on the first insert rather than in production.
 */
const OWNERS_DDL = `CREATE TABLE owners (
  id TEXT PRIMARY KEY NOT NULL,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL
)`;

const SESSIONS_DDL = `CREATE TABLE sessions (
  id TEXT PRIMARY KEY NOT NULL,
  owner_id TEXT NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  csrf_token TEXT NOT NULL,
  expires_at INTEGER NOT NULL,
  last_seen_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL
)`;

const NOW = 1_700_000_000_000;

function database(): DatabaseHandle {
  const handle = openDatabase({ path: ":memory:" });
  handle.raw.exec(OWNERS_DDL);
  handle.raw.exec(SESSIONS_DDL);
  return handle;
}

function seedOwner(handle: DatabaseHandle, id = "owner-1"): void {
  handle.raw
    .prepare("INSERT INTO owners (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)")
    .run(id, "author", "hash:0123456789", NOW);
}

describe("sqlite owner store", () => {
  it("creates the owner and finds it by username", () => {
    const handle = database();
    const store = createSqliteOwnerStore(handle);
    const created = store.create("author", "hash:0123456789", NOW);

    expect(created.username).toBe("author");
    expect(store.ownerExists()).toBe(true);
    expect(store.findByUsername("author")).toEqual(created);
    expect(store.findFirst()).toEqual(created);
    handle.close();
  });

  it("returns null for an unknown username and an empty installation", () => {
    const handle = database();
    const store = createSqliteOwnerStore(handle);
    expect(store.ownerExists()).toBe(false);
    expect(store.findFirst()).toBeNull();
    expect(store.findByUsername("nobody")).toBeNull();
    handle.close();
  });

  it("refuses a second owner and leaves the first intact", () => {
    const handle = database();
    const store = createSqliteOwnerStore(handle);
    store.create("author", "hash:0123456789", NOW);

    expect(() => store.create("intruder", "hash:other", NOW)).toThrow(OwnerAlreadyConfiguredError);
    expect(store.findByUsername("intruder")).toBeNull();
    const rows = handle.raw.prepare("SELECT COUNT(*) AS n FROM owners").get() as { n: number };
    expect(rows.n).toBe(1);
    handle.close();
  });
});

describe("sqlite session store", () => {
  it("creates a session and finds it by token digest", () => {
    const handle = database();
    seedOwner(handle);
    const store = createSqliteSessionStore(handle);

    const created = store.create({
      ownerId: "owner-1",
      tokenHash: "digest-1",
      csrfToken: "csrf-1",
      expiresAt: NOW + 1_000,
      now: NOW,
    });

    expect(store.findByTokenHash("digest-1")).toEqual(created);
    expect(created.lastSeenAt).toBe(NOW);
    expect(created.createdAt).toBe(NOW);
    handle.close();
  });

  it("deletes a session so it is no longer found", () => {
    const handle = database();
    seedOwner(handle);
    const store = createSqliteSessionStore(handle);
    const created = store.create({
      ownerId: "owner-1",
      tokenHash: "digest-1",
      csrfToken: "csrf-1",
      expiresAt: NOW + 1_000,
      now: NOW,
    });

    store.delete(created.id);
    expect(store.findByTokenHash("digest-1")).toBeNull();
    handle.close();
  });

  it("touches last-seen without moving the expiry", () => {
    const handle = database();
    seedOwner(handle);
    const store = createSqliteSessionStore(handle);
    const created = store.create({
      ownerId: "owner-1",
      tokenHash: "digest-1",
      csrfToken: "csrf-1",
      expiresAt: NOW + 1_000,
      now: NOW,
    });

    store.touch(created.id, NOW + 500);
    const after = store.findByTokenHash("digest-1");
    expect(after?.lastSeenAt).toBe(NOW + 500);
    expect(after?.expiresAt).toBe(created.expiresAt);
    handle.close();
  });

  it("rejects a duplicate token digest", () => {
    const handle = database();
    seedOwner(handle);
    const store = createSqliteSessionStore(handle);
    const input = {
      ownerId: "owner-1",
      tokenHash: "digest-1",
      csrfToken: "csrf-1",
      expiresAt: NOW + 1_000,
      now: NOW,
    };
    store.create(input);
    expect(() => store.create(input)).toThrow();
    handle.close();
  });
});
