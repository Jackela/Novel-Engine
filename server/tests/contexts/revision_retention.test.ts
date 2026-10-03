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

/**
 * DR-047 revision growth guards around an autosave: an unchanged body writes
 * nothing, an autosave folds an unreferenced author predecessor inside the
 * collapse window into the new revision, and snapshot-pinned or non-author
 * revisions are never folded. The retention prune lives in
 * revision_retention_prune.test.ts.
 */
describe("revision growth guards (#DR-047)", () => {
  it("writes nothing when an author save repeats the current body and metadata", async () => {
    const harness = await openRetentionHarness();
    try {
      const before = revisionRows(harness.studio);
      const saved = save(harness, "seed", { at: 1_000, autosave: true });

      expect(saved.currentRevisionId).toBe(harness.currentRevisionId);
      expect(revisionRows(harness.studio)).toHaveLength(before.length);
      const document = harness.store.documents.findDocument(
        harness.scope,
        harness.projectId,
        harness.documentId,
      );
      expect(document.currentRevisionId).toBe(harness.currentRevisionId);
    } finally {
      await harness.cleanup();
    }
  });

  it("folds an unreferenced autosave predecessor inside the collapse window", async () => {
    const harness = await openRetentionHarness();
    try {
      const first = save(harness, "draft 1", { at: 1_000 });
      const second = save(harness, "draft 2", { at: 2_000 });

      const rows = revisionRows(harness.studio);
      // The seed revision (1) survives as the document's origin; revision 2
      // folded away, and revision 3 inherits its parent.
      expect(rows.map((row) => row.revisionNumber)).toEqual([1, 3]);
      expect(rows.map((row) => row.contentMarkdown)).toEqual(["seed", "draft 2"]);
      const newest = rows.at(-1);
      expect(newest?.id).toBe(second.currentRevisionId);
      expect(newest?.parentRevisionId).toBe(harness.currentRevisionId);
      expect(first.currentRevisionId).not.toBe(second.currentRevisionId);
    } finally {
      await harness.cleanup();
    }
  });

  it("keeps the predecessor once the collapse window has passed", async () => {
    const harness = await openRetentionHarness();
    try {
      save(harness, "draft 1", { at: 1_000 });
      save(harness, "draft 2", { at: 61_000 });

      expect(revisionRows(harness.studio).map((row) => row.revisionNumber)).toEqual([1, 2, 3]);
    } finally {
      await harness.cleanup();
    }
  });

  it("never folds a revision a snapshot pins, and never folds a restore", async () => {
    const harness = await openRetentionHarness();
    try {
      const pinned = save(harness, "pinned draft", { at: 1_000 });
      const pinnedRevisionId = requireRevisionId(
        pinned.currentRevisionId,
        "Expected the pinned save to advance the document.",
      );
      pinSnapshot(harness.studio, {
        id: "snapshot-1",
        projectId: harness.projectId,
        documentId: harness.documentId,
        revisionId: pinnedRevisionId,
        createdAt: SEED_TIME,
      });

      save(harness, "after snapshot", { at: 2_000 });
      save(harness, "restored", { at: 3_000, source: "restore", autosave: false });
      const afterRestore = save(harness, "autosave again", { at: 4_000 });

      const rows = revisionRows(harness.studio);
      expect(rows.map((row) => row.revisionNumber)).toEqual([1, 2, 3, 4, 5]);
      expect(rows.find((row) => row.id === pinnedRevisionId)?.contentMarkdown).toBe("pinned draft");
      expect(rows.find((row) => row.revisionNumber === 4)?.source).toBe("restore");
      expect(afterRestore.currentRevisionId).toBe(rows.at(-1)?.id);
    } finally {
      await harness.cleanup();
    }
  });

  it("keeps a plain save's revisions out of the collapse and prune policy", async () => {
    const harness = await openRetentionHarness();
    try {
      for (let index = 1; index <= 3; index += 1) {
        save(harness, `plain ${index}`, { at: index * 1_000, autosave: false });
      }

      expect(revisionRows(harness.studio).map((row) => row.revisionNumber)).toEqual([1, 2, 3, 4]);
    } finally {
      await harness.cleanup();
    }
  });

  it("still writes a revision when only the metadata changed", async () => {
    const harness = await openRetentionHarness();
    try {
      const saved = save(harness, "seed", {
        at: 1_000,
        metadataJson: '{"prompt":"kept"}',
        autosave: false,
      });

      expect(saved.currentRevisionId).not.toBe(harness.currentRevisionId);
      expect(revisionRows(harness.studio)).toHaveLength(2);
    } finally {
      await harness.cleanup();
    }
  });

  it("keeps the FTS index on the folded revision's body", async () => {
    const harness = await openRetentionHarness();
    try {
      save(harness, "folded body", { at: 1_000 });
      const latest = save(harness, "final body", { at: 2_000 });
      const currentRevisionId = requireRevisionId(
        latest.currentRevisionId,
        "Expected the autosave to advance the document.",
      );

      const indexed = harness.studio.raw
        .prepare("SELECT content FROM document_search WHERE document_id = ?")
        .all(harness.documentId) as Array<{ content: string }>;
      expect(indexed).toHaveLength(1);
      expect(indexed[0]?.content).toBe("final body");
      expect(currentRevisionId).toBe(latestRevisionId(harness));
    } finally {
      await harness.cleanup();
    }
  });
});
