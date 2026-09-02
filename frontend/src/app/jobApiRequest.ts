export interface JobsRequestOptions extends RequestInit {
  readonly cursor?: string;
  readonly limit?: number;
}

export function projectJobsRequest(
  projectId: string,
  options: JobsRequestOptions,
): readonly [path: string, init: RequestInit] {
  const query = new URLSearchParams();
  if (options.limit !== undefined) query.set("limit", String(options.limit));
  if (options.cursor !== undefined) query.set("cursor", options.cursor);
  const encoded = query.toString();
  const { cursor: _cursor, limit: _limit, ...init } = options;
  return [`/api/projects/${projectId}/jobs${encoded ? `?${encoded}` : ""}`, init];
}

export function retryJobRequest(
  projectId: string,
  jobId: string,
  idempotencyKey: string,
): readonly [path: string, init: RequestInit] {
  return [
    `/api/projects/${projectId}/jobs/${jobId}/retry`,
    { method: "POST", headers: { "Idempotency-Key": idempotencyKey } },
  ];
}
