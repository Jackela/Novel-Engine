const DECIMAL_INTEGER = /^(0|[1-9]\d*)$/;

/** Reject a usage-ledger value that cannot be represented exactly by the public number contract. */
export function assertSafeUsageToken(value: number, label: string): void {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new RangeError(`${label} token count must be a non-negative safe integer.`);
  }
}

/** Parse an exact decimal aggregate returned by SQLite without crossing a floating-point boundary. */
export function safeUsageAggregate(value: unknown, label: string): number {
  if (typeof value !== "string" || !DECIMAL_INTEGER.test(value)) {
    throw new Error(`${label} usage aggregate is not an exact non-negative integer.`);
  }
  const parsed = Number(value);
  assertSafeUsageToken(parsed, label);
  return parsed;
}

/** Add exact non-negative counts while preserving the public safe-integer invariant. */
export function addSafeUsage(total: number, value: number, label: string): number {
  assertSafeUsageToken(total, label);
  assertSafeUsageToken(value, label);
  const result = total + value;
  assertSafeUsageToken(result, label);
  return result;
}
