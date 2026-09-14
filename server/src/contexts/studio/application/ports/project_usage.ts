/** Per-model aggregate row of the usage ledger (#317). */
interface ProjectUsageBreakdownEntry {
  model: string;
  requests: number;
  promptTokens: number;
  completionTokens: number;
}

/**
 * The trailing-UTC-day count of `daily` (#384). The writing-statistics day
 * rows (#653) reuse the same window so both surfaces' day keys stay
 * aligned — one constant, never two.
 */
export const USAGE_DAILY_WINDOW_DAYS = 30;

/** One UTC day of usage in the trailing-30-day window (#384). */
export interface ProjectUsageDailyBucket {
  /** UTC calendar day, `YYYY-MM-DD`. */
  date: string;
  requestCount: number;
  promptTokens: number;
  completionTokens: number;
}

/** The aggregated AI usage ledger of one project (#317, #384). */
export interface ProjectUsageAggregate {
  projectId: string;
  requestCount: number;
  promptTokens: number;
  completionTokens: number;
  perModel: ProjectUsageBreakdownEntry[];
  /** The last 30 UTC days (today included), zero-filled (#384). */
  daily: ProjectUsageDailyBucket[];
}
