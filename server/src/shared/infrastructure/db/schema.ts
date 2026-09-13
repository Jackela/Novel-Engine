import { integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

/**
 * The first schema of the TS rewrite (#264): the sessions table with its
 * adjudicated columns (kind/token_hash/csrf_token/expires_at/last_seen_at,
 * pre-rewrite audit C2). The auth spine (#265) added owners, and the studio
 * data model (#266) grew through generated migrations; the jobs, job-events,
 * and usage tables now live beside their studio consumers (#534).
 */
/**
 * The auth spine (#265): exactly one owner per store with a unique username
 * and a bcrypt password hash, and sessions.owner_id gains its adjudicated
 * owners(id) foreign key with cascade delete.
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
