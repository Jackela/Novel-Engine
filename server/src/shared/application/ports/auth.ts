/** The single session flavor since #311 retired the guest principal: the owner. */
export type SessionKind = "owner";

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
 * The authenticated actor bound to a request — the owner. Owner data is
 * keyed by ownerId; identifiers outside it resolve to not-found.
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
  /** The configured owner of a single-owner installation, if any. */
  getFirstOwner(): OwnerRecord | null;
  /** Rejects with InvalidOperationError when the single-owner invariant would break. */
  createOwner(username: string, passwordHash: string): OwnerRecord;
  createSession(input: CreateSessionInput): SessionRecord;
  getSessionByTokenHash(tokenHash: string): SessionRecord | null;
  deleteSession(sessionId: string): void;
  updateSessionLastSeen(sessionId: string, lastSeenAt: Date): void;
}
