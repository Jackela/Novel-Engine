import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type Database from "better-sqlite3";
import { migrate } from "drizzle-orm/better-sqlite3/migrator";

import { backupDatabaseFile } from "./backup.js";
import {
  openConnection,
  StudioConnectionInitializationCleanupError,
  type StudioQueryLogger,
  type StudioSqliteDatabase,
} from "./connection.js";
import { acquireDataDirectoryLock, type DataDirectoryLock } from "./data_directory_lock.js";
import { assertNoLegacyDatabaseSibling, databaseDataDirectory } from "./database_authority.js";

const SEARCH_DEPTH = 8;
const PACKAGE_ROOT_MARKER = "drizzle.config.ts";
const MIGRATIONS_DIRECTORY = "drizzle";

export interface StudioDatabase {
  readonly db: StudioSqliteDatabase;
  readonly raw: Database.Database;
  readonly databasePath: string;
  readonly dataDirectory: string;
  close(): void;
}

interface OpenStudioDatabaseOptions {
  /** Context-owned reconciliation after schema migration and before job recovery. */
  readonly beforeJobRecovery?:
    | ((database: StudioSqliteDatabase, dataDirectory: string) => Promise<void> | void)
    | undefined;
  /**
   * Context-owned job-state recovery after the reconciliation hook; production
   * wires the studio restart recovery here (#534). Opening without it skips
   * recovery, so callers relying on the restart contract must inject it.
   */
  readonly recoverJobs?: ((database: StudioSqliteDatabase) => number) | undefined;
  /** Optional statement observer; persistence behavior remains unchanged. */
  readonly queryLogger?: StudioQueryLogger | undefined;
}

/**
 * The startup pipeline of the content authority, in the adjudicated order:
 * exclusive data-directory ownership, legacy-authority ambiguity rejection,
 * online backup of any pre-existing non-empty database, schema migrations, the optional context-owned
 * reconciliation hook, then the injected job-state recovery — only afterwards
 * may the caller serve.
 */
export async function openStudioDatabase(
  databasePath: string,
  options: OpenStudioDatabaseOptions = {},
): Promise<StudioDatabase> {
  const dataDirectory = databaseDataDirectory(databasePath);
  const ownership = acquireDataDirectoryLock(dataDirectory);
  let connection: ReturnType<typeof openConnection> | undefined;
  try {
    await assertNoLegacyDatabaseSibling(databasePath, dataDirectory);
    await backupDatabaseFile(databasePath);

    connection = openConnection(databasePath, { queryLogger: options.queryLogger });
    const { db } = connection;
    migrate(db, { migrationsFolder: locateMigrationsFolder() });
    await options.beforeJobRecovery?.(db, dataDirectory);
    options.recoverJobs?.(db);
  } catch (error) {
    const failedRaw =
      error instanceof StudioConnectionInitializationCleanupError ? error.raw : connection?.raw;
    releaseAfterStartupFailure(failedRaw, ownership, error);
  }
  const { raw, db } = connection;
  let contentClosed = false;
  let ownershipReleased = false;
  return {
    db,
    raw,
    databasePath,
    dataDirectory,
    close: () => {
      if (!contentClosed) {
        raw.close();
        contentClosed = true;
      }
      if (!ownershipReleased) {
        ownership.close();
        ownershipReleased = true;
      }
    },
  };
}

function releaseAfterStartupFailure(
  raw: Database.Database | undefined,
  ownership: DataDirectoryLock,
  startupError: unknown,
): never {
  if (raw !== undefined) {
    try {
      raw.close();
    } catch (closeError) {
      // The ownership connection must remain locked when the content authority
      // cannot prove that its handle closed. Releasing it here would allow a
      // second process to open the same data directory concurrently.
      throw new AggregateError(
        [startupError, closeError],
        "Studio database startup failed and the content database did not close.",
      );
    }
  }
  try {
    ownership.close();
  } catch (ownershipError) {
    throw new AggregateError(
      [startupError, ownershipError],
      "Studio database startup and ownership release failed.",
    );
  }
  throw startupError;
}

function locateMigrationsFolder(): string {
  let directory = dirname(fileURLToPath(import.meta.url));
  for (let depth = 0; depth < SEARCH_DEPTH; depth += 1) {
    if (existsSync(join(directory, PACKAGE_ROOT_MARKER))) {
      return join(directory, MIGRATIONS_DIRECTORY);
    }
    const parent = dirname(directory);
    if (parent === directory) {
      break;
    }
    directory = parent;
  }
  throw new Error(
    "drizzle migrations folder not found above server/src — run the server from the workspace checkout",
  );
}
