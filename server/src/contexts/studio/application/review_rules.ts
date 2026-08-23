import { wordCount } from "./payloads.js";

export interface SnapshotDocumentInput {
  id: string;
  kind: string;
  title: string;
  contentMarkdown: string;
}

export interface EditorialFinding {
  documentId: string;
  severity: "blocker" | "warning";
  code: "empty_chapter" | "thin_chapter";
  message: string;
  suggestion: string;
  evidence: Record<string, number>;
}

/**
 * Assess persisted snapshot content without reaching into storage or live
 * documents. The caller owns snapshot construction and finding persistence.
 */
export function inspectSnapshotDocuments(
  documents: readonly SnapshotDocumentInput[],
): EditorialFinding[] {
  const findings = documents.flatMap((document) => {
    if (document.kind !== "chapter") {
      return [];
    }
    const words = wordCount(document.contentMarkdown);
    const documentFindings: EditorialFinding[] = [];
    if (document.contentMarkdown.trim() === "") {
      documentFindings.push({
        documentId: document.id,
        severity: "blocker",
        code: "empty_chapter",
        message: `${document.title} has no manuscript content.`,
        suggestion: "Draft the chapter before exporting.",
        evidence: {},
      });
    }
    if (words < 250) {
      documentFindings.push({
        documentId: document.id,
        severity: "warning",
        code: "thin_chapter",
        message: `${document.title} contains only ${words} words.`,
        suggestion: "Develop the scene turn, consequence, and sensory detail.",
        evidence: { word_count: words },
      });
    }
    return documentFindings;
  });
  return findings.sort(
    (left, right) =>
      left.severity.localeCompare(right.severity) || left.code.localeCompare(right.code),
  );
}
