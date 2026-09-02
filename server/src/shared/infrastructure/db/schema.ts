import { index, integer, real, sqliteTable, text, uniqueIndex } from "drizzle-orm/sqlite-core";

/**
 * The first schema of the TS rewrite (#264): the sessions table with its
 * adjudicated columns (kind/token_hash/csrf_token/expires_at/last_seen_at,
 * pre-rewrite audit C2) plus the minimal jobs pair the restart-recovery
 * contract needs. The studio data model (#266) and the auth spine (#265)
 * grow through generated migrations from here.
 */
/**
 * The auth spine (#265): the owners table mirrors the Python gold standard
 * (models.py Owner) — one owner per store, unique username, bcrypt hash —
 * and sessions.owner_id gains its adjudicated owners(id) foreign key with
 * cascade delete.
 */
export const owners = sqliteTable("owners", {
  id: text("id").primaryKey(),
  username: text("username").notNull().unique(),
  password_hash: text("password_hash").notNull(),
  created_at: integer("created_at", { mode: "timestamp_ms" }).notNull(),
});

export const sessions = sqliteTable("sessions", {
  id: text("id").primaryKey(),
  kind: text("kind").notNull(),
  owner_id: text("owner_id").references(() => owners.id, { onDelete: "cascade" }),
  token_hash: text("token_hash").notNull().unique(),
  csrf_token: text("csrf_token"),
  created_at: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  expires_at: integer("expires_at", { mode: "timestamp_ms" }),
  last_seen_at: integer("last_seen_at", { mode: "timestamp_ms" }).notNull(),
});

/**
 * Durable audit rows for the synchronous jobs model: jobs run inside the
 * request lifecycle, and these tables record their state so a restart can
 * mark running work interrupted. The proposal workflow (#268) grew the
 * persistence columns (project/document scoping, provider, request/result
 * payloads, retry chain); project linkage is a plain column — the studio
 * tables live in their own schema file, so cascade deletes are enforced by
 * the studio store's dropProject transaction, not by a cross-schema FK.
 */
export const jobs = sqliteTable(
  "jobs",
  {
    id: text("id").primaryKey(),
    project_id: text("project_id").notNull().default(""),
    document_id: text("document_id"),
    kind: text("kind").notNull(),
    operation: text("operation").notNull(),
    status: text("status").notNull(),
    provider: text("provider").notNull().default("mock"),
    model: text("model").notNull().default(""),
    request_json: text("request_json").notNull().default("{}"),
    result_json: text("result_json").notNull().default("{}"),
    error: text("error"),
    retry_of_job_id: text("retry_of_job_id"),
    created_at: integer("created_at", { mode: "timestamp_ms" }).notNull(),
    updated_at: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
    started_at: integer("started_at", { mode: "timestamp_ms" }),
    finished_at: integer("finished_at", { mode: "timestamp_ms" }),
  },
  (table) => [
    index("idx_jobs_status").on(table.status),
    index("idx_jobs_project_id").on(table.project_id),
  ],
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
    sequence: integer("sequence").notNull().default(1),
    created_at: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  },
  (table) => [uniqueIndex("uq_job_events_job_sequence").on(table.job_id, table.sequence)],
);

/**
 * Usage accounting for AI requests (#268): one row per completed generation,
 * with provider-reported token counts or the shared word-count fallback.
 */
export const usageEvents = sqliteTable(
  "usage_events",
  {
    id: text("id").primaryKey(),
    project_id: text("project_id").notNull().default(""),
    job_id: text("job_id").references(() => jobs.id, { onDelete: "set null" }),
    provider: text("provider").notNull(),
    model: text("model").notNull(),
    prompt_tokens: integer("prompt_tokens").notNull().default(0),
    completion_tokens: integer("completion_tokens").notNull().default(0),
    request_evidence_json: text("request_evidence_json").notNull().default("{}"),
    estimated_cost: real("estimated_cost"),
    created_at: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  },
  (table) => [index("idx_usage_events_project_id").on(table.project_id)],
);
