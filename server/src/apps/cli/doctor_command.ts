import { existsSync } from "node:fs";

import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";

import {
  type DocumentIndexReconciliation,
  documentIndexReconciliation,
} from "../../contexts/studio/infrastructure/db/document_search.js";
import type { ServerConfig } from "../../shared/infrastructure/config/server_config.js";
import { DrizzleAuthStore } from "../../shared/infrastructure/db/auth_store.js";
import type { StudioSqliteDatabase } from "../../shared/infrastructure/db/connection.js";
import {
  databaseDataDirectory,
  legacyDatabaseSibling,
} from "../../shared/infrastructure/db/database_authority.js";
import {
  type MigrationProgress,
  readMigrationProgress,
} from "../../shared/infrastructure/db/pending_migrations.js";
import * as schema from "../../shared/infrastructure/db/schema.js";
import { bundledMigrationsJournalPath } from "../../shared/infrastructure/db/startup.js";
import { readProductIdentity } from "../../shared/infrastructure/workspace_manifest.js";

type WriteLine = (line: string) => void;

export interface DoctorCommandContext {
  readonly config: ServerConfig;
  readonly writeLine: WriteLine;
}

interface DoctorReport {
  name: string;
  version: string;
  database: string;
  /** The integrity pragma's result, or "unknown" when it could not run. */
  quick_check: string;
  journal_mode: string;
  foreign_keys: boolean;
  owner_configured: boolean;
  /** Index reconciliation (#DR-004); null when the probe could not run. */
  document_index: DocumentIndexReconciliation | null;
  /** Applied/pending migration reading; null when the probe could not run. */
  migrations: MigrationProgress | null;
  /** The first probe failure's reason; null when every probe ran. */
  error: string | null;
}

interface DoctorSession {
  readonly raw: Database.Database;
  readonly db: StudioSqliteDatabase;
}

const SIDECAR_SUFFIXES = ["-wal", "-shm", "-journal"] as const;

/**
 * The `novel-engine doctor` command body — a strictly read-only health
 * report. It never migrates, backs up, reconciles, or takes the exclusive
 * data-directory ownership a running server holds, so it can run against a
 * stopped copy or a database a server is currently serving. Every failure
 * is reported through the `error` field with the actual reason (a locked
 * database reads "database is locked", a missing file names the path) and
 * never through `quick_check`, whose only values are the integrity pragma's
 * result and "unknown"; the exit code is zero only when the database opens,
 * passes `quick_check`, and enforces foreign keys. The write path is
 * `novel-engine migrate`.
 */
export async function runDoctorCommand(context: DoctorCommandContext): Promise<number> {
  const { config, writeLine } = context;
  const identity = readProductIdentity();
  const report: DoctorReport = {
    name: identity.name,
    version: identity.version,
    database: config.databasePath,
    quick_check: "unknown",
    journal_mode: "unknown",
    foreign_keys: false,
    owner_configured: false,
    document_index: null,
    migrations: null,
    error: null,
  };
  const legacySibling = await legacyDatabaseSibling(
    config.databasePath,
    databaseDataDirectory(config.databasePath),
  );
  if (legacySibling !== null) {
    report.error =
      `The configured database ${config.databasePath} stands beside the legacy default ` +
      `database ${legacySibling}; choose one database authority explicitly — Novel Engine ` +
      "will not move, merge, or fall back.";
  } else if (!existsSync(config.databasePath)) {
    report.error =
      `No database file exists at ${config.databasePath}; run \`novel-engine migrate\` or ` +
      "`novel-engine serve` to initialize it.";
  } else {
    probeDatabase(report, config.databasePath);
  }
  writeLine(JSON.stringify(report, null, 2));
  return report.error === null && report.quick_check === "ok" && report.foreign_keys ? 0 : 1;
}

/** Run every probe on one session, sending the first failure to `error`. */
function probeDatabase(report: DoctorReport, databasePath: string): void {
  let session: DoctorSession | undefined;
  try {
    session = openDoctorSession(databasePath);
    report.quick_check = String(session.raw.pragma("quick_check", { simple: true }));
    report.journal_mode = String(session.raw.pragma("journal_mode", { simple: true }));
    report.foreign_keys = Boolean(session.raw.pragma("foreign_keys", { simple: true }));
    report.migrations = readMigrationProgress(session.raw, bundledMigrationsJournalPath());
    report.owner_configured = new DrizzleAuthStore(session.db).ownerExists();
    report.document_index = documentIndexReconciliation(session.raw);
  } catch (error) {
    report.error = error instanceof Error ? error.message : String(error);
  } finally {
    session?.raw.close();
  }
}

/**
 * Open one diagnostic session without writing to the database directory.
 * better-sqlite3 cannot open a read-only SQLite WAL database without creating
 * the missing `-shm`/`-wal` sidecars (measured: both files appear after a
 * read-only probe of a cleanly closed WAL database), which would write to the
 * very copy doctor must not touch. So when no sidecar exists — the database
 * was closed cleanly, nothing can be recovered, and no writer can be mid-WAL —
 * the session opens the file and immediately enables `query_only`, making
 * SQLite reject every write at the statement level while the session's clean
 * close removes only the transient sidecars it created; tests pin that the
 * directory listing, file bytes, and mtime stay exactly as found. When a
 * sidecar does exist (a writer is running or ended uncleanly), the WAL must
 * be read through that sidecar set: a plain read-only open attaches to the
 * existing files, creates nothing new, and never checkpoints or recovers
 * them. Both shapes enable `foreign_keys` exactly the way `openConnection`
 * does, so the reported value reflects the application's own session policy.
 * A locked database surfaces its lock as a probe failure instead of being
 * written to.
 */
function openDoctorSession(databasePath: string): DoctorSession {
  const attachToExistingWal = hasDatabaseSidecar(databasePath);
  const raw = new Database(databasePath, {
    readonly: attachToExistingWal,
    fileMustExist: true,
    timeout: 0,
  });
  try {
    if (!attachToExistingWal) raw.pragma("query_only = ON");
    raw.pragma("foreign_keys = ON");
    return { raw, db: drizzle(raw, { schema }) };
  } catch (error) {
    raw.close();
    throw error;
  }
}

/** True when any SQLite sidecar of the database file is present. */
function hasDatabaseSidecar(databasePath: string): boolean {
  return SIDECAR_SUFFIXES.some((suffix) => existsSync(`${databasePath}${suffix}`));
}
