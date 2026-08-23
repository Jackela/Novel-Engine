import { sql } from "drizzle-orm";

import type { DocumentMatchRecord } from "../../application/ports/studio_store.js";
import type { Tx } from "./studio_query_helpers.js";

/**
 * The single full-text module of the studio store (twin of the Python
 * authority's `document_search` mixin): every FTS5 statement — index
 * refresh, index cleanup, and the ranked query — lives here and runs
 * inside the caller's transaction, parameter-bound. The `document_search`
 * virtual table is created by the hand-written FTS5 migration and never
 * enters the drizzle schema or snapshots.
 */

/** Result cap of the ranked query (Python authority: LIMIT 30). */
export const MATCH_RESULT_LIMIT = 30;

export interface DocumentIndexEntry {
  documentId: string;
  projectId: string;
  title: string;
  content: string;
}

/** Replace a document's index row (delete + insert, mirroring _refresh_search). */
export function refreshDocumentIndex(tx: Tx, entry: DocumentIndexEntry): void {
  tx.run(sql`DELETE FROM document_search WHERE document_id = ${entry.documentId}`);
  tx.run(
    sql`INSERT INTO document_search(document_id, project_id, title, content)
        VALUES (${entry.documentId}, ${entry.projectId}, ${entry.title}, ${entry.content})`,
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
 * Ranked full-text query over one project: 16-token plain-text excerpt of
 * the content column (column 3), no highlight markers, ' … ' ellipsis
 * truncation, `ORDER BY rank`, capped at MATCH_RESULT_LIMIT.
 */
export function matchDocumentIndex(
  tx: Tx,
  projectId: string,
  matchQuery: string,
): DocumentMatchRecord[] {
  const rows = tx.all<{
    document_id: string;
    title: string;
    excerpt: string;
  }>(sql`SELECT document_id, title,
        snippet(document_search, 3, '', '', ' … ', 16) AS excerpt
        FROM document_search
        WHERE project_id = ${projectId} AND document_search MATCH ${matchQuery}
        ORDER BY rank
        LIMIT ${MATCH_RESULT_LIMIT}`);
  return rows.map((row) => ({
    documentId: row.document_id,
    title: row.title,
    excerpt: row.excerpt,
  }));
}
