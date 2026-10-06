/**
 * The browser's own day boundary (DR-045). The stats endpoint buckets its
 * daily and weekly rows on the boundary the client asks for, so a UTC+8
 * author's "today" starts at 00:00 local instead of 08:00 local.
 */

/** Every real UTC offset (UTC-12 … UTC+14), in minutes. */
const MAX_TZ_OFFSET_MINUTES = 840;

/**
 * The runtime's current offset east of UTC in whole minutes. `getTimezoneOffset`
 * answers the opposite sign (minutes to add to reach UTC) and may carry a
 * historical non-integer value, so the result is negated, rounded, and clamped
 * to the range the API accepts. Failure semantics: never throws — an
 * implausible runtime value degrades to the nearest accepted boundary instead
 * of failing the stats request.
 */
export function browserTzOffsetMinutes(): number {
  const offset = Math.round(-new Date().getTimezoneOffset());
  if (!Number.isFinite(offset)) {
    return 0;
  }
  return Math.min(MAX_TZ_OFFSET_MINUTES, Math.max(-MAX_TZ_OFFSET_MINUTES, offset));
}

/** Render an offset in minutes east of UTC as `UTC+08:00` / `UTC-05:30`. */
export function formatTzOffsetLabel(offsetMinutes: number): string {
  const sign = offsetMinutes < 0 ? "-" : "+";
  const absolute = Math.abs(Math.round(offsetMinutes));
  const hours = String(Math.floor(absolute / 60)).padStart(2, "0");
  const minutes = String(absolute % 60).padStart(2, "0");
  return `UTC${sign}${hours}:${minutes}`;
}
