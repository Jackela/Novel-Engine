/**
 * The observability snapshot behind `GET /metrics` (DR-041): process facts
 * plus store counters. The port is deliberately small — counts only, never a
 * secret, a manuscript body, or a raw configuration value — so rendering it
 * can never leak one.
 */
export interface MetricsSnapshot {
  /** Seconds since this server process started. */
  readonly uptimeSeconds: number;
  /** Resident set size of the server process, in bytes. */
  readonly residentMemoryBytes: number;
  /** Used V8 heap of the server process, in bytes. */
  readonly heapUsedBytes: number;
  /** Documents in the content authority (0 without a configured database). */
  readonly documents: number;
  /** Immutable revisions in the content authority. */
  readonly revisions: number;
  /** Job counts keyed by persisted status. */
  readonly jobsByStatus: Readonly<Record<string, number>>;
  /** Provider prompt tokens recorded for completed attempts. */
  readonly promptTokens: number;
  /** Provider completion tokens recorded for completed attempts. */
  readonly completionTokens: number;
  /** Recorded provider attempts, completed or failed. */
  readonly usageRequests: number;
}

/**
 * Collects one snapshot per scrape. Failure semantics: a probe that cannot
 * read its counters must throw — the route answers the unified error
 * envelope instead of publishing a fabricated zero.
 */
export type MetricsProbe = () => MetricsSnapshot;
