import { apiPath, type PageRequestOptions, pageRequest } from "./pageRequest";

/** Options for one bounded project-jobs page request. */
export type JobsRequestOptions = PageRequestOptions;

/** Build the project-jobs page request. */
export function projectJobsRequest(
  projectId: string,
  options: JobsRequestOptions,
): readonly [path: string, init: RequestInit] {
  return pageRequest(apiPath("projects", projectId, "jobs"), options, "Jobs page");
}

/** Build the idempotent job-retry request. */
export function retryJobRequest(
  projectId: string,
  jobId: string,
  idempotencyKey: string,
): readonly [path: string, init: RequestInit] {
  return [
    apiPath("projects", projectId, "jobs", jobId, "retry"),
    { method: "POST", headers: { "Idempotency-Key": idempotencyKey } },
  ];
}
