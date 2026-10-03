import { openReconciledStudioDatabase } from "../../contexts/studio/infrastructure/reconciled_studio_database.js";
import type { ServerConfig } from "../../shared/infrastructure/config/server_config.js";
import { readMigrationProgress } from "../../shared/infrastructure/db/pending_migrations.js";
import { bundledMigrationsJournalPath } from "../../shared/infrastructure/db/startup.js";

type WriteLine = (line: string) => void;

export interface MigrateCommandContext {
  readonly config: ServerConfig;
  readonly writeLine: WriteLine;
}

/**
 * The `novel-engine migrate` command body — the explicit write path doctor
 * separates from: it reuses the production startup open (exclusive
 * data-directory ownership, the conditional pre-migration backup of DR-031,
 * the bundled schema migrations, export-publication reconciliation, and
 * interrupted-job recovery), closes the handle immediately, and prints the
 * post-run applied/pending migration reading. A running server refuses the
 * command before anything is read or written through the same ownership
 * error every maintenance command reports; any failure surfaces through the
 * shared CLI error channel with a non-zero exit and no report line.
 */
export async function runMigrateCommand(context: MigrateCommandContext): Promise<number> {
  const database = await openReconciledStudioDatabase(context.config.databasePath);
  try {
    const migrations = readMigrationProgress(database.raw, bundledMigrationsJournalPath());
    context.writeLine(JSON.stringify({ database: database.databasePath, migrations }, null, 2));
    return 0;
  } finally {
    database.close();
  }
}
