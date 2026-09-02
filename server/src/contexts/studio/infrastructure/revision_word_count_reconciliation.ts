import { and, asc, eq, isNull } from "drizzle-orm";

import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import {
  assertStoredRevisionWordCount,
  RevisionWordCountInvariantError,
  revisionWordCount,
} from "../domain/revision_word_count.js";
import { documentRevisions } from "./db/schema.js";

export const REVISION_WORD_COUNT_BATCH_SIZE = 256;

export interface RevisionWordCountReconciliationOptions {
  readonly afterBatchCommitted?: ((completed: number) => void) | undefined;
}

/** Populate upgrade sentinels in bounded, committed, restart-safe batches. */
export function reconcileRevisionWordCounts(
  db: StudioSqliteDatabase,
  options: RevisionWordCountReconciliationOptions = {},
): number {
  let completed = 0;
  while (true) {
    const batch = db
      .select({ id: documentRevisions.id, contentMarkdown: documentRevisions.contentMarkdown })
      .from(documentRevisions)
      .where(isNull(documentRevisions.wordCount))
      .orderBy(asc(documentRevisions.id))
      .limit(REVISION_WORD_COUNT_BATCH_SIZE)
      .all();
    if (batch.length === 0) break;

    db.transaction((tx) => {
      for (const revision of batch) {
        const count = assertStoredRevisionWordCount(revisionWordCount(revision.contentMarkdown));
        const result = tx
          .update(documentRevisions)
          .set({ wordCount: count })
          .where(and(eq(documentRevisions.id, revision.id), isNull(documentRevisions.wordCount)))
          .run();
        if (result.changes !== 1) throw new RevisionWordCountInvariantError();
      }
    });
    completed += batch.length;
    options.afterBatchCommitted?.(completed);
  }

  const unresolved = db
    .select({ id: documentRevisions.id })
    .from(documentRevisions)
    .where(isNull(documentRevisions.wordCount))
    .limit(1)
    .get();
  if (unresolved !== undefined) throw new RevisionWordCountInvariantError();
  return completed;
}
