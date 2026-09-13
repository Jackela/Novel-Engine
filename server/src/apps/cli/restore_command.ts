import type { ServerConfig } from "../../shared/infrastructure/config/server_config.js";
import { acquireDataDirectoryLock } from "../../shared/infrastructure/db/data_directory_lock.js";
import {
  assertNoLegacyDatabaseSibling,
  databaseDataDirectory,
} from "../../shared/infrastructure/db/database_authority.js";
import { restoreDatabaseFile } from "../../shared/infrastructure/db/restore.js";
import { closeResourceAndRethrow } from "../api/app_lifecycle.js";

type WriteLine = (line: string) => void;

export interface RestoreCommandInput {
  /** Parsed `--input` flag; undefined when the flag was omitted. */
  readonly input: string | undefined;
}

export interface RestoreCommandContext {
  readonly config: ServerConfig;
  readonly writeLine: WriteLine;
}

/**
 * The `novel-engine restore` command body — the programmatic entry the CLI
 * dispatcher registers. It takes data-directory ownership first, so a running
 * server refuses the restore before anything is read or written. The backup
 * input is verified (read-only `PRAGMA quick_check`), the current database
 * receives a safety backup through the same path as `novel-engine backup`,
 * and only then is the database replaced atomically. Every completed step is
 * reported through `writeLine`; a refused restore reports its reason through
 * the shared CLI error channel and exits non-zero before the database is
 * touched. The one failure that can surface after the replacement has landed
 * — stale WAL sidecar removal — is reported as "database replaced, sidecar
 * removal unresolved" so the operator never mistakes a completed restore for
 * a no-op. Backup file contents and database paths
 * are printed, never credentials or other secret configuration.
 */
export async function runRestoreCommand(
  input: RestoreCommandInput,
  context: RestoreCommandContext,
): Promise<number> {
  if (input.input === undefined) {
    context.writeLine("Restore requires --input BACKUP.");
    return 2;
  }
  const { config, writeLine } = context;
  const dataDirectory = databaseDataDirectory(config.databasePath);
  const ownership = acquireDataDirectoryLock(dataDirectory);
  let safetyBackup: string | null;
  try {
    await assertNoLegacyDatabaseSibling(config.databasePath, dataDirectory);
    writeLine(`Verifying restore input: ${input.input}`);
    safetyBackup = await restoreDatabaseFile(config.databasePath, input.input);
  } catch (error) {
    return closeResourceAndRethrow(
      () => ownership.close(),
      error,
      "Database restore and ownership cleanup both failed.",
    );
  }
  ownership.close();
  writeLine(
    safetyBackup === null
      ? "No existing database to back up."
      : `Backed up the replaced database: ${safetyBackup}`,
  );
  writeLine(`Restored the database: ${config.databasePath}`);
  return 0;
}
