import { mkdir, mkdtemp, readdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import Database from "better-sqlite3";
import { describe, expect, it } from "vitest";

import { runCli } from "../../../src/apps/cli/main.js";

interface CliHarness {
  directory: string;
  dataDirectory: string;
  databasePath: string;
  lines: string[];
  context: Parameters<typeof runCli>[1];
}

async function cliHarness(): Promise<CliHarness> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-backup-cli-"));
  const dataDirectory = join(directory, "data");
  await mkdir(dataDirectory, { recursive: true });
  const databasePath = join(dataDirectory, "novel-engine.sqlite3");
  const lines: string[] = [];
  return {
    directory,
    dataDirectory,
    databasePath,
    lines,
    context: {
      envFile: null,
      workingDirectory: directory,
      env: { DB_URL: `sqlite:///${databasePath}`, APP_ENVIRONMENT: "testing" },
      writeLine: (line: string) => {
        lines.push(line);
      },
    },
  };
}

/** Leave a non-empty database behind that the bundled migrations have not seen. */
function seedPreMigrationDatabase(harness: CliHarness): void {
  const preRelease = new Database(harness.databasePath);
  try {
    preRelease.exec("CREATE TABLE pre_rewrite_marker (id TEXT PRIMARY KEY)");
    preRelease.prepare("INSERT INTO pre_rewrite_marker (id) VALUES (?)").run("kept-content");
  } finally {
    preRelease.close();
  }
}

async function backupNames(directory: string): Promise<string[]> {
  return readdir(join(directory, "backups")).catch(() => []);
}

describe("backup CLI policy", () => {
  it("backs up once for a pending migration and not on the following restart", async () => {
    const harness = await cliHarness();
    seedPreMigrationDatabase(harness);
    let backupsAtListen = -1;
    const context = {
      ...harness.context,
      serve: {
        owner: "runner-owned" as const,
        run: async (app: { close(): Promise<void> }) => {
          backupsAtListen = (await backupNames(harness.dataDirectory)).length;
          await app.close();
        },
      },
    };

    expect(await runCli(["serve", "--host", "127.0.0.1", "--port", "8765"], context)).toBe(0);
    expect(backupsAtListen).toBe(1);

    harness.lines.length = 0;
    expect(await runCli(["serve", "--host", "127.0.0.1", "--port", "8765"], context)).toBe(0);
    expect(await backupNames(harness.dataDirectory)).toHaveLength(1);
  });

  it("fails the backup command with a readable error and removes the unverifiable file", async () => {
    const harness = await cliHarness();
    seedPreMigrationDatabase(harness);
    const originalPragma = Database.prototype.pragma;
    Database.prototype.pragma = function pragmaWithFailingQuickCheck(source, options) {
      if (this.name.endsWith(".sqlite3.bak") && source === "quick_check") {
        throw new Error("simulated malformed backup");
      }
      return originalPragma.call(this, source, options);
    };
    try {
      expect(await runCli(["backup"], harness.context)).toBe(1);
      expect(harness.lines.join("\n")).toMatch(
        /Backup failed its integrity self-check \(simulated malformed backup\)/,
      );
    } finally {
      Database.prototype.pragma = originalPragma;
    }

    expect(await backupNames(harness.dataDirectory)).toEqual([]);
  });

  it("documents that backups are plaintext in the CLI help", async () => {
    const harness = await cliHarness();

    expect(await runCli(["teleport"], harness.context)).toBe(2);

    expect(harness.lines.join("\n")).toMatch(/Backups are plaintext SQLite files/);
  });
});
