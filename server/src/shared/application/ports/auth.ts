/** Session flavors of the auth spine: the configured owner or a sandboxed guest. */
export type SessionKind = "owner" | "guest";

export interface OwnerRecord {
  id: string;
  username: string;
  passwordHash: string;
  createdAt: Date;
}

export interface SessionRecord {
  id: string;
  kind: SessionKind;
  ownerId: string | null;
  tokenHash: string;
  csrfToken: string | null;
  createdAt: Date;
  expiresAt: Date | null;
  lastSeenAt: Date;
}

/**
 * The authenticated actor bound to a request — the principal-scoping
 * foundation: owner data is keyed by ownerId, guest data by sessionId.
 */
export interface Principal {
  sessionId: string;
  kind: SessionKind;
  ownerId: string | null;
  expiresAt: Date | null;
}

export interface CreateSessionInput {
  kind: SessionKind;
  ownerId: string | null;
  tokenHash: string;
  csrfToken: string;
  expiresAt: Date | null;
  createdAt: Date;
  lastSeenAt: Date;
}

/**
 * Persistence port of the auth spine. The application layer orchestrates
 * owner setup and session lifecycle through this port; the Drizzle store
 * implements it in infrastructure.
 */
export interface AuthStore {
  ownerExists(): boolean;
  getOwnerByUsername(username: string): OwnerRecord | null;
  /** Rejects with InvalidOperationError when the single-owner invariant would break. */
  createOwner(username: string, passwordHash: string): OwnerRecord;
  createSession(input: CreateSessionInput): SessionRecord;
  getSessionByTokenHash(tokenHash: string): SessionRecord | null;
  deleteSession(sessionId: string): void;
  updateSessionLastSeen(sessionId: string, lastSeenAt: Date): void;
}
