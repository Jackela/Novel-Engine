import {
  arrayField,
  literalField,
  nullableString,
  nullableStringField,
  numberField,
  objectValue,
  recordField,
  stringField,
  stringValue,
} from "@/app/apiContract";
import type {
  ExportFormat,
  ProjectUsage,
  Review,
  ReviewIssue,
  ReviewSummary,
  ReviewsPage,
  StudioExport,
  StudioJob,
  StudioJobEvent,
  StudioJobKind,
  StudioJobOperation,
  StudioJobStatus,
  StudioJobSummary,
  StudioJobSummaryKind,
  StudioJobSummaryOperation,
  UsageModelRow,
} from "@/app/types/studio";

const exportFormats = ["markdown", "docx", "epub"] as const;
const jobKinds = ["proposal", "review", "export"] as const;
const jobOperations = ["continue", "rewrite", "generate", "review", "export"] as const;
const jobStatuses = ["pending", "running", "completed", "failed", "interrupted"] as const;
const jobSummaryKinds = [...jobKinds, "import"] as const;
const jobSummaryOperations = [...jobOperations, "import"] as const;
const jobSummaryFields = [
  "id",
  "project_id",
  "document_id",
  "kind",
  "operation",
  "status",
  "provider",
  "model",
  "error",
  "retry_of_job_id",
  "created_at",
  "updated_at",
] as const;
const jobSummaryFieldSet = new Set<string>(jobSummaryFields);
const isoUtcTimestamp = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?Z$/;
const severities = ["blocker", "warning", "suggestion"] as const;

function isoUtcStringField(source: Record<string, unknown>, key: string, parent: string): string {
  const value = stringField(source, key, parent);
  const match = isoUtcTimestamp.exec(value);
  const parsed = new Date(value);
  if (
    match === null ||
    Number.isNaN(parsed.getTime()) ||
    parsed.getUTCFullYear() !== Number(match[1]) ||
    parsed.getUTCMonth() + 1 !== Number(match[2]) ||
    parsed.getUTCDate() !== Number(match[3]) ||
    parsed.getUTCHours() !== Number(match[4]) ||
    parsed.getUTCMinutes() !== Number(match[5]) ||
    parsed.getUTCSeconds() !== Number(match[6])
  ) {
    throw new Error(`Invalid ${parent}.${key}`);
  }
  return value;
}

function parseJobSummary(value: unknown, label: string): StudioJobSummary {
  const item = objectValue(value, label);
  const fields = Object.keys(item);
  if (
    fields.length !== jobSummaryFields.length ||
    fields.some((key) => !jobSummaryFieldSet.has(key))
  ) {
    throw new Error(`Invalid ${label}`);
  }
  return {
    id: stringField(item, "id", label),
    project_id: stringField(item, "project_id", label),
    document_id: nullableStringField(item, "document_id", label),
    kind: literalField(item, "kind", label, jobSummaryKinds) as StudioJobSummaryKind,
    operation: literalField(
      item,
      "operation",
      label,
      jobSummaryOperations,
    ) as StudioJobSummaryOperation,
    status: literalField(item, "status", label, jobStatuses) as StudioJobStatus,
    provider: stringField(item, "provider", label),
    model: stringField(item, "model", label),
    error: nullableStringField(item, "error", label),
    retry_of_job_id: nullableStringField(item, "retry_of_job_id", label),
    created_at: isoUtcStringField(item, "created_at", label),
    updated_at: isoUtcStringField(item, "updated_at", label),
  };
}

function optionalString(
  source: Record<string, unknown>,
  key: string,
  label: string,
): string | undefined {
  const value = source[key];
  return value === undefined ? undefined : stringValue(value, label);
}

function parseIssue(value: unknown, label: string): ReviewIssue {
  const item = objectValue(value, label);
  return {
    id: stringField(item, "id", label),
    document_id: nullableStringField(item, "document_id", label),
    severity: literalField(item, "severity", label, severities),
    code: stringField(item, "code", label),
    message: stringField(item, "message", label),
    suggestion: stringField(item, "suggestion", label),
    evidence: recordField(item, "evidence", label),
  };
}

function parseReviewSummary(value: unknown, label: string): ReviewSummary {
  const item = objectValue(value, label);
  return {
    id: stringField(item, "id", label),
    project_id: stringField(item, "project_id", label),
    snapshot_id: stringField(item, "snapshot_id", label),
    provider: stringField(item, "provider", label),
    model: stringField(item, "model", label),
    summary: stringField(item, "summary", label),
    issue_count: numberField(item, "issue_count", label),
    created_at: isoUtcStringField(item, "created_at", label),
  };
}

export function parseReviews(value: unknown): ReviewsPage {
  const item = objectValue(value, "reviews response");
  return {
    reviews: arrayField(item, "reviews", "reviews response", (entry, index) =>
      parseReviewSummary(entry, `reviews[${index}]`),
    ),
    next_cursor: nullableStringField(item, "next_cursor", "reviews response"),
  };
}

