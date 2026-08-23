/**
 * Safe FTS5 MATCH expression builder — the twin of the Python authority's
 * `_build_fts5_match_query`. User input is reduced to case-folded word
 * tokens, de-duplicated preserving first occurrence, capped at eight, then
 * each token is quoted and the tokens are joined with AND semantics.
 * FTS5 operators, column filters, NEAR groups, wildcards, and punctuation
 * never cross this boundary.
 */

/** Unicode word tokens, the `\w+` twin (letters, digits, underscore). */
const FTS_TOKEN_PATTERN = /[\p{L}\p{N}_]+/gu;

export const MAX_MATCH_TOKENS = 8;

/**
 * `toLowerCase` is the deliberate JS stand-in for Python's `casefold()`:
 * it matches FTS5's unicode61 tokenizer folding, which does not expand
 * ligatures like ß either, so quoted tokens stay findable.
 */
export function buildFtsMatchQuery(query: string): string | null {
  const tokens = query.toLowerCase().match(FTS_TOKEN_PATTERN);
  if (tokens === null) {
    return null;
  }
  const unique = [...new Set(tokens)].slice(0, MAX_MATCH_TOKENS);
  return unique.map((token) => `"${token}"`).join(" ");
}
