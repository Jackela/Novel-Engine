import { randomUUID } from "node:crypto";
import { asc, desc, eq } from "drizzle-orm";
import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import type {
  DocumentSummaryRecord,
  DocumentWithCurrent,
  ProjectScope,
} from "../application/ports/studio_store.js";
import type {
  AddVolumeInput,
  AlterVolumeInput,
  PlaceDocumentInput,
  StudioVolumeStore,
  VolumeRecord,
} from "../application/ports/volume_store.js";
import { DuplicateVolumeError, NotFoundError } from "../domain/exceptions.js";
import { documents, projects, volumes } from "./db/schema.js";
import {
  assertMergedVolumeChapterCapacity,
  assertProjectVolumeCapacity,
  assertVolumeChapterCapacity,
} from "./db/structure_capacity_checks.js";
import {
  documentSummaries,
  documentWithCurrent,
  isUniqueViolation,
  scopedDocument,
  scopedProject,
  scopedVolume,
  type Tx,
  type VolumeRow,
  volumesInOrder,
} from "./db/studio_query_helpers.js";
import { projectOrderOntoVolumes } from "./db/volume_projection.js";

/**
 * The volume half of the Drizzle studio store (ADR-0005): seeded default
 * volumes on creation/import live in the project part; this part owns the
 * CRUD, chapter placement, and reorder behavior behind the reading-order
 * invariants — at least one volume per project, chapters in exactly one.
 */
export class VolumeStorePart implements StudioVolumeStore {
  protected readonly db: StudioSqliteDatabase;

  constructor(db: StudioSqliteDatabase) {
    this.db = db;
  }

  findVolumes(scope: ProjectScope, projectId: string): VolumeRecord[] {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      return volumesInOrder(tx, project.id);
    });
  }

  addVolume(scope: ProjectScope, projectId: string, input: AddVolumeInput): VolumeRecord {
    try {
      return this.db.transaction((tx) => {
        const project = scopedProject(tx, scope, projectId);
        assertProjectVolumeCapacity(tx, project.id);
        const position = nextVolumePosition(tx, project.id);
        const row = insertVolume(tx, {
          projectId: project.id,
          title: input.title,
          position,
          now: input.now,
        });
        touchProject(tx, project.id, input.now);
        return row;
      });
    } catch (error) {
      if (isUniqueViolation(error)) {
        throw new DuplicateVolumeError(input.title);
      }
      throw error;
    }
  }

  alterVolume(
    scope: ProjectScope,
    projectId: string,
    volumeId: string,
    input: AlterVolumeInput,
  ): VolumeRecord {
    try {
      return this.db.transaction((tx) => {
        const current = scopedVolume(tx, scope, projectId, volumeId);
        tx.update(volumes)
          .set({ title: input.title, updatedAt: input.now })
          .where(eq(volumes.id, volumeId))
          .run();
        touchProject(tx, projectId, input.now);
        return { ...current, title: input.title, updatedAt: input.now };
      });
    } catch (error) {
      if (isUniqueViolation(error)) {
        throw new DuplicateVolumeError(input.title);
      }
      throw error;
    }
  }

  dropVolume(scope: ProjectScope, projectId: string, volumeId: string): void {
    this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const doomed = scopedVolume(tx, scope, projectId, volumeId);
      const ordered = volumesInOrder(tx, project.id);
      if (ordered.length <= 1) {
        throw new InvalidOperationError(
          "A project must keep at least one volume; create another before deleting this one.",
        );
      }
      const index = ordered.findIndex((volume) => volume.id === doomed.id);
      // Chapters merge into the nearest surviving neighbour so no chapter is
      // ever unplaced: the preceding volume in reading order, else the
      // following one. Tail positions continue after the survivor's chapters.
      const survivor = index > 0 ? ordered[index - 1] : ordered[index + 1];
      if (survivor === undefined) {
        throw new NotFoundError("Surviving volume not found.");
      }
      // The merge itself is a chapter-capacity write: refuse it before any
      // orphan moves (#461).
      assertMergedVolumeChapterCapacity(tx, survivor.id, doomed.id);
      const orphans = tx
        .select()
        .from(documents)
        .where(eq(documents.volumeId, doomed.id))
        .orderBy(asc(documents.position))
        .all();
      let tail = tailPosition(tx, survivor.id);
      for (const orphan of orphans) {
        tx.update(documents)
          .set({ volumeId: survivor.id, position: ++tail })
          .where(eq(documents.id, orphan.id))
          .run();
      }
      tx.delete(volumes).where(eq(volumes.id, doomed.id)).run();
      renumberVolumesAfterRemoval(tx, project.id);
    });
  }

  placeDocumentInVolume(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: PlaceDocumentInput,
  ): DocumentWithCurrent {
    return this.db.transaction((tx) => {
      const target = scopedVolume(tx, scope, projectId, input.volumeId);
      const document = scopedDocument(tx, scope, projectId, documentId);
      if (document.kind !== "chapter") {
        throw new InvalidOperationError("Only chapters belong to volumes.");
      }
      assertVolumeChapterCapacity(tx, target.id, { excludingDocumentId: document.id });
      const position = tailPosition(tx, target.id) + 1;
      tx.update(documents)
        .set({ volumeId: target.id, position, updatedAt: input.now })
        .where(eq(documents.id, document.id))
        .run();
      touchProject(tx, projectId, input.now);
      return documentWithCurrent(tx, projectId, document.id);
    });
  }

  renumberVolumes(
    scope: ProjectScope,
    projectId: string,
    volumeIds: string[],
    now: Date,
  ): VolumeRecord[] {
    return this.db.transaction((tx) => {
      scopedProject(tx, scope, projectId);
      const existing = volumesInOrder(tx, projectId);
      const byId = new Map(existing.map((volume) => [volume.id, volume]));
      const unique = new Set(volumeIds);
      if (
        volumeIds.length !== existing.length ||
        unique.size !== volumeIds.length ||
        volumeIds.some((id) => !byId.has(id))
      ) {
        throw new InvalidOperationError("Reorder must include every project volume once.");
      }
      for (const [index, id] of volumeIds.entries()) {
        tx.update(volumes)
          .set({ position: index + 1, updatedAt: now })
          .where(eq(volumes.id, id))
          .run();
      }
      touchProject(tx, projectId, now);
      const updated = volumesInOrder(tx, projectId);
      return volumeIds.map((id, orderIndex) => {
        const volume = updated.find((candidate) => candidate.id === id);
        if (volume === undefined) {
          throw new NotFoundError("Volume not found.");
        }
        // Position and timestamp restate what this transaction just wrote.
        return { ...volume, position: orderIndex + 1, updatedAt: now };
      });
    });
  }

  /** The authoring port's whole-set reorder, projected onto volumes. */
  renumberDocuments(
    scope: ProjectScope,
    projectId: string,
    documentIds: string[],
    now: Date,
  ): DocumentSummaryRecord[] {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const rows = tx
        .select({ id: documents.id, kind: documents.kind, volumeId: documents.volumeId })
        .from(documents)
        .where(eq(documents.projectId, project.id))
        .all();
      projectOrderOntoVolumes(tx, rows, documentIds, project.id, now);
      return documentSummaries(tx, project.id);
    });
  }
}

