import type { FastifyReply } from "fastify";

import type { Principal, SessionKind } from "../../application/ports/auth.js";

/** Adjudicated cookie contract (#260): product-prefixed names. */
export const SESSION_COOKIE = "novel_engine_session";
export const CSRF_COOKIE = "novel_engine_csrf";
export const CSRF_HEADER = "x-csrf-token";

/** Owner sessions last 30 days — mirrored by the server-side lazy expiry. */
export const OWNER_COOKIE_MAX_AGE = 60 * 60 * 24 * 30;

export function isSecureEnvironment(environment: string): boolean {
  return environment === "production" || environment === "staging";
}

export function issueSessionCookies(
  reply: FastifyReply,
  token: string,
  csrfToken: string,
  environment: string,
): void {
  const maxAge = OWNER_COOKIE_MAX_AGE;
  const secure = isSecureEnvironment(environment);
  reply.setCookie(SESSION_COOKIE, token, {
    path: "/",
    httpOnly: true,
    sameSite: "lax",
    maxAge,
    secure,
  });
  // The CSRF cookie must stay readable by the page: double-submit compares
  // this cookie against the X-CSRF-Token header the client echoes back.
  reply.setCookie(CSRF_COOKIE, csrfToken, {
    path: "/",
    httpOnly: false,
    sameSite: "lax",
    maxAge,
    secure,
  });
}

export function clearSessionCookies(reply: FastifyReply): void {
  reply.clearCookie(SESSION_COOKIE, { path: "/" });
  reply.clearCookie(CSRF_COOKIE, { path: "/" });
}

export interface PrincipalPayload {
  session_id: string;
  kind: SessionKind;
  owner_id: string | null;
  expires_at: string | null;
}

export function principalPayload(principal: Principal): PrincipalPayload {
  return {
    session_id: principal.sessionId,
    kind: principal.kind,
    owner_id: principal.ownerId,
    expires_at: principal.expiresAt === null ? null : principal.expiresAt.toISOString(),
  };
}
