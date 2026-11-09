/**
 * The SQLite implementation of `SessionStore`.
 *
 * `touch` writes `lastSeenAt` and nothing else. It must never extend `expiresAt`:
 * sessions have a fixed 30-day life, and a sliding window would silently turn
 * "log in once a month" into "never log in again". If renewal is ever wanted, it
 * belongs in the use case and in `domain/session.ts`, not here.
 */

import { randomUUID } from "node:crypto";

import { eq } from "drizzle-orm";

import type { DatabaseHandle } from "../../../platform/db/connection.js";
import { sessions } from "../../../platform/db/schema/index.js";
import type { NewSession, SessionRecord, SessionStore } from "../ports.js";

export function createSqliteSessionStore(handle: DatabaseHandle): SessionStore {
  const { db } = handle;

  return {
    create: (input: NewSession) => {
      const record: SessionRecord = {
        id: randomUUID(),
        ownerId: input.ownerId,
        tokenHash: input.tokenHash,
        csrfToken: input.csrfToken,
        expiresAt: input.expiresAt,
        lastSeenAt: input.now,
        createdAt: input.now,
      };
      db.insert(sessions).values(record).run();
      return record;
    },
    findByTokenHash: (tokenHash) =>
      db.select().from(sessions).where(eq(sessions.tokenHash, tokenHash)).get() ?? null,
    delete: (sessionId) => {
      db.delete(sessions).where(eq(sessions.id, sessionId)).run();
    },
    touch: (sessionId, now) => {
      db.update(sessions).set({ lastSeenAt: now }).where(eq(sessions.id, sessionId)).run();
    },
  };
}
