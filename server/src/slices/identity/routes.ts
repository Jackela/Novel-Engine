/**
 * The identity HTTP surface.
 *
 * Four routes, and the shape of the surface is itself a decision:
 *
 * - `POST /api/setup` answers 201 with the owner's identity only. It does not
 *   create a session — the author logs in afterwards, and tests can tell the two
 *   steps apart.
 * - `POST /api/session` sets both cookies and returns the expiry.
 * - `GET /api/session` answers 200 for both outcomes. "Not authenticated" is a
 *   normal state on a first visit; a 401 would paint the browser console red on
 *   every cold start and teach people to ignore the error channel.
 * - `DELETE /api/session` is idempotent and answers 204 regardless.
 *
 * None of these verify CSRF: they are the entry points, and CSRF is a
 * double-submit against a session that does not exist yet. Protected routes
 * carry that check; putting it here would make the first login impossible.
 */

import type { FastifyInstance } from "fastify";

import type {
  CredentialsRequest,
  OwnerView,
  SessionProbeView,
  SessionView,
} from "../../contracts/identity.js";
import { AppError } from "../../platform/http/error_envelope.js";
import { CredentialPolicyError } from "./domain/credentials.js";
import { OwnerAlreadyConfiguredError } from "./domain/errors.js";
import type { OwnerStore, SecretHasher, SessionStore, SessionTokenIssuer } from "./ports.js";
import { InvalidCredentialsError, login } from "./usecases/login.js";
import { logout } from "./usecases/logout.js";
import { resolvePrincipal } from "./usecases/resolve_principal.js";
import { setupOwner } from "./usecases/setup_owner.js";

/** Cookie names carried over verbatim; changing them logs every author out. */
export const SESSION_COOKIE = "novel_engine_session";
export const CSRF_COOKIE = "novel_engine_csrf";

const SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

export interface IdentityDeps {
  readonly owners: OwnerStore;
  readonly hasher: SecretHasher;
  readonly sessions: SessionStore;
  readonly tokens: SessionTokenIssuer;
  readonly now: () => number;
  /** Secure cookies in production/staging only; localhost over http must work. */
  readonly secureCookies: boolean;
}

/** Every identity failure is 422 INVALID_OPERATION, matching the previous build. */
function asInvalidOperation(error: unknown): never {
  if (error instanceof CredentialPolicyError) {
    throw new AppError("INVALID_OPERATION", { message: error.message });
  }
  if (error instanceof OwnerAlreadyConfiguredError) {
    throw new AppError("INVALID_OPERATION", { message: error.message });
  }
  if (error instanceof InvalidCredentialsError) {
    throw new AppError("INVALID_OPERATION", { message: error.message });
  }
  throw error;
}

export function registerIdentityRoutes(app: FastifyInstance, deps: IdentityDeps): void {
  const shared = { owners: deps.owners, hasher: deps.hasher, now: deps.now };

  app.post<{ Body: CredentialsRequest }>("/api/setup", async (request, reply): Promise<OwnerView> => {
    try {
      const owner = await setupOwner(shared, request.body);
      void reply.status(201);
      return owner;
    } catch (error) {
      return asInvalidOperation(error);
    }
  });

  app.post<{ Body: CredentialsRequest }>("/api/session", async (request, reply): Promise<SessionView> => {
    try {
      const issued = await login(
        { ...shared, sessions: deps.sessions, tokens: deps.tokens },
        request.body,
      );
      void reply.setCookie(SESSION_COOKIE, issued.token, {
        path: "/",
        httpOnly: true,
        sameSite: "lax",
        maxAge: SESSION_MAX_AGE_SECONDS,
        secure: deps.secureCookies,
      });
      // The CSRF cookie must stay readable by the page: double-submit compares it
      // against a header the client script sets.
      void reply.setCookie(CSRF_COOKIE, issued.csrfToken, {
        path: "/",
        httpOnly: false,
        sameSite: "lax",
        maxAge: SESSION_MAX_AGE_SECONDS,
        secure: deps.secureCookies,
      });
      return { ownerId: issued.ownerId, expiresAt: issued.expiresAt };
    } catch (error) {
      return asInvalidOperation(error);
    }
  });

  app.get("/api/session", (request): SessionProbeView => {
    const principal = resolvePrincipal(
      { sessions: deps.sessions, tokens: deps.tokens, now: deps.now },
      request.cookies[SESSION_COOKIE],
    );
    return principal === null
      ? { authenticated: false }
      : { authenticated: true, ownerId: principal.ownerId, expiresAt: principal.expiresAt };
  });

  app.delete("/api/session", (request, reply) => {
    logout(
      { sessions: deps.sessions, tokens: deps.tokens },
      request.cookies[SESSION_COOKIE],
    );
    void reply.clearCookie(SESSION_COOKIE, { path: "/" });
    void reply.clearCookie(CSRF_COOKIE, { path: "/" });
    // A bare `status(204)` never sends, and Fastify then waits for a body that
    // will not come — the request hangs until the client times out.
    return reply.status(204).send();
  });
}
