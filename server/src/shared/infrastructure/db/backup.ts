import { mkdir, stat } from "node:fs/promises";
import { basename, dirname, join } from "node:path";

import Database from "better-sqlite3";

export const DATABASE_FILENAME = "novel-engine.sqlite3";
export const BACKUPS_DIRECTORY = "backups";

/**
 * Write a consistent online backup of a non-empty SQLite database under
 * data/backups/ before migrations touch the schema. A missing or empty
 * database file is a clean bootstrap and produces no backup; the system
 * never removes backups afterwards.
 */
export async function backupDatabaseFile(databasePath: string): Promise<string | null> {
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
  const target = join(backupsDirectory, backupFileName(basename(databasePath)));
  await mkdir(backupsDirectory, { recursive: true });

  const source = new Database(databasePath);
  try {
    await source.backup(target);
  } finally {
    source.close();
  }
  return target;
}

function backupFileName(databaseFileName: string): string {
  const stem = databaseFileName.replace(/\.sqlite3$/, "");
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(".", "");
  return `${stem}-${stamp}.sqlite3.bak`;
}
