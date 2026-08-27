import { index, integer, sqliteTable, text, uniqueIndex } from "drizzle-orm/sqlite-core";

import { owners } from "../../../../shared/infrastructure/db/schema.js";

/**
 * The authoring core (#266): projects, documents, and immutable revisions —
 * the single authoring authority. Mirrors the Python gold standard
 * (infrastructure/models.py): the identity and revision-number unique
 * constraints, and cascade deletes. Pointer columns (current_revision_id)
 * stay plain text exactly like the gold standard.
 *
 * Import idempotency is per owner scope (#273): at most one row per
 * (owner_id, import_hash). The guest scoping column and its unique index
 * were removed with the guest principal (#311).
 */
export const projects = sqliteTable(
  "projects",
  {
    id: text("id").primaryKey(),
    ownerId: text("owner_id")
      .notNull()
      .references(() => owners.id, { onDelete: "cascade" }),
    title: text("title").notNull(),
    description: text("description").notNull().default(""),
    settingsJson: text("settings_json").notNull().default("{}"),
    importHash: text("import_hash"),
    createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
    updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
  },
  (table) => [uniqueIndex("uq_project_owner_import_hash").on(table.ownerId, table.importHash)],
);

/**
 * The fixed two-level hierarchy (ADR-0005): every chapter belongs to exactly
 * one volume, and a project always holds at least one volume. Non-chapter
 * documents stay outside volumes (volume_id stays NULL for them).
 */
export const volumes = sqliteTable(
  "volumes",
  {
    id: text("id").primaryKey(),
    projectId: text("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    title: text("title").notNull(),
    position: integer("position").notNull(),
    createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
    updatedAt: integer("updated_at", { mode: "timestamp_ms" }).notNull(),
  },
  (table) => [
    uniqueIndex("uq_volume_identity").on(table.projectId, table.title),
    index("idx_volumes_project_position").on(table.projectId, table.position),
  ],
);

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
    volumeId: text("volume_id").references(() => volumes.id, { onDelete: "cascade" }),
    // Beat association (#313): a chapter may reference one beat of its
    // project's outline document (the beat's heading title). The reference is
    // document-level state — it must survive the metadata-replacing revision
    // writes — and resolves only while an identically titled beat still exists.
    beatRef: text("beat_ref"),
    // Lorebook aliases (#315): a character/world document's extra prompt keys
    // as a JSON string array. Document-level state like the beat reference:
    // ordinary saves replace revision metadata wholesale, so prompt keys live
    // outside revisions to survive them.
    loreAliasesJson: text("lore_aliases_json").notNull().default("[]"),
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

/**
 * Snapshot-bound export artifacts. The stored path is relative to the data
 * root so the export service can confine downloads before reading a file.
 */
export const exports = sqliteTable(
  "exports",
  {
    id: text("id").primaryKey(),
    projectId: text("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    snapshotId: text("snapshot_id")
      .notNull()
      .references(() => projectSnapshots.id, { onDelete: "cascade" }),
    format: text("format").notNull(),
    relativePath: text("relative_path").notNull(),
    sizeBytes: integer("size_bytes").notNull(),
    checksumSha256: text("checksum_sha256").notNull(),
    createdAt: integer("created_at", { mode: "timestamp_ms" }).notNull(),
  },
  (table) => [
    index("idx_exports_project_created").on(table.projectId, table.createdAt),
    index("idx_exports_snapshot").on(table.snapshotId),
  ],
);
