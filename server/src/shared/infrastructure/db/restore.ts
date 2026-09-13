import { randomBytes } from "node:crypto";
import { copyFile, rename, stat, unlink } from "node:fs/promises";
import { basename, dirname, join } from "node:path";

import Database from "better-sqlite3";

import { backupDatabaseFile } from "./backup.js";

/**
 * WAL sidecar files of the replaced database. A stale `-wal` from the previous
 * database generation could be replayed onto the restored file on the next
 * open, so the replacement is never allowed to keep them.
 */
const WAL_SIDECAR_SUFFIXES = ["-wal", "-shm"] as const;

/**
 * Replace the configured database file with a verified backup file. The input
 * is opened read-only for `PRAGMA quick_check` before anything is touched; a
 * missing, unreadable, empty, or corrupt input refuses the restore with no
 * side effects. The current database then receives a safety backup through the
 * same online-backup path as `novel-engine backup` (a missing or empty
 * database is a clean bootstrap and produces none), so a failed backup never
 * reaches the replacement step. The replacement itself copies the verified
 * input to a staged file inside the data directory and renames it over the
 * database path — atomic within the data directory's filesystem.
 *
 * Returns the safety backup path, or null when no previous database existed.
 * Any refusal or filesystem failure throws and leaves the configured database
 * byte-for-byte untouched.
 */
export async function restoreDatabaseFile(
  databasePath: string,
  backupPath: string,
): Promise<string | null> {
  await verifyRestoreInput(backupPath);
  const safetyBackup = await backupDatabaseFile(databasePath);
  const stagedPath = stagedRestorePath(databasePath);
  try {
    await copyFile(backupPath, stagedPath);
    await rename(stagedPath, databasePath);
  } catch (error) {
    return discardStagedCopyAndRethrow(stagedPath, error);
  }
  await removeStaleWalSidecars(databasePath);
  return safetyBackup;
}

/**
 * Refuse any input that is missing, unreadable, empty, or fails the SQLite
 * integrity check. Only this module's refusal errors are raised here; every
 * branch names the exact input and why it was rejected.
 */
async function verifyRestoreInput(backupPath: string): Promise<void> {
  let size: number;
  try {
    size = (await stat(backupPath)).size;
  } catch (error) {
    throw new Error(`Restore input is missing or unreadable: ${backupPath}`, { cause: error });
  }
  if (size === 0) {
    throw new Error(`Restore input is empty and cannot be a Novel Engine backup: ${backupPath}`);
  }
  let input: Database.Database;
  try {
    input = new Database(backupPath, { readonly: true, fileMustExist: true });
  } catch (error) {
    if (error instanceof Database.SqliteError) {
      throw new Error(
        `Restore input failed the integrity check (${error.message}): ${backupPath}`,
        { cause: error },
      );
    }
    throw error;
  }
  let check: string;
  try {
    check = String(input.pragma("quick_check", { simple: true }));
  } catch (error) {
    if (error instanceof Database.SqliteError) {
      throw new Error(
        `Restore input failed the integrity check (${error.message}): ${backupPath}`,
        { cause: error },
      );
    }
    throw error;
  } finally {
    input.close();
  }
  if (check !== "ok") {
    throw new Error(`Restore input failed the integrity check (${check}): ${backupPath}`);
  }
}

/** Stage the verified copy inside the data directory so the rename is atomic. */
function stagedRestorePath(databasePath: string): string {
  const stamp = randomBytes(6).toString("hex");
  return join(dirname(databasePath), `.${basename(databasePath)}.${stamp}.restore-tmp`);
}

/**
 * Discard the staged copy after a failed copy or rename without discarding
 * either the staging failure or the cleanup failure; the database itself is
 * untouched because the rename never landed.
 */
async function discardStagedCopyAndRethrow(stagedPath: string, error: unknown): Promise<never> {
  try {
    await unlink(stagedPath);
  } catch (cleanupError) {
    if (errorCode(cleanupError) !== "ENOENT") {
      throw new AggregateError([error, cleanupError], "Restore staging and cleanup both failed.");
    }
  }
  throw error;
}

/**
 * Remove `-wal`/`-shm` sidecars left by the replaced database generation.
 * Runs only after a successful rename; a missing sidecar is the clean case.
 */
async function removeStaleWalSidecars(databasePath: string): Promise<void> {
  for (const suffix of WAL_SIDECAR_SUFFIXES) {
    try {
      await unlink(databasePath + suffix);
    } catch (error) {
      if (errorCode(error) !== "ENOENT") throw error;
    }
  }
}

function errorCode(error: unknown): string | undefined {
  if (typeof error !== "object" || error === null || !("code" in error)) return undefined;
  return typeof error.code === "string" ? error.code : undefined;
}
