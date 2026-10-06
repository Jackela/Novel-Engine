import { describe, expect, it } from "vitest";

import {
  latestRevisionId,
  openRetentionHarness,
  pinSnapshot,
  requireRevisionId,
  revisionRows,
  SEED_TIME,
  save,
} from "./revision_retention_harness.js";

/** One minute of wall clock in milliseconds; every write stays outside the collapse window. */
const MINUTE_MS = 60_000;
const DAY_MS = 24 * 60 * 60_000;

/**
 * DR-047 retention guard: an autosave prunes unreferenced author revisions
 * that are older than the retention window and below the newest-N floor —
 * never a snapshot-pinned revision, never the current revision — and repairs
 * the lineage pointer of surviving children past the pruned ancestors.
 */
describe("revision retention prune (#DR-047)", () => {
  it("prunes old unreferenced autosave revisions beyond the newest floor", async () => {
    const harness = await openRetentionHarness();
    try {
      // The first six writes are dated far before the rest, so they are older
      // than the retention window once the newest write sets its `now`; every
      // write stays one minute apart, far outside the collapse window.
      const oldBase = SEED_TIME.getTime();
      const futureBase = oldBase + 200 * DAY_MS;
      const writeTime = (index: number): number =>
        index <= 6 ? oldBase + index * MINUTE_MS : futureBase + (index - 6) * MINUTE_MS;

      // The write at index N mints revision number N + 1 (the seed is 1); the
      // snapshot pins the revision of write index 3.
      let pinnedRevisionId = "";
      let latest = harness.currentRevisionId;
      for (let index = 1; index <= 205; index += 1) {
        const saved = save(harness, `autosave ${index}`, {
          at: writeTime(index) - oldBase,
        });
        latest = requireRevisionId(
          saved.currentRevisionId,
          "Expected every autosave to advance the document.",
        );
        if (index === 3) {
          pinnedRevisionId = latest;
          pinSnapshot(harness.studio, {
            id: "snapshot-old",
            projectId: harness.projectId,
            documentId: harness.documentId,
            revisionId: pinnedRevisionId,
            createdAt: new Date(writeTime(index)),
          });
        }
      }

      const rows = revisionRows(harness.studio);
      const numbers = rows.map((row) => row.revisionNumber);
      const pinnedNumber = 3 + 1;
      expect(pinnedRevisionId).not.toBe("");
      // Everything unreferenced below the newest-N floor and inside the
      // retention window's past is pruned.
      for (const pruned of [1, 2, 3, 5, 6]) {
        expect(numbers).not.toContain(pruned);
      }
      // The snapshot-pinned revision is immutable, and the latest survives
      // even though it is old and unreferenced.
      expect(numbers).toContain(pinnedNumber);
      expect(numbers).toContain(206);
      expect(rows.find((row) => row.revisionNumber === 206)?.id).toBe(latest);
      expect(latest).toBe(latestRevisionId(harness));
      // The newest-N floor keeps exactly the newest 200 revisions beyond the
      // pruned/foldable head of the chain.
      expect(numbers.filter((number) => number > 6)).toHaveLength(200);
      // Lineage repair: a surviving child of a pruned row points past the
      // pruned ancestors instead of keeping a dangling reference, and the
      // pinned revision itself re-links to the chain root it survived.
      expect(rows.find((row) => row.revisionNumber === 7)?.parentRevisionId).toBe(pinnedRevisionId);
      expect(rows.find((row) => row.revisionNumber === pinnedNumber)?.parentRevisionId).toBeNull();
      const survivingIds = new Set(rows.map((row) => row.id));
      for (const row of rows) {
        if (row.parentRevisionId !== null) {
          expect(survivingIds.has(row.parentRevisionId)).toBe(true);
        }
      }
    } finally {
      await harness.cleanup();
    }
  });
});
