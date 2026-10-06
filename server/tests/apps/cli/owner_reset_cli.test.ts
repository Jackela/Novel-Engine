import { mkdir, mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { buildApp } from "../../../src/apps/api/app.js";
import { runCli } from "../../../src/apps/cli/main.js";
import { owners, sessions } from "../../../src/shared/infrastructure/db/schema.js";
import { openStudioDatabase } from "../../../src/shared/infrastructure/db/startup.js";
import {
  OWNER_PASSWORD,
  OWNER_USERNAME,
  setupOwner,
  TEST_SESSION_SECRET,
} from "../../api/auth_helpers.js";

interface CliHarness {
  dataDirectory: string;
  databasePath: string;
  lines: string[];
  context: Parameters<typeof runCli>[1];
}

async function cliHarness(): Promise<CliHarness> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-owner-reset-"));
  const dataDirectory = join(directory, "data");
  await mkdir(dataDirectory, { recursive: true });
  const databasePath = join(dataDirectory, "novel-engine.sqlite3");
  const lines: string[] = [];
  return {
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

/** One owner with one live session: the credential state a reset must invalidate. */
async function seedOwnerAndSession(harness: CliHarness): Promise<void> {
  const studio = await openStudioDatabase(harness.databasePath);
  try {
    const now = new Date("2026-10-01T00:00:00.000Z");
    studio.db
      .insert(owners)
      .values({ id: "owner-seeded", username: "author", password_hash: "seeded", created_at: now })
      .run();
    studio.db
      .insert(sessions)
      .values({
        id: "session-seeded",
        kind: "owner",
        owner_id: "owner-seeded",
        token_hash: "token-hash-seeded",
        csrf_token: "csrf-seeded",
        created_at: now,
        expires_at: new Date(now.getTime() + 86_400_000),
        last_seen_at: now,
      })
      .run();
  } finally {
    studio.close();
  }
}

describe("owner reset CLI", () => {
  it("deletes the seeded owner and its sessions, prints a summary, and frees setup", async () => {
    const harness = await cliHarness();
    await seedOwnerAndSession(harness);

    expect(await runCli(["owner", "reset"], harness.context)).toBe(0);
    expect(JSON.parse(harness.lines[0] ?? "")).toEqual({
      owners_deleted: 1,
      sessions_deleted: 1,
      username: "author",
    });

    const studio = await openStudioDatabase(harness.databasePath);
    try {
      expect(studio.db.select().from(owners).all()).toHaveLength(0);
      expect(studio.db.select().from(sessions).all()).toHaveLength(0);
    } finally {
      studio.close();
    }

    const app = await buildApp({
      logger: false,
      databasePath: harness.databasePath,
      sessionSecret: TEST_SESSION_SECRET,
    });
    try {
      expect((await setupOwner(app, OWNER_USERNAME, OWNER_PASSWORD)).statusCode).toBe(201);
    } finally {
      await app.close();
    }
  });

  it("reports zero deletions when no owner is configured", async () => {
    const harness = await cliHarness();

    expect(await runCli(["owner", "reset"], harness.context)).toBe(0);
    expect(JSON.parse(harness.lines[0] ?? "")).toEqual({
      owners_deleted: 0,
      sessions_deleted: 0,
      username: null,
    });
  });

  it("refuses while another process owns the data directory", async () => {
    const harness = await cliHarness();
    await seedOwnerAndSession(harness);
    const active = await openStudioDatabase(harness.databasePath);
    try {
      expect(await runCli(["owner", "reset"], harness.context)).toBe(1);
      expect(harness.lines.join("\n")).toMatch(/already owned by another Novel Engine process/i);
    } finally {
      active.close();
    }

    harness.lines.length = 0;
    expect(await runCli(["owner", "reset"], harness.context)).toBe(0);
    expect(JSON.parse(harness.lines[0] ?? "").owners_deleted).toBe(1);
  });

  it("refuses an unknown subcommand and lists owner reset in the usage", async () => {
    const harness = await cliHarness();

    expect(await runCli(["owner", "teleport"], harness.context)).toBe(2);
    expect(harness.lines.join("\n")).toContain("owner reset");

    harness.lines.length = 0;
    expect(await runCli(["teleport"], harness.context)).toBe(2);
    expect(harness.lines.join("\n")).toContain("owner reset");
  });
});
