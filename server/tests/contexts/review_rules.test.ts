import { describe, expect, it } from "vitest";
import type { ReviewSnapshotDocument } from "../../src/contexts/studio/application/ports/studio_store.js";
import {
  chapterWordCounts,
  coerceEditorialFindings,
  isReviewDimension,
  REVIEW_DIMENSIONS,
} from "../../src/contexts/studio/application/review_rules.js";

function chapter(
  id: string,
  position: number,
  contentMarkdown = "word ".repeat(300),
): ReviewSnapshotDocument {
  return {
    documentId: id,
    snapshotDocumentId: `snap-${id}`,
    revisionId: `rev-${id}`,
    kind: "chapter",
    title: id,
    contentMarkdown,
    metadataJson: "{}",
    position,
  };
}

const documents = [chapter("chapter-1", 1), chapter("chapter-2", 2)];

describe("editorial finding coercion (#316)", () => {
  it("keeps findings that name a captured document with a closed dimension", () => {
    const issues = coerceEditorialFindings(
      {
        findings: [
          {
            document_id: "chapter-2",
            severity: "warning",
            dimension: "Pacing",
            message: "The middle sags.",
            suggestion: "Compress the travel.",
          },
        ],
      },
      documents,
    );
    expect(issues).toEqual([
      {
        documentId: "chapter-2",
        severity: "warning",
        code: "pacing",
        message: "The middle sags.",
        suggestion: "Compress the travel.",
        evidence: {},
      },
    ]);
  });

  it("orders by severity, then dimension, then document position", () => {
    const issues = coerceEditorialFindings(
      {
        findings: [
          { document_id: "chapter-2", severity: "warning", dimension: "pov", message: "b" },
          { document_id: "chapter-1", severity: "blocker", dimension: "continuity", message: "a" },
          { document_id: "chapter-1", severity: "warning", dimension: "dialogue", message: "c" },
        ],
      },
      documents,
    );
    expect(issues.map((issue) => issue.message)).toEqual(["a", "c", "b"]);
  });

  it("drops unknown dimensions, unknown documents, and empty messages", () => {
    const issues = coerceEditorialFindings(
      {
        findings: [
          { document_id: "chapter-1", severity: "warning", dimension: "vibes", message: "m" },
          { document_id: "ghost", severity: "warning", dimension: "pacing", message: "m" },
          { document_id: "chapter-1", severity: "warning", dimension: "pacing", message: "   " },
          { document_id: "chapter-1", severity: "warning", dimension: "pacing" },
        ],
      },
      documents,
    );
    expect(issues).toEqual([]);
  });

  it("falls back to warning for unknown severities and tolerates non-array payloads", () => {
    const issues = coerceEditorialFindings(
      {
        findings: [
          { document_id: "chapter-1", severity: "catastrophic", dimension: "pacing", message: "m" },
        ],
      },
      documents,
    );
    expect(issues.map((issue) => issue.severity)).toEqual(["warning"]);
    expect(coerceEditorialFindings({ findings: "nope" }, documents)).toEqual([]);
    expect(coerceEditorialFindings(null, documents)).toEqual([]);
  });

  it("exposes the closed dimension vocabulary", () => {
    expect(REVIEW_DIMENSIONS).toEqual(["pacing", "continuity", "pov", "foreshadowing", "dialogue"]);
    expect(isReviewDimension("pacing")).toBe(true);
    expect(isReviewDimension("vibes")).toBe(false);
  });

  it("feeds the deterministic provider a chapter manifest with word counts", () => {
    const manifest = chapterWordCounts([
      chapter("chapter-1", 1, ""),
      chapter("chapter-2", 2),
      { ...chapter("chapter-1", 3), documentId: "outline-1", kind: "outline" },
    ]);
    expect(manifest).toEqual([
      { id: "chapter-1", title: "chapter-1", words: 0, empty: true },
      { id: "chapter-2", title: "chapter-2", words: 300, empty: false },
    ]);
  });
});
