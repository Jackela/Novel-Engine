import type { DocumentWithCurrent, ProjectScope } from "./studio_store.js";

/**
 * Persistence-neutral volume row shape (ADR-0005): the fixed two-level
 * hierarchy keeps volumes in an ordered list per project.
 */
export interface VolumeRecord {
  id: string;
  projectId: string;
  title: string;
  position: number;
  createdAt: Date;
  updatedAt: Date;
}

export interface AddVolumeInput {
  title: string;
  now: Date;
}

/** Retitle input; positions change only through the volume reorder. */
export interface AlterVolumeInput {
  title: string;
  now: Date;
}

/** A chapter move lands at the tail of its target volume. */
export interface PlaceDocumentInput {
  volumeId: string;
  now: Date;
}

/**
 * Volume-port of the authoring core. Kept as its own module so the authoring
 * StudioStore stays within its file-size budget; methods avoid stems that
 * collide with frontend client methods (create/update/delete/reorder/move).
 */
export interface StudioVolumeStore {
  /** Volumes of the project in reading order. */
  findVolumes(scope: ProjectScope, projectId: string): VolumeRecord[];
  /** Append a new tail volume; rejects duplicate titles in the project. */
  addVolume(scope: ProjectScope, projectId: string, input: AddVolumeInput): VolumeRecord;
  alterVolume(
    scope: ProjectScope,
    projectId: string,
    volumeId: string,
    input: AlterVolumeInput,
  ): VolumeRecord;
  /**
   * Remove a non-last volume; its chapters merge into the nearest surviving
   * neighbour (preceding by reading order, else following). The LAST
   * remaining volume is refused so the project invariant holds.
   */
  dropVolume(scope: ProjectScope, projectId: string, volumeId: string): void;
  /** Place an existing chapter document at the tail of the target volume. */
  placeDocumentInVolume(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: PlaceDocumentInput,
  ): DocumentWithCurrent;
  /** Whole-set volume reorder: every volume exactly once, renumbered 1..n. */
  renumberVolumes(
    scope: ProjectScope,
    projectId: string,
    volumeIds: string[],
    now: Date,
  ): VolumeRecord[];
}
