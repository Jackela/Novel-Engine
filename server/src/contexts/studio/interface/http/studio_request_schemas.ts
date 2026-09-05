import { type Static, Type } from "@fastify/type-provider-typebox";
import type { TextProviderName } from "../../../ai/application/ports/text_generation.js";
import { PROVIDER_NAMES } from "../../../ai/application/ports/text_generation.js";
import { DOCUMENT_KINDS, type DocumentKind } from "../../domain/kinds.js";

/**
 * TypeBox request schemas (params, querystring, body). Response schemas stay
 * in `studio_schemas.ts` and friends. The emitted JSON Schema here is
 * identical to the previous hand-written request schemas, so the OpenAPI
 * snapshot changes only by the newly documented path params; `Static` gives
 * handlers compile-time request types instead of `as` casts.
 *
 * Nullable fields use `Type.Unsafe` with `nullable: true` (the exact original
 * shape) rather than a `Type.Union` with `Type.Null()`: Fastify's coercing
 * AJV would otherwise coerce an explicit `null` to `""`/`0` against the
 * non-null anyOf branch, silently changing runtime behavior.
 */

/** Request schemas deliberately expose no `source` field (closed server enum). */

const pathSegment = Type.String();

export const projectIdParams = Type.Object({ projectId: pathSegment });
export type ProjectIdParams = Static<typeof projectIdParams>;

export const documentIdParams = Type.Object({
  projectId: pathSegment,
  documentId: pathSegment,
});
export type DocumentIdParams = Static<typeof documentIdParams>;

export const revisionIdParams = Type.Object({
  projectId: pathSegment,
  documentId: pathSegment,
  revisionId: pathSegment,
});
export type RevisionIdParams = Static<typeof revisionIdParams>;

export const volumeIdParams = Type.Object({ projectId: pathSegment, volumeId: pathSegment });
export type VolumeIdParams = Static<typeof volumeIdParams>;

export const jobIdParams = Type.Object({ projectId: pathSegment, jobId: pathSegment });
export type JobIdParams = Static<typeof jobIdParams>;

export const exportIdParams = Type.Object({ projectId: pathSegment, exportId: pathSegment });
export type ExportIdParams = Static<typeof exportIdParams>;

/** Free-form metadata object, byte-identical to the original JSON Schema. */
const metadataObject = Type.Unsafe<Record<string, unknown>>({
  type: "object",
  additionalProperties: true,
});

const nullableString = (options: Record<string, unknown>) =>
  Type.Unsafe<string | null>({ type: "string", ...options, nullable: true });

const nullableInteger = (options: Record<string, unknown>) =>
  Type.Unsafe<number | null>({ type: "integer", ...options, nullable: true });

export const projectCreateSchema = Type.Object(
  {
    title: Type.String({ minLength: 1, maxLength: 240 }),
    description: Type.Optional(Type.String({ maxLength: 10_000, default: "" })),
  },
  { additionalProperties: false },
);
export type ProjectCreateBody = Static<typeof projectCreateSchema>;

export const projectUpdateSchema = Type.Object(
  {
    title: Type.Optional(Type.String({ minLength: 1, maxLength: 240 })),
    description: Type.Optional(Type.String({ maxLength: 10_000 })),
    settings: Type.Optional(metadataObject),
  },
  { additionalProperties: false, minProperties: 1 },
);
export type ProjectUpdateBody = Static<typeof projectUpdateSchema>;

export const documentCreateSchema = Type.Object(
  {
    kind: Type.Unsafe<DocumentKind>({ type: "string", enum: [...DOCUMENT_KINDS] }),
    title: Type.String({ minLength: 1, maxLength: 240 }),
    content_markdown: Type.Optional(Type.String({ default: "" })),
    position: Type.Optional(nullableInteger({ minimum: 0 })),
    metadata: Type.Optional(metadataObject),
  },
  { additionalProperties: false },
);
export type DocumentCreateBody = Static<typeof documentCreateSchema>;

export const documentSaveSchema = Type.Object(
  {
    content_markdown: Type.String(),
    base_revision_id: nullableString({}),
    title: Type.Optional(Type.String({ maxLength: 240 })),
    metadata: Type.Optional(metadataObject),
  },
  { additionalProperties: false },
);
export type DocumentSaveBody = Static<typeof documentSaveSchema>;

export const reorderSchema = Type.Object(
  { document_ids: Type.Array(Type.String(), { minItems: 1 }) },
  { additionalProperties: false },
);
export type ReorderBody = Static<typeof reorderSchema>;

/**
 * The proposal request carries the frontend operation vocabulary and the
 * provider choice only — models are resolved server-side, never sent.
 */
const proposalOperations = ["continue", "rewrite", "generate"] as const;

export const proposalCreateSchema = Type.Object(
  {
    operation: Type.Unsafe<(typeof proposalOperations)[number]>({
      type: "string",
      enum: [...proposalOperations],
    }),
    instruction: Type.Optional(Type.String({ maxLength: 10_000, default: "" })),
    provider: Type.Optional(
      Type.Unsafe<TextProviderName | undefined>({
        type: "string",
        enum: [...PROVIDER_NAMES],
        default: "mock",
      }),
    ),
  },
  { additionalProperties: false },
);
export type ProposalCreateBody = Static<typeof proposalCreateSchema>;

export const restoreSchema = Type.Object(
  { base_revision_id: nullableString({}) },
  { additionalProperties: false },
);
export type RestoreBody = Static<typeof restoreSchema>;

export const revisionListQuerySchema = Type.Object(
  {
    limit: Type.Optional(Type.Integer({ default: 50, minimum: 1, maximum: 100 })),
    cursor: Type.Optional(
      Type.String({
        minLength: 1,
        maxLength: 1024,
        pattern: "^[A-Za-z0-9_-]+$",
      }),
    ),
  },
  { additionalProperties: false },
);
export type RevisionListQuery = Static<typeof revisionListQuerySchema>;

/** The bounded catalog read: `limit` defaults to 50 (missing → bounded page). */
export const projectListQuerySchema = Type.Object(
  {
    limit: Type.Optional(Type.Integer({ default: 50, minimum: 1, maximum: 100 })),
    cursor: Type.Optional(
      Type.String({
        minLength: 1,
        maxLength: 1024,
        pattern: "^[A-Za-z0-9_-]+$",
      }),
    ),
  },
  { additionalProperties: false },
);
export type ProjectListQuery = Static<typeof projectListQuerySchema>;

/** The full-text query string: `q` is required (missing → 422). */
export const projectMatchQuerySchema = Type.Object(
  { q: Type.String() },
  { additionalProperties: false },
);
export type ProjectMatchQuery = Static<typeof projectMatchQuerySchema>;
