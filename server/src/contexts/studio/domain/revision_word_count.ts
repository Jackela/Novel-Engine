const HAN_CHARACTER = /\p{Script=Han}/gu;
const WORD_RUN = /[\p{L}\p{N}_'-]+/gu;

/**
 * Exact unified word count retained with each immutable revision. One word is
 * either a single Han-script character (counted individually, code point by
 * code point, so punctuation-delimited Chinese prose never collapses into one
 * "word") or one maximal run of non-Han word characters — letters, digits,
 * underscores, apostrophes, or hyphens — matching the established Unicode
 * run semantics for other scripts. Han characters separate adjacent runs, so
 * mixed English/Chinese text sums both sides. Punctuation, whitespace, and
 * unmatched characters count as nothing; the function is total, returns 0 for
 * empty input, and never throws.
 */
export function revisionWordCount(markdown: string): number {
  const hanCount = markdown.match(HAN_CHARACTER)?.length ?? 0;
  const runCount = markdown.replace(HAN_CHARACTER, " ").match(WORD_RUN)?.length ?? 0;
  return hanCount + runCount;
}

/** Internal persistence invariant failure; HTTP deliberately treats it as unexpected. */
export class RevisionWordCountInvariantError extends Error {
  constructor() {
    super("Stored revision word count is invalid.");
    this.name = "RevisionWordCountInvariantError";
  }
}

/** Refuse missing or corrupt stored evidence instead of publishing a placeholder. */
export function assertStoredRevisionWordCount(value: number | null): number {
  if (!Number.isSafeInteger(value) || value === null || value < 0) {
    throw new RevisionWordCountInvariantError();
  }
  return value;
}
