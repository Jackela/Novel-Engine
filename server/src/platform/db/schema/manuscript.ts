/**
 * Manuscript tables: documents and their append-only revision chain.
 *
 * Two structural rules carry most of the product's trust story:
 *
 * 1. `documents.current_revision_id` and the revision row move together in one
 *    transaction. The column has no foreign key on purpose — the pair is
 *    circular (a document points at a revision, a revision points at a
 *    document) and SQLite cannot express it without deferring. The invariant is
 *    enforced by the single write path, not by the schema.
 * 2. `revisions` is append-only. A restore writes a new row whose
 *    `metadata_json.restored_from` names the target; nothing is ever updated in
 *    place except a surviving row's `parent_revision_id` during retention
 *    pruning.
 */

import { index, integer, sqliteTable, text, uniqueIndex } from "drizzle-orm/sqlite-core";

import { projects, volumes } from "./library.js";

export const documents = sqliteTable(
  "documents",
  {
    id: text("id").primaryKey(),
    projectId: text("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    /** Null means the chapter sits outside any volume (outline, notes, lore). */
    volumeId: text("volume_id").references(() => volumes.id, { onDelete: "set null" }),
    /** chapter | outline | character | world | note — mirrored in contracts. */
    kind: text("kind").notNull(),
    title: text("title").notNull(),
    position: integer("position").notNull().default(0),
    /** Outline beat this chapter fulfils; free text, resolved by the outline doc. */
    beatRef: text("beat_ref"),
    /** Null only between the document insert and its first revision insert. */
    currentRevisionId: text("current_revision_id"),
    createdAt: integer("created_at").notNull(),
    updatedAt: integer("updated_at").notNull(),
  },
  (table) => [
    uniqueIndex("uq_documents_identity").on(table.projectId, table.kind, table.title),
    index("idx_documents_order").on(table.projectId, table.position, table.id),
  ],
);

export const revisions = sqliteTable(
  "revisions",
  {
    id: text("id").primaryKey(),
    documentId: text("document_id")
      .notNull()
      .references(() => documents.id, { onDelete: "cascade" }),
    /**
     * Null only for the first revision of a document. Every other null is data
     * corruption, which is why retention refuses to collapse a row whose parent
     * is null.
     */
    parentRevisionId: text("parent_revision_id"),
    /** 1-based, monotonic per document. Gaps appear when autosave collapses. */
    revisionNumber: integer("revision_number").notNull(),
    contentMarkdown: text("content_markdown").notNull().default(""),
    /** SHA-256 of the body; deduplication and the migration checksum ride on it. */
    contentHash: text("content_hash").notNull(),
    /**
     * Computed at write time by the one word-count rule and never recomputed on
     * read. Storing it removes the startup reconciliation the old build needed.
     */
    wordCount: integer("word_count").notNull(),
    /** author | ai-accepted | restore. Closed set, validated on read. */
    source: text("source").notNull(),
    /** Author-supplied label: "the version I sent my editor". */
    note: text("note"),
    /**
     * Opaque per-source payload. Two paths treat it differently and both are
     * intentional: accepting a proposal REPLACES it with `{ai_job_id}`, while
     * restoring MERGES in `restored_from` and keeps the author's keys.
     */
    metadataJson: text("metadata_json").notNull().default("{}"),
    createdAt: integer("created_at").notNull(),
  },
  (table) => [
    uniqueIndex("uq_revisions_number").on(table.documentId, table.revisionNumber),
    // History pagination walks newest first; the id breaks ties within one second.
    index("idx_revisions_history").on(table.documentId, table.revisionNumber),
    index("idx_revisions_parent").on(table.parentRevisionId),
  ],
);
