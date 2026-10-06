import type { StudioSqliteDatabase } from "./connection.js";
import { owners, sessions } from "./schema.js";

/** Machine-readable outcome of `novel-engine owner reset`. */
export interface OwnerResetSummary {
  /** Deleted `owners` rows; zero on a fresh installation. */
  owners_deleted: number;
  /** Deleted `sessions` rows; zero when no session was live. */
  sessions_deleted: number;
  /** Username of the removed owner when exactly one existed, otherwise null. */
  username: string | null;
}

/**
 * Reset the owner credential state in one transaction: every `owners` row and
 * every `sessions` row is deleted, and the summary reports the counts. Sessions
 * must go with the owner because they are live bearer credentials: the auth
 * spine resolves a session token straight to its `owner_id` and never re-checks
 * that the owner row still exists, so a surviving session would keep
 * authenticating after a reset. Deleting all owners (not just the first) is
 * deliberate — the single-owner invariant checks only whether any owner exists,
 * so any stray row would keep `POST /api/setup` locked after a partial reset.
 */
export function resetOwnerState(db: StudioSqliteDatabase): OwnerResetSummary {
  return db.transaction((tx) => {
    const existing = tx.select({ username: owners.username }).from(owners).all();
    const deletedSessions = tx.delete(sessions).run();
    const deletedOwners = tx.delete(owners).run();
    return {
      owners_deleted: deletedOwners.changes,
      sessions_deleted: deletedSessions.changes,
      username: existing.length === 1 ? (existing[0]?.username ?? null) : null,
    };
  });
}
