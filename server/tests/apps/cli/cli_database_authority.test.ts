import { existsSync } from "node:fs";
import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it, vi } from "vitest";

import { runCli } from "../../../src/apps/cli/main.js";
import { AuthService } from "../../../src/shared/application/auth_service.js";
import { DrizzleAuthStore } from "../../../src/shared/infrastructure/db/auth_store.js";
import { openStudioDatabase } from "../../../src/shared/infrastructure/db/startup.js";
import { directoryFingerprint, makeLegacyWorkspace } from "../../legacy_workspace_fixtures.js";

async function harness() {
  const workspace = await mkdtemp(join(tmpdir(), "novel-engine-cli-authority-"));
  const dataDirectory = join(workspace, "data");
  await mkdir(dataDirectory, { recursive: true });
  const databasePath = join(dataDirectory, "author.sqlite3");
  const legacyPath = join(dataDirectory, "novel-engine.sqlite3");
  const lines: string[] = [];
  const context: Parameters<typeof runCli>[1] = {
    envFile: null,
    workingDirectory: workspace,
    env: { APP_ENVIRONMENT: "testing", DB_URL: `sqlite:///${databasePath}` },
    writeLine: (line) => lines.push(line),
  };
  return { context, dataDirectory, databasePath, legacyPath, lines };
}

describe("configured database authority in the CLI", () => {
  it("serve and doctor preserve a custom basename", async () => {
    const state = await harness();
    const serveCode = await runCli(["serve", "--port", "8765"], {
      ...state.context,
      serve: async (app) => app.close(),
    });

    expect(serveCode).toBe(0);
    expect(existsSync(state.databasePath)).toBe(true);
    expect(existsSync(state.legacyPath)).toBe(false);

    state.lines.length = 0;
    const doctorCode = await runCli(["doctor"], state.context);
    expect(doctorCode).toBe(0);
    expect(JSON.parse(state.lines[0] ?? "").database).toBe(state.databasePath);
    expect(existsSync(state.legacyPath)).toBe(false);

    state.lines.length = 0;
    const backupCode = await runCli(["backup"], state.context);
    expect(backupCode).toBe(0);
    expect(state.lines[0]).toContain("author-");
    expect(existsSync(state.lines[0] ?? "")).toBe(true);
    expect(existsSync(state.legacyPath)).toBe(false);
  });

  it("backup rejects a legacy sibling before invoking the backup boundary", async () => {
    const state = await harness();
    await writeFile(state.legacyPath, "legacy authority");
    const backup = vi.fn(async () => null);

    const code = await runCli(["backup"], {
      ...state.context,
      backupDatabaseFile: backup,
    });

    expect(code).toBe(1);
    expect(backup).not.toHaveBeenCalled();
    expect(state.lines.join("\n")).toContain(state.databasePath);
    expect(state.lines.join("\n")).toContain(state.legacyPath);
  });

  it("imports into the custom basename without creating the default sibling", async () => {
    const state = await harness();
    const database = await openStudioDatabase(state.databasePath);
    try {
      await new AuthService({
        store: new DrizzleAuthStore(database.db),
        sessionSecret: "cli-authority-test-session-secret",
      }).configureOwner("owner", "correct horse battery");
    } finally {
      database.close();
    }
    const source = makeLegacyWorkspace(join(state.dataDirectory, "legacy-source"), {
      title: "Custom database import",
      chapters: [{ filename: "chapter-001.md", content: "# Exact authority\n" }],
    });

    const code = await runCli(["import", "--source", source, "--owner", "owner"], state.context);

    expect(code).toBe(0);
    expect(state.lines.join("\n")).toContain("Custom database import");
    expect(existsSync(state.databasePath)).toBe(true);
    expect(existsSync(state.legacyPath)).toBe(false);
  });

  it("rejects ambiguity before listening or importing", async () => {
    const state = await harness();
    await writeFile(state.legacyPath, "legacy authority");
    const listen = vi.fn(async () => undefined);

    const serveCode = await runCli(["serve", "--port", "8765"], {
      ...state.context,
      serve: listen,
    });
    expect(serveCode).toBe(1);
    expect(listen).not.toHaveBeenCalled();

    state.lines.length = 0;
    const doctorCode = await runCli(["doctor"], state.context);
    expect(doctorCode).toBe(1);
    const doctor = JSON.parse(state.lines[0] ?? "") as { quick_check: string };
    expect(doctor.quick_check).toContain(state.databasePath);
    expect(doctor.quick_check).toContain(state.legacyPath);

    state.lines.length = 0;
    const source = makeLegacyWorkspace(join(state.dataDirectory, "blocked-import"), {
      title: "Must remain untouched",
      chapters: [{ filename: "chapter-001.md", content: "# Untouched\n" }],
    });
    const before = directoryFingerprint(source);
    const importCode = await runCli(
      ["import", "--source", source, "--owner", "owner"],
      state.context,
    );

    expect(importCode).toBe(1);
    expect(directoryFingerprint(source)).toBe(before);
    expect(existsSync(state.databasePath)).toBe(false);
    expect(existsSync(join(state.dataDirectory, "backups"))).toBe(false);
  });
});
