import type { RevisionDetail } from "@/app/types/revision";

import {
  exactKeys,
  integerField,
  literalField,
  nonnegativeIntegerField,
  nullableStringField,
  objectValue,
  recordField,
  stringField,
} from "./apiContract";

const revisionSources = ["author", "ai-accepted", "restore"] as const;

const revisionDetailKeys = [
  "id",
  "document_id",
  "parent_revision_id",
  "revision_number",
  "content_markdown",
  "metadata",
  "source",
  "word_count",
  "created_at",
] as const;

/**
 * DR-011 single-revision read: the immutable body plus every summary
 * invariant. Strict keys, mirroring `parseRevisionSummary`: an unexpected
 * field fails the contract instead of drifting silently.
 */
export function parseRevisionDetail(value: unknown): RevisionDetail {
  const item = objectValue(value, "revision response");
  exactKeys(item, revisionDetailKeys, "revision response");
  return {
    id: stringField(item, "id", "revision response"),
    document_id: stringField(item, "document_id", "revision response"),
    parent_revision_id: nullableStringField(item, "parent_revision_id", "revision response"),
    revision_number: integerField(item, "revision_number", "revision response"),
    content_markdown: stringField(item, "content_markdown", "revision response"),
    metadata: recordField(item, "metadata", "revision response"),
    source: literalField(item, "source", "revision response", revisionSources),
    word_count: nonnegativeIntegerField(item, "word_count", "revision response"),
    created_at: stringField(item, "created_at", "revision response"),
  };
}
