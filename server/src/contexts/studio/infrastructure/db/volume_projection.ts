import { eq } from "drizzle-orm";

import { InvalidOperationError } from "../../../../shared/domain/exceptions.js";
import { documents, projects } from "./schema.js";
import type { Tx } from "./studio_query_helpers.js";

interface ReorderRow {
  id: string;
  kind: string;
  volumeId: string | null;
}

/**
 * Whole-set document reorder projected onto the fixed two-level structure
 * (ADR-0005): each volume keeps its submitted relative order inside that
 * volume; non-chapter documents keep the flat order among themselves. The
 * chapter reading order across volumes always resolves through volume
 * positions alone.
 */
export function projectOrderOntoVolumes(
  tx: Tx,
  rows: ReorderRow[],
  documentIds: string[],
  projectId: string,
  now: Date,
): void {
  const byId = new Map(rows.map((row) => [row.id, row]));
  const unique = new Set(documentIds);
  if (
    documentIds.length !== rows.length ||
    unique.size !== documentIds.length ||
    documentIds.some((id) => !byId.has(id))
  ) {
    throw new InvalidOperationError("Reorder must include every project document once.");
  }
  const nextInVolume = new Map<string, number>();
  let nextFlat = 0;
  for (const id of documentIds) {
    const row = byId.get(id);
    if (row === undefined) {
      throw new InvalidOperationError("Reorder must include every project document once.");
    }
    if (row.kind === "chapter") {
      if (row.volumeId === null) {
        throw new InvalidOperationError("Every chapter belongs to exactly one volume.");
      }
      const position = (nextInVolume.get(row.volumeId) ?? 0) + 1;
      nextInVolume.set(row.volumeId, position);
      applyDocumentPosition(tx, id, position, now);
    } else {
      nextFlat += 1;
      applyDocumentPosition(tx, id, nextFlat, now);
    }
  }
  tx.update(projects).set({ updatedAt: now }).where(eq(projects.id, projectId)).run();
}

function applyDocumentPosition(tx: Tx, documentId: string, position: number, now: Date): void {
  tx.update(documents).set({ position, updatedAt: now }).where(eq(documents.id, documentId)).run();
}
