/**
 * Delivery tables: export artifacts and the usage ledger.
 *
 * `exports.state` is a two-value machine (`staging` → `ready`) rather than the
 * old multi-stage publication journal. The journal existed because a crashed
 * export could leave a half-written file plus a record claiming success; one
 * state column plus a checksum makes the same guarantee readable.
 */

import { index, integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

import { projects } from "./library.js";
import { generationRuns, snapshots } from "./generation.js";

export const exports = sqliteTable(
  "exports",
  {
    id: text("id").primaryKey(),
    projectId: text("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    /** Every export is bound to a snapshot; editing afterwards cannot change it. */
    snapshotId: text("snapshot_id")
      .notNull()
      .references(() => snapshots.id, { onDelete: "restrict" }),
    /** markdown | docx | epub. */
    format: text("format").notNull(),
    /** Relative to the data directory; never an absolute path. */
    relativePath: text("relative_path").notNull(),
    sizeBytes: integer("size_bytes").notNull(),
    /** SHA-256 of the written bytes; the download path re-checks it. */
    checksumSha256: text("checksum_sha256").notNull(),
    /** staging | ready. A row is only listed once its file is complete. */
    state: text("state").notNull().default("staging"),
    createdAt: integer("created_at").notNull(),
  },
  (table) => [index("idx_exports_recency").on(table.projectId, table.createdAt, table.id)],
);

export const usageEvents = sqliteTable(
  "usage_events",
  {
    id: text("id").primaryKey(),
    projectId: text("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    /** Null when the provider replied outside a recorded run (health checks). */
    runId: text("run_id").references(() => generationRuns.id, { onDelete: "set null" }),
    provider: text("provider").notNull(),
    model: text("model"),
    promptTokens: integer("prompt_tokens"),
    completionTokens: integer("completion_tokens"),
    /**
     * provider | estimated | unreported — where the token counts came from.
     * Failed attempts stay in the ledger so a retry is visible, not inferred.
     */
    provenance: text("provenance").notNull(),
    recordedAt: integer("recorded_at").notNull(),
  },
  (table) => [index("idx_usage_window").on(table.projectId, table.recordedAt)],
);
