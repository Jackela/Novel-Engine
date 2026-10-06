import type Database from "better-sqlite3";
import { eq, sql } from "drizzle-orm";

import type {
  DocumentMatchPage,
  DocumentMatchPageInput,
} from "../../application/ports/document_store.js";
import { restoreFtsDisplayText, segmentFtsIndexText } from "../../domain/fts_segmentation.js";
import { documentRevisions, documents } from "./schema.js";
import type { Tx } from "./studio_query_helpers.js";

/**
 * The single full-text module of the studio store: every FTS5 statement —
 * index refresh, index cleanup, the ranked page query, and the rebuild —
 * lives here and runs inside the caller's transaction, parameter-bound. The
 * `document_search` virtual table is created by the hand-written FTS5
 * migration and never enters the drizzle schema or snapshots.
 *
 * Index rows store `segmentFtsIndexText` output for title and content, so
 * Han characters are individual unicode61 tokens (#DR-003); titles and
 * excerpts leave through `restoreFtsDisplayText`.
 */

interface DocumentIndexEntry {
  documentId: string;
  projectId: string;
  title: string;
  content: string;
}

/** Replace a document's index row (delete + insert within the caller's transaction). */
export function refreshDocumentIndex(tx: Tx, entry: DocumentIndexEntry): void {
  tx.run(sql`DELETE FROM document_search WHERE document_id = ${entry.documentId}`);
  tx.run(
    sql`INSERT INTO document_search(document_id, project_id, title, content)
        VALUES (${entry.documentId}, ${entry.projectId}, ${segmentFtsIndexText(entry.title)}, ${segmentFtsIndexText(entry.content)})`,
  );
}

/** Remove one document's index row; the FTS table has no FK to cascade. */
export function clearDocumentIndex(tx: Tx, documentId: string): void {
  tx.run(sql`DELETE FROM document_search WHERE document_id = ${documentId}`);
}

/** Remove every index row of a project being deleted. */
export function clearProjectDocumentIndex(tx: Tx, projectId: string): void {
  tx.run(sql`DELETE FROM document_search WHERE project_id = ${projectId}`);
}

/**
 * Replace the whole index from the current revisions inside the caller's
 * transaction: existing rows are cleared first, so the rebuild is idempotent
 * on clean and drifted databases alike and rows whose document vanished do
 * not survive. Documents without a current revision have no content to index
 * and are skipped. Returns the number of indexed documents.
 */
export function rebuildDocumentIndex(tx: Tx): number {
  tx.run(sql`DELETE FROM document_search`);
  const rows = tx
    .select({
      documentId: documents.id,
      projectId: documents.projectId,
      title: documents.title,
      content: documentRevisions.contentMarkdown,
    })
    .from(documents)
    .innerJoin(documentRevisions, eq(documents.currentRevisionId, documentRevisions.id))
    .all();
  for (const row of rows) {
    refreshDocumentIndex(tx, row);
  }
  return rows.length;
}

/** The doctor reconciliation item (#DR-004): document rows vs index rows. */
export interface DocumentIndexReconciliation {
  /** Documents whose current revision a rebuild would index. */
  readonly documents: number;
  /** Rows currently stored in the `document_search` virtual table. */
  readonly indexed: number;
  /** True when the two counts disagree. */
  readonly drifted: boolean;
}

/**
 * Count documents against index rows for `doctor` and `reindex`. The document
 * count uses the rebuild's own join, so a document whose current revision
 * row is missing is not reported as permanent drift; a row whose document
 * vanished counts toward `indexed`. A read failure propagates to the caller
 * (the doctor field family reports it through its own error channel).
 */
export function documentIndexReconciliation(raw: Database.Database): DocumentIndexReconciliation {
  const indexedRow = raw.prepare("SELECT COUNT(*) AS n FROM document_search").get() as
    | { n: number }
    | undefined;
  const documentsRow = raw
    .prepare(
      `SELECT COUNT(*) AS n FROM documents
       INNER JOIN document_revisions ON documents.current_revision_id = document_revisions.id`,
    )
    .get() as { n: number } | undefined;
  const documents = documentsRow?.n ?? -1;
  const indexed = indexedRow?.n ?? -1;
  return { documents, indexed, drifted: documents !== indexed };
}

/**
 * Ranked full-text page over one project (DR-029): 16-token plain-text
 * excerpt of the content column (column 3), no highlight markers, ' … '
 * ellipsis truncation, `ORDER BY rank, document_id ASC` — the total order a
 * LIMIT/OFFSET page can walk without duplicating or skipping rows — and the
 * honest `COUNT(*)` of the same project + MATCH expression, so `total` is
 * never the page size. For Chinese text each Han character is one token, so
 * the same window is the 16-character CJK window the search fix requires,
 * while Latin keeps its 16-word window. Excerpts and titles are restored to
 * display text.
 */
export function matchDocumentIndex(
  tx: Tx,
  projectId: string,
  matchQuery: string,
  page: DocumentMatchPageInput,
): DocumentMatchPage {
  const totalRow = tx.get<{ n: number }>(
    sql`SELECT COUNT(*) AS n FROM document_search
        WHERE project_id = ${projectId} AND document_search MATCH ${matchQuery}`,
  );
  if (totalRow === undefined) {
    // COUNT(*) always yields exactly one row; a missing row is a driver anomaly.
    throw new Error("FTS5 match count returned no row.");
  }
  const rows = tx.all<{
    document_id: string;
    title: string;
    excerpt: string;
  }>(sql`SELECT document_id, title,
        snippet(document_search, 3, '', '', ' … ', 16) AS excerpt
        FROM document_search
        WHERE project_id = ${projectId} AND document_search MATCH ${matchQuery}
        ORDER BY rank, document_id ASC
        LIMIT ${page.limit} OFFSET ${page.offset}`);
  return {
    matches: rows.map((row) => ({
      documentId: row.document_id,
      title: restoreFtsDisplayText(row.title),
      excerpt: restoreFtsDisplayText(row.excerpt),
    })),
    total: totalRow.n,
  };
}
