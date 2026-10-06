import { useCallback, useEffect, useRef } from "react";
import { type Location, useLocation, useNavigate } from "react-router-dom";

/**
 * History-state marker written only by a 401-forced return to the entry page
 * (DR-020). Voluntary visits — a first load, a sign-out, an unknown URL —
 * never carry it, which is what lets the entry page tell "your session
 * expired, sign in again" from "you came here yourself".
 */
export const SESSION_EXPIRED_REASON = "session-expired";

/** Where the app lands when a session loss preserved no source route. */
export const PROJECT_LIBRARY_ROUTE = "/projects";

/** Entry-route history state written by a forced return from a rejected session. */
export interface SessionExpiredState {
  /** App-internal route (`pathname + search + hash`) the author was reading. */
  readonly from: string;
  readonly reason: typeof SESSION_EXPIRED_REASON;
}

/** Route coordinates (path, query, fragment) of one router location. */
export function routeHref(location: Location): string {
  return `${location.pathname}${location.search}${location.hash}`;
}

/**
 * True when a rejected session forced this entry visit. The notice is driven
 * by the marker alone: a malformed `from` still means the author was thrown
 * out of a signed-in surface, so the explanation must not disappear with it.
 */
export function isSessionExpiredEntry(state: unknown): boolean {
  return (
    typeof state === "object" &&
    state !== null &&
    (state as Partial<SessionExpiredState>).reason === SESSION_EXPIRED_REASON
  );
}

/**
 * True for an app-internal route that can be restored. Entry-page sources and
 * protocol-relative paths (`//host`) restore nothing, so a malformed history
 * entry can never turn the post-login return into a cross-origin hop.
 */
function isReturnableRoute(from: unknown): from is string {
  return typeof from === "string" && from.startsWith("/") && !from.startsWith("//") && from !== "/";
}

/**
 * The route the entry page restores after sign-in, or null when the visit was
 * voluntary. Router state is external input, so the shape is validated rather
 * than trusted; every unexpected value degrades to null (the caller's
 * fallback) instead of throwing.
 */
export function readSessionReturnRoute(state: unknown): string | null {
  if (!isSessionExpiredEntry(state)) return null;
  const from = (state as Partial<SessionExpiredState>).from;
  return isReturnableRoute(from) ? from : null;
}

/**
 * Stable callback that returns to the entry page with the source route and
 * the expiry marker. `navigate` and the location are held behind refs so the
 * callback feeds effect dependencies without replaying reads on pathname
 * changes (#465), and the redirect replaces the expired route so
 * back-navigation cannot bounce through the expired screen.
 */
export function useSessionExpiredRedirect(): () => void {
  const navigate = useNavigate();
  const location = useLocation();
  const navigateRef = useRef(navigate);
  const locationRef = useRef(location);
  useEffect(() => {
    navigateRef.current = navigate;
    locationRef.current = location;
  }, [navigate, location]);
  return useCallback(() => {
    void navigateRef.current("/", {
      replace: true,
      state: {
        from: routeHref(locationRef.current),
        reason: SESSION_EXPIRED_REASON,
      } satisfies SessionExpiredState,
    });
  }, []);
}

/**
 * Route the entry page opens after a successful sign-in: the source route a
 * 401 preserved, else the project library. The result is a primitive, so it
 * also stays referentially stable for `useEntryBootstrap`'s dependency chain.
 */
export function useEntryReturnRoute(): string {
  const location = useLocation();
  return readSessionReturnRoute(location.state) ?? PROJECT_LIBRARY_ROUTE;
}
