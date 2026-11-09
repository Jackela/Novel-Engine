/**
 * Generation tables: lore state, durable runs, snapshots, and reviews.
 *
 * `generation_runs` replaces the old jobs/job_events naming but keeps their
 * purpose: a run is the idempotency anchor (one request key, one run, one usage
 * charge) and the audit trail for a failure. The author never browses runs; the
 * table exists so a retried request cannot be billed twice.
 */

import { index, integer, primaryKey, sqliteTable, text, uniqueIndex } from "drizzle-orm/sqlite-core";

import { projects } from "./library.js";
import { documents, revisions } from "./manuscript.js";

export const loreProfiles = sqliteTable("lore_profiles", {
  documentId: text("document_id")
    .primaryKey()
    .references(() => documents.id, { onDelete: "cascade" }),
  /** draft | stable | deprecated. Only `stable` participates in injection. */
  status: text("status").notNull().default("draft"),
  updatedAt: integer("updated_at").notNull(),
});

export const loreAliases = sqliteTable(
  "lore_aliases",
  {
    projectId: text("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    documentId: text("document_id")
      .notNull()
      .references(() => documents.id, { onDelete: "cascade" }),
    /** Case-folded alias; the unique key that keeps triggers unambiguous. */
    normalizedAlias: text("normalized_alias").notNull(),
    /** What the author typed, rendered back in the UI. */
    displayAlias: text("display_alias").notNull(),
  },
  (table) => [
    // One alias resolves to exactly one entry within a project.
    primaryKey({ columns: [table.projectId, table.normalizedAlias] }),
    index("idx_lore_aliases_document").on(table.documentId),
  ],
);

export const generationRuns = sqliteTable(
  "generation_runs",
  {
    id: text("id").primaryKey(),
    projectId: text("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    /** Null for whole-book runs, which target every chapter in order. */
    documentId: text("document_id").references(() => documents.id, { onDelete: "set null" }),
    /** proposal | review | whole-book. */
    kind: text("kind").notNull(),
    /** queued | running | succeeded | failed | stopped. */
    status: text("status").notNull(),
    /**
     * Client-supplied idempotency key. A duplicate submission replays the
     * persisted terminal run instead of creating a second one.
     */
    requestKey: text("request_key"),
    provider: text("provider"),
    model: text("model"),
    inputJson: text("input_json").notNull().default("{}"),
    /** Partial output is preserved on failure so the author keeps what arrived. */
    outputJson: text("output_json"),
    errorCode: text("error_code"),
    errorMessage: text("error_message"),
    /**
     * Failure diagnostics: the failing stage plus a truncated copy of the raw
     * provider output (head and tail, 2 KB each).
     *
     * Written only on failure — on success the output is already the artifact,
     * so a second copy would just double the manuscript on disk. Never returned
     * by a public endpoint: the raw text can echo the prompt, which carries the
     * author's own prose. It is readable through the CLI so a support
     * conversation has material without turning the manuscript into an API
     * surface.
     */
    diagnosticsJson: text("diagnostics_json"),
    startedAt: integer("started_at").notNull(),
    finishedAt: integer("finished_at"),
  },
  (table) => [
    uniqueIndex("uq_runs_request").on(table.projectId, table.requestKey),
    index("idx_runs_recency").on(table.projectId, table.startedAt),
  ],
);

export const generationEvents = sqliteTable(
  "generation_events",
  {
    id: text("id").primaryKey(),
    runId: text("run_id")
      .notNull()
      .references(() => generationRuns.id, { onDelete: "cascade" }),
    /** Monotonic within one run; the ordering the resume path replays. */
    sequence: integer("sequence").notNull(),
    type: text("type").notNull(),
    payloadJson: text("payload_json").notNull().default("{}"),
    createdAt: integer("created_at").notNull(),
  },
  (table) => [uniqueIndex("uq_events_sequence").on(table.runId, table.sequence)],
);

export const snapshots = sqliteTable(
  "snapshots",
  {
    id: text("id").primaryKey(),
    projectId: text("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    /** review | export. Records why the snapshot exists, not who reads it. */
    reason: text("reason").notNull(),
    /** Author-facing name: "the version I sent my editor". */
    label: text("label"),
    /** Digest over the ordered revision set; proves two runs saw the same text. */
    contentHash: text("content_hash").notNull(),
    documentCount: integer("document_count").notNull(),
    wordCount: integer("word_count").notNull(),
    createdAt: integer("created_at").notNull(),
  },
  (table) => [index("idx_snapshots_recency").on(table.projectId, table.createdAt)],
);

export const snapshotItems = sqliteTable(
  "snapshot_items",
  {
    snapshotId: text("snapshot_id")
      .notNull()
      .references(() => snapshots.id, { onDelete: "cascade" }),
    documentId: text("document_id")
      .notNull()
      .references(() => documents.id, { onDelete: "cascade" }),
    /**
     * RESTRICT, not CASCADE: a revision captured by a snapshot can never be
     * deleted, which is what makes an export reproducible months later.
     */
    revisionId: text("revision_id")
      .notNull()
      .references(() => revisions.id, { onDelete: "restrict" }),
    kind: text("kind").notNull(),
    title: text("title").notNull(),
    position: integer("position").notNull(),
    wordCount: integer("word_count").notNull(),
  },
  (table) => [primaryKey({ columns: [table.snapshotId, table.documentId] })],
);

export const reviews = sqliteTable(
  "reviews",
  {
    id: text("id").primaryKey(),
    projectId: text("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    snapshotId: text("snapshot_id")
      .notNull()
      .references(() => snapshots.id, { onDelete: "cascade" }),
    provider: text("provider").notNull(),
    model: text("model"),
    summary: text("summary").notNull().default(""),
    createdAt: integer("created_at").notNull(),
  },
  (table) => [index("idx_reviews_recency").on(table.projectId, table.createdAt)],
);

export const reviewIssues = sqliteTable(
  "review_issues",
  {
    id: text("id").primaryKey(),
    reviewId: text("review_id")
      .notNull()
      .references(() => reviews.id, { onDelete: "cascade" }),
    documentId: text("document_id")
      .notNull()
      .references(() => documents.id, { onDelete: "cascade" }),
    /** blocker | warning. Closed set; the UI groups by it. */
    severity: text("severity").notNull(),
    code: text("code").notNull(),
    message: text("message").notNull(),
    suggestion: text("suggestion"),
    evidenceJson: text("evidence_json").notNull().default("{}"),
  },
  (table) => [index("idx_issues_review").on(table.reviewId, table.severity)],
);
