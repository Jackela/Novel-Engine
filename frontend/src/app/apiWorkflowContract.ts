import type {
  ExportFormat,
  Review,
  ReviewIssue,
  StudioExport,
  StudioJob,
  StudioJobEvent,
  StudioJobKind,
  StudioJobOperation,
  StudioJobStatus,
} from '@/app/types/studio';

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
} from '@/app/apiContract';

const exportFormats = ['markdown', 'docx', 'epub'] as const;
const jobKinds = ['proposal', 'review', 'export'] as const;
const jobOperations = ['continue', 'rewrite', 'generate', 'review', 'export'] as const;
const jobStatuses = ['pending', 'running', 'completed', 'failed', 'interrupted'] as const;
const severities = ['blocker', 'warning', 'suggestion'] as const;

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
    id: stringField(item, 'id', label),
    document_id: nullableStringField(item, 'document_id', label),
    severity: literalField(item, 'severity', label, severities),
    code: stringField(item, 'code', label),
    message: stringField(item, 'message', label),
    suggestion: stringField(item, 'suggestion', label),
    evidence: recordField(item, 'evidence', label),
  };
}

export function parseReview(value: unknown, label = 'review'): Review {
  const item = objectValue(value, label);
  return {
    id: stringField(item, 'id', label),
    project_id: stringField(item, 'project_id', label),
    snapshot_id: stringField(item, 'snapshot_id', label),
    provider: stringField(item, 'provider', label),
    model: stringField(item, 'model', label),
    summary: stringField(item, 'summary', label),
    created_at: stringField(item, 'created_at', label),
    issues: arrayField(item, 'issues', label, (issue, index) =>
      parseIssue(issue, `${label}.issues[${index}]`),
    ),
  };
}

export function parseReviews(value: unknown): { reviews: Review[] } {
  const item = objectValue(value, 'reviews response');
  return {
    reviews: arrayField(item, 'reviews', 'reviews response', (entry, index) =>
      parseReview(entry, `reviews[${index}]`),
    ),
  };
}

function parseJobEvent(value: unknown, label: string): StudioJobEvent {
  const item = objectValue(value, label);
  return {
    id: stringField(item, 'id', label),
    status: literalField(item, 'status', label, jobStatuses) as StudioJobStatus,
    details: recordField(item, 'details', label),
    created_at: stringField(item, 'created_at', label),
  };
}

export function parseJob(value: unknown, label = 'job'): StudioJob {
  const item = objectValue(value, label);
  const result = recordField(item, 'result', label);
  return {
    id: stringField(item, 'id', label),
    project_id: stringField(item, 'project_id', label),
    document_id: nullableStringField(item, 'document_id', label),
    kind: literalField(item, 'kind', label, jobKinds) as StudioJobKind,
    operation: literalField(item, 'operation', label, jobOperations) as StudioJobOperation,
    status: literalField(item, 'status', label, jobStatuses) as StudioJobStatus,
    provider: stringField(item, 'provider', label),
    model: stringField(item, 'model', label),
    request: recordField(item, 'request', label),
    result: {
      proposal_markdown: optionalString(
        result,
        'proposal_markdown',
        `${label}.result.proposal_markdown`,
      ),
      base_revision_id: optionalString(
        result,
        'base_revision_id',
        `${label}.result.base_revision_id`,
      ),
      accepted_revision_id:
        result.accepted_revision_id === undefined
          ? undefined
          : nullableString(result.accepted_revision_id, `${label}.result.accepted_revision_id`),
    },
    error: nullableStringField(item, 'error', label),
    retry_of_job_id: nullableStringField(item, 'retry_of_job_id', label),
    events: arrayField(item, 'events', label, (event, index) =>
      parseJobEvent(event, `${label}.events[${index}]`),
    ),
    created_at: stringField(item, 'created_at', label),
    updated_at: stringField(item, 'updated_at', label),
  };
}

export function parseJobs(value: unknown): { jobs: StudioJob[] } {
  const item = objectValue(value, 'jobs response');
  return {
    jobs: arrayField(item, 'jobs', 'jobs response', (entry, index) =>
      parseJob(entry, `jobs[${index}]`),
    ),
  };
}

export function parseExport(value: unknown, label = 'export'): StudioExport {
  const item = objectValue(value, label);
  return {
    id: stringField(item, 'id', label),
    project_id: stringField(item, 'project_id', label),
    snapshot_id: stringField(item, 'snapshot_id', label),
    format: literalField(item, 'format', label, exportFormats) as ExportFormat,
    size_bytes: numberField(item, 'size_bytes', label),
    checksum_sha256: stringField(item, 'checksum_sha256', label),
    created_at: stringField(item, 'created_at', label),
    download_url: stringField(item, 'download_url', label),
  };
}

export function parseExports(value: unknown): { exports: StudioExport[] } {
  const item = objectValue(value, 'exports response');
  return {
    exports: arrayField(item, 'exports', 'exports response', (entry, index) =>
      parseExport(entry, `exports[${index}]`),
    ),
  };
}
