import { generateSQLiteDrizzleJson, generateSQLiteMigration } from "drizzle-kit/api";
import { beforeAll, describe, expect, it } from "vitest";

import * as schema from "../../src/platform/db/schema/index.js";

/**
 * The platform schema has no consumers yet, so nothing else in the suite would
 * notice a dropped cascade, a lost composite key, or a renamed column. This
 * test pins the SQL the schema actually produces — the same DDL the future
 * migration will run — instead of the TypeScript declarations that describe it.
 */

const DEFAULTS = {
  schemaVersion: "schema_version",
  ftsTokenizerVersion: "fts_tokenizer_version",
  dataEpoch: "data_epoch",
};

let statements: string[] = [];
const tables = new Map<string, string>();

function normalized(statement: string): string {
  return statement.replace(/\s+/g, " ").trim();
}

function table(name: string): string {
  const statement = tables.get(name);
  if (statement === undefined) throw new Error(`schema declares no table ${name}`);
  return statement;
}

beforeAll(async () => {
  const empty = await generateSQLiteDrizzleJson({});
  const current = await generateSQLiteDrizzleJson(schema as unknown as Record<string, unknown>);
  statements = (await generateSQLiteMigration(empty, current)).map(normalized);
  for (const statement of statements) {
    const created = /^CREATE TABLE `([^`]+)`/.exec(statement);
    const tableName = created?.[1];
    if (tableName !== undefined) tables.set(tableName, statement);
  }
});

describe("platform schema DDL", () => {
  it("creates every table the rebuild defines", () => {
    expect([...tables.keys()].sort()).toEqual([
      "app_meta",
      "documents",
      "exports",
      "generation_events",
      "generation_runs",
      "lore_aliases",
      "lore_profiles",
      "owners",
      "projects",
      "review_issues",
      "reviews",
      "revisions",
      "sessions",
      "setup_tokens",
      "snapshot_items",
      "snapshots",
      "usage_events",
      "volumes",
    ]);
  });

  it("mounts a foreign key on every cross-table reference", () => {
    const foreignKeys = statements.join("\n").match(/FOREIGN KEY/g) ?? [];
    // 24 cross-table references are declared across the platform schema.
    expect(foreignKeys.length).toBe(24);
  });

  it("cascades project deletion through the content children", () => {
    for (const name of ["volumes", "documents", "revisions", "snapshots"]) {
      expect(table(name)).toMatch(/ON DELETE cascade/);
    }
    expect(table("documents")).toContain(
      "FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE cascade",
    );
    // A chapter outside any volume is legal; deleting the volume only detaches it.
    expect(table("documents")).toContain(
      "FOREIGN KEY (`volume_id`) REFERENCES `volumes`(`id`) ON UPDATE no action ON DELETE set null",
    );
  });

  it("never lets a snapshot or export delete the revision it captured", () => {
    expect(table("snapshot_items")).toContain(
      "FOREIGN KEY (`revision_id`) REFERENCES `revisions`(`id`) ON UPDATE no action ON DELETE restrict",
    );
    expect(table("exports")).toContain(
      "FOREIGN KEY (`snapshot_id`) REFERENCES `snapshots`(`id`) ON UPDATE no action ON DELETE restrict",
    );
  });

  it("detaches a usage event instead of deleting it with its run", () => {
    expect(table("usage_events")).toContain(
      "FOREIGN KEY (`run_id`) REFERENCES `generation_runs`(`id`) ON UPDATE no action ON DELETE set null",
    );
    expect(table("usage_events")).toMatch(/`run_id` text,/);
  });

  it("leaves the circular document/revision pointer without a foreign key", () => {
    // Enforced by the single write path; SQLite cannot express the cycle.
    expect(table("documents")).toContain("`current_revision_id` text,");
    expect(table("documents")).not.toContain("`current_revision_id`) REFERENCES");
  });

  it("keeps the composite primary keys where the identity is a pair", () => {
    expect(table("lore_aliases")).toContain("PRIMARY KEY(`project_id`, `normalized_alias`)");
    expect(table("snapshot_items")).toContain("PRIMARY KEY(`snapshot_id`, `document_id`)");
  });

  it("keeps the partial-repository defaults the insert paths rely on", () => {
    expect(table("revisions")).toContain("`content_markdown` text DEFAULT '' NOT NULL");
    expect(table("generation_runs")).toContain("`input_json` text DEFAULT '{}' NOT NULL");
    expect(table("generation_events")).toContain("`payload_json` text DEFAULT '{}' NOT NULL");
    expect(table("exports")).toContain("`state` text DEFAULT 'staging' NOT NULL");
    expect(table("projects")).toContain("`settings_version` integer DEFAULT 1 NOT NULL");
    expect(table("lore_profiles")).toContain("`status` text DEFAULT 'draft' NOT NULL");
  });

  it("does not put an owner column on the content children", () => {
    for (const name of ["volumes", "documents", "revisions"]) {
      expect(table(name)).not.toContain("`owner_id`");
    }
    expect(table("projects")).toContain("`owner_id` text NOT NULL");
  });
});

describe("platform schema indexes", () => {
  it("declares the uniqueness each write path depends on", () => {
    expect(statements).toContain(
      "CREATE UNIQUE INDEX `owners_username_unique` ON `owners` (`username`);",
    );
    expect(statements).toContain(
      "CREATE UNIQUE INDEX `sessions_token_hash_unique` ON `sessions` (`token_hash`);",
    );
    expect(statements).toContain(
      "CREATE UNIQUE INDEX `setup_tokens_token_hash_unique` ON `setup_tokens` (`token_hash`);",
    );
    for (const index of [
      "uq_projects_import",
      "uq_volumes_title",
      "uq_documents_identity",
      "uq_revisions_number",
      "uq_runs_request",
      "uq_events_sequence",
    ]) {
      expect(
        statements.some((statement) => statement.startsWith(`CREATE UNIQUE INDEX \`${index}\``)),
      ).toBe(true);
    }
  });

  it("keeps the keyset-pagination indexes the list queries walk", () => {
    expect(statements).toContain(
      "CREATE INDEX `idx_projects_catalog` ON `projects` (`owner_id`,`updated_at`,`id`);",
    );
    expect(statements).toContain(
      "CREATE INDEX `idx_documents_order` ON `documents` (`project_id`,`position`,`id`);",
    );
    expect(statements).toContain(
      "CREATE INDEX `idx_revisions_history` ON `revisions` (`document_id`,`revision_number`);",
    );
    expect(statements).toContain(
      "CREATE INDEX `idx_exports_recency` ON `exports` (`project_id`,`created_at`,`id`);",
    );
  });
});

describe("installation metadata", () => {
  it("keeps the tokenizer version in app_meta", () => {
    expect(schema.APP_META_KEYS).toEqual(DEFAULTS);
    expect(table("app_meta")).toContain("`key` text PRIMARY KEY NOT NULL");
  });
});
