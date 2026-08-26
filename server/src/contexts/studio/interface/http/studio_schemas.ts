import { PROVIDER_NAMES } from "../../../ai/application/ports/text_generation.js";
import { DOCUMENT_KINDS, REVISION_SOURCES } from "../../domain/kinds.js";

const kindLiteral = {
  type: "string",
  enum: [...DOCUMENT_KINDS],
} as const;
const sourceLiteral = { type: "string", enum: [...REVISION_SOURCES] } as const;
const timestamp = { type: "string" } as const;
const metadataObject = { type: "object", additionalProperties: true } as const;

/** Request schemas deliberately expose no `source` field (closed server enum). */

export const projectCreateSchema = {
  type: "object",
  properties: {
    title: { type: "string", minLength: 1, maxLength: 240 },
    description: { type: "string", maxLength: 10_000, default: "" },
  },
  required: ["title"],
  additionalProperties: false,
} as const;

export const documentCreateSchema = {
  type: "object",
  properties: {
    kind: kindLiteral,
    title: { type: "string", minLength: 1, maxLength: 240 },
    content_markdown: { type: "string", default: "" },
    position: { type: "integer", minimum: 0, nullable: true },
    metadata: metadataObject,
  },
  required: ["kind", "title"],
  additionalProperties: false,
} as const;

export const documentSaveSchema = {
  type: "object",
  properties: {
    content_markdown: { type: "string" },
    base_revision_id: { type: "string", nullable: true },
    title: { type: "string", maxLength: 240 },
    metadata: metadataObject,
  },
  required: ["content_markdown", "base_revision_id"],
  additionalProperties: false,
} as const;

export const reorderSchema = {
  type: "object",
  properties: {
    document_ids: { type: "array", items: { type: "string" }, minItems: 1 },
  },
  required: ["document_ids"],
  additionalProperties: false,
} as const;

/**
 * The proposal request carries the frontend operation vocabulary and the
 * provider choice only — models are resolved server-side, never sent.
 */
export const proposalCreateSchema = {
  type: "object",
  properties: {
    operation: { type: "string", enum: ["continue", "rewrite", "generate"] },
    instruction: { type: "string", maxLength: 10_000, default: "" },
    provider: { type: "string", enum: [...PROVIDER_NAMES], default: "mock" },
  },
  required: ["operation"],
  additionalProperties: false,
} as const;

export const restoreSchema = {
  type: "object",
  properties: {
    base_revision_id: { type: "string", nullable: true },
  },
  required: ["base_revision_id"],
  additionalProperties: false,
} as const;

/** The full-text query string: `q` is required (missing → 422). */
export const projectMatchQuerySchema = {
  type: "object",
  properties: {
    q: { type: "string" },
  },
  required: ["q"],
  additionalProperties: false,
} as const;

/** Response payload shapes (fast-json-stringify passes unknown fields through). */

export const documentResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: {
    id: { type: "string" },
    project_id: { type: "string" },
    kind: kindLiteral,
    title: { type: "string" },
    position: { type: "integer" },
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
    "current_revision_id",
    "content_markdown",
    "metadata",
    "revision_source",
    "word_count",
    "created_at",
    "updated_at",
  ],
} as const;

export const revisionResponseSchema = {
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
} as const;

/** One ranked full-text hit: identifier, title, plain-text excerpt. */
export const matchResultSchema = {
  type: "object",
  additionalProperties: true,
  properties: {
    document_id: { type: "string" },
    title: { type: "string" },
    excerpt: { type: "string" },
  },
  required: ["document_id", "title", "excerpt"],
} as const;

export const matchListResponseSchema = {
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

export const projectResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: projectResponseProperties,
  required: [...PROJECT_REQUIRED],
} as const;

export const projectDetailResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: projectResponseProperties,
  required: [...PROJECT_REQUIRED, "documents"],
} as const;

/** The 409 conflict envelope: details.current_revision_id identifies the winner. */
export const revisionConflictSchema = {
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

export const documentConflictSchema = {
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
export const operationInFlightSchema = {
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
export const snapshotConflictSchema = {
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
