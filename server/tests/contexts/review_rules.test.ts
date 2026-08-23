import { describe, expect, it } from "vitest";

import { inspectSnapshotDocuments } from "../../src/contexts/studio/application/review_rules.js";

describe("snapshot editorial rules", () => {
  it("flags a 249-word chapter using the shared word-count boundary", () => {
    const findings = inspectSnapshotDocuments([
      {
        id: "chapter-1",
        kind: "chapter",
        title: "The Crossing",
        contentMarkdown: Array.from({ length: 249 }, () => "word").join(" "),
      },
    ]);

    expect(findings).toEqual([
      {
        documentId: "chapter-1",
        severity: "warning",
        code: "thin_chapter",
        message: "The Crossing contains only 249 words.",
        suggestion: "Develop the scene turn, consequence, and sensory detail.",
        evidence: { word_count: 249 },
      },
    ]);
  });

  it("places an empty chapter blocker before its thin-chapter warning", () => {
    const findings = inspectSnapshotDocuments([
      {
        id: "chapter-1",
        kind: "chapter",
        title: "The Empty Room",
        contentMarkdown: "   \n\t",
      },
    ]);

    expect(findings).toEqual([
      {
        documentId: "chapter-1",
        severity: "blocker",
        code: "empty_chapter",
        message: "The Empty Room has no manuscript content.",
        suggestion: "Draft the chapter before exporting.",
        evidence: {},
      },
      {
        documentId: "chapter-1",
        severity: "warning",
        code: "thin_chapter",
        message: "The Empty Room contains only 0 words.",
        suggestion: "Develop the scene turn, consequence, and sensory detail.",
        evidence: { word_count: 0 },
      },
    ]);
  });

  it("skips non-chapters and leaves a 250-word chapter unflagged", () => {
    const findings = inspectSnapshotDocuments([
      {
        id: "outline-1",
        kind: "outline",
        title: "Beat sheet",
        contentMarkdown: "brief outline",
      },
      {
        id: "chapter-1",
        kind: "chapter",
        title: "At the boundary",
        contentMarkdown: Array.from({ length: 250 }, () => "word").join(" "),
      },
      {
        id: "chapter-2",
        kind: "chapter",
        title: "Needs work",
        contentMarkdown: "short scene",
      },
    ]);

    expect(findings).toEqual([
      {
        documentId: "chapter-2",
        severity: "warning",
        code: "thin_chapter",
        message: "Needs work contains only 2 words.",
        suggestion: "Develop the scene turn, consequence, and sensory detail.",
        evidence: { word_count: 2 },
      },
    ]);
  });
});
