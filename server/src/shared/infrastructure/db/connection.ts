import Database from "better-sqlite3";
import { type BetterSQLite3Database, drizzle } from "drizzle-orm/better-sqlite3";

import * as schema from "./schema.js";

export type StudioSchema = typeof schema;
export type StudioSqliteDatabase = BetterSQLite3Database<StudioSchema>;

export interface StudioConnection {
  readonly raw: Database.Database;
  readonly db: StudioSqliteDatabase;
}

/**
 * Open the content-authority connection with the adjudicated per-connection
 * PRAGMAs: write-ahead logging for abrupt-stop durability, enforced foreign
 * keys for cascade integrity, and NORMAL sync — the WAL checkpoint cadence
 * makes it the safe default the Python runtime also pins.
 */
export function openConnection(databasePath: string): StudioConnection {
  const raw = new Database(databasePath);
  raw.pragma("journal_mode = WAL");
  raw.pragma("foreign_keys = ON");
  raw.pragma("synchronous = NORMAL");
  return { raw, db: drizzle(raw, { schema }) };
}
