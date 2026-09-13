/**
 * Shared engine for the per-port branded page-limit trios (#536): each port
 * keeps its own distinct nominal brand (a `unique symbol` alias), its named
 * MIN/MAX constants, and a one-line validator that delegates here, so the
 * integer-range check, the exact RangeError wording, and the brand assertion
 * live in one place.
 */

/** Bounds and message subject of one port's page-limit validation. */
export interface PageLimitRules {
  /** Inclusive lower bound of one page's row budget. */
  readonly min: number;
  /** Inclusive upper bound of one page's row budget. */
  readonly max: number;
  /** Resource name opening the error, e.g. `"Export"` for export pages. */
  readonly subject: string;
}

/**
 * Validate one page-limit number and assert the caller's branded page-limit
 * type: the value must be an integer within `[min, max]`, otherwise a
 * RangeError with the port's exact message is thrown. The validated input is
 * returned unchanged so each port can expose it under its own distinct
 * nominal brand instead of a bare number.
 */
export function pageLimit<Brand extends number>(value: number, rules: PageLimitRules): Brand {
  const { min, max, subject } = rules;
  if (!Number.isInteger(value) || value < min || value > max) {
    throw new RangeError(`${subject} page limit must be an integer from ${min} through ${max}.`);
  }
  return value as Brand;
}
