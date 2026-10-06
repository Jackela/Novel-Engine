/** Per-model aggregate row of the usage ledger (#317, DR-028). */
interface ProjectUsageBreakdownEntry {
  model: string;
  /** Completed provider attempts; the token totals below fold these rows only. */
  requests: number;
  /** Provider attempts that failed without reported usage (DR-028). */
  failedAttempts: number;
  /** Completed attempts whose counts include a word-count estimate (DR-028). */
  estimatedRequests: number;
  promptTokens: number;
  completionTokens: number;
}

/**
 * The trailing-UTC-day count of `daily` (#384). The writing-statistics day
 * rows (#653) reuse the same window so both surfaces' day keys stay
 * aligned — one constant, never two.
 */
export const USAGE_DAILY_WINDOW_DAYS = 30;

/** One UTC day of usage in the trailing-30-day window (#384, DR-028). */
export interface ProjectUsageDailyBucket {
  /** UTC calendar day, `YYYY-MM-DD`. */
  date: string;
  /** Completed provider attempts of that day; failures are counted separately. */
  requestCount: number;
  promptTokens: number;
  completionTokens: number;
}

/**
 * The aggregated AI usage ledger of one project (#317, #384, DR-028): token
 * totals fold `completed` usage rows only, failed provider attempts are
 * reported as their own count instead of disappearing, and estimated token
 * counts are disclosed rather than presented as provider reports.
 */
export interface ProjectUsageAggregate {
  projectId: string;
  /** Completed provider attempts — the rows every token total below folds. */
  requestCount: number;
  /** Provider attempts that failed and carry no token counts (DR-028). */
  failedAttemptCount: number;
  /** Completed attempts whose counts include a word-count estimate (DR-028). */
  estimatedRequestCount: number;
  promptTokens: number;
  completionTokens: number;
  perModel: ProjectUsageBreakdownEntry[];
  /** The last 30 UTC days (today included), zero-filled (#384). */
  daily: ProjectUsageDailyBucket[];
}
