/**
 * Document, revision, and snapshot contracts.
 *
 * The revision chain is append-only: every save appends one revision and moves
 * the document's `currentRevisionId`. A restore appends a new revision whose
 * `restoredFrom` names the target, so history is never rewritten.
 */

import { Type, type Static } from "typebox";

import { EpochMillis, PageInfo, ProjectId, VolumeId } from "./projects.js";

export const DocumentId = Type.String({ minLength: 1, maxLength: 64 });
export type DocumentId = Static<typeof DocumentId>;

export const RevisionId = Type.String({ minLength: 1, maxLength: 64 });
export type RevisionId = Static<typeof RevisionId>;

export const SnapshotId = Type.String({ minLength: 1, maxLength: 64 });
export type SnapshotId = Static<typeof SnapshotId>;

/** The closed document-kind set; mirrors the five navigator groups. */
export const DocumentKind = Type.Union([
  Type.Literal("chapter"),
  Type.Literal("outline"),
  Type.Literal("character"),
  Type.Literal("world"),
  Type.Literal("note"),
]);
export type DocumentKind = Static<typeof DocumentKind>;

/** How a revision came to exist. */
export const RevisionSource = Type.Union([
  Type.Literal("author"),
  Type.Literal("ai-accepted"),
  Type.Literal("restore"),
  Type.Literal("import"),
]);
export type RevisionSource = Static<typeof RevisionSource>;

/** The maximum body size of one document, in UTF-16 code units of markdown. */
export const MAX_DOCUMENT_BODY = 1_048_576;

export const DocumentView = Type.Object(
  {
    id: DocumentId,
    projectId: ProjectId,
    volumeId: Type.Union([VolumeId, Type.Null()]),
    kind: DocumentKind,
    title: Type.String({ maxLength: 200 }),
    position: Type.Integer({ minimum: 0 }),
    beatRef: Type.Union([Type.String({ maxLength: 200 }), Type.Null()]),
    currentRevisionId: RevisionId,
    wordCount: Type.Integer({ minimum: 0 }),
    createdAt: EpochMillis,
    updatedAt: EpochMillis,
  },
  { additionalProperties: false },
);
export type DocumentView = Static<typeof DocumentView>;

export const DocumentCreateRequest = Type.Object(
  {
    kind: DocumentKind,
    title: Type.String({ minLength: 1, maxLength: 200 }),
    volumeId: Type.Optional(Type.Union([VolumeId, Type.Null()])),
    contentMarkdown: Type.Optional(Type.String({ maxLength: MAX_DOCUMENT_BODY })),
  },
  { additionalProperties: false },
);
export type DocumentCreateRequest = Static<typeof DocumentCreateRequest>;

export const RevisionView = Type.Object(
  {
    id: RevisionId,
    documentId: DocumentId,
    revisionNumber: Type.Integer({ minimum: 1 }),
    source: RevisionSource,
    wordCount: Type.Integer({ minimum: 0 }),
    note: Type.Union([Type.String({ maxLength: 200 }), Type.Null()]),
    restoredFrom: Type.Union([RevisionId, Type.Null()]),
    createdAt: EpochMillis,
  },
  { additionalProperties: false },
);
export type RevisionView = Static<typeof RevisionView>;

/** A revision including its body; only detail reads return this. */
export const RevisionDetailView = Type.Object(
  {
    ...RevisionView.properties,
    contentMarkdown: Type.String(),
    contentHash: Type.String(),
  },
  { additionalProperties: false },
);
export type RevisionDetailView = Static<typeof RevisionDetailView>;

export const SaveDocumentRequest = Type.Object(
  {
    contentMarkdown: Type.String({ maxLength: MAX_DOCUMENT_BODY }),
    /**
     * The revision the author started from. Every document always has a current
     * revision, so `null` can never match and always produces
     * REVISION_CONFLICT — it exists so a client that lost its state can send a
     * well-formed request and read the current revision from the 409 details.
     * Any mismatch returns REVISION_CONFLICT with zero writes.
     */
    baseRevisionId: Type.Union([RevisionId, Type.Null()]),
    title: Type.Optional(Type.String({ minLength: 1, maxLength: 200 })),
    /** Autosave writes are collapsed by the use case, not by the client. */
    autosave: Type.Optional(Type.Boolean()),
  },
  { additionalProperties: false },
);
export type SaveDocumentRequest = Static<typeof SaveDocumentRequest>;

export const SaveDocumentResponse = Type.Object(
  {
    document: DocumentView,
    revision: RevisionView,
  },
  { additionalProperties: false },
);
export type SaveDocumentResponse = Static<typeof SaveDocumentResponse>;

/** Payload carried on a 409 so the client can show both versions. */
export const RevisionConflictDetails = Type.Object(
  {
    documentId: DocumentId,
    baseRevisionId: Type.Union([RevisionId, Type.Null()]),
    currentRevisionId: RevisionId,
    currentRevisionNumber: Type.Integer({ minimum: 1 }),
  },
  { additionalProperties: false },
);
export type RevisionConflictDetails = Static<typeof RevisionConflictDetails>;

export const RevisionNoteRequest = Type.Object(
  { note: Type.Union([Type.String({ maxLength: 200 }), Type.Null()]) },
  { additionalProperties: false },
);
export type RevisionNoteRequest = Static<typeof RevisionNoteRequest>;

export const RevisionPage = Type.Object(
  {
    items: Type.Array(RevisionView),
    page: PageInfo,
  },
  { additionalProperties: false },
);
export type RevisionPage = Static<typeof RevisionPage>;

export const SnapshotView = Type.Object(
  {
    id: SnapshotId,
    projectId: ProjectId,
    reason: Type.Union([Type.Literal("review"), Type.Literal("export")]),
    label: Type.Union([Type.String({ maxLength: 200 }), Type.Null()]),
    documentCount: Type.Integer({ minimum: 0 }),
    wordCount: Type.Integer({ minimum: 0 }),
    contentHash: Type.String(),
    createdAt: EpochMillis,
  },
  { additionalProperties: false },
);
export type SnapshotView = Static<typeof SnapshotView>;
