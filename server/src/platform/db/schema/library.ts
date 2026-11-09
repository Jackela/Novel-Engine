/**
 * Library tables: projects and their volumes.
 *
 * A project is one novel. There is no `owner_id` on volumes and documents —
 * ownership flows through the project, and every query joins or filters by the
 * project first. Keeping the owner on one table means an ownership check cannot
 * disagree between a parent and its children.
 */

import { index, integer, sqliteTable, text, uniqueIndex } from "drizzle-orm/sqlite-core";

import { owners } from "./identity.js";

export const projects = sqliteTable(
  "projects",
  {
    id: text("id").primaryKey(),
    ownerId: text("owner_id")
      .notNull()
      .references(() => owners.id, { onDelete: "cascade" }),
    title: text("title").notNull(),
    description: text("description").notNull().default(""),
    /** Provider and generation settings, serialized; schema owned by settings. */
    settingsJson: text("settings_json").notNull().default("{}"),
    /** Bumped on every settings write so stale clients can be detected. */
    settingsVersion: integer("settings_version").notNull().default(1),
    /**
     * Legacy import identity: relative paths plus content. Re-importing the same
     * workspace returns the existing project instead of creating a duplicate.
     * Null for hand-created projects, which is why the unique index tolerates
     * multiple nulls (SQLite treats nulls as distinct).
     */
    importHash: text("import_hash"),
    createdAt: integer("created_at").notNull(),
    updatedAt: integer("updated_at").notNull(),
  },
  (table) => [
    // Keyset pagination for the project catalog: newest first, id as tie-breaker.
    index("idx_projects_catalog").on(table.ownerId, table.updatedAt, table.id),
    uniqueIndex("uq_projects_import").on(table.ownerId, table.importHash),
  ],
);

export const volumes = sqliteTable(
  "volumes",
  {
    id: text("id").primaryKey(),
    projectId: text("project_id")
      .notNull()
      .references(() => projects.id, { onDelete: "cascade" }),
    title: text("title").notNull(),
    position: integer("position").notNull().default(0),
    createdAt: integer("created_at").notNull(),
  },
  (table) => [
    uniqueIndex("uq_volumes_title").on(table.projectId, table.title),
    index("idx_volumes_order").on(table.projectId, table.position, table.id),
  ],
);
