import { existsSync } from "node:fs";
import { mkdir, mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it, vi } from "vitest";

import { buildApp } from "../../../src/apps/api/app.js";
import { runCli } from "../../../src/apps/cli/main.js";

interface EnvironmentFileFailureHarness {
  readonly workspace: string;
  readonly envFile: string;
  readonly dataDirectory: string;
  readonly databasePath: string;
  readonly lines: string[];
  readonly context: Parameters<typeof runCli>[1];
}

async function environmentFileFailureHarness(): Promise<EnvironmentFileFailureHarness> {
  const workspace = await mkdtemp(join(tmpdir(), "novel-engine-cli-env-file-"));
  const envFile = join(workspace, ".env.local");
  await mkdir(envFile);
  const dataDirectory = join(workspace, "data");
  const databasePath = join(dataDirectory, "novel-engine.sqlite3");
  const lines: string[] = [];

  return {
    workspace,
    envFile,
    dataDirectory,
    databasePath,
    lines,
    context: {
      envFile,
      workingDirectory: workspace,
      env: {
        APP_ENVIRONMENT: "testing",
        DB_URL: `sqlite:///${databasePath}`,
      },
      writeLine: (line) => lines.push(line),
    },
  };
}

function expectConfigurationFailureWithoutArtifacts(
  harness: EnvironmentFileFailureHarness,
  code: number,
): void {
  expect(code).toBe(1);
  expect(harness.lines).toEqual([`Environment file must be a regular file: ${harness.envFile}`]);
  expect(existsSync(harness.dataDirectory)).toBe(false);
  expect(existsSync(harness.databasePath)).toBe(false);
  expect(existsSync(`${harness.databasePath}-journal`)).toBe(false);
  expect(existsSync(`${harness.databasePath}-shm`)).toBe(false);
  expect(existsSync(`${harness.databasePath}-wal`)).toBe(false);
  expect(existsSync(join(harness.dataDirectory, "backups"))).toBe(false);
}

describe("CLI environment-file failure boundaries", () => {
  it("fails serve before API composition or listener startup", async () => {
    const harness = await environmentFileFailureHarness();
    const buildApplication = vi.fn(buildApp);
    const run = vi.fn(async () => undefined);

    const code = await runCli(["serve", "--port", "8765"], {
      ...harness.context,
      buildApplication,
      serve: { owner: "runner-owned", run },
    });

    expectConfigurationFailureWithoutArtifacts(harness, code);
    expect(buildApplication).not.toHaveBeenCalled();
    expect(run).not.toHaveBeenCalled();
  });

  it("fails backup before ownership, backup, or cleanup boundaries", async () => {
    const harness = await environmentFileFailureHarness();
    const close = vi.fn();
    const acquireDataDirectoryLock = vi.fn(() => ({ close }));
    const backupDatabaseFile = vi.fn(async () => null);

    const code = await runCli(["backup"], {
      ...harness.context,
      acquireDataDirectoryLock,
      backupDatabaseFile,
    });

    expectConfigurationFailureWithoutArtifacts(harness, code);
    expect(acquireDataDirectoryLock).not.toHaveBeenCalled();
    expect(backupDatabaseFile).not.toHaveBeenCalled();
    expect(close).not.toHaveBeenCalled();
  });

  it("fails import before invoking its runner", async () => {
    const harness = await environmentFileFailureHarness();
    const importRunner = vi.fn(async () => 0);

    const code = await runCli(["import", "--source", join(harness.workspace, "legacy")], {
      ...harness.context,
      importRunner,
    });

    expectConfigurationFailureWithoutArtifacts(harness, code);
    expect(importRunner).not.toHaveBeenCalled();
  });

  it("fails doctor before reporting or opening a database", async () => {
    const harness = await environmentFileFailureHarness();

    const code = await runCli(["doctor"], harness.context);

    expectConfigurationFailureWithoutArtifacts(harness, code);
    expect(harness.lines[0]?.trimStart().startsWith("{")).toBe(false);
  });
});
