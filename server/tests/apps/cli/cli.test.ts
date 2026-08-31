import { existsSync, readFileSync } from "node:fs";
import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { runCli } from "../../../src/apps/cli/main.js";
import { AuthService } from "../../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../../src/shared/infrastructure/db/startup.js";
import { makeLegacyWorkspace } from "../../legacy_workspace_fixtures.js";

const productManifest = JSON.parse(
  readFileSync(new URL("../../../package.json", import.meta.url), "utf8"),
) as { productName: string; version: string };

interface CliHarness {
  directory: string;
  dataDirectory: string;
  databasePath: string;
  lines: string[];
  context: Parameters<typeof runCli>[1];
}

async function cliHarness(): Promise<CliHarness> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-cli-"));
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

/** Leave a migrated, non-empty database behind so backup/serve have state. */
async function seedDatabase(harness: CliHarness): Promise<void> {
  const studio = await openStudioDatabase(harness.dataDirectory);
  studio.close();
  expect(existsSync(harness.databasePath)).toBe(true);
}

describe("operational CLI", () => {
  it("backs up an existing database and prints the backup path", async () => {
    const harness = await cliHarness();
    await seedDatabase(harness);

    const code = await runCli(["backup"], harness.context);

    expect(code).toBe(0);
    expect(harness.lines).toHaveLength(1);
    const target = harness.lines[0];
    expect(typeof target).toBe("string");
    expect(existsSync(target ?? "")).toBe(true);
    expect(target).toContain("backups");
  });

  it("reports when no database exists to back up", async () => {
    const harness = await cliHarness();

    const code = await runCli(["backup"], harness.context);

    expect(code).toBe(0);
    expect(harness.lines).toEqual(["No database exists yet."]);
  });

  it("reports a healthy database through doctor and exits zero", async () => {
    const harness = await cliHarness();
    await seedDatabase(harness);

    const code = await runCli(["doctor"], harness.context);

    expect(code).toBe(0);
    expect(harness.lines).toHaveLength(1);
    const payload = JSON.parse(harness.lines[0] ?? "") as Record<string, unknown>;
    expect(payload).toEqual({
      name: productManifest.productName,
      version: productManifest.version,
      database: harness.databasePath,
      quick_check: "ok",
      journal_mode: "wal",
      foreign_keys: true,
      owner_configured: false,
    });
  });

  it("reports corruption through doctor and exits non-zero", async () => {
    const harness = await cliHarness();
    await seedDatabase(harness);
    await writeFile(harness.databasePath, "this is definitely not a sqlite database");

    const code = await runCli(["doctor"], harness.context);

    expect(code).toBe(1);
    const payload = JSON.parse(harness.lines[0] ?? "") as Record<string, unknown>;
    expect(payload.name).toBe(productManifest.productName);
    expect(payload.version).toBe(productManifest.version);
    expect(payload.database).toBe(harness.databasePath);
    expect(payload.quick_check).toEqual(expect.any(String));
    expect(payload.quick_check).not.toBe("ok");
    expect(payload.foreign_keys).toBe(false);
  });

  it("backs up and migrates before serve starts listening", async () => {
    const harness = await cliHarness();
    await seedDatabase(harness);
    const events: string[] = [];
    let backupsAtListen = -1;
    const context = {
      ...harness.context,
      serve: async (app: { close(): Promise<void> }, host: string, port: number) => {
        events.push(`listen:${host}:${port}`);
        const backups = join(harness.dataDirectory, "backups");
        backupsAtListen = existsSync(backups)
          ? (await (await import("node:fs/promises")).readdir(backups)).length
          : -1;
        await app.close();
      },
    };

    const code = await runCli(["serve", "--host", "127.0.0.1", "--port", "8765"], context);

    expect(code).toBe(0);
    expect(events).toEqual(["listen:127.0.0.1:8765"]);
    expect(backupsAtListen).toBeGreaterThan(0);
  });

  it("imports a legacy workspace through the default #273 runner", async () => {
    const harness = await cliHarness();
    const source = makeLegacyWorkspace(join(harness.directory, "legacy"), {
      title: "CLI Import Story",
      chapters: [{ filename: "chapter-001.md", content: "# One\n" }],
    });
    const database = await openStudioDatabase(harness.dataDirectory);
    try {
      await new AuthService({
        store: new DrizzleAuthStore(database.db),
        sessionSecret: "cli-test-session-secret",
      }).configureOwner("owner", "correct horse battery");
    } finally {
      database.close();
    }

    const code = await runCli(["import", "--source", source, "--owner", "owner"], harness.context);

    expect(code).toBe(0);
    expect(harness.lines.join("\n")).toContain("CLI Import Story");
    expect(harness.lines.join("\n")).toContain("import_hash");
  });

  it("reports a missing owner or bad source as a failed import (exit 1)", async () => {
    const harness = await cliHarness();

    const code = await runCli(
      ["import", "--source", join(harness.directory, "absent")],
      harness.context,
    );

    expect(code).toBe(1);
    expect(harness.lines.join("\n")).toContain("Configure the local owner");
  });

  it("delegates import to the registered runner (#273 seam)", async () => {
    const harness = await cliHarness();
    const received: Array<{ source: string; owner: string | undefined }> = [];
    const context = {
      ...harness.context,
      importRunner: async (args: { source: string; owner: string | undefined }) => {
        received.push(args);
        return 7;
      },
    };

    const code = await runCli(["import", "--source", "/legacy", "--owner", "ada"], context);

    expect(code).toBe(7);
    expect(received).toEqual([{ source: "/legacy", owner: "ada" }]);
  });

  it("prints usage for an unknown command", async () => {
    const harness = await cliHarness();

    const code = await runCli(["teleport"], harness.context);

    expect(code).toBe(2);
    expect(harness.lines.join("\n")).toContain("serve");
    expect(harness.lines.join("\n")).toContain("backup");
    expect(harness.lines.join("\n")).toContain("doctor");
  });
});
