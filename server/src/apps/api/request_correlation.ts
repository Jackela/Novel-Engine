/**
 * Inbound correlation ids are honored only when short and plain: a hostile
 * header value must not flow into logs, responses, or error ids.
 */
export const REQUEST_ID_HEADER = "x-request-id";
const SAFE_REQUEST_ID = /^[A-Za-z0-9._-]{1,128}$/;

export function correlationIdFrom(value: string | string[] | undefined): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  return SAFE_REQUEST_ID.test(trimmed) ? trimmed : undefined;
}
