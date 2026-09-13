import { and, count, eq, ne } from "drizzle-orm";

import { splitOutlineBeats } from "../../application/outline_beats.js";
import {
  STRUCTURE_CAPACITY_LIMITS,
  StructureCapacityExceededError,
} from "../../domain/structure_capacity.js";
import { documents, volumes } from "./schema.js";
import type { Tx } from "./studio_query_helpers.js";

/**
 * In-transaction authoring-structure capacity assertions (#461). Each count
 * runs as a bounded `limit + 1` projection (the export source-count pattern),
 * so a saturated structure never materializes more than one row past its
 * limit, and the check-then-insert stays atomic inside SQLite's serialized
 * write transaction.
 */
export function assertProjectDocumentCapacity(tx: Tx, projectId: string): void {
  const limit = STRUCTURE_CAPACITY_LIMITS.project_documents;
  const bounded = tx
    .select({ id: documents.id })
    .from(documents)
    .where(eq(documents.projectId, projectId))
    .limit(limit + 1)
    .as("bounded_structure_project_documents");
  const row = tx.select({ value: count() }).from(bounded).get();
  if (row === undefined) {
    throw new Error("Structure project-document count query returned no result.");
  }
  if (row.value >= limit) {
    throw new StructureCapacityExceededError("project_documents", limit, row.value + 1);
  }
}

export function assertProjectVolumeCapacity(tx: Tx, projectId: string): void {
  const limit = STRUCTURE_CAPACITY_LIMITS.project_volumes;
  const bounded = tx
    .select({ id: volumes.id })
    .from(volumes)
    .where(eq(volumes.projectId, projectId))
    .limit(limit + 1)
    .as("bounded_structure_project_volumes");
  const row = tx.select({ value: count() }).from(bounded).get();
  if (row === undefined) {
    throw new Error("Structure project-volume count query returned no result.");
  }
  if (row.value >= limit) {
    throw new StructureCapacityExceededError("project_volumes", limit, row.value + 1);
  }
}

/**
 * Chapter placement excludes the moving document itself: re-placing a chapter
 * inside its current volume must not count it twice.
 */
export function assertVolumeChapterCapacity(
  tx: Tx,
  volumeId: string,
  options: { excludingDocumentId?: string } = {},
): void {
  const limit = STRUCTURE_CAPACITY_LIMITS.volume_chapters;
  const filter =
    options.excludingDocumentId === undefined
      ? and(eq(documents.volumeId, volumeId), eq(documents.kind, "chapter"))
      : and(
          eq(documents.volumeId, volumeId),
          eq(documents.kind, "chapter"),
          ne(documents.id, options.excludingDocumentId),
        );
  const observed = volumeChapterCount(tx, filter, limit);
  if (observed >= limit) {
    throw new StructureCapacityExceededError("volume_chapters", limit, observed + 1);
  }
}

/** Volume deletion merges the doomed volume's chapters into the survivor. */
export function assertMergedVolumeChapterCapacity(
  tx: Tx,
  survivorId: string,
  doomedId: string,
): void {
  const limit = STRUCTURE_CAPACITY_LIMITS.volume_chapters;
  const merged =
    volumeChapterCount(
      tx,
      and(eq(documents.volumeId, survivorId), eq(documents.kind, "chapter")),
      limit,
    ) +
    volumeChapterCount(
      tx,
      and(eq(documents.volumeId, doomedId), eq(documents.kind, "chapter")),
      limit,
    );
  if (merged > limit) {
    // Each side saturates at limit + 1, so the error constructor clamps the
    // reported total to limit + 1.
    throw new StructureCapacityExceededError("volume_chapters", limit, merged);
  }
}

/**
 * The outline-beat budget at the chokepoints that mint outline content:
 * document creation and every revision advance (author saves, restores, and
 * accepted AI proposals share `advanceDocumentInTransaction`).
 */
export function assertOutlineBeatCapacity(kind: string, contentMarkdown: string): void {
  if (kind !== "outline") return;
  const limit = STRUCTURE_CAPACITY_LIMITS.outline_beats;
  const observed = splitOutlineBeats(contentMarkdown).length;
  if (observed > limit) {
    throw new StructureCapacityExceededError("outline_beats", limit, observed);
  }
}

function volumeChapterCount(tx: Tx, filter: ReturnType<typeof and>, limit: number): number {
  const bounded = tx
    .select({ id: documents.id })
    .from(documents)
    .where(filter)
    .limit(limit + 1)
    .as("bounded_structure_volume_chapters");
  const row = tx.select({ value: count() }).from(bounded).get();
  if (row === undefined) {
    throw new Error("Structure volume-chapter count query returned no result.");
  }
  return row.value;
}
