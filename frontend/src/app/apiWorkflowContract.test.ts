import { describe, expect, it } from "vitest";

import {
  parseExportJobResponse,
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
  it("requires a nullable next cursor", () => {
    expect(parseJobs({ jobs: [jobReview], next_cursor: "cursor-2" })).toEqual({
      jobs: [parseReviewJobResponse(jobReview)],
      next_cursor: "cursor-2",
    });
    expect(parseJobs({ jobs: [], next_cursor: null })).toEqual({ jobs: [], next_cursor: null });
  });

  it.each([{ jobs: [] }, { jobs: [], next_cursor: 4 }])(
    "rejects a missing or invalid next cursor: %o",
    (payload) => {
      expect(() => parseJobs(payload)).toThrow("Invalid jobs response.next_cursor");
    },
  );
});
