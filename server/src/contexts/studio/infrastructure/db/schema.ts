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
