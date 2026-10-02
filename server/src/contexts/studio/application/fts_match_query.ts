import { reduceFtsQueryElements } from "../domain/fts_segmentation.js";

/**
 * Safe FTS5 MATCH expression builder. User input is reduced to case-folded
 * match elements — one per Latin word, one character phrase per CJK run (see
 * fts_segmentation) — de-duplicated preserving first occurrence, capped at
 * eight, then each element is quoted and the elements are joined with AND
 * semantics. FTS5 operators, column filters, NEAR groups, wildcards, and
 * punctuation never cross this boundary.
 */

const MAX_MATCH_ELEMENTS = 8;

/**
 * `toLowerCase` (not the stronger `casefold` folding) is deliberate: it
 * matches FTS5's unicode61 tokenizer folding, which does not expand
 * ligatures like ß either, so quoted tokens stay findable.
 */
export function buildFtsMatchQuery(query: string): string | null {
  const elements = reduceFtsQueryElements(query.toLowerCase());
  if (elements.length === 0) {
    return null;
  }
  const unique = [...new Set(elements)].slice(0, MAX_MATCH_ELEMENTS);
  return unique.map((element) => `"${element}"`).join(" ");
}
