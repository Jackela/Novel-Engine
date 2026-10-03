import { existsSync, readFileSync } from "node:fs";
import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { runCli } from "../../../src/apps/cli/main.js";
import { buildFtsMatchQuery } from "../../../src/contexts/studio/application/fts_match_query.js";
import {
  documentRevisions,
  documents,
  projects,
} from "../../../src/contexts/studio/infrastructure/db/schema.js";
import { owners } from "../../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../../src/shared/infrastructure/db/startup.js";

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

/**
 * Two documents with current revisions, one orphan index row, and no index
 * rows for the real documents: the drifted database `doctor` must expose and
 * `reindex` must reconcile (2 indexable documents vs 1 stray row).
 */
async function seedIndexDrift(harness: CliHarness): Promise<void> {
  const studio = await openStudioDatabase(harness.databasePath);
  const now = new Date("2026-08-31T18:00:00.000Z");
  try {
    const { db, raw } = studio;
    db.insert(owners)
      .values([{ id: "owner-index", username: "owner", password_hash: "x", created_at: now }])
      .run();
    db.insert(projects)
      .values([
        {
          id: "project-index",
          ownerId: "owner-index",
          title: "Drift",
          description: "",
          settingsJson: "{}",
          importHash: null,
          createdAt: now,
          updatedAt: now,
        },
      ])
      .run();
    db.insert(documents)
      .values([
        {
          id: "doc-dai",
          projectId: "project-index",
          kind: "chapter",
          title: "初见",
          position: 0,
          currentRevisionId: "rev-dai",
          createdAt: now,
          updatedAt: now,
        },
        {
          id: "doc-flower",
          projectId: "project-index",
          kind: "note",
          title: "葬花吟",
          position: 1,
          currentRevisionId: "rev-flower",
          createdAt: now,
          updatedAt: now,
        },
      ])
      .run();
    db.insert(documentRevisions)
      .values([
        {
          id: "rev-dai",
          documentId: "doc-dai",
          revisionNumber: 1,
          contentMarkdown: "林黛玉初进贾府，宝玉迎接。",
          createdAt: now,
        },
        {
          id: "rev-flower",
          documentId: "doc-flower",
          revisionNumber: 1,
          contentMarkdown: "花谢花飞花满天。",
          createdAt: now,
        },
      ])
      .run();
    raw
      .prepare(
        "INSERT INTO document_search(document_id, project_id, title, content) VALUES (?, ?, ?, ?)",
      )
      .run("doc-ghost", "project-index", "Ghost", "ghosttoken stranded");
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
      document_index: { documents: 0, indexed: 0, drifted: false },
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
    expect(payload.document_index).toBeNull();
  });

  it("serves a fully migrated database without writing a backup on restart", async () => {
    const harness = await cliHarness();
    await seedDatabase(harness);
    const events: string[] = [];
    let backupsAtListen = -1;
    const context = {
      ...harness.context,
      serve: {
        owner: "runner-owned" as const,
        run: async (app: { close(): Promise<void> }, host: string, port: number) => {
          events.push(`listen:${host}:${port}`);
          const backups = join(harness.dataDirectory, "backups");
          backupsAtListen = existsSync(backups)
            ? (await (await import("node:fs/promises")).readdir(backups)).length
            : 0;
          await app.close();
        },
      },
    };

    const code = await runCli(["serve", "--host", "127.0.0.1", "--port", "8765"], context);

    expect(code).toBe(0);
    expect(events).toEqual(["listen:127.0.0.1:8765"]);
    expect(backupsAtListen).toBe(0);
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

  it("reconciles a drifted index through doctor and rebuilds it idempotently", async () => {
    const harness = await cliHarness();
    await seedIndexDrift(harness);

    expect(await runCli(["doctor"], harness.context)).toBe(0);
    const drift = JSON.parse(harness.lines[0] ?? "") as { document_index: unknown };
    expect(drift.document_index).toEqual({ documents: 2, indexed: 1, drifted: true });

    for (let run = 0; run < 2; run += 1) {
      harness.lines.length = 0;
      expect(await runCli(["reindex"], harness.context)).toBe(0);
      expect(JSON.parse(harness.lines[0] ?? "")).toEqual({ documents: 2, indexed: 2 });
    }

    const studio = await openStudioDatabase(harness.databasePath);
    try {
      const match = studio.raw.prepare(
        "SELECT document_id FROM document_search WHERE document_search MATCH ?",
      );
      const matchIds = (term: string): string[] =>
        (match.all(buildFtsMatchQuery(term) ?? "") as Array<{ document_id: string }>).map(
          (row) => row.document_id,
        );
      expect(matchIds("黛玉")).toEqual(["doc-dai"]);
      expect(matchIds("葬花")).toEqual(["doc-flower"]);
      expect(matchIds("ghosttoken")).toEqual([]);
    } finally {
      studio.close();
    }
  });
});
