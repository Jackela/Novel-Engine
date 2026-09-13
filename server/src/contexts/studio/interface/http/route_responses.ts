import { errorEnvelopeResponse } from "../../../../shared/interface/http/error_envelope.js";

/**
 * Shared response-map composers for the Studio HTTP surface. Every
 * authenticated route answers with the same error envelope contract, so the
 * route modules declare only the codes that differ from the shared base —
 * the success payload and any code whose schema is not the plain envelope
 * (specific 409/422/503 shapes) — instead of re-declaring the boilerplate.
 *
 * The shared bases read as: 401 guard failure, 404 foreign or missing
 * scoped parent, 403 CSRF double-submit rejection (writes only), and 503
 * store unavailability.
 */

/** Route-declared codes layered on top of a shared error base. */
type ResponseExtras = Record<string, unknown>;

/** Guard (401), scope-miss (404), and store-unavailability (503) envelopes shared by authenticated reads. */
const READ_ERROR_RESPONSE_BASE = {
  401: errorEnvelopeResponse,
  404: errorEnvelopeResponse,
  503: errorEnvelopeResponse,
} as const;

/** Reads plus the CSRF rejection (403) shared by authenticated writes. */
const WRITE_ERROR_RESPONSE_BASE = {
  ...READ_ERROR_RESPONSE_BASE,
  403: errorEnvelopeResponse,
} as const;

/**
 * Complete response map for an authenticated project-scoped read: the
 * shared 401/404/503 error envelopes plus the route-declared `extra` codes
 * (at minimum the success payload).
 */
export function authedReadResponses<const E extends ResponseExtras>(extra: E) {
  return { ...READ_ERROR_RESPONSE_BASE, ...extra };
}

/**
 * Complete response map for an authenticated write: the shared
 * 401/403/404/503 error envelopes plus the route-declared `extra` codes
 * (success payload and any specific 409/422/503 schema, which override the
 * shared envelope for that status).
 */
export function authedWriteResponses<const E extends ResponseExtras>(extra: E) {
  return { ...WRITE_ERROR_RESPONSE_BASE, ...extra };
}
