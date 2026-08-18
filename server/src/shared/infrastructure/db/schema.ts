import { index, integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

/**
 * The first schema of the TS rewrite (#264): the sessions table with its
 * adjudicated columns (kind/token_hash/csrf_token/expires_at/last_seen_at,
 * pre-rewrite audit C2) plus the minimal jobs pair the restart-recovery
 * contract needs. The studio data model (#266) and the auth spine (#265)
 * grow through generated migrations from here.
 */
export const sessions = sqliteTable("sessions", {
  id: text("id").primaryKey(),
  kind: text("kind").notNull(),
  // owner_id gains its owners(id) foreign key when #265 lands the owners
  // table; the column itself is part of the adjudicated first schema.
  owner_id: text("owner_id"),
  token_hash: text("token_hash").notNull().unique(),
  csrf_token: text("csrf_token"),
  created_at: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  expires_at: integer("expires_at", { mode: "timestamp_ms" }),
  last_seen_at: integer("last_seen_at", { mode: "timestamp_ms" }).notNull(),
});

/**
 * Minimal durable audit row for the synchronous jobs model: jobs run inside
 * the request lifecycle, and this table records their state so a restart can
 * mark running work interrupted. Persistence columns (project, request,
 * result, retry chain) arrive with the jobs surface (#272) via migrations.
 */
export const jobs = sqliteTable(
  "jobs",
  {
    id: text("id").primaryKey(),
    kind: text("kind").notNull(),
    operation: text("operation").notNull(),
    status: text("status").notNull(),
    error: text("error"),
    created_at: integer("created_at", { mode: "timestamp_ms" }).notNull(),
    updated_at: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
    started_at: integer("started_at", { mode: "timestamp_ms" }),
    finished_at: integer("finished_at", { mode: "timestamp_ms" }),
  },
  (table) => [index("idx_jobs_status").on(table.status)],
);

export const jobEvents = sqliteTable(
  "job_events",
  {
    id: text("id").primaryKey(),
    job_id: text("job_id")
      .notNull()
      .references(() => jobs.id, { onDelete: "cascade" }),
    status: text("status").notNull(),
    details_json: text("details_json").notNull().default("{}"),
    created_at: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  },
  (table) => [index("idx_job_events_job_id").on(table.job_id)],
);
