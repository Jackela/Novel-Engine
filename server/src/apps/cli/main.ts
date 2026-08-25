#!/usr/bin/env node
import { pathToFileURL } from "node:url";

import type { FastifyInstance } from "fastify";
import {
  type LoadServerConfigInput,
  loadServerConfig,
  type ServerConfig,
} from "../../shared/infrastructure/config/server_config.js";
import { DrizzleAuthStore } from "../../shared/infrastructure/db/auth_store.js";
import { backupDatabaseFile } from "../../shared/infrastructure/db/backup.js";
import { openStudioDatabase } from "../../shared/infrastructure/db/startup.js";
import { readWorkspaceVersion } from "../../shared/infrastructure/workspace_manifest.js";
import { buildApp } from "../api/app.js";
import { runLegacyImportCommand } from "./legacy_import_command.js";

/**
 * The single emitted TS CLI root (#272): `serve`, `import`, `backup`, and
 * `doctor`. #273's legacy-import runner registers through `importRunner`;
 * there is no competing executable root.
 */

export type WriteLine = (line: string) => void;

export type ServeRunner = (app: FastifyInstance, host: string, port: number) => Promise<void>;

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
  /** Injectable listener for tests; the default binds the built app. */
  readonly serve?: ServeRunner | undefined;
  readonly importRunner?: ImportRunner | undefined;
}

const USAGE = [
  "Usage: novel-engine <command> [options]",
  "",
  "Commands:",
  "  serve [--host HOST] [--port PORT]",
  "      Back up the SQLite store, apply migrations, then serve the API.",
  "  import --source DIR [--owner NAME]",
  "      Import a legacy file workspace as the owner principal.",
  "  backup",
  "      Write a SQLite backup beneath the backups directory and print its path.",
  "  doctor",
  "      Report version, database integrity, journal mode, foreign keys, owner.",
].join("\n");

const NO_DATABASE_MESSAGE = "No database exists yet.";

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

/** serve: the persistence pipeline (backup → migrate → recover) runs inside buildApp. */
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
  const app = await buildApp({ logger: true, config });
  const runServe = context.serve ?? defaultServe;
  await runServe(app, host, port);
  return 0;
}

async function backupCommand(context: CliContext, writeLine: WriteLine): Promise<number> {
  const config = configFor(context);
  const target = await backupDatabaseFile(config.databasePath);
  writeLine(target ?? NO_DATABASE_MESSAGE);
  return 0;
}

interface DoctorReport {
  version: string;
  database: string;
  quick_check: string;
  journal_mode: string;
  foreign_keys: boolean;
  owner_configured: boolean;
}

async function doctorCommand(context: CliContext, writeLine: WriteLine): Promise<number> {
  const config = configFor(context);
  const report: DoctorReport = {
    version: readWorkspaceVersion(),
    database: config.databasePath,
    quick_check: "unknown",
    journal_mode: "unknown",
    foreign_keys: false,
    owner_configured: false,
  };
  try {
    const studio = await openStudioDatabase(config.dataDirectory);
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
      dataDirectory: context.config.dataDirectory,
      source: args.source,
      owner: args.owner,
    });
    context.writeLine(JSON.stringify(imported, null, 2));
    return 0;
  } catch (error) {
    context.writeLine(error instanceof Error ? error.message : String(error));
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
    writeLine(error instanceof Error ? error.message : String(error));
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
