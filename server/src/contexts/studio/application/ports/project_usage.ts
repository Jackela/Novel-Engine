/** Per-model aggregate row of the usage ledger (#317). */
export interface ProjectUsageBreakdownEntry {
  model: string;
  requests: number;
  promptTokens: number;
  completionTokens: number;
}

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
