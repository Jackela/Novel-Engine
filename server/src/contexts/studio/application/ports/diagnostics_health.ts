/**
 * The database health half of the diagnostics export (#654): the `doctor`
 * command's field family read through the app's own database handle — the
 * composition root wires the in-process SQLite implementation, and nothing
 * ever shells out to the CLI.
 */
export interface DiagnosticsHealthReport {
  /** `PRAGMA quick_check` verdict, or the read failure's message. */
  readonly quickCheck: string;
  readonly journalMode: string;
  readonly foreignKeys: boolean;
  /** Whether the installation's single owner account exists. */
  readonly ownerConfigured: boolean;
}

/** Injectable probe so the assembly service stays persistence-neutral. */
export type DiagnosticsHealthProbe = () => DiagnosticsHealthReport;
