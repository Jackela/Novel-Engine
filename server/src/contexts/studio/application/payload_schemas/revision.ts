import { type Static, Type } from "@fastify/type-provider-typebox";
import { REVISION_SOURCES, type RevisionSource } from "../../domain/kinds.js";
import { freeFormObject, nullableString } from "./common.js";

/**
 * Revision payload (#433 SSOT): the immutable history entry emitted by
 * `revisionPayload`. The server-assigned `source` is a closed enum
 * (`domain/kinds.ts`); request schemas never expose it.
 */
export const revisionPayloadSchema = Type.Object(
  {
    id: Type.String(),
    document_id: Type.String(),
    parent_revision_id: nullableString,
    revision_number: Type.Integer(),
    content_markdown: Type.String(),
    metadata: freeFormObject,
    source: Type.Unsafe<RevisionSource>({ type: "string", enum: [...REVISION_SOURCES] }),
    word_count: Type.Integer(),
    created_at: Type.String(),
  },
  { additionalProperties: false },
);

export type RevisionPayload = Static<typeof revisionPayloadSchema>;
