import { mkdir, readdir, stat, statfs, unlink } from "node:fs/promises";
import { basename, dirname, join } from "node:path";

import Database from "better-sqlite3";

import { errorCode } from "../error_code.js";
import { removeSqliteSidecars } from "./sqlite_sidecars.js";

export const DATABASE_FILENAME = "novel-engine.sqlite3";
const BACKUPS_DIRECTORY = "backups";

/** Newest backup generations kept after each verified write; older ones are pruned. */
export const DEFAULT_BACKUP_RETENTION = 3;

/**
 * Injectable free-space probe: resolves the bytes available for new files in
 * the backups directory. Tests inject a constrained probe because a real
 * filesystem cannot be filled to the threshold reliably.
 */
export type BackupSpaceProbe = (backupsDirectory: string) => number | Promise<number>;

export interface BackupOptions {
  /** Backup generations to keep, newest first; defaults to `DEFAULT_BACKUP_RETENTION`. */
  readonly retention?: number;
  /** Free-space probe; defaults to `statfs` availability in the backups directory. */
  readonly spaceProbe?: BackupSpaceProbe;
}

/**
 * Write a consistent online backup of a non-empty SQLite database under
 * data/backups/ before migrations touch the schema. A missing or empty
 * database file is a clean bootstrap and produces no backup. Before writing,
 * the available space of the backups directory must cover the database size;
 * otherwise the call fails with the required and available byte counts and
 * writes nothing. After writing, the artifact must open read-only and pass
 * `PRAGMA quick_check`; an unopenable or failing artifact is deleted (with
 * its sidecars) and reported, never left behind. Only then are backups
 * beyond the retention count pruned, so the newest generations survive.
 */
export async function backupDatabaseFile(
  databasePath: string,
  options: BackupOptions = {},
): Promise<string | null> {
  let size: number;
  try {
    size = (await stat(databasePath)).size;
  } catch {
    return null;
  }
  if (size === 0) {
    return null;
  }

  const backupsDirectory = join(dirname(databasePath), BACKUPS_DIRECTORY);
  await mkdir(backupsDirectory, { recursive: true });
  await assertSufficientSpace(databasePath, backupsDirectory, size, options.spaceProbe);
  const target = join(backupsDirectory, backupFileName(basename(databasePath)));

  const source = new Database(databasePath);
  try {
    await source.backup(target);
  } finally {
    source.close();
  }
  await verifyWrittenBackup(target);
  await pruneOldBackups(
    backupsDirectory,
    basename(databasePath),
    options.retention ?? DEFAULT_BACKUP_RETENTION,
  );
  return target;
}

/** Fail with the exact numbers when the backups directory cannot hold the copy. */
async function assertSufficientSpace(
  databasePath: string,
  backupsDirectory: string,
  size: number,
  probe: BackupSpaceProbe | undefined,
): Promise<void> {
  const available = await (probe ?? defaultSpaceProbe)(backupsDirectory);
  if (available >= size) {
    return;
  }
  throw new Error(
    `Not enough free space to back up ${databasePath}: need ${size} bytes, only ${available} bytes are available in ${backupsDirectory}. Free disk space or move old backups out of the directory, then retry.`,
  );
}

async function defaultSpaceProbe(backupsDirectory: string): Promise<number> {
  const filesystem = await statfs(backupsDirectory);
  return filesystem.bavail * filesystem.bsize;
}

/**
 * Prove the fresh artifact openable and structurally sound. The read-only
 * check connection can leave `-wal`/`-shm` sidecars next to the artifact, so
 * they are removed in every outcome. Any failed check deletes the artifact
 * and throws naming both the artifact and the underlying detail: a backup
 * that cannot be trusted is never left behind.
 */
async function verifyWrittenBackup(backupPath: string): Promise<void> {
  let failure: unknown;
  try {
    await assertBackupIntegrity(backupPath);
  } catch (error) {
    failure = error;
  }
  await removeSqliteSidecars(backupPath);
  if (failure !== undefined) {
    await discardUnverifiableBackup(backupPath, failure);
  }
}

async function assertBackupIntegrity(backupPath: string): Promise<void> {
  const target = new Database(backupPath, { readonly: true, fileMustExist: true });
  try {
    const check = String(target.pragma("quick_check", { simple: true }));
    if (check !== "ok") {
      throw new Error(`PRAGMA quick_check reported "${check}"`);
    }
  } finally {
    target.close();
  }
}

/**
 * Remove an artifact that failed verification without losing either failure:
 * a concurrent removal (ENOENT) already achieved the goal, any other removal
 * failure surfaces as an AggregateError next to the verification cause.
 */
async function discardUnverifiableBackup(backupPath: string, cause: unknown): Promise<never> {
  try {
    await unlink(backupPath);
  } catch (removalError) {
    if (errorCode(removalError) !== "ENOENT") {
      throw new AggregateError(
        [cause, removalError],
        `Backup failed its integrity self-check and the unusable file could not be removed: ${backupPath}`,
        { cause: removalError },
      );
    }
  }
  const detail = cause instanceof Error ? cause.message : String(cause);
  throw new Error(
    `Backup failed its integrity self-check (${detail}): ${backupPath}. The file was removed; resolve the reported cause and run the backup again.`,
    { cause },
  );
}

/** Keep only the newest `retention` backups belonging to this database's naming family. */
async function pruneOldBackups(
  backupsDirectory: string,
  databaseFileName: string,
  retention: number,
): Promise<void> {
  if (retention < 1) {
    throw new Error(`Backup retention must keep at least one generation, received ${retention}.`);
  }
  const pattern = backupNamePattern(databaseFileName);
  const names = (await readdir(backupsDirectory)).filter((name) => pattern.test(name)).sort();
  for (const name of names.slice(0, Math.max(0, names.length - retention))) {
    const stalePath = join(backupsDirectory, name);
    try {
      await unlink(stalePath);
    } catch (error) {
      if (errorCode(error) === "ENOENT") continue;
      const detail = error instanceof Error ? error.message : String(error);
      throw new Error(`Pruning the superseded backup ${stalePath} failed: ${detail}`, {
        cause: error,
      });
    }
  }
}

/** Only artifacts this module writes are pruned; foreign files are left alone. */
function backupNamePattern(databaseFileName: string): RegExp {
  const stem = escapeForRegExp(databaseFileName.replace(/\.sqlite3$/, ""));
  return new RegExp(`^${stem}-\\d{8}T\\d{6,9}Z\\.sqlite3\\.bak$`);
}

function escapeForRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function backupFileName(databaseFileName: string): string {
  const stem = databaseFileName.replace(/\.sqlite3$/, "");
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(".", "");
  return `${stem}-${stamp}.sqlite3.bak`;
}
