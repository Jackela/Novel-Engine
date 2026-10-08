import { and, eq, inArray, lt, lte, ne, sql } from "drizzle-orm";
import type { RevisionPins } from "../../application/ports/revision_pins.js";

import { documentRevisions, snapshotDocuments } from "./schema.js";
import type { Tx } from "./studio_query_helpers.js";

/**
 * Revision growth policy (#DR-047). Every editor autosave mints a full copy of
 * the body plus a full FTS rewrite, so an unbounded history is an unbounded
 * disk and index cost. This module owns the two write-time guards the store
 * applies to autosave writes: adjacent autosave revisions inside a short
 * window fold into the newest state, and unreferenced old autosave revisions
 * are pruned once they fall outside both the recency window and the newest-N
 * floor. Explicit saves (restores, accepted proposals, CLI imports) never
 * take part in either guard.
 */

/**
 * Adjacent autosave revisions closer together than this window fold into the
 * newest state: a continuous typing session keeps one revision per window
 * instead of one per keystroke burst. 30 s sits far above the editor's 1.5 s
 * autosave debounce and far below the interval at which a distinct revision
 * is meaningful.
 */
export const AUTOSAVE_COLLAPSE_WINDOW_MS = 30_000;

/** Unreferenced autosave revisions older than this many days become prunable. */
export const REVISION_RETENTION_DAYS = 90;

/**
 * The newest N revisions of a document are always retained, whatever their
 * age: the visible history page (50 rows) and any nearby author intent stay
 * intact, and pruning can never empty a document's history.
 */
export const REVISION_RETENTION_KEEP_NEWEST = 200;

/** One prune pass deletes at most this many rows; later saves drain the rest. */
const PRUNE_BATCH_LIMIT = 200;

const DAY_MS = 86_400_000;

/** The identity facts of one already-written revision a collapse decision needs. */
export interface PredecessorFacts {
  readonly revisionId: string;
  readonly parentRevisionId: string | null;
  readonly source: string;
  readonly createdAt: Date;
}

/** True when a snapshot pins the revision, which makes it immutable forever. */
export function isSnapshotReferencedRevision(tx: Tx, revisionId: string): boolean {
  const reference = tx
    .select({ id: snapshotDocuments.id })
    .from(snapshotDocuments)
    .where(eq(snapshotDocuments.revisionId, revisionId))
    .get();
  return reference !== undefined;
}

/**
 * True when an autosave may fold the predecessor away: the predecessor is an
 * author revision (autosave lineage — never a restore or an accepted
 * proposal), it was written inside the collapse window, it carries a parent
 * (the document's first revision is its origin record and is never folded
 * away), and no snapshot or in-flight evaluation pins it. A retained revision
 * is never a candidate.
 */
export function isCollapsibleAutosavePredecessor(
  tx: Tx,
  predecessor: PredecessorFacts,
  now: Date,
  revisionPins?: RevisionPins,
): boolean {
  if (predecessor.source !== "author" || predecessor.parentRevisionId === null) {
    return false;
  }
  const age = now.getTime() - predecessor.createdAt.getTime();
  if (age < 0 || age > AUTOSAVE_COLLAPSE_WINDOW_MS) {
    return false;
  }
  return (
    !revisionPins?.has(predecessor.revisionId) &&
    !isSnapshotReferencedRevision(tx, predecessor.revisionId)
  );
}

export interface RevisionPruneInput {
  readonly documentId: string;
  /** The revision written by this save; the newest row of the document. */
  readonly currentRevisionId: string;
  /** Its revision number: the high-water mark the newest-N floor anchors on. */
  readonly currentRevisionNumber: number;
  readonly now: Date;
}

/**
 * Prune old unreferenced autosave revisions of one document (DR-047c). A row
 * is prunable when all of these hold: its source is `author` (autosave
 * lineage), it is not the current revision, it sits below the newest-N floor,
 * it is older than the retention window, and neither a snapshot nor an
 * in-flight evaluation pins it.
 *
 * Surviving children of a pruned row are re-linked to the pruned row's own
 * parent before the delete, so the lineage chain never dangles — the stats
 * attribution keeps computing honest deltas instead of degrading a child to a
 * first-revision full count. Bodies and metadata of surviving revisions are
 * never touched.
 *
 * Returns the number of pruned rows; one pass is bounded by
 * `PRUNE_BATCH_LIMIT` and later saves continue where it stopped.
 */
export function pruneRetainedRevisions(
  tx: Tx,
  input: RevisionPruneInput,
  revisionPins?: RevisionPins,
): number {
  const boundary = input.currentRevisionNumber - REVISION_RETENTION_KEEP_NEWEST;
  if (boundary < 1) {
    return 0;
  }
  const cutoff = new Date(input.now.getTime() - REVISION_RETENTION_DAYS * DAY_MS);
  const candidates = tx
    .select({ id: documentRevisions.id })
    .from(documentRevisions)
    .where(
      and(
        eq(documentRevisions.documentId, input.documentId),
        eq(documentRevisions.source, "author"),
        lte(documentRevisions.revisionNumber, boundary),
        lt(documentRevisions.createdAt, cutoff),
        ne(documentRevisions.id, input.currentRevisionId),
        sql`NOT EXISTS (SELECT 1 FROM snapshot_documents AS referenced WHERE referenced.revision_id = ${documentRevisions.id})`,
      ),
    )
    .orderBy(documentRevisions.revisionNumber)
    .limit(PRUNE_BATCH_LIMIT)
    .all()
    .filter((candidate) => !revisionPins?.has(candidate.id));
  if (candidates.length === 0) {
    return 0;
  }
  const parents = new Map(
    tx
      .select({ id: documentRevisions.id, parentRevisionId: documentRevisions.parentRevisionId })
      .from(documentRevisions)
      .where(eq(documentRevisions.documentId, input.documentId))
      .all()
      .map((row) => [row.id, row.parentRevisionId] as const),
  );
  const pruned = new Set(candidates.map((candidate) => candidate.id));
  const survivingParent = (revisionId: string): string | null => {
    let parent = parents.get(revisionId) ?? null;
    while (parent !== null && pruned.has(parent)) {
      parent = parents.get(parent) ?? null;
    }
    return parent;
  };
  for (const candidate of candidates) {
    tx.update(documentRevisions)
      .set({ parentRevisionId: survivingParent(candidate.id) })
      .where(eq(documentRevisions.parentRevisionId, candidate.id))
      .run();
  }
  tx.delete(documentRevisions)
    .where(inArray(documentRevisions.id, [...pruned]))
    .run();
  return candidates.length;
}
