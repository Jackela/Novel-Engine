import { type Static, Type } from "@fastify/type-provider-typebox";
import {
  DOCUMENT_KINDS,
  type DocumentKind,
  REVISION_SOURCES,
  type RevisionSource,
} from "../../domain/kinds.js";
import { freeFormObject, nullableString } from "./common.js";

/**
 * Document payload (#433 SSOT): the list/save/read shape emitted by
 * `documentPayload`. `volume_id`/`beat_ref` stay null for documents outside
 * volumes. The store rows carry write-validated enum values; the payload
 * schema declares the closed sets from `domain/kinds.ts`.
 */
export const documentPayloadSchema = Type.Object(
  {
    id: Type.String(),
    project_id: Type.String(),
    kind: Type.Unsafe<DocumentKind>({ type: "string", enum: [...DOCUMENT_KINDS] }),
    title: Type.String(),
    position: Type.Integer(),
    volume_id: nullableString,
    beat_ref: nullableString,
    current_revision_id: Type.String(),
    content_markdown: Type.String(),
    metadata: freeFormObject,
    revision_source: Type.Unsafe<RevisionSource>({ type: "string", enum: [...REVISION_SOURCES] }),
    word_count: Type.Integer(),
    created_at: Type.String(),
    updated_at: Type.String(),
  },
  { additionalProperties: false },
);

export type DocumentPayload = Static<typeof documentPayloadSchema>;

/** One ranked full-text hit: identifier, title, plain-text excerpt. */
export const matchResultPayloadSchema = Type.Object(
  {
    document_id: Type.String(),
    title: Type.String(),
    excerpt: Type.String(),
  },
  { additionalProperties: false },
);

export type MatchResultPayload = Static<typeof matchResultPayloadSchema>;
