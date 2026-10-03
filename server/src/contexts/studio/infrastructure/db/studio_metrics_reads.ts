import type Database from "better-sqlite3";

/**
 * Store counters for `GET /metrics` (DR-041): fixed aggregate reads over the
 * content authority — documents, immutable revisions, jobs by status, and the
 * usage ledger's request/token totals. Only counts and sums leave this
 * module; no row content, no configuration, no credential is selected, so a
 * scrape cannot expose one. A missing aggregate row is a driver anomaly and
 * raises instead of degrading to a fabricated zero.
 */
export interface StudioMetricsCounts {
  readonly documents: number;
  readonly revisions: number;
  readonly jobsByStatus: Readonly<Record<string, number>>;
  readonly promptTokens: number;
  readonly completionTokens: number;
  readonly usageRequests: number;
}

export function readStudioMetricsCounts(raw: Database.Database): StudioMetricsCounts {
  const jobsByStatus: Record<string, number> = {};
  const jobRows = raw
    .prepare("SELECT status, COUNT(*) AS n FROM jobs GROUP BY status")
    .all() as Array<{ status: string; n: number }>;
  for (const row of jobRows) {
    jobsByStatus[row.status] = row.n;
  }
  return {
    documents: scalar(raw, "SELECT COUNT(*) AS n FROM documents"),
    revisions: scalar(raw, "SELECT COUNT(*) AS n FROM document_revisions"),
    jobsByStatus,
    // Token totals fold completed attempts only, matching the usage
    // aggregation's own rule (a failed attempt contributes zeros).
    ...usageTotals(raw),
  };
}

function scalar(raw: Database.Database, statement: string): number {
  const row = raw.prepare(statement).get() as { n: number } | undefined;
  if (row === undefined) {
    throw new Error(`Metrics aggregate returned no row: ${statement}`);
  }
  return row.n;
}

function usageTotals(raw: Database.Database): {
  promptTokens: number;
  completionTokens: number;
  usageRequests: number;
} {
  const row = raw
    .prepare(
      `SELECT COUNT(*) AS requests,
              COALESCE(SUM(CASE WHEN outcome = 'completed' THEN prompt_tokens ELSE 0 END), 0) AS prompt_tokens,
              COALESCE(SUM(CASE WHEN outcome = 'completed' THEN completion_tokens ELSE 0 END), 0) AS completion_tokens
       FROM usage_events`,
    )
    .get() as { requests: number; prompt_tokens: number; completion_tokens: number } | undefined;
  if (row === undefined) {
    throw new Error("Metrics usage aggregate returned no row.");
  }
  return {
    usageRequests: row.requests,
    promptTokens: row.prompt_tokens,
    completionTokens: row.completion_tokens,
  };
}
