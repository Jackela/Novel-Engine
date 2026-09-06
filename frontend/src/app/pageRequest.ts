/** Pagination options shared by every bounded keyset-page request builder (#479). */
export interface PageRequestOptions extends RequestInit {
  readonly cursor?: string;
  readonly limit?: number;
}

/**
 * Encode one opaque path identifier so user-controlled ids stay uniformly
 * encoded in every request path (#479).
 */
export function encodePathSegment(value: string): string {
  return encodeURIComponent(value);
}

/** Join API path segments into one request path, encoding every segment. */
export function apiPath(...segments: readonly string[]): string {
  return ["/api", ...segments.map(encodePathSegment)].join("/");
}

function assertPageLimit(limit: number, limitErrorSubject: string): void {
  if (!Number.isInteger(limit) || limit < 1 || limit > 100) {
    throw new RangeError(`${limitErrorSubject} limit must be an integer from 1 through 100.`);
  }
}

/**
 * Build one bounded keyset-page request (#479): validate the shared 1..100
 * client limit, append the optional continuation cursor, and strip both
 * pagination keys from the fetch init. `limitErrorSubject` names the resource
 * in the out-of-range limit error.
 */
export function pageRequest(
  path: string,
  options: PageRequestOptions,
  limitErrorSubject: string,
): readonly [path: string, init: RequestInit] {
  const query = new URLSearchParams();
  if (options.limit !== undefined) {
    assertPageLimit(options.limit, limitErrorSubject);
    query.set("limit", String(options.limit));
  }
  if (options.cursor !== undefined) query.set("cursor", options.cursor);
  const encoded = query.toString();
  const { cursor: _cursor, limit: _limit, ...init } = options;
  return [`${path}${encoded ? `?${encoded}` : ""}`, init];
}
