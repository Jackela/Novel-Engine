import { cpSync, readFileSync, writeFileSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import Database from "better-sqlite3";
import { drizzle } from "drizzle-orm/better-sqlite3";
import { migrate } from "drizzle-orm/better-sqlite3/migrator";
import { afterEach, describe, expect, it } from "vitest";

import { openReconciledStudioDatabase } from "../../src/contexts/studio/infrastructure/reconciled_studio_database.js";
import {
  REVISION_WORD_COUNT_BATCH_SIZE,
  reconcileRevisionWordCounts,
} from "../../src/contexts/studio/infrastructure/revision_word_count_reconciliation.js";
import { openStudioDatabase } from "../../src/shared/infrastructure/db/startup.js";

const directories: string[] = [];

interface Journal {
  entries: Array<{ idx: number }>;
}

async function migrationsBeforeWordCount(): Promise<string> {
  const destination = await mkdtemp(join(tmpdir(), "novel-engine-before-revision-count-"));
  directories.push(destination);
  cpSync(join(process.cwd(), "drizzle"), destination, { recursive: true });
  const journalPath = join(destination, "meta", "_journal.json");
  const journal = JSON.parse(readFileSync(journalPath, "utf8")) as Journal;
  writeFileSync(
    journalPath,
    JSON.stringify({ entries: journal.entries.filter((entry) => entry.idx <= 18) }, null, 2),
    "utf8",
  );
  return destination;
}

afterEach(async () => {
  await Promise.all(
    directories.splice(0).map((directory) => rm(directory, { recursive: true, force: true })),
  );
});

async function openLegacyRows(count: number) {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-revision-count-"));
  directories.push(directory);
  const databasePath = join(directory, "novel-engine.sqlite3");
  const studio = await openStudioDatabase(databasePath);
  const now = Date.parse("2026-09-03T00:00:00.000Z");
  studio.raw
    .prepare("INSERT INTO owners (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)")
    .run("owner-1", "owner", "hash", now);
  studio.raw
    .prepare(
      "INSERT INTO projects (id, owner_id, title, description, settings_json, created_at, updated_at) " +
        "VALUES (?, ?, ?, '', '{}', ?, ?)",
    )
    .run("project-1", "owner-1", "Project", now, now);
  studio.raw
    .prepare(
      "INSERT INTO volumes (id, project_id, title, position, created_at, updated_at) " +
        "VALUES (?, ?, ?, 1, ?, ?)",
    )
    .run("volume-1", "project-1", "Volume", now, now);
  studio.raw
    .prepare(
      "INSERT INTO documents (id, project_id, kind, title, position, volume_id, " +
        "current_revision_id, created_at, updated_at) VALUES (?, ?, 'chapter', ?, 1, ?, ?, ?, ?)",
    )
    .run("document-1", "project-1", "Chapter", "volume-1", "legacy-0000", now, now);
  const insert = studio.raw.prepare(
    "INSERT INTO document_revisions (id, document_id, parent_revision_id, revision_number, " +
      "content_markdown, metadata_json, source, word_count, created_at) " +
      "VALUES (?, 'document-1', NULL, ?, ?, '{}', 'author', NULL, ?)",
  );
  studio.raw.transaction(() => {
    for (let index = 0; index < count; index += 1) {
      insert.run(`legacy-${String(index).padStart(4, "0")}`, index + 1, "你好 world", now + index);
    }
  })();
  return { databasePath, directory, studio };
}

describe("revision word-count reconciliation", () => {
  it("migrates an earlier revision unchanged and fills its exact count before open", async () => {
    const directory = await mkdtemp(join(tmpdir(), "novel-engine-revision-count-upgrade-"));
    directories.push(directory);
    const databasePath = join(directory, "novel-engine.sqlite3");
    const legacy = new Database(databasePath);
    migrate(drizzle(legacy), { migrationsFolder: await migrationsBeforeWordCount() });
    legacy.exec(`
      INSERT INTO owners (id, username, password_hash, created_at)
      VALUES ('owner-1', 'owner', 'hash', 1);
      INSERT INTO projects (id, owner_id, title, description, settings_json, created_at, updated_at)
      VALUES ('project-1', 'owner-1', 'Project', '', '{}', 1, 1);
      INSERT INTO volumes (id, project_id, title, position, created_at, updated_at)
      VALUES ('volume-1', 'project-1', 'Volume', 1, 1, 1);
      INSERT INTO documents
        (id, project_id, kind, title, position, volume_id, current_revision_id, created_at, updated_at)
      VALUES ('document-1', 'project-1', 'chapter', 'Chapter', 1, 'volume-1', 'revision-1', 1, 1);
      INSERT INTO document_revisions
        (id, document_id, parent_revision_id, revision_number, content_markdown,
         metadata_json, source, created_at)
      VALUES ('revision-1', 'document-1', NULL, 1, '你好 world', '{"kept":true}', 'import', 1);
    `);
    legacy.close();

    const upgraded = await openReconciledStudioDatabase(databasePath);
    try {
      expect(
        upgraded.raw
          .prepare(
            "SELECT id, document_id, parent_revision_id, revision_number, content_markdown, " +
              "metadata_json, source, word_count, created_at FROM document_revisions",
          )
          .get(),
      ).toEqual({
        id: "revision-1",
        document_id: "document-1",
        parent_revision_id: null,
        revision_number: 1,
        content_markdown: "你好 world",
        metadata_json: '{"kept":true}',
        source: "import",
        word_count: 2,
        created_at: 1,
      });
    } finally {
      upgraded.close();
    }
  });

  it("commits bounded batches and resumes only remaining null rows", async () => {
    const harness = await openLegacyRows(REVISION_WORD_COUNT_BATCH_SIZE + 1);
    try {
      expect(() =>
        reconcileRevisionWordCounts(harness.studio.db, {
          afterBatchCommitted: (completed) => {
            expect(completed).toBe(REVISION_WORD_COUNT_BATCH_SIZE);
            throw new Error("simulated interruption");
          },
        }),
      ).toThrow("simulated interruption");
      expect(
        harness.studio.raw
          .prepare("SELECT COUNT(*) AS count FROM document_revisions WHERE word_count IS NULL")
          .get(),
      ).toEqual({ count: 1 });

      expect(reconcileRevisionWordCounts(harness.studio.db)).toBe(1);
      expect(reconcileRevisionWordCounts(harness.studio.db)).toBe(0);
      expect(
        harness.studio.raw
          .prepare("SELECT DISTINCT word_count AS count FROM document_revisions")
          .all(),
      ).toEqual([{ count: 2 }]);
    } finally {
      harness.studio.close();
    }
  });

  it("processes 513 rows in committed batches no larger than 256", async () => {
    const harness = await openLegacyRows(REVISION_WORD_COUNT_BATCH_SIZE * 2 + 1);
    try {
      const checkpoints: number[] = [];
      expect(
        reconcileRevisionWordCounts(harness.studio.db, {
          afterBatchCommitted: (completed) => checkpoints.push(completed),
        }),
      ).toBe(REVISION_WORD_COUNT_BATCH_SIZE * 2 + 1);
      expect(checkpoints).toEqual([256, 512, 513]);
    } finally {
      harness.studio.close();
    }
  });

  it("fails production startup before export reconciliation and job recovery", async () => {
    const harness = await openLegacyRows(1);
    harness.studio.raw
      .prepare(
        "INSERT INTO jobs (id, project_id, kind, operation, status, provider, model, " +
          "request_json, result_json, created_at, updated_at) " +
          "VALUES ('running-1', 'project-1', 'proposal', 'continue', 'running', 'mock', '', '{}', '{}', 1, 1)",
      )
      .run();
    harness.studio.raw.exec(
      "CREATE TRIGGER fail_revision_count BEFORE UPDATE OF word_count ON document_revisions " +
        "BEGIN SELECT RAISE(FAIL, 'simulated count failure'); END",
    );
    harness.studio.close();
    let exportReconciled = false;

    await expect(
      openReconciledStudioDatabase(harness.databasePath, {
        onReconciled: () => {
          exportReconciled = true;
        },
      }),
    ).rejects.toThrow("simulated count failure");
    expect(exportReconciled).toBe(false);

    const raw = new Database(harness.databasePath, { readonly: true });
    try {
      expect(raw.prepare("SELECT status FROM jobs WHERE id = 'running-1'").get()).toEqual({
        status: "running",
      });
      expect(
        raw.prepare("SELECT word_count FROM document_revisions WHERE id = 'legacy-0000'").get(),
      ).toEqual({ word_count: null });
    } finally {
      raw.close();
    }
  });
});
