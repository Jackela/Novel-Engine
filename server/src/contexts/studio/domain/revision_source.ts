import { REVISION_SOURCES, type RevisionSource } from "./kinds.js";

/** Internal persistence invariant failure; HTTP deliberately keeps it opaque. */
export class RevisionSourceInvariantError extends Error {
  constructor() {
    super("Stored revision source is invalid.");
    this.name = "RevisionSourceInvariantError";
  }
}

/** Refuse missing or unknown stored workflow state instead of publishing an open string. */
export function assertStoredRevisionSource(value: string | null): RevisionSource {
  const source = REVISION_SOURCES.find((candidate) => candidate === value);
  if (source === undefined) throw new RevisionSourceInvariantError();
  return source;
}
