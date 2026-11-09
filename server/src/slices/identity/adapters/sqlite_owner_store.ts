/**
 * The SQLite implementation of `OwnerStore`.
 *
 * `create` re-checks the single-owner invariant even though the use case already
 * did. That is not redundancy: between the use case's check and this insert, a
 * second request can pass the same check, and the database is the only place the
 * race can actually be stopped. The check here runs inside the caller's
 * transaction, so it sees the same snapshot the insert will commit into.
 */

import { randomUUID } from "node:crypto";

import { eq } from "drizzle-orm";

import type { DatabaseHandle } from "../../../platform/db/connection.js";
import { owners } from "../../../platform/db/schema/index.js";
import { OwnerAlreadyConfiguredError } from "../domain/errors.js";
import type { OwnerRecord, OwnerStore } from "../ports.js";

export function createSqliteOwnerStore(handle: DatabaseHandle): OwnerStore {
  const { db } = handle;

  function firstOwner(): OwnerRecord | null {
    return db.select().from(owners).limit(1).get() ?? null;
  }

  return {
    ownerExists: () => firstOwner() !== null,
    findByUsername: (username) =>
      db.select().from(owners).where(eq(owners.username, username)).get() ?? null,
    findFirst: () => firstOwner(),
    create: (username, passwordHash, now) => {
      if (firstOwner() !== null) {
        throw new OwnerAlreadyConfiguredError();
      }
      const record: OwnerRecord = { id: randomUUID(), username, passwordHash, createdAt: now };
      db.insert(owners).values(record).run();
      return record;
    },
  };
}
