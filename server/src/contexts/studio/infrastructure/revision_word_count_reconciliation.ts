import { asc, eq, gt, isNull } from "drizzle-orm";

import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import {
  assertStoredRevisionWordCount,
  RevisionWordCountInvariantError,
  revisionWordCount,
} from "../domain/revision_word_count.js";
import { documentRevisions } from "./db/schema.js";

export const REVISION_WORD_COUNT_BATCH_SIZE = 256;

interface RevisionWordCountReconciliationOptions {
  /**
   * Called after each batch that committed corrections, with the cumulative
   * number of corrections; batches that found nothing stale stay silent.
   */
  readonly afterBatchCommitted?: ((corrected: number) => void) | undefined;
}

/**
 * Repairs retained revision word counts before the server accepts traffic, in
 * bounded, committed, restart-safe batches ordered by revision id. Every
 * revision body is re-counted under the current shared definition and a row is
 * updated only when its stored value differs, so the first upgrade fills NULL
 * sentinels and any later counting-semantics change rewrites stale numbers
 * through the same pass. The pass is idempotent — a consistent database
 * commits zero writes — returns the number of rows corrected, and restarts
 * from the first revision after an interruption, which is safe because
 * repeated batches observe already-correct rows as no-ops. A failed batch
 * write, an update that matches no row, or a revision still NULL after the
 * pass raises RevisionWordCountInvariantError so startup fails before traffic
 * instead of publishing placeholder or stale counts.
 */
export function reconcileRevisionWordCounts(
  db: StudioSqliteDatabase,
  options: RevisionWordCountReconciliationOptions = {},
): number {
  let cursor = "";
  let corrected = 0;
  while (true) {
    // Revision ids are non-empty, so `id > ""` serves the first page and the
    // keyset walk resumes strictly after the last id of the previous batch.
    const batch = db
      .select({
        id: documentRevisions.id,
        contentMarkdown: documentRevisions.contentMarkdown,
        wordCount: documentRevisions.wordCount,
      })
      .from(documentRevisions)
      .where(gt(documentRevisions.id, cursor))
      .orderBy(asc(documentRevisions.id))
      .limit(REVISION_WORD_COUNT_BATCH_SIZE)
      .all();
    const last = batch[batch.length - 1];
    if (last === undefined) break;
    cursor = last.id;

    const corrections = batch
      .map((revision) => ({
        id: revision.id,
        wordCount: assertStoredRevisionWordCount(revisionWordCount(revision.contentMarkdown)),
        stored: revision.wordCount,
      }))
      .filter((revision) => revision.stored !== revision.wordCount);
    if (corrections.length === 0) continue;

    db.transaction((tx) => {
      for (const correction of corrections) {
        const result = tx
          .update(documentRevisions)
          .set({ wordCount: correction.wordCount })
          .where(eq(documentRevisions.id, correction.id))
          .run();
        if (result.changes !== 1) throw new RevisionWordCountInvariantError();
      }
    });
    corrected += corrections.length;
    options.afterBatchCommitted?.(corrected);
  }

  const unresolved = db
    .select({ id: documentRevisions.id })
    .from(documentRevisions)
    .where(isNull(documentRevisions.wordCount))
    .limit(1)
    .get();
  if (unresolved !== undefined) throw new RevisionWordCountInvariantError();
  return corrected;
}
