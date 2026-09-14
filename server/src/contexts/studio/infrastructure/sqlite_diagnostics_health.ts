import type Database from "better-sqlite3";
import { DrizzleAuthStore } from "../../../shared/infrastructure/db/auth_store.js";
import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import type {
  DiagnosticsHealthProbe,
  DiagnosticsHealthReport,
} from "../application/ports/diagnostics_health.js";

/**
 * The diagnostics export's database health probe (#654): the `doctor`
 * command's field family read in-process through the app's own database
 * handle. A database whose pragmas cannot be read reports the failure through
 * the integrity field while the rest stays at the doctor defaults — exactly
 * the CLI's unopenable-database behavior, without shelling out to it.
 */
export function sqliteDiagnosticsHealth(
  raw: Database.Database,
  database: StudioSqliteDatabase,
): DiagnosticsHealthProbe {
  return (): DiagnosticsHealthReport => {
    const report: {
      quickCheck: string;
      journalMode: string;
      foreignKeys: boolean;
      ownerConfigured: boolean;
    } = {
      quickCheck: "unknown",
      journalMode: "unknown",
      foreignKeys: false,
      ownerConfigured: false,
    };
    try {
      report.quickCheck = String(raw.pragma("quick_check", { simple: true }));
      report.journalMode = String(raw.pragma("journal_mode", { simple: true }));
      report.foreignKeys = Boolean(raw.pragma("foreign_keys", { simple: true }));
      report.ownerConfigured = new DrizzleAuthStore(database).ownerExists();
    } catch (error) {
      // The integrity field carries the read failure; doctor parity.
      report.quickCheck = error instanceof Error ? error.message : "the database could not be read";
    }
    return report;
  };
}
