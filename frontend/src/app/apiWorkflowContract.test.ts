import { describe, expect, it } from "vitest";

import {
  parseExportJobResponse,
  parseJob,
  parseJobs,
  parseReviewJobResponse,
} from "@/app/apiWorkflowContract";

const jobReview = {
  id: "job-1",
  project_id: "project-1",
  document_id: null,
  kind: "review",
  operation: "review",
  status: "completed",
  provider: "mock",
  model: "deterministic-story-v1",
  request: {},
  result: { review_id: "review-9", snapshot_id: "snapshot-9", summary: "S" },
  error: null,
  retry_of_job_id: null,
  created_at: "2026-08-25T00:00:00.000Z",
  updated_at: "2026-08-25T00:00:00.000Z",
  events: [],
};

const jobExport = {
  ...jobReview,
  id: "job-2",
  kind: "export",
  operation: "export",
  provider: "studio",
  model: "",
  result: { export_id: "export-9", snapshot_id: "snapshot-9", format: "epub" },
};

const jobSummary = {
  id: "job-import-1",
  project_id: "project-1",
  document_id: null,
  kind: "import",
  operation: "import",
  status: "completed",
  provider: "studio",
  model: "",
  error: null,
  retry_of_job_id: null,
  created_at: "2026-08-25T00:00:00.000Z",
  updated_at: "2026-08-25T00:00:00Z",
};
const { provider: _missingProvider, ...summaryMissingProvider } = jobSummary;

describe("workflow contract POST responses", () => {
  it("passes the terminal job shape through unchanged", () => {
    expect(parseReviewJobResponse(jobReview).result.review_id).toBe("review-9");
    expect(parseExportJobResponse(jobExport).result.export_id).toBe("export-9");
  });

  it("rejects the retired Python response shapes instead of normalizing them", () => {
    const retiredReview = {
      id: "review-1",
      project_id: "project-1",
      snapshot_id: "snapshot-1",
      provider: "mock",
      model: "deterministic-story-v1",
      summary: "Snapshot review.",
      created_at: "2026-08-25T00:00:00.000Z",
      issues: [],
    };
    expect(() => parseReviewJobResponse(retiredReview)).toThrow();
  });
});

describe("workflow contract jobs page", () => {
  it("parses exactly the twelve summary fields and a nullable next cursor", () => {
    expect(parseJobs({ jobs: [jobSummary], next_cursor: "cursor-2" })).toEqual({
      jobs: [jobSummary],
      next_cursor: "cursor-2",
    });
    expect(parseJobs({ jobs: [], next_cursor: null })).toEqual({ jobs: [], next_cursor: null });
  });

  it("accepts the string variants of nullable summary fields", () => {
    const summary = {
      ...jobSummary,
      document_id: "document-1",
      error: "Import failed.",
      retry_of_job_id: "job-original",
    };
    expect(parseJobs({ jobs: [summary], next_cursor: null }).jobs).toEqual([summary]);
  });

  it.each([
    ["missing field", summaryMissingProvider],
    ["wrong nullable field", { ...jobSummary, error: 4 }],
    ["unknown kind", { ...jobSummary, kind: "other" }],
    ["unknown operation", { ...jobSummary, operation: "other" }],
    ["unknown status", { ...jobSummary, status: "other" }],
    ["non-UTC timestamp", { ...jobSummary, created_at: "2026-08-25T00:00:00+08:00" }],
    ["invalid timestamp", { ...jobSummary, updated_at: "2026-02-30T00:00:00Z" }],
    ["full Job fields", { ...jobSummary, request: {}, result: {}, events: [] }],
  ])("rejects a %s in a summary", (_label, summary) => {
    expect(() => parseJobs({ jobs: [summary], next_cursor: null })).toThrow();
  });

  it.each([{ jobs: [] }, { jobs: [], next_cursor: 4 }])(
    "rejects a missing or invalid next cursor: %o",
    (payload) => {
      expect(() => parseJobs(payload)).toThrow("Invalid jobs response.next_cursor");
    },
  );
});

describe("workflow contract complete Job", () => {
  it("keeps request, result, and events required on terminal responses", () => {
    expect(parseJob(jobReview)).toEqual(parseReviewJobResponse(jobReview));
    for (const field of ["request", "result", "events"] as const) {
      const incomplete = { ...jobReview };
      delete incomplete[field];
      expect(() => parseJob(incomplete)).toThrow();
    }
  });
});
