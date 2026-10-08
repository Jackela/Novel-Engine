import type { RevisionCaptureLease, RevisionPins } from "../application/ports/revision_pins.js";

/** Refcounted, app-instance-owned captures; independent evaluations release independently. */
export class RevisionRetentionPins implements RevisionPins {
  private readonly references = new Map<string, number>();

  acquire(revisionIds: readonly string[]): RevisionCaptureLease {
    const ids = new Set(revisionIds);
    for (const id of ids) this.references.set(id, (this.references.get(id) ?? 0) + 1);
    let released = false;
    return {
      release: () => {
        if (released) return;
        released = true;
        for (const id of ids) {
          const remaining = (this.references.get(id) ?? 1) - 1;
          if (remaining === 0) this.references.delete(id);
          else this.references.set(id, remaining);
        }
      },
    };
  }

  has(revisionId: string): boolean {
    return this.references.has(revisionId);
  }
}
