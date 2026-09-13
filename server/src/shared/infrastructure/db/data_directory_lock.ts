import { mkdirSync } from "node:fs";
import { join } from "node:path";

import Database from "better-sqlite3";

const OWNERSHIP_DATABASE_FILENAME = ".novel-engine-ownership.sqlite3";
const DATA_DIRECTORY_OWNED_MESSAGE =
  "The data directory is already owned by another Novel Engine process.";
const LOCK_CONFLICT_CODES = new Set(["SQLITE_BUSY", "SQLITE_LOCKED"]);

/** Process-lifetime ownership of one configured data directory. */
export interface DataDirectoryLock {
  close(): void;
}

/**
 * Acquire a cross-process writer lock without wrapping the content database in
 * one lifetime transaction. SQLite releases the exclusive transaction if the
 * process exits, so abrupt stops do not leave a stale lock file protocol.
 */
export function acquireDataDirectoryLock(directory: string): DataDirectoryLock {
  mkdirSync(directory, { recursive: true });
  const ownership = new Database(join(directory, OWNERSHIP_DATABASE_FILENAME), { timeout: 0 });
  try {
    ownership.exec("BEGIN EXCLUSIVE");
  } catch (error) {
    try {
      ownership.close();
    } catch (closeError) {
      throw new AggregateError([error, closeError], "Data-directory ownership cleanup failed.");
    }
    const code = sqliteErrorCode(error);
    if (code !== undefined && LOCK_CONFLICT_CODES.has(code)) {
      throw new Error(DATA_DIRECTORY_OWNED_MESSAGE, { cause: error });
    }
    throw error;
  }

  let closed = false;
  return {
    close: () => {
      if (closed) return;
      releaseOwnership(ownership);
      closed = true;
    },
  };
}

function releaseOwnership(ownership: Database.Database): void {
  // Closing the ownership connection is the single release boundary. An
  // explicit ROLLBACK followed by close would release the lock even when close
  // fails, making a reported release failure impossible to retry safely.
  ownership.close();
}

function sqliteErrorCode(error: unknown): string | undefined {
  if (typeof error !== "object" || error === null || !("code" in error)) return undefined;
  return typeof error.code === "string" ? error.code : undefined;
}
