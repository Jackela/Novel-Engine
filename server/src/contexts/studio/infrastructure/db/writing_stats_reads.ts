import { and, eq } from "drizzle-orm";

import type {
  WritingStatsChapterRow,
  WritingStatsHistory,
} from "../../application/ports/writing_stats.js";
import { assertStoredRevisionSource } from "../../domain/revision_source.js";
import { assertStoredRevisionWordCount } from "../../domain/revision_word_count.js";
import { documentRevisions, documents } from "./schema.js";
import type { Tx } from "./studio_query_helpers.js";

/**
 * The bounded stats read of one project (#653): every revision's identity,
 * lineage, source, and stored unified word count, plus the chapter
 * documents' current word counts. Bodies and metadata are never selected —
 * attribution needs deltas only. The caller re-verifies principal scoping
 * before this read.
 */
export function writingStatsHistory(tx: Tx, projectId: string): WritingStatsHistory {
  return {
    revisions: tx
      .select({
        id: documentRevisions.id,
        documentId: documentRevisions.documentId,
        parentRevisionId: documentRevisions.parentRevisionId,
        source: documentRevisions.source,
        wordCount: documentRevisions.wordCount,
        createdAt: documentRevisions.createdAt,
      })
      .from(documentRevisions)
      .innerJoin(documents, eq(documentRevisions.documentId, documents.id))
      .where(eq(documents.projectId, projectId))
      .all()
      .map((row) => ({
        ...row,
        source: assertStoredRevisionSource(row.source),
        wordCount: assertStoredRevisionWordCount(row.wordCount),
      })),
    chapters: chapterRows(tx, projectId),
  };
}

/** Chapter documents with their current content word count. */
function chapterRows(tx: Tx, projectId: string): WritingStatsChapterRow[] {
  return tx
    .select({
      documentId: documents.id,
      wordCount: documentRevisions.wordCount,
    })
    .from(documents)
    .leftJoin(
      documentRevisions,
      and(
        eq(documents.currentRevisionId, documentRevisions.id),
        eq(documentRevisions.documentId, documents.id),
      ),
    )
    .where(and(eq(documents.projectId, projectId), eq(documents.kind, "chapter")))
    .all()
    .map((row) => ({
      documentId: row.documentId,
      currentWordCount: row.wordCount === null ? 0 : assertStoredRevisionWordCount(row.wordCount),
    }));
}
