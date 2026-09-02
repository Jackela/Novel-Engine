import { existsSync, readFileSync } from "node:fs";
import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { runCli } from "../../../src/apps/cli/main.js";
import {
  exports as exportArtifacts,
  projectSnapshots,
  projects,
} from "../../../src/contexts/studio/infrastructure/db/schema.js";
import { AuthService } from "../../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../../src/shared/infrastructure/db/auth_store.js";
import { owners } from "../../../src/shared/infrastructure/db/schema.js";
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
  const studio = await openStudioDatabase(harness.databasePath);
  studio.close();
  expect(existsSync(harness.databasePath)).toBe(true);
}

async function seedMissingCommittedExport(harness: CliHarness): Promise<void> {
  const studio = await openStudioDatabase(harness.databasePath);
  const now = new Date("2026-08-31T18:00:00.000Z");
  try {
    studio.db
      .insert(owners)
      .values({
        id: "owner-recovery",
        username: "owner",
        password_hash: "test-only",
        created_at: now,
      })
      .run();
    studio.db
      .insert(projects)
      .values({
        id: "project-recovery",
        ownerId: "owner-recovery",
        title: "Recovery evidence",
        description: "",
        settingsJson: "{}",
        importHash: null,
        createdAt: now,
        updatedAt: now,
      })
      .run();
    studio.db
      .insert(projectSnapshots)
      .values({
        id: "snapshot-recovery",
        projectId: "project-recovery",
        reason: "export",
        createdAt: now,
      })
      .run();
    studio.db
      .insert(exportArtifacts)
      .values({
        id: "artifact-recovery",
        projectId: "project-recovery",
        snapshotId: "snapshot-recovery",
        format: "markdown",
        relativePath: "exports/project-recovery/artifact-recovery.md",
        sizeBytes: 7,
        checksumSha256: "a".repeat(64),
        createdAt: now,
      })
      .run();
  } finally {
    studio.close();
  }
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

  it("refuses backup while another process owns the data directory", async () => {
    const harness = await cliHarness();
    const active = await openStudioDatabase(harness.databasePath);
    try {
      const blockedCode = await runCli(["backup"], harness.context);

      expect(blockedCode).toBe(1);
      expect(harness.lines.join("\n")).toMatch(/already owned by another Novel Engine process/i);
      expect(existsSync(join(harness.dataDirectory, "backups"))).toBe(false);
    } finally {
      active.close();
    }

    harness.lines.length = 0;
    const completedCode = await runCli(["backup"], harness.context);
    expect(completedCode).toBe(0);
    expect(harness.lines[0]).toContain("backups");
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

  it("fails doctor and import before mutation when committed export bytes are missing", async () => {
    const harness = await cliHarness();
    await seedMissingCommittedExport(harness);

    const doctorCode = await runCli(["doctor"], harness.context);
    expect(doctorCode).toBe(1);
    const doctor = JSON.parse(harness.lines[0] ?? "") as Record<string, unknown>;
    expect(doctor.quick_check).toMatch(/missing/i);

    harness.lines.length = 0;
    const source = makeLegacyWorkspace(join(harness.directory, "blocked-import"), {
      title: "Must not import",
      chapters: [{ filename: "chapter-001.md", content: "# Blocked\n" }],
    });
    const importCode = await runCli(
      ["import", "--source", source, "--owner", "owner"],
      harness.context,
    );
    expect(importCode).toBe(1);
    expect(harness.lines.join("\n")).toMatch(/missing/i);

    const unchanged = await openStudioDatabase(harness.databasePath);
    try {
      expect(unchanged.db.select().from(projects).all()).toHaveLength(1);
      expect(unchanged.db.select().from(exportArtifacts).all()).toHaveLength(1);
    } finally {
      unchanged.close();
    }
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
    const database = await openStudioDatabase(harness.databasePath);
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
