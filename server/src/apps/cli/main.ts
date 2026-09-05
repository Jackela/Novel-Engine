#!/usr/bin/env node
import { pathToFileURL } from "node:url";

import type { FastifyInstance } from "fastify";
import { openReconciledStudioDatabase } from "../../contexts/studio/infrastructure/reconciled_studio_database.js";
import {
  type LoadServerConfigInput,
  loadServerConfig,
  type ServerConfig,
} from "../../shared/infrastructure/config/server_config.js";
import { DrizzleAuthStore } from "../../shared/infrastructure/db/auth_store.js";
import { backupDatabaseFile } from "../../shared/infrastructure/db/backup.js";
import { acquireDataDirectoryLock } from "../../shared/infrastructure/db/data_directory_lock.js";
import {
  assertNoLegacyDatabaseSibling,
  databaseDataDirectory,
} from "../../shared/infrastructure/db/database_authority.js";
import { readProductIdentity } from "../../shared/infrastructure/workspace_manifest.js";
import { buildApp } from "../api/app.js";
import { closeResourceAndRethrow } from "../api/app_lifecycle.js";
import { runLegacyImportCommand } from "./legacy_import_command.js";
import {
  processShutdownSignalSource,
  runCliOwnedServeLifecycle,
  type ShutdownSignalSource,
} from "./shutdown_signals.js";

/**
 * The single emitted TS CLI root (#272): `serve`, `import`, `backup`, and
 * `doctor`. #273's legacy-import runner registers through `importRunner`;
 * there is no competing executable root.
 */

export type WriteLine = (line: string) => void;

type ServeOperation = (app: FastifyInstance, host: string, port: number) => Promise<void>;

/** The lifecycle owner is explicit before a serve operation is invoked. */
export type ServeRunner =
  | { readonly owner: "cli-owned"; readonly run: ServeOperation }
  | { readonly owner: "runner-owned"; readonly run: ServeOperation };

export interface ImportRunnerContext {
  readonly config: ServerConfig;
  readonly writeLine: WriteLine;
}

/** #273 registers its owner-principal import here (CLI-only, no HTTP auth). */
export type ImportRunner = (
  args: { source: string; owner: string | undefined },
  context: ImportRunnerContext,
) => Promise<number>;

export interface CliContext {
  /** Process-style variables; defaults to `process.env`. */
  readonly env?: LoadServerConfigInput["env"];
  /** `.env.local` location; `null` disables file loading (tests). */
  readonly envFile?: LoadServerConfigInput["envFile"];
  readonly workingDirectory?: LoadServerConfigInput["workingDirectory"];
  readonly writeLine?: WriteLine | undefined;
  /** Injectable lifecycle for tests; the default is CLI-owned. */
  readonly serve?: ServeRunner | undefined;
  /** Injectable signal event source; used only by CLI-owned serve lifecycles. */
  readonly shutdownSignalSource?: ShutdownSignalSource | undefined;
  /** Injectable composition boundary for lifecycle failure tests. */
  readonly buildApplication?: typeof buildApp | undefined;
  readonly importRunner?: ImportRunner | undefined;
  /** Injectable backup boundary for lifecycle failure tests. */
  readonly backupDatabaseFile?: typeof backupDatabaseFile | undefined;
  /** Injectable ownership boundary for lifecycle failure tests. */
  readonly acquireDataDirectoryLock?: typeof acquireDataDirectoryLock | undefined;
}

const USAGE = [
  "Usage: novel-engine <command> [options]",
  "",
  "Commands:",
  "  serve [--host HOST] [--port PORT]",
  "      Back up, migrate, reconcile exports, recover jobs, then serve the API.",
  "  import --source DIR [--owner NAME]",
  "      Import a legacy file workspace as the owner principal.",
  "  backup",
  "      Write a SQLite backup beneath the backups directory and print its path.",
  "  doctor",
  "      Report product identity, database integrity, journal mode, foreign keys, owner.",
].join("\n");

const NO_DATABASE_MESSAGE = "No database exists yet.";

function writeCliError(error: unknown, writeLine: WriteLine): void {
  if (error instanceof AggregateError) {
    writeLine(error.message);
    for (const nested of error.errors) writeCliError(nested, writeLine);
    return;
  }
  writeLine(error instanceof Error ? error.message : String(error));
}

interface ParsedArguments {
  command: string | undefined;
  readonly flags: Map<string, string | true>;
}

function parseArguments(argv: readonly string[]): ParsedArguments {
  const flags = new Map<string, string | true>();
  const valueFlags = new Set(["--host", "--port", "--source", "--owner"]);
  const [command] = argv;
  for (let index = 1; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === undefined) break;
    if (valueFlags.has(token)) {
      const value = argv[index + 1];
      if (value === undefined) {
        flags.set(token, true);
        break;
      }
      flags.set(token, value);
      index += 1;
      continue;
    }
    flags.set(token, true);
  }
  return { command, flags };
}

function configFor(context: CliContext): ServerConfig {
  return loadServerConfig({
    ...(context.env === undefined ? {} : { env: context.env }),
    ...(context.envFile === undefined ? {} : { envFile: context.envFile }),
    ...(context.workingDirectory === undefined
      ? {}
      : { workingDirectory: context.workingDirectory }),
  });
}

function flagValue(flags: Map<string, string | true>, name: string): string | undefined {
  const value = flags.get(name);
  return typeof value === "string" ? value : undefined;
}

