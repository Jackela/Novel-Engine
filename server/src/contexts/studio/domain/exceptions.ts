import { ERROR_CODES } from "../../../shared/domain/error_codes.js";
import {
  GENERATION_CAPACITY_RESOURCES,
  type GenerationCapacityResource,
} from "./generation_capacity_policy.js";

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

/** A Project settings command is structurally valid but invalid after normalization. */
export class InvalidProjectUpdateError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InvalidProjectUpdateError";
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

/** A captured review document/revision disappeared before its result landed. */
export class ReviewSourceInvalidatedError extends Error {
  constructor() {
    super("Review source changed before the evaluated result could be recorded.");
    this.name = "ReviewSourceInvalidatedError";
  }
}

/** A captured export document/revision disappeared before publication landed. */
export class ExportSourceInvalidatedError extends Error {
  constructor() {
    super("Export source changed before the artifact outcome could be recorded.");
    this.name = "ExportSourceInvalidatedError";
  }
}

/** A known operational filesystem failure prevented artifact publication. */
export class ExportArtifactWriteError extends Error {
  constructor() {
    super("Export artifact could not be written.");
    this.name = "ExportArtifactWriteError";
  }
}

export const EXPORT_CAPACITY_RESOURCES = Object.freeze([
  "source_documents",
  "source_bytes",
  "artifact_bytes",
  "manifest_bytes",
] as const);
export type ExportCapacityResource = (typeof EXPORT_CAPACITY_RESOURCES)[number];

/** Fixed inclusive export budgets; no request or environment override may relax them. */
export const EXPORT_CAPACITY_LIMITS = Object.freeze({
  source_documents: 65_536,
  source_bytes: 16_777_216,
  artifact_bytes: 67_108_864,
  manifest_bytes: 16_384,
} as const satisfies Readonly<Record<ExportCapacityResource, number>>);

const EXPORT_CAPACITY_RESOURCE_SET: ReadonlySet<string> = new Set(EXPORT_CAPACITY_RESOURCES);

/** A fresh export exceeded one permanent source or artifact budget. */
export class ExportCapacityExceededError extends Error {
  readonly resource: ExportCapacityResource;
  readonly limit: number;
  readonly observed: number;

  constructor(resource: ExportCapacityResource, limit: number, observed: number) {
    if (
      !EXPORT_CAPACITY_RESOURCE_SET.has(resource) ||
      !Number.isSafeInteger(limit) ||
      limit < 0 ||
      limit >= Number.MAX_SAFE_INTEGER ||
      !Number.isSafeInteger(observed) ||
      observed <= limit
    ) {
      throw new RangeError(
        "Export capacity resource and values must identify a bounded safe-integer excess.",
      );
    }
    super("Export capacity exceeded.");
    this.name = "ExportCapacityExceededError";
    this.resource = resource;
    this.limit = limit;
    this.observed = Math.min(observed, limit + 1);
  }
}

export {
  GENERATION_CAPACITY_RESOURCES,
  type GenerationCapacityResource,
} from "./generation_capacity_policy.js";

const GENERATION_CAPACITY_RESOURCE_SET: ReadonlySet<string> = new Set(
  GENERATION_CAPACITY_RESOURCES,
);

/** A complete Provider prompt exceeded the fixed application-owned byte budget. */
export class GenerationCapacityExceededError extends Error {
  readonly code = ERROR_CODES.GENERATION_CAPACITY_EXCEEDED;
  readonly resource: GenerationCapacityResource;
  readonly limit: number;
  readonly observed: number;

  constructor(resource: GenerationCapacityResource, limit: number, observed: number) {
    if (
      !GENERATION_CAPACITY_RESOURCE_SET.has(resource) ||
      !Number.isSafeInteger(limit) ||
      limit < 0 ||
      limit >= Number.MAX_SAFE_INTEGER ||
      !Number.isSafeInteger(observed) ||
      observed <= limit
    ) {
      throw new RangeError(
        "Generation capacity resource and values must identify a bounded safe-integer excess.",
      );
    }
    super("Generation capacity exceeded.");
    this.name = "GenerationCapacityExceededError";
    this.resource = resource;
    this.limit = limit;
    this.observed = Math.min(observed, limit + 1);
  }
}

export type ImportCapacityResource =
  | "story_bytes"
  | "chapter_bytes"
  | "workspace_bytes"
  | "chapter_count"
  | "directory_entries";

/** A legacy workspace exceeded one fixed inspection budget before decoding. */
export class ImportCapacityExceededError extends Error {
  readonly resource: ImportCapacityResource;
  readonly limit: number;
  readonly observed: number;

  constructor(resource: ImportCapacityResource, limit: number, observed: number) {
    if (
      !Number.isSafeInteger(limit) ||
      limit < 0 ||
      !Number.isSafeInteger(observed) ||
      observed < 0
    ) {
      throw new RangeError("Import capacity values must be non-negative safe integers.");
    }
    super("Legacy import capacity exceeded.");
    this.name = "ImportCapacityExceededError";
    this.resource = resource;
    this.limit = limit;
    this.observed = observed;
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

/** A terminal outcome was offered to a job that is no longer open (#392). */
export class InvalidJobTransitionError extends Error {
  readonly jobId: string;
  readonly currentStatus: string;
  readonly attemptedStatus: string;

  constructor(jobId: string, currentStatus: string, attemptedStatus: string) {
    super(
      `Job ${jobId} is ${currentStatus}; a ${attemptedStatus} outcome requires a running or pending job.`,
    );
    this.name = "InvalidJobTransitionError";
    this.jobId = jobId;
    this.currentStatus = currentStatus;
    this.attemptedStatus = attemptedStatus;
  }
}

/** The same synchronous pipeline operation is already running for this target. */
export class OperationInFlightError extends Error {
  readonly projectId: string;
  readonly documentId: string | null;
  readonly operation: string;
  readonly retryAfterSeconds: number | undefined;

  constructor(
    projectId: string,
    documentId: string | null,
    operation: string,
    retryAfterSeconds?: number,
  ) {
    super(
      documentId === null
        ? `The ${operation} operation is already running for this project.`
        : `The ${operation} operation is already running for this document.`,
    );
    this.name = "OperationInFlightError";
    this.projectId = projectId;
    this.documentId = documentId;
    this.operation = operation;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

export type OperationCapacityScope = "project" | "application";

/** An admitted expensive workflow would exceed one app-local capacity limit. */
export class OperationCapacityExceededError extends Error {
  readonly scope: OperationCapacityScope;
  readonly limit: number;
  readonly inFlight: number;
  readonly projectId: string;
  readonly retryAfterSeconds: number;

  constructor(
    scope: OperationCapacityScope,
    limit: number,
    inFlight: number,
    projectId: string,
    retryAfterSeconds = 5,
  ) {
    super("Studio operation capacity is exhausted.");
    this.name = "OperationCapacityExceededError";
    this.scope = scope;
    this.limit = limit;
    this.inFlight = inFlight;
    this.projectId = projectId;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}