function nextVolumePosition(tx: Tx, projectId: string): number {
  const rows = tx
    .select({ position: volumes.position })
    .from(volumes)
    .where(eq(volumes.projectId, projectId))
    .orderBy(desc(volumes.position))
    .limit(1)
    .all();
  return (rows[0]?.position ?? 0) + 1;
}

function tailPosition(tx: Tx, volumeId: string): number {
  const rows = tx
    .select({ position: documents.position })
    .from(documents)
    .where(eq(documents.volumeId, volumeId))
    .orderBy(desc(documents.position))
    .limit(1)
    .all();
  return rows[0]?.position ?? 0;
}

/** The sole insert path keeps the shared timestamp/id conventions visible. */
export function insertVolume(
  tx: Tx,
  input: { projectId: string; title: string; position: number; now: Date },
): VolumeRow {
  const row: typeof volumes.$inferInsert = {
    id: randomUUID(),
    projectId: input.projectId,
    title: input.title,
    position: input.position,
    createdAt: input.now,
    updatedAt: input.now,
  };
  tx.insert(volumes).values(row).run();
  return row as VolumeRow;
}

/** The seeded volume of a freshly created or imported project (ADR-0005). */
export const DEFAULT_VOLUME_TITLE = "Default Volume";

/** Any volume write keeps the project's updated_at fresh for the library list. */
function touchProject(tx: Tx, projectId: string, now: Date): void {
  tx.update(projects).set({ updatedAt: now }).where(eq(projects.id, projectId)).run();
}

/** Close position gaps left by a removal so order stays dense and stable. */
function renumberVolumesAfterRemoval(tx: Tx, projectId: string): void {
  const ordered = volumesInOrder(tx, projectId);
  for (const [index, volume] of ordered.entries()) {
    if (volume.position !== index + 1) {
      tx.update(volumes)
        .set({ position: index + 1 })
        .where(eq(volumes.id, volume.id))
        .run();
    }
  }
}
