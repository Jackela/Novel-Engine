/** Exact Unicode-aware word count retained with each immutable revision. */
export function revisionWordCount(markdown: string): number {
  return markdown.match(/[\p{L}\p{N}_'-]+/gu)?.length ?? 0;
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
