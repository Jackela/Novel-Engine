/**
 * Identity tables: the single local Owner and its sessions.
 *
 * One Owner per installation is a product invariant, not a convenience: the
 * whole authorization model assumes exactly one principal, so there is no
 * `owner_id` on projects to join against — ownership is implied. If a second
 * owner were ever admitted, every scope predicate in the codebase would silently
 * see the first owner's rows.
 */

import { index, integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const owners = sqliteTable("owners", {
  id: text("id").primaryKey(),
  username: text("username").notNull().unique(),
  /** bcrypt hash; never the plaintext, never logged. */
  passwordHash: text("password_hash").notNull(),
  createdAt: integer("created_at").notNull(),
});

export const sessions = sqliteTable(
  "sessions",
  {
    id: text("id").primaryKey(),
    ownerId: text("owner_id")
      .notNull()
      .references(() => owners.id, { onDelete: "cascade" }),
    /** HMAC-derived token digest; the cookie carries the token, not this value. */
    tokenHash: text("token_hash").notNull().unique(),
    /** Double-submit CSRF secret bound to this session. */
    csrfToken: text("csrf_token").notNull(),
    expiresAt: integer("expires_at").notNull(),
    lastSeenAt: integer("last_seen_at").notNull(),
    /**
     * Creation instant, distinct from `lastSeenAt`. Kept because "when did this
     * session start" and "when was it last used" answer different questions:
     * expiry is computed from creation, while activity is diagnostics only.
     */
    createdAt: integer("created_at").notNull(),
  },
  (table) => [index("idx_sessions_owner").on(table.ownerId)],
);

/** One-time bootstrap token state for first-start setup on a non-loopback peer. */
export const setupTokens = sqliteTable("setup_tokens", {
  id: text("id").primaryKey(),
  tokenHash: text("token_hash").notNull().unique(),
  createdAt: integer("created_at").notNull(),
  consumedAt: integer("consumed_at"),
});
