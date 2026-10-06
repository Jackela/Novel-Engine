import { reduceFtsQueryElements, restoreFtsDisplayText } from "../domain/fts_segmentation.js";

/**
 * Safe FTS5 MATCH expression builder. User input is reduced to case-folded
 * match elements — one per Latin word, one character phrase per CJK run (see
 * fts_segmentation) — de-duplicated preserving first occurrence, capped at
 * three, then each element is quoted and the elements are joined with AND
 * semantics. FTS5 operators, column filters, NEAR groups, wildcards, and
 * punctuation never cross this boundary. The cap is three (DR-030): every
 * additional AND element widens the ranked match set bm25 must score, so
 * eight-element adversarial queries measured 453–970ms of synchronous loop
 * freeze over a 6MiB corpus, while three elements measured ~71ms.
 */

const MAX_MATCH_ELEMENTS = 3;

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

/**
 * The first reduced element in display form (DR-029): Han phrase separators
 * are removed, so the term reads as plain text and can be located inside a
 * document body by the editor's find machinery. The first element is the
 * honest locator — AND semantics guarantee every element matches the row,
 * but only one plain term can be handed to a text search — and it is null
 * exactly when `buildFtsMatchQuery` is null (same reduction input).
 */
export function buildFtsLocateTerm(query: string): string | null {
  const [first] = new Set(reduceFtsQueryElements(query.toLowerCase()));
  return first === undefined ? null : restoreFtsDisplayText(first);
}
