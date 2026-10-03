import { readFileSync, statSync } from "node:fs";

import Database from "better-sqlite3";

import { errorCode } from "../error_code.js";

/** Drizzle's migration journal table, the probe target for applied migrations. */
const MIGRATIONS_TABLE = "__drizzle_migrations";

/**
 * Whether the bundled journal (`meta/_journal.json`) holds an entry newer
 * than the database's newest applied migration — the cheap pre-flight twin
 * of the drizzle migrator's own decision (`Number(lastDbMigration.created_at)
 * < migration.folderMillis`; a missing journal table means every entry is
 * pending). Startup backs up only when this returns true, so a restart
 * without a schema change writes no backup. A missing or empty database file
 * reports false: there is nothing to back up and the migrator bootstraps it.
 * A database that fails to open (unreadable, corrupt) reports true so the
 * conservative pre-migration safety backup still runs and the migrator (or
 * the backup) reports the real failure; unexpected probe errors rethrow.
 */
export function hasPendingMigrations(databasePath: string, journalPath: string): boolean {
  let size: number;
  try {
    size = statSync(databasePath).size;
  } catch (error) {
    if (errorCode(error) === "ENOENT") return false;
    throw error;
  }
  if (size === 0) return false;

  const newestJournalMillis = newestJournalEntryMillis(journalPath);
  let probe: Database.Database;
  try {
    probe = new Database(databasePath, { readonly: true, fileMustExist: true });
  } catch (error) {
    if (error instanceof Database.SqliteError) return true;
    throw error;
  }
  try {
    if (!migrationsTableExists(probe)) return true;
    const newest = probe
      .prepare('SELECT created_at FROM "__drizzle_migrations" ORDER BY created_at DESC LIMIT 1')
      .get() as { created_at: number | string } | undefined;
    if (newest === undefined) return true;
    return Number(newest.created_at) < newestJournalMillis;
  } catch (error) {
    if (error instanceof Database.SqliteError) return true;
    throw error;
  } finally {
    probe.close();
  }
}

/** Whether the journal table exists at all; lookup is parameterized, never concatenated. */
function migrationsTableExists(probe: Database.Database): boolean {
  const row = probe
    .prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?")
    .get(MIGRATIONS_TABLE);
  return row !== undefined;
}

/** The newest `when` timestamp across the bundled journal entries. */
function newestJournalEntryMillis(journalPath: string): number {
  let raw: string;
  try {
    raw = readFileSync(journalPath, "utf8");
  } catch (error) {
    throw new Error(`Bundled migration journal is unreadable: ${journalPath}`, { cause: error });
  }
  let entries: unknown;
  try {
    const parsed: unknown = JSON.parse(raw);
    entries =
      typeof parsed === "object" && parsed !== null
        ? (parsed as { entries?: unknown }).entries
        : undefined;
  } catch (error) {
    throw new Error(`Bundled migration journal is not valid JSON: ${journalPath}`, {
      cause: error,
    });
  }
  if (!Array.isArray(entries) || entries.length === 0) {
    throw new Error(`Bundled migration journal has no entries: ${journalPath}`);
  }
  return entries.reduce((newest: number, entry: unknown) => {
    const when = (entry as { when?: unknown }).when;
    if (typeof when !== "number") {
      throw new Error(
        `Bundled migration journal entry is missing its "when" timestamp: ${journalPath}`,
      );
    }
    return Math.max(newest, when);
  }, 0);
}
