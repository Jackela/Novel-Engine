/**
 * The SQLite connection used by every adapter in the rebuild.
 *
 * The three PRAGMAs are not defaults, they are decisions carried over from the
 * previous build and each one has a failure mode behind it:
 *
 * - `journal_mode = WAL`: readers must not block the single writer. Without it
 *   an export running while the author types stalls the editor.
 * - `foreign_keys = ON`: SQLite ships with them **off**, so cascade deletes and
 *   the `RESTRICT` that protects snapshot revisions only work if this is set on
 *   every connection, not just the migration one.
 * - `synchronous = FULL`: a commit must survive power loss. Files are deleted
 *   after a commit in the export path, so a lost commit would leave the database
 *   claiming a file exists that has already been removed.
 *
 * `busy_timeout` is new: one process, but parallel connections (an export worker,
 * a CLI backup) can still contend. Waiting briefly beats failing instantly with
 * SQLITE_BUSY.
 */

import Database from "better-sqlite3";
import { type BetterSQLite3Database, drizzle } from "drizzle-orm/better-sqlite3";

import * as schema from "./schema/index.js";

export type Schema = typeof schema;
// Named `PlatformDatabase` so it does not shadow the `better-sqlite3` default
// import (`Database.Database` is the raw handle below), mirroring the
// `StudioSqliteDatabase` naming in shared/infrastructure/db/connection.ts.
export type PlatformDatabase = BetterSQLite3Database<Schema>;

export interface DatabaseHandle {
  /** Escape hatch for PRAGMAs, the backup API, and `transaction()`. */
  readonly raw: Database.Database;
  readonly db: PlatformDatabase;
  close(): void;
}

export interface OpenDatabaseOptions {
  /** A file path, or `":memory:"` for tests. */
  readonly path: string;
  readonly busyTimeoutMs?: number;
}

export function openDatabase(options: OpenDatabaseOptions): DatabaseHandle {
  const raw = new Database(options.path);
  try {
    raw.pragma("journal_mode = WAL");
    raw.pragma("foreign_keys = ON");
    raw.pragma("synchronous = FULL");
    raw.pragma(`busy_timeout = ${String(options.busyTimeoutMs ?? 5_000)}`);
    return {
      raw,
      db: drizzle(raw, { schema }),
      close: () => {
        raw.close();
      },
    };
  } catch (error) {
    // A half-opened connection leaks a file lock; close before rethrowing.
    raw.close();
    throw error;
  }
}
