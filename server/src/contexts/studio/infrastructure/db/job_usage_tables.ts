import { isNotNull, sql } from "drizzle-orm";
import {
  check,
  index,
  integer,
  real,
  sqliteTable,
  text,
  uniqueIndex,
} from "drizzle-orm/sqlite-core";

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
    retry_idempotency_key: text("retry_idempotency_key"),
    created_at: integer("created_at", { mode: "timestamp_ms" }).notNull(),
    updated_at: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
    started_at: integer("started_at", { mode: "timestamp_ms" }),
    finished_at: integer("finished_at", { mode: "timestamp_ms" }),
  },
  (table) => [
    index("idx_jobs_status").on(table.status),
    index("idx_jobs_project_created_id").on(table.project_id, table.created_at, table.id),
    uniqueIndex("uq_jobs_retry_idempotency")
      .on(table.project_id, table.retry_of_job_id, table.retry_idempotency_key)
      .where(isNotNull(table.retry_idempotency_key)),
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
  (table) => [
    index("idx_usage_events_project_id").on(table.project_id),
    check(
      "ck_usage_events_prompt_tokens_safe",
      sql`typeof(${table.prompt_tokens}) = 'integer' AND ${table.prompt_tokens} BETWEEN 0 AND 9007199254740991`,
    ),
    check(
      "ck_usage_events_completion_tokens_safe",
      sql`typeof(${table.completion_tokens}) = 'integer' AND ${table.completion_tokens} BETWEEN 0 AND 9007199254740991`,
    ),
  ],
);
