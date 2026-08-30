import type { UsageDailyBucket } from "@/app/types/studio";

const formatCount = (value: number) => value.toLocaleString("en-US");

function dailyTotal(bucket: UsageDailyBucket): number {
  return bucket.prompt_tokens + bucket.completion_tokens;
}

function UsageDailyRow({ bucket, max }: { bucket: UsageDailyBucket; max: number }) {
  const total = dailyTotal(bucket);
  const width = max > 0 ? `${Math.max((total / max) * 100, total > 0 ? 2 : 0)}%` : "0%";
  return (
    <div className="usage__daily-row">
      <span className="usage__daily-date">{bucket.date}</span>
      <span
        aria-label={`${bucket.date}: ${formatCount(total)} tokens`}
        className="usage__daily-bar-track"
        role="img"
      >
        <span className="usage__daily-bar" style={{ width }} />
      </span>
      <span className="usage__daily-count">{formatCount(total)}</span>
    </div>
  );
}

interface UsageDailyBarsProps {
  buckets: UsageDailyBucket[];
}

/**
 * Trailing-30-day daily usage (#384): one pure-CSS width bar per UTC day,
 * oldest first, token totals with thousands separators.
 */
export function UsageDailyBars({ buckets }: UsageDailyBarsProps) {
  const max = Math.max(...buckets.map(dailyTotal), 0);
  return (
    <section aria-label="Daily usage, last 30 days" className="usage__daily">
      <h3>Last 30 days</h3>
      {buckets.map((bucket) => (
        <UsageDailyRow key={bucket.date} bucket={bucket} max={max} />
      ))}
    </section>
  );
}
