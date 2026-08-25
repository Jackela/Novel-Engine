import { describe, expect, it } from 'vitest';

import { parseExportJobResponse, parseReviewJobResponse } from '@/app/apiWorkflowContract';

const legacyReview = {
  id: 'review-1',
  project_id: 'project-1',
  snapshot_id: 'snapshot-1',
  provider: 'mock',
  model: 'deterministic-story-v1',
  summary: 'Snapshot review.',
  created_at: '2026-08-25T00:00:00.000Z',
  issues: [],
};

const jobReview = {
  id: 'job-1',
  project_id: 'project-1',
  document_id: null,
  kind: 'review',
  operation: 'review',
  status: 'completed',
  provider: 'mock',
  model: 'deterministic-story-v1',
  request: {},
  result: { review_id: 'review-9', snapshot_id: 'snapshot-9', summary: 'S' },
  error: null,
  retry_of_job_id: null,
  created_at: '2026-08-25T00:00:00.000Z',
  updated_at: '2026-08-25T00:00:00.000Z',
  events: [],
};

const legacyExport = {
  id: 'export-1',
  project_id: 'project-1',
  snapshot_id: 'snapshot-1',
  format: 'epub',
  size_bytes: 128,
  checksum_sha256: 'abc',
  created_at: '2026-08-25T00:00:00.000Z',
  download_url: '/api/projects/project-1/exports/export-1/download',
};

const jobExport = {
  ...jobReview,
  kind: 'export',
  operation: 'export',
  provider: 'studio',
  model: '',
  result: { export_id: 'export-9', snapshot_id: 'snapshot-9', format: 'epub' },
};

describe('workflow contract dual-shape POST responses', () => {
  it('passes the terminal job shape through unchanged', () => {
    expect(parseReviewJobResponse(jobReview).result.review_id).toBe('review-9');
    expect(parseExportJobResponse(jobExport).result.export_id).toBe('export-9');
  });

  it('normalizes the legacy Python review shape to a completed job', () => {
    const job = parseReviewJobResponse(legacyReview);
    expect(job.id).toBe('review-1');
    expect(job.kind).toBe('review');
    expect(job.status).toBe('completed');
    expect(job.result.review_id).toBe('review-1');
    expect(job.events).toEqual([]);
  });

  it('normalizes the legacy Python export shape to a completed job', () => {
    const job = parseExportJobResponse(legacyExport);
    expect(job.id).toBe('export-1');
    expect(job.kind).toBe('export');
    expect(job.status).toBe('completed');
    expect(job.result.export_id).toBe('export-1');
  });
});
