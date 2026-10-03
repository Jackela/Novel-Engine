/**
 * Usage accounting types for `GET /api/projects/:projectId/usage` (#377,
 * DR-028): completed attempts fold into the token totals, failures are
 * reported separately, and `estimated_*` counts name the rows whose numbers
 * include a provider-unreported word-count estimate.
 */

/** Per-model aggregate row of `GET /api/projects/:projectId/usage`. */
export interface UsageModelRow {
  model: string;
  /** Completed attempts; the token fields below fold these rows only. */
  requests: number;
  /** Failed provider attempts, counted outside the token totals (DR-028). */
  failed_attempts: number;
  /** Completed attempts whose counts include a word-count estimate (DR-028). */
  estimated_requests: number;
  prompt_tokens: number;
  completion_tokens: number;
}

/** One UTC day of the trailing-30-day usage window (#384, DR-028). */
export interface UsageDailyBucket {
  date: string;
  /** Completed attempts of that day; failures are reported separately. */
  request_count: number;
  prompt_tokens: number;
  completion_tokens: number;
}

/** Project-level cumulative AI usage (matching the generated api contract). */
export interface ProjectUsage {
  project_id: string;
  /** Completed provider attempts — the rows every token total folds (DR-028). */
  request_count: number;
  /** Provider attempts that failed without reported usage (DR-028). */
  failed_attempt_count: number;
  /** Completed attempts whose counts include a provider-unreported estimate (DR-028). */
  estimated_requests: number;
  prompt_tokens: number;
  completion_tokens: number;
  per_model: UsageModelRow[];
  daily?: UsageDailyBucket[];
}
