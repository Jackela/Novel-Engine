import { and, eq, inArray } from "drizzle-orm";

import type { ExportSourceDocument } from "../../application/ports/export_store.js";
import { ExportSourceInvalidatedError } from "../../domain/exceptions.js";
import { documentRevisions, documents } from "./schema.js";
import type { Tx } from "./studio_query_helpers.js";

const EXPORT_SOURCE_REVISION_BATCH_SIZE = 500;

interface CapturedExportRevisionRow {
  readonly documentId: string;
  readonly revisionId: string;
  readonly contentMarkdown: string;
  readonly metadataJson: string;
}

export function assertCapturedExportSource(
  tx: Tx,
  projectId: string,
  source: readonly ExportSourceDocument[],
): void {
  if (source.length === 0) return;
  assertUniqueCapturedIdentities(source);

  const available = new Map<string, Map<string, CapturedExportRevisionRow>>();
  let rowCount = 0;
  for (let offset = 0; offset < source.length; offset += EXPORT_SOURCE_REVISION_BATCH_SIZE) {
    const revisionIds = source
      .slice(offset, offset + EXPORT_SOURCE_REVISION_BATCH_SIZE)
      .map((document) => document.revisionId);
    const rows = readCapturedExportRevisionRows(tx, projectId, revisionIds);
    for (const row of rows) {
      const documentRows = available.get(row.documentId) ?? new Map();
      if (documentRows.has(row.revisionId)) {
        throw new Error("Export source revalidation returned a duplicate identity.");
      }
      documentRows.set(row.revisionId, row);
      available.set(row.documentId, documentRows);
      rowCount += 1;
    }
  }

  if (rowCount !== source.length) throw new ExportSourceInvalidatedError();
  for (const document of source) {
    const row = available.get(document.documentId)?.get(document.revisionId);
    if (row === undefined) throw new ExportSourceInvalidatedError();
    if (
      row.contentMarkdown !== document.contentMarkdown ||
      row.metadataJson !== document.metadataJson
    ) {
      throw new Error("Persisted immutable export source changed after capture.");
    }
  }
}

function assertUniqueCapturedIdentities(source: readonly ExportSourceDocument[]): void {
  const documentIds = new Set<string>();
  const revisionIds = new Set<string>();
  for (const document of source) {
    if (documentIds.has(document.documentId)) {
      throw new Error("Captured export source contains a duplicate document identity.");
    }
    if (revisionIds.has(document.revisionId)) {
      throw new Error("Captured export source contains a duplicate revision identity.");
    }
    documentIds.add(document.documentId);
    revisionIds.add(document.revisionId);
  }
}

function readCapturedExportRevisionRows(
  tx: Tx,
  projectId: string,
  revisionIds: string[],
): CapturedExportRevisionRow[] {
  return tx
    .select({
      documentId: documents.id,
      revisionId: documentRevisions.id,
      contentMarkdown: documentRevisions.contentMarkdown,
      metadataJson: documentRevisions.metadataJson,
    })
    .from(documents)
    .innerJoin(documentRevisions, eq(documentRevisions.documentId, documents.id))
    .where(and(eq(documents.projectId, projectId), inArray(documentRevisions.id, revisionIds)))
    .all();
}
