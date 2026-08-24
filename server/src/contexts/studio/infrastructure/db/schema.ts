import { index, integer, sqliteTable, text, uniqueIndex } from "drizzle-orm/sqlite-core";

import { owners, sessions } from "../../../../shared/infrastructure/db/schema.js";

/**
 * The authoring core (#266): projects, documents, and immutable revisions —
 * the single authoring authority. Mirrors the Python gold standard
 * (infrastructure/models.py): principal scoping columns, the identity and
 * revision-number unique constraints, and cascade deletes. Pointer columns
 * (current_revision_id) stay plain text exactly like the gold standard.
 */
export const projects = sqliteTable("projects", {
  id: text("id").primaryKey(),
  ownerId: text("owner_id").references(() => owners.id, { onDelete: "cascade" }),
  guestSessionId: text("guest_session_id").references(() => sessions.id, {
    onDelete: "cascade",
  }),
  title: text("title").notNull(),
  description: text("description").notNull().default(""),
  settingsJson: text("settings_json").notNull().default("{}"),
  importHash: text("import_hash").unique(),
  createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
});

export const documents = sqliteTable(
  "documents",
  {
    id: text("id").primaryKey(),
    projectId: text("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    kind: text("kind").notNull(),
    title: text("title").notNull(),
    position: integer("position").notNull().default(0),
    currentRevisionId: text("current_revision_id"),
    createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
    updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
  },
  (table) => [
    uniqueIndex("uq_document_identity").on(table.projectId, table.kind, table.title),
    index("idx_documents_project_kind").on(table.projectId, table.kind),
  ],
);

export const documentRevisions = sqliteTable(
  "document_revisions",
  {
    id: text("id").primaryKey(),
    documentId: text("document_id")
      .notNull()
      .references(() => documents.id, { onDelete: "cascade" }),
    parentRevisionId: text("parent_revision_id"),
    revisionNumber: integer("revision_number").notNull(),
    contentMarkdown: text("content_markdown").notNull().default(""),
    metadataJson: text("metadata_json").notNull().default("{}"),
    source: text("source").notNull().default("author"),
    createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  },
  (table) => [
    uniqueIndex("uq_document_revision_number").on(table.documentId, table.revisionNumber),
    index("idx_document_revisions_document").on(table.documentId),
  ],
);

/**
 * Immutable project revision sets. A snapshot has a workflow reason so review
 * can create one now and export can later reuse only export-reason snapshots.
 */
export const projectSnapshots = sqliteTable(
  "project_snapshots",
  {
    id: text("id").primaryKey(),
    projectId: text("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    reason: text("reason").notNull(),
    createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  },
  (table) => [
    index("idx_project_snapshots_project_reason_created").on(
      table.projectId,
      table.reason,
      table.createdAt,
    ),
  ],
);

/**
 * Captures the document/revision pair and its presentation data at snapshot
 * time. Restricting both references protects the immutable revision set from
 * a document or revision deletion.
 */
export const snapshotDocuments = sqliteTable(
  "snapshot_documents",
  {
    id: text("id").primaryKey(),
    snapshotId: text("snapshot_id")
      .notNull()
      .references(() => projectSnapshots.id, { onDelete: "cascade" }),
    documentId: text("document_id")
      .notNull()
      .references(() => documents.id, { onDelete: "restrict" }),
    revisionId: text("revision_id")
      .notNull()
      .references(() => documentRevisions.id, { onDelete: "restrict" }),
    documentKind: text("document_kind").notNull(),
    documentTitle: text("document_title").notNull(),
    revisionMetadataJson: text("revision_metadata_json").notNull().default("{}"),
    position: integer("position").notNull(),
  },
  (table) => [
    uniqueIndex("uq_snapshot_document").on(table.snapshotId, table.documentId),
    index("idx_snapshot_documents_snapshot_position").on(table.snapshotId, table.position),
  ],
);

/**
 * Editorial review history is bound to a single immutable snapshot. Individual
 * findings retain both their stable snapshot-document reference and an optional
 * live-document link for later presentation.
 */
export const reviews = sqliteTable(
  "reviews",
  {
    id: text("id").primaryKey(),
    projectId: text("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    snapshotId: text("snapshot_id")
      .notNull()
      .references(() => projectSnapshots.id, { onDelete: "cascade" }),
    provider: text("provider").notNull(),
    model: text("model").notNull(),
    summary: text("summary").notNull().default(""),
    createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  },
  (table) => [
    index("idx_reviews_project_created").on(table.projectId, table.createdAt),
    index("idx_reviews_snapshot").on(table.snapshotId),
  ],
);

export const reviewIssues = sqliteTable(
  "review_issues",
  {
    id: text("id").primaryKey(),
    reviewId: text("review_id")
      .notNull()
      .references(() => reviews.id, { onDelete: "cascade" }),
    snapshotDocumentId: text("snapshot_document_id")
      .notNull()
      .references(() => snapshotDocuments.id, { onDelete: "cascade" }),
    documentId: text("document_id").references(() => documents.id, { onDelete: "set null" }),
    severity: text("severity").notNull(),
    code: text("code").notNull(),
    message: text("message").notNull(),
    suggestion: text("suggestion").notNull().default(""),
    evidenceJson: text("evidence_json").notNull().default("{}"),
  },
  (table) => [
    index("idx_review_issues_review_severity_code").on(table.reviewId, table.severity, table.code),
    index("idx_review_issues_snapshot_document").on(table.snapshotDocumentId),
  ],
);
