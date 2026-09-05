export interface ExportsRequestOptions extends RequestInit {
  readonly cursor?: string;
  readonly limit?: number;
}

export function projectExportsRequest(
  projectId: string,
  options: ExportsRequestOptions,
): readonly [path: string, init: RequestInit] {
  const query = new URLSearchParams();
  if (options.limit !== undefined) query.set("limit", String(options.limit));
  if (options.cursor !== undefined) query.set("cursor", options.cursor);
  const encoded = query.toString();
  const { cursor: _cursor, limit: _limit, ...init } = options;
  return [`/api/projects/${projectId}/exports${encoded ? `?${encoded}` : ""}`, init];
}
