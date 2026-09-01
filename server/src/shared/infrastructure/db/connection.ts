import Database from "better-sqlite3";
import { type BetterSQLite3Database, drizzle } from "drizzle-orm/better-sqlite3";

import * as schema from "./schema.js";

export type StudioSchema = typeof schema;
export type StudioSqliteDatabase = BetterSQLite3Database<StudioSchema>;

export interface StudioConnection {
  readonly raw: Database.Database;
  readonly db: StudioSqliteDatabase;
}

/** Carries the still-open handle when initialization cleanup itself fails. */
export class StudioConnectionInitializationCleanupError extends AggregateError {
  constructor(
    readonly raw: Database.Database,
    initializationError: unknown,
    cleanupError: unknown,
  ) {
    super(
      [initializationError, cleanupError],
      "Studio connection initialization and cleanup both failed.",
    );
    this.name = "StudioConnectionInitializationCleanupError";
  }
}

/**
 * Open the content-authority connection with the adjudicated per-connection
 * PRAGMAs: write-ahead logging, enforced foreign keys for cascade integrity,
 * and FULL sync. Export publication and project deletion remove filesystem
 * recovery evidence only after a commit, so that commit must survive power
 * loss rather than relying on a later WAL checkpoint.
 */
export function openConnection(databasePath: string): StudioConnection {
  const raw = new Database(databasePath);
  try {
    raw.pragma("journal_mode = WAL");
    raw.pragma("foreign_keys = ON");
    raw.pragma("synchronous = FULL");
    return { raw, db: drizzle(raw, { schema }) };
  } catch (error) {
    try {
      raw.close();
    } catch (cleanupError) {
      throw new StudioConnectionInitializationCleanupError(raw, error, cleanupError);
    }
    throw error;
  }
}
