import type Database from "better-sqlite3";

import { readStudioMetricsCounts } from "../../contexts/studio/infrastructure/db/studio_metrics_reads.js";
import type { MetricsProbe } from "../../shared/application/ports/metrics.js";

/**
 * Compose the `/metrics` probe (DR-041) at the composition root: the process
 * facts are always available, while the store counters come from the
 * content-authority handle when one exists (a database-free app reports
 * zeros for them rather than failing the scrape). The process start time is
 * captured once, so uptime is monotonic per app instance.
 */
export function buildMetricsProbe(
  raw: Database.Database | undefined,
  startedAt: number = Date.now(),
): MetricsProbe {
  return () => {
    const memory = process.memoryUsage();
    const counts =
      raw === undefined
        ? {
            documents: 0,
            revisions: 0,
            jobsByStatus: {},
            promptTokens: 0,
            completionTokens: 0,
            usageRequests: 0,
          }
        : readStudioMetricsCounts(raw);
    return {
      uptimeSeconds: Math.max(0, (Date.now() - startedAt) / 1000),
      residentMemoryBytes: memory.rss,
      heapUsedBytes: memory.heapUsed,
      ...counts,
    };
  };
}