async function defaultServe(app: FastifyInstance, host: string, port: number): Promise<void> {
  await app.listen({ host, port });
}

const DEFAULT_SERVE_RUNNER: ServeRunner = { owner: "cli-owned", run: defaultServe };

/** serve: backup → migrate → reconcile exports → recover jobs runs inside buildApp. */
async function serveCommand(
  parsed: ParsedArguments,
  context: CliContext,
  writeLine: WriteLine,
): Promise<number> {
  const config = configFor(context);
  const host = flagValue(parsed.flags, "--host") ?? config.host;
  const rawPort = flagValue(parsed.flags, "--port");
  const port = rawPort === undefined ? config.port : Number(rawPort);
  if (!Number.isInteger(port) || port < 1024 || port > 65535) {
    writeLine(`Invalid port: ${rawPort ?? String(port)}`);
    return 2;
  }
  const buildApplication = context.buildApplication ?? buildApp;
  const app = await buildApplication({ logger: true, config });
  const serve = context.serve ?? DEFAULT_SERVE_RUNNER;
  if (serve.owner === "runner-owned") {
    await serve.run(app, host, port);
    return 0;
  }
  return runCliOwnedServeLifecycle({
    source: context.shutdownSignalSource ?? processShutdownSignalSource,
    listen: () => serve.run(app, host, port),
    close: () => app.close(),
  });
}

async function backupCommand(context: CliContext, writeLine: WriteLine): Promise<number> {
  const config = configFor(context);
  const acquireOwnership = context.acquireDataDirectoryLock ?? acquireDataDirectoryLock;
  const runBackup = context.backupDatabaseFile ?? backupDatabaseFile;
  const dataDirectory = databaseDataDirectory(config.databasePath);
  const ownership = acquireOwnership(dataDirectory);
  let target: string | null;
  try {
    await assertNoLegacyDatabaseSibling(config.databasePath, dataDirectory);
    target = await runBackup(config.databasePath);
  } catch (error) {
    return closeResourceAndRethrow(
      () => ownership.close(),
      error,
      "Database backup and ownership cleanup both failed.",
    );
  }
  ownership.close();
  writeLine(target ?? NO_DATABASE_MESSAGE);
  return 0;
}

interface DoctorReport {
  name: string;
  version: string;
  database: string;
  quick_check: string;
  journal_mode: string;
  foreign_keys: boolean;
  owner_configured: boolean;
}

async function doctorCommand(context: CliContext, writeLine: WriteLine): Promise<number> {
  const config = configFor(context);
  const identity = readProductIdentity();
  const report: DoctorReport = {
    name: identity.name,
    version: identity.version,
    database: config.databasePath,
    quick_check: "unknown",
    journal_mode: "unknown",
    foreign_keys: false,
    owner_configured: false,
  };
  try {
    const studio = await openReconciledStudioDatabase(config.databasePath);
    try {
      report.quick_check = String(studio.raw.pragma("quick_check", { simple: true }));
      report.journal_mode = String(studio.raw.pragma("journal_mode", { simple: true }));
      report.foreign_keys = Boolean(studio.raw.pragma("foreign_keys", { simple: true }));
      report.owner_configured = new DrizzleAuthStore(studio.db).ownerExists();
    } finally {
      studio.close();
    }
  } catch (error) {
    // A database that cannot even be opened fails the integrity requirement.
    report.quick_check =
      error instanceof Error ? error.message : "the database could not be opened";
  }
  writeLine(JSON.stringify(report, null, 2));
  return report.quick_check === "ok" && report.foreign_keys ? 0 : 1;
}

async function importCommand(
  parsed: ParsedArguments,
  context: CliContext,
  writeLine: WriteLine,
): Promise<number> {
  const source = flagValue(parsed.flags, "--source");
  if (source === undefined) {
    writeLine("Import requires --source DIR.");
    return 2;
  }
  const runner = context.importRunner ?? legacyImportRunner;
  return runner(
    { source, owner: flagValue(parsed.flags, "--owner") },
    { config: configFor(context), writeLine },
  );
}

/** The default import runner: #273's owner-principal legacy import. */
const legacyImportRunner: ImportRunner = async (args, context) => {
  try {
    const imported = await runLegacyImportCommand({
      databasePath: context.config.databasePath,
      source: args.source,
      owner: args.owner,
    });
    context.writeLine(JSON.stringify(imported, null, 2));
    return 0;
  } catch (error) {
    writeCliError(error, context.writeLine);
    return 1;
  }
};

/** Dispatch one CLI invocation; the returned number is the exit code. */
export async function runCli(argv: readonly string[], context: CliContext = {}): Promise<number> {
  const writeLine = context.writeLine ?? console.log;
  const parsed = parseArguments(argv);
  try {
    switch (parsed.command) {
      case "serve":
        return await serveCommand(parsed, context, writeLine);
      case "backup":
        return await backupCommand(context, writeLine);
      case "doctor":
        return await doctorCommand(context, writeLine);
      case "import":
        return await importCommand(parsed, context, writeLine);
      default:
        writeLine(USAGE);
        return 2;
    }
  } catch (error) {
    // Every command reports failures through the same error channel; an
    // unhandled rejection would still exit 1 but silently.
    writeCliError(error, writeLine);
    return 1;
  }
}

async function main(): Promise<void> {
  const invoked = process.argv[1];
  if (invoked === undefined) return;
  process.exitCode = await runCli(process.argv.slice(2));
}

const invokedDirectly =
  process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href;
if (invokedDirectly) {
  await main();
}
