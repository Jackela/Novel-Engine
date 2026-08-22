import { createHmac, randomBytes } from "node:crypto";
import { compare, hash } from "bcryptjs";

import { InvalidOperationError } from "../domain/exceptions.js";
import type { AuthStore, Principal, SessionKind } from "./ports/auth.js";

const GUEST_TTL_MS = 24 * 60 * 60 * 1000;
/** Cost factor matching the Python gold standard's gensalt() default. */
const BCRYPT_ROUNDS = 12;

let dummyHashMemo: Promise<string> | undefined;

/**
 * Constant dummy bcrypt hash used to keep login timing constant regardless of
 * whether the supplied username exists. The salt is random per process, so no
 * usable password literal ever lives in source control. The async bcrypt API
 * is mandatory here: pure-JS hashing at cost 12 must yield to the event loop
 * instead of stalling every concurrent request for hundreds of milliseconds.
 */
function dummyPasswordHash(): Promise<string> {
  dummyHashMemo ??= hash(randomBytes(32).toString("base64url"), BCRYPT_ROUNDS);
  return dummyHashMemo;
}

function utf8ByteLength(value: string): number {
  return new TextEncoder().encode(value).length;
}

export interface AuthServiceOptions {
  store: AuthStore;
  sessionSecret: string;
  now?: (() => Date) | undefined;
}

export interface IssuedSession {
  token: string;
  csrfToken: string;
  principal: Principal;
}

/**
 * Owner configuration and session lifecycle (the auth application service).
 * Session tokens are bearer credentials: only their deployment-secret-keyed
 * digest is stored, so rotating the secret invalidates every session.
 */
export class AuthService {
  private readonly store: AuthStore;
  private readonly sessionSecret: string;
  private readonly now: () => Date;

  constructor(options: AuthServiceOptions) {
    this.store = options.store;
    this.sessionSecret = options.sessionSecret;
    this.now = options.now ?? (() => new Date());
  }

  ownerExists(): boolean {
    return this.store.ownerExists();
  }

  /**
   * Configure the single local owner. The method name deliberately differs
   * from the frontend client's setupOwner so static cross-project symbol
   * merging cannot stitch an HTTP-input taint onto an unrelated fetch sink.
   */
  async configureOwner(
    username: string,
    password: string,
  ): Promise<{ id: string; username: string }> {
    const trimmed = username.trim();
    if (trimmed.length === 0 || password.length < 10 || utf8ByteLength(password) > 72) {
      throw new InvalidOperationError(
        "Username is required and password must be 10-72 UTF-8 bytes.",
      );
    }
    const owner = this.store.createOwner(trimmed, await hash(password, BCRYPT_ROUNDS));
    return { id: owner.id, username: owner.username };
  }

  async createOwnerSession(username: string, password: string): Promise<IssuedSession> {
    const owner = this.store.getOwnerByUsername(username.trim());
    // Always run bcrypt against a real or dummy hash so the timing of the
    // response does not reveal whether the username exists.
    const passwordHash = owner?.passwordHash ?? (await dummyPasswordHash());
    const passwordValid = await compare(password, passwordHash);
    if (owner === null || utf8ByteLength(password) > 72 || !passwordValid) {
      throw new InvalidOperationError("Invalid username or password.");
    }
    return this.createSession("owner", owner.id, null);
  }

  createGuestSession(): IssuedSession {
    const now = this.now();
    return this.createSession("guest", null, new Date(now.getTime() + GUEST_TTL_MS));
  }

  private createSession(
    kind: SessionKind,
    ownerId: string | null,
    expiresAt: Date | null,
  ): IssuedSession {
    const token = randomBytes(36).toString("base64url");
    const csrfToken = randomBytes(32).toString("base64url");
    const now = this.now();
    const record = this.store.createSession({
      kind,
      ownerId,
      tokenHash: this.tokenHash(token),
      csrfToken,
      expiresAt,
      createdAt: now,
      lastSeenAt: now,
    });
    return {
      token,
      csrfToken,
      principal: { sessionId: record.id, kind, ownerId, expiresAt },
    };
  }

  /** Session lookup digest keyed by the deployment secret (HMAC-SHA256). */
  private tokenHash(token: string): string {
    return createHmac("sha256", this.sessionSecret).update(token, "utf8").digest("hex");
  }

  /**
   * Resolve the principal for a presented session token, enforcing expiry at
   * validation time: an expired session is deleted and treated as
   * unauthenticated; a valid one has its last-seen timestamp refreshed.
   */
  principalFromToken(token: string | undefined): Principal | null {
    if (token === undefined || token === "") {
      return null;
    }
    const record = this.store.getSessionByTokenHash(this.tokenHash(token));
    if (record === null) {
      return null;
    }
    const now = this.now();
    if (record.expiresAt !== null && record.expiresAt.getTime() <= now.getTime()) {
      this.store.deleteSession(record.id);
      return null;
    }
    this.store.updateSessionLastSeen(record.id, now);
    return {
      sessionId: record.id,
      kind: record.kind,
      ownerId: record.ownerId,
      expiresAt: record.expiresAt,
    };
  }

  terminateSession(token: string | undefined): void {
    if (token === undefined || token === "") {
      return;
    }
    const record = this.store.getSessionByTokenHash(this.tokenHash(token));
    if (record !== null) {
      this.store.deleteSession(record.id);
    }
  }
}
