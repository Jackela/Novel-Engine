import {
  documentIndexReconciliation,
  rebuildDocumentIndex,
} from "../../contexts/studio/infrastructure/db/document_search.js";
import { openReconciledStudioDatabase } from "../../contexts/studio/infrastructure/reconciled_studio_database.js";
import type { ServerConfig } from "../../shared/infrastructure/config/server_config.js";

type WriteLine = (line: string) => void;

export interface ReindexCommandContext {
  readonly config: ServerConfig;
  readonly writeLine: WriteLine;
}

/**
 * The `novel-engine reindex` command body (#DR-004): every document's
 * current revision is replayed through the same index-write path a save
 * uses, inside one transaction, so the full-text index is rebuilt from the
 * content authority and drift — missing, stale, or orphaned rows — is
 * repaired idempotently. The reconciled opener gives the command the same
 * data-directory ownership as `backup`, so a running server refuses it; a
 * failed rebuild surfaces through the shared CLI error channel with a
 * non-zero exit and nothing committed. The printed summary reports the
 * post-rebuild document and index-row counts, never manuscript content.
 */
export async function runReindexCommand(context: ReindexCommandContext): Promise<number> {
  const database = await openReconciledStudioDatabase(context.config.databasePath);
  try {
    database.db.transaction((tx) => rebuildDocumentIndex(tx));
    const { documents, indexed } = documentIndexReconciliation(database.raw);
    context.writeLine(JSON.stringify({ documents, indexed }, null, 2));
    return 0;
  } finally {
    database.close();
  }
}
