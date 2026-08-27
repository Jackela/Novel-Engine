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

/** An immutable snapshot still references the requested document. */
export class SnapshotConflict extends Error {
  constructor() {
    super("Document is referenced by an immutable snapshot.");
    this.name = "SnapshotConflict";
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

/** A volume with the same (project, title) identity already exists. */
export class DuplicateVolumeError extends Error {
  readonly title: string;

  constructor(title: string) {
    super(`A volume titled "${title}" already exists in this project.`);
    this.name = "DuplicateVolumeError";
    this.title = title;
  }
}

/** The same synchronous pipeline operation is already running for this target. */
export class OperationInFlightError extends Error {
  readonly projectId: string;
  readonly documentId: string | null;
  readonly operation: string;

  constructor(projectId: string, documentId: string | null, operation: string) {
    super(
      documentId === null
        ? `The ${operation} operation is already running for this project.`
        : `The ${operation} operation is already running for this document.`,
    );
    this.name = "OperationInFlightError";
    this.projectId = projectId;
    this.documentId = documentId;
    this.operation = operation;
  }
}