export function parseReviewDetail(value: unknown, label = "review detail"): Review {
  const item = objectValue(value, label);
  return {
    id: stringField(item, "id", label),
    project_id: stringField(item, "project_id", label),
    snapshot_id: stringField(item, "snapshot_id", label),
    provider: stringField(item, "provider", label),
    model: stringField(item, "model", label),
    summary: stringField(item, "summary", label),
    created_at: stringField(item, "created_at", label),
    issues: arrayField(item, "issues", label, (issue, index) =>
      parseIssue(issue, `${label}.issues[${index}]`),
    ),
  };
}

function parseJobEvent(value: unknown, label: string): StudioJobEvent {
  const item = objectValue(value, label);
  return {
    id: stringField(item, "id", label),
    status: literalField(item, "status", label, jobStatuses) as StudioJobStatus,
    details: recordField(item, "details", label),
    created_at: stringField(item, "created_at", label),
  };
}

export function parseJob(value: unknown, label = "job"): StudioJob {
  const item = objectValue(value, label);
  const result = recordField(item, "result", label);
  return {
    id: stringField(item, "id", label),
    project_id: stringField(item, "project_id", label),
    document_id: nullableStringField(item, "document_id", label),
    kind: literalField(item, "kind", label, jobKinds) as StudioJobKind,
    operation: literalField(item, "operation", label, jobOperations) as StudioJobOperation,
    status: literalField(item, "status", label, jobStatuses) as StudioJobStatus,
    provider: stringField(item, "provider", label),
    model: stringField(item, "model", label),
    request: recordField(item, "request", label),
    result: {
      proposal_markdown: optionalString(
        result,
        "proposal_markdown",
        `${label}.result.proposal_markdown`,
      ),
      base_revision_id: optionalString(
        result,
        "base_revision_id",
        `${label}.result.base_revision_id`,
      ),
      accepted_revision_id:
        result.accepted_revision_id === undefined
          ? undefined
          : nullableString(result.accepted_revision_id, `${label}.result.accepted_revision_id`),
      export_id: optionalString(result, "export_id", `${label}.result.export_id`),
      review_id: optionalString(result, "review_id", `${label}.result.review_id`),
    },
    error: nullableStringField(item, "error", label),
    retry_of_job_id: nullableStringField(item, "retry_of_job_id", label),
    events: arrayField(item, "events", label, (event, index) =>
      parseJobEvent(event, `${label}.events[${index}]`),
    ),
    created_at: stringField(item, "created_at", label),
    updated_at: stringField(item, "updated_at", label),
  };
}

export interface JobsPage {
  readonly jobs: StudioJobSummary[];
  readonly next_cursor: string | null;
}

export function parseJobs(value: unknown): JobsPage {
  const item = objectValue(value, "jobs response");
  return {
    jobs: arrayField(item, "jobs", "jobs response", (entry, index) =>
      parseJobSummary(entry, `jobs[${index}]`),
    ),
    next_cursor: nullableStringField(item, "next_cursor", "jobs response"),
  };
}

function parseExport(value: unknown, label = "export"): StudioExport {
  const item = objectValue(value, label);
  return {
    id: stringField(item, "id", label),
    project_id: stringField(item, "project_id", label),
    snapshot_id: stringField(item, "snapshot_id", label),
    format: literalField(item, "format", label, exportFormats) as ExportFormat,
    size_bytes: numberField(item, "size_bytes", label),
    checksum_sha256: stringField(item, "checksum_sha256", label),
    created_at: stringField(item, "created_at", label),
    download_url: stringField(item, "download_url", label),
  };
}

function parseUsageModelRow(value: unknown, label: string): UsageModelRow {
  const item = objectValue(value, label);
  return {
    model: stringField(item, "model", label),
    requests: numberField(item, "requests", label),
    prompt_tokens: numberField(item, "prompt_tokens", label),
    completion_tokens: numberField(item, "completion_tokens", label),
  };
}

export function parseUsage(value: unknown): ProjectUsage {
  const item = objectValue(value, "usage response");
  return {
    project_id: stringField(item, "project_id", "usage response"),
    request_count: numberField(item, "request_count", "usage response"),
    prompt_tokens: numberField(item, "prompt_tokens", "usage response"),
    completion_tokens: numberField(item, "completion_tokens", "usage response"),
    per_model: arrayField(item, "per_model", "usage response", (entry, index) =>
      parseUsageModelRow(entry, `per_model[${index}]`),
    ),
  };
}

export function parseExports(value: unknown): { exports: StudioExport[] } {
  const item = objectValue(value, "exports response");
  return {
    exports: arrayField(item, "exports", "exports response", (entry, index) =>
      parseExport(entry, `exports[${index}]`),
    ),
  };
}

/**
 * POST /reviews and POST /exports carry the synchronous terminal job under
 * the TS backend — the only contract since the cutover retired the Python
 * stack.
 */
export function parseReviewJobResponse(value: unknown, label = "review job response"): StudioJob {
  const item = objectValue(value, label);
  return parseJob(item, label);
}

export function parseExportJobResponse(value: unknown, label = "export job response"): StudioJob {
  const item = objectValue(value, label);
  return parseJob(item, label);
}
