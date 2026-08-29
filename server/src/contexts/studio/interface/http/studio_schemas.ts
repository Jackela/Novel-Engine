import { DOCUMENT_KINDS, REVISION_SOURCES } from "../../domain/kinds.js";
import type { JsonResponseSchema } from "./json_response_schema.js";
import { volumeResponseSchema } from "./volume_schemas.js";

/**
 * Response payload shapes (fast-json-stringify passes unknown fields through).
 * Request schemas live in `studio_request_schemas.ts` as TypeBox schemas.
 */

const kindLiteral = {
  type: "string",
  enum: [...DOCUMENT_KINDS],
} as const;
const sourceLiteral = { type: "string", enum: [...REVISION_SOURCES] } as const;
const timestamp = { type: "string" } as const;
const metadataObject = { type: "object", additionalProperties: true } as const;

/** Response payload shapes live above; the schemas below document hit shapes and error envelopes. */

export const documentResponseSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: {
    id: { type: "string" },
    project_id: { type: "string" },
    kind: kindLiteral,
    title: { type: "string" },
    position: { type: "integer" },
    volume_id: { type: "string", nullable: true },
    beat_ref: { type: "string", nullable: true },
    current_revision_id: { type: "string" },
    content_markdown: { type: "string" },
    metadata: metadataObject,
    revision_source: sourceLiteral,
    word_count: { type: "integer" },
    created_at: timestamp,
    updated_at: timestamp,
  },
  required: [
    "id",
    "project_id",
    "kind",
    "title",
    "position",
    "volume_id",
    "current_revision_id",
    "content_markdown",
    "metadata",
    "revision_source",
    "word_count",
    "created_at",
    "updated_at",
  ],
} as const;

export const revisionResponseSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: {
    id: { type: "string" },
    document_id: { type: "string" },
    parent_revision_id: { type: "string", nullable: true },
    revision_number: { type: "integer" },
    content_markdown: { type: "string" },
    metadata: metadataObject,
    source: sourceLiteral,
    word_count: { type: "integer" },
    created_at: timestamp,
  },
  required: [
    "id",
    "document_id",
    "parent_revision_id",
    "revision_number",
    "content_markdown",
    "metadata",
    "source",
    "word_count",
    "created_at",
  ],
} as const;

const projectResponseProperties = {
  id: { type: "string" },
  title: { type: "string" },
  description: { type: "string" },
  settings: metadataObject,
  import_hash: { type: "string", nullable: true },
  created_at: timestamp,
  updated_at: timestamp,
  documents: { type: "array", items: documentResponseSchema },
  volumes: { type: "array", items: volumeResponseSchema },
} as const;

/** One ranked full-text hit: identifier, title, plain-text excerpt. */
export const matchResultSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: {
    document_id: { type: "string" },
    title: { type: "string" },
    excerpt: { type: "string" },
  },
  required: ["document_id", "title", "excerpt"],
} as const;

export const matchListResponseSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: { results: { type: "array", items: matchResultSchema } },
  required: ["results"],
} as const;

const PROJECT_REQUIRED = [
  "id",
  "title",
  "description",
  "settings",
  "import_hash",
  "created_at",
  "updated_at",
] as const;

export const projectResponseSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: projectResponseProperties,
  required: [...PROJECT_REQUIRED],
} as const;

export const projectDetailResponseSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: projectResponseProperties,
  required: [...PROJECT_REQUIRED, "documents", "volumes"],
} as const;

/** The 409 conflict envelope: details.current_revision_id identifies the winner. */
export const revisionConflictSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: ["REVISION_CONFLICT"] },
        message: { type: "string" },
        details: {
          type: "object",
          additionalProperties: false,
          properties: { current_revision_id: { type: "string", nullable: true } },
          required: ["current_revision_id"],
        },
      },
      required: ["code", "message", "details"],
    },
  },
  required: ["error"],
} as const;

export const documentConflictSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: ["DOCUMENT_CONFLICT"] },
        message: { type: "string" },
      },
      required: ["code", "message"],
    },
  },
  required: ["error"],
} as const;

/** The 409 envelope when an identical pipeline operation is already running (#305). */
export const operationInFlightSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: ["OPERATION_IN_FLIGHT"] },
        message: { type: "string" },
        details: {
          type: "object",
          additionalProperties: false,
          properties: {
            project_id: { type: "string" },
            document_id: { type: "string", nullable: true },
            operation: { type: "string" },
          },
          required: ["project_id", "document_id", "operation"],
        },
      },
      required: ["code", "message", "details"],
    },
  },
  required: ["error"],
} as const;

/** The fixed 409 envelope when an immutable snapshot references the document. */
export const snapshotConflictSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: ["SNAPSHOT_CONFLICT"] },
        message: {
          type: "string",
          enum: ["Document is referenced by an immutable snapshot."],
        },
      },
      required: ["code", "message"],
    },
  },
  required: ["error"],
} as const;
