import { randomUUID } from "node:crypto";
import { eq } from "drizzle-orm";

import type { DocumentWithCurrent } from "../../application/ports/document_store.js";
import { DEFAULT_LORE_STATUS } from "../../domain/kinds.js";
import { refreshDocumentIndex } from "./document_search.js";
import { documents } from "./schema.js";
import { insertRevision, type Tx } from "./studio_query_helpers.js";

/** One seed document's placement and body, written inside a caller transaction. */
interface SeedDocumentWrite {
  readonly projectId: string;
  readonly volumeId: string | null;
  readonly kind: string;
  readonly title: string;
  readonly position: number;
  readonly contentMarkdown: string;
  readonly metadataJson: string;
  /** The immutable first revision's provenance; seed and import paths differ. */
  readonly revisionSource: string;
  readonly now: Date;
  /**
   * addDocument stamps `updatedAt` again when linking the first revision;
   * project seeding and legacy import never touch it after the insert.
   */
  readonly touchDocumentUpdatedAt: boolean;
}

/**
 * The sole transaction-owned implementation of a document seed write: insert
 * the document row, mint its first immutable revision, link it as current,
 * and refresh the FTS entry — all inside the caller's transaction. Returns
 * the DocumentWithCurrent shape without a re-read.
 */
export function seedDocumentInTransaction(tx: Tx, seed: SeedDocumentWrite): DocumentWithCurrent {
  const document: typeof documents.$inferInsert = {
    id: randomUUID(),
    projectId: seed.projectId,
    kind: seed.kind,
    title: seed.title,
    position: seed.position,
    volumeId: seed.volumeId,
    currentRevisionId: null,
    createdAt: seed.now,
    updatedAt: seed.now,
  };
  tx.insert(documents).values(document).run();
  const revision = insertRevision(tx, {
    documentId: document.id,
    parentRevisionId: null,
    revisionNumber: 1,
    contentMarkdown: seed.contentMarkdown,
    metadataJson: seed.metadataJson,
    source: seed.revisionSource,
    now: seed.now,
  });
  tx.update(documents)
    .set(
      seed.touchDocumentUpdatedAt
        ? { currentRevisionId: revision.id, updatedAt: seed.now }
        : { currentRevisionId: revision.id },
    )
    .where(eq(documents.id, document.id))
    .run();
  refreshDocumentIndex(tx, {
    documentId: document.id,
    projectId: seed.projectId,
    title: seed.title,
    content: seed.contentMarkdown,
  });
  return {
    id: document.id,
    projectId: seed.projectId,
    kind: seed.kind,
    title: seed.title,
    position: seed.position,
    volumeId: seed.volumeId,
    beatRef: null,
    loreAliasesJson: "[]",
    loreStatus: DEFAULT_LORE_STATUS,
    currentRevisionId: revision.id,
    createdAt: seed.now,
    updatedAt: seed.now,
    currentRevision: revision,
  };
}
