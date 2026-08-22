/**
 * A resource is not visible to the active principal: unknown ids and
 * cross-principal lookups are indistinguishable by design.
 */
export class NotFoundError extends Error {
  constructor(message = "Resource not found.") {
    super(message);
    this.name = "NotFoundError";
  }
}

/**
 * A save was based on a revision that is no longer the document's current
 * revision; no revision may be created, overwritten, or merged.
 */
export class RevisionConflictError extends Error {
  readonly currentRevisionId: string | null;

  constructor(currentRevisionId: string | null) {
    super("Document changed since the requested base revision.");
    this.name = "RevisionConflictError";
    this.currentRevisionId = currentRevisionId;
  }
}

/** A document with the same (project, kind, title) identity already exists. */
export class DuplicateDocumentError extends Error {
  readonly kind: string;
  readonly title: string;

  constructor(kind: string, title: string) {
    super(`A ${kind} document titled "${title}" already exists in this project.`);
    this.name = "DuplicateDocumentError";
    this.kind = kind;
    this.title = title;
  }
}
