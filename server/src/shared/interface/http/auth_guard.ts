import { timingSafeEqual } from "node:crypto";
import type { FastifyReply, FastifyRequest, HookHandlerDoneFunction } from "fastify";

import type { AuthService } from "../../application/auth_service.js";
import type { Principal } from "../../application/ports/auth.js";
import { AppError } from "./error_envelope.js";
import { CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE } from "./session_cookies.js";

/**
 * First-contact surfaces: cookie-less by design, so they are exempt from CSRF
 * double-submit AND the paths whose abuse the per-IP rate limiter blunts.
 * One list on purpose — the two duties must never drift apart.
 */
export const FIRST_CONTACT_PATHS = new Set(["/api/setup", "/api/session/login"]);
const WRITE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

declare module "fastify" {
  interface FastifyRequest {
    /** Set by the principal guard on authenticated routes. */
    principal?: Principal;
  }
}

function tokensEqual(left: string, right: string): boolean {
  if (left.length !== right.length) {
    return false;
  }
  return timingSafeEqual(Buffer.from(left, "utf8"), Buffer.from(right, "utf8"));
}

/**
 * PreHandler factory for authenticated surfaces: resolves the principal from
 * the session cookie (401 otherwise) and enforces CSRF double-submit on every
 * write outside the exempt paths (403 on missing or mismatched tokens).
 */
export function principalGuard(
  service: AuthService | undefined,
): (request: FastifyRequest, reply: FastifyReply, done: HookHandlerDoneFunction) => void {
  return (request, _reply, done) => {
    if (service === undefined) {
      throw new AppError({
        statusCode: 503,
        code: "SERVICE_UNAVAILABLE",
        message: "The persistence layer is not configured.",
      });
    }
    const principal = service.principalFromToken(request.cookies[SESSION_COOKIE]);
    if (principal === null) {
      throw new AppError({
        statusCode: 401,
        code: "UNAUTHORIZED",
        message: "Owner session required.",
      });
    }
    const path = request.url.split("?")[0] ?? request.url;
    if (WRITE_METHODS.has(request.method) && !FIRST_CONTACT_PATHS.has(path)) {
      const cookieToken = request.cookies[CSRF_COOKIE];
      const headerToken = request.headers[CSRF_HEADER];
      if (
        typeof cookieToken !== "string" ||
        cookieToken === "" ||
        typeof headerToken !== "string" ||
        headerToken === ""
      ) {
        throw new AppError({
          statusCode: 403,
          code: "CSRF_TOKEN_MISSING",
          message: "CSRF token missing.",
        });
      }
      if (!tokensEqual(cookieToken, headerToken)) {
        throw new AppError({
          statusCode: 403,
          code: "CSRF_TOKEN_INVALID",
          message: "CSRF token invalid.",
        });
      }
    }
    request.principal = principal;
    done();
  };
}
