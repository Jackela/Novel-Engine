import { and, desc, eq, lt, or } from "drizzle-orm";

import type { RevisionPageInput } from "../application/ports/studio_store.js";
import { documentRevisions } from "./db/schema.js";
import type { Tx } from "./db/studio_query_helpers.js";

/** Summary-only keyset query; complete revision bodies are read only by exact restore. */
export function buildRevisionSummariesQuery(tx: Tx, documentId: string, input: RevisionPageInput) {
  const after = input.cursor;
  return tx
    .select({
      id: documentRevisions.id,
      documentId: documentRevisions.documentId,
      parentRevisionId: documentRevisions.parentRevisionId,
      revisionNumber: documentRevisions.revisionNumber,
      source: documentRevisions.source,
      wordCount: documentRevisions.wordCount,
      createdAt: documentRevisions.createdAt,
    })
    .from(documentRevisions)
    .where(
      and(
        eq(documentRevisions.documentId, documentId),
        after === undefined
          ? undefined
          : or(
              lt(documentRevisions.revisionNumber, after.revisionNumber),
              and(
                eq(documentRevisions.revisionNumber, after.revisionNumber),
                lt(documentRevisions.id, after.id),
              ),
            ),
      ),
    )
    .orderBy(desc(documentRevisions.revisionNumber), desc(documentRevisions.id))
    .limit(input.limit + 1);
}
