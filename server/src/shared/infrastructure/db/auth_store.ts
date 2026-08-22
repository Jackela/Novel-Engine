import { randomUUID } from "node:crypto";
import { count, eq } from "drizzle-orm";
import type {
  AuthStore,
  CreateSessionInput,
  OwnerRecord,
  SessionRecord,
} from "../../application/ports/auth.js";
import { InvalidOperationError } from "../../domain/exceptions.js";
import type { StudioSqliteDatabase } from "./connection.js";
import { owners, sessions } from "./schema.js";

type OwnerRow = typeof owners.$inferSelect;
type SessionRow = typeof sessions.$inferSelect;

function toOwnerRecord(row: OwnerRow): OwnerRecord {
  return {
    id: row.id,
    username: row.username,
    passwordHash: row.password_hash,
    createdAt: row.created_at,
  };
}

function toSessionRecord(row: SessionRow): SessionRecord {
  return {
    id: row.id,
    kind: row.kind === "owner" ? "owner" : "guest",
    ownerId: row.owner_id,
    tokenHash: row.token_hash,
    csrfToken: row.csrf_token,
    createdAt: row.created_at,
    expiresAt: row.expires_at,
    lastSeenAt: row.last_seen_at,
  };
}

/**
 * Drizzle-backed AuthStore: parameterized queries only, and the single-owner
 * invariant is re-checked inside the insert transaction so racing first-run
 * setups cannot both succeed (better-sqlite3 serializes writers).
 */
export class DrizzleAuthStore implements AuthStore {
  private readonly db: StudioSqliteDatabase;

  constructor(db: StudioSqliteDatabase) {
    this.db = db;
  }

  ownerExists(): boolean {
    const [row] = this.db.select({ value: count() }).from(owners).all();
    return (row?.value ?? 0) > 0;
  }

  getOwnerByUsername(username: string): OwnerRecord | null {
    const [row] = this.db.select().from(owners).where(eq(owners.username, username)).all();
    return row === undefined ? null : toOwnerRecord(row);
  }

  createOwner(username: string, passwordHash: string): OwnerRecord {
    return this.db.transaction((tx) => {
      const [existing] = tx.select({ value: count() }).from(owners).all();
      if ((existing?.value ?? 0) > 0) {
        throw new InvalidOperationError("The local owner has already been configured.");
      }
      const [row] = tx
        .insert(owners)
        .values({
          id: randomUUID(),
          username,
          password_hash: passwordHash,
          created_at: new Date(),
        })
        .returning()
        .all();
      if (row === undefined) {
        throw new InvalidOperationError("The local owner could not be created.");
      }
      return toOwnerRecord(row);
    });
  }

  createSession(input: CreateSessionInput): SessionRecord {
    const [row] = this.db
      .insert(sessions)
      .values({
        id: randomUUID(),
        kind: input.kind,
        owner_id: input.ownerId,
        token_hash: input.tokenHash,
        csrf_token: input.csrfToken,
        created_at: input.createdAt,
        expires_at: input.expiresAt,
        last_seen_at: input.lastSeenAt,
      })
      .returning()
      .all();
    if (row === undefined) {
      throw new Error("session insert returned no row");
    }
    return toSessionRecord(row);
  }

  getSessionByTokenHash(tokenHash: string): SessionRecord | null {
    const [row] = this.db.select().from(sessions).where(eq(sessions.token_hash, tokenHash)).all();
    return row === undefined ? null : toSessionRecord(row);
  }

  deleteSession(sessionId: string): void {
    this.db.delete(sessions).where(eq(sessions.id, sessionId)).run();
  }

  updateSessionLastSeen(sessionId: string, lastSeenAt: Date): void {
    this.db
      .update(sessions)
      .set({ last_seen_at: lastSeenAt })
      .where(eq(sessions.id, sessionId))
      .run();
  }
}
