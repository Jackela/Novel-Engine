/** A capture lease keeps revisions available until outcome landing; release is idempotent. */
export interface RevisionCaptureLease {
  release(): void;
}

/** App-owned retention coordination; it neither creates snapshots nor freezes edits. */
export interface RevisionPins {
  acquire(revisionIds: readonly string[]): RevisionCaptureLease;
  has(revisionId: string): boolean;
}
