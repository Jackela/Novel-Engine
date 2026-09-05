export interface RevisionRequestOptions extends RequestInit {
  readonly cursor?: string;
  readonly limit?: number;
}

function assertRevisionLimit(limit: number): void {
  if (!Number.isInteger(limit) || limit < 1 || limit > 100) {
    throw new RangeError("Revision page limit must be an integer from 1 through 100.");
  }
}

export function documentRevisionsRequest(
  projectId: string,
  documentId: string,
  options: RevisionRequestOptions,
): readonly [path: string, init: RequestInit] {
  const query = new URLSearchParams();
  if (options.limit !== undefined) {
    assertRevisionLimit(options.limit);
    query.set("limit", String(options.limit));
  }
  if (options.cursor !== undefined) query.set("cursor", options.cursor);
  const encoded = query.toString();
  const { cursor: _cursor, limit: _limit, ...init } = options;
  return [
    `/api/projects/${projectId}/documents/${documentId}/revisions${encoded ? `?${encoded}` : ""}`,
    init,
  ];
}
