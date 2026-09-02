import { revisionWordCount } from "../domain/revision_word_count.js";
import type { EditorialIssueInput, ReviewSourceDocument } from "./ports/studio_store.js";

/**
 * The server-owned closed review vocabulary (#316): the LLM may only report
 * findings inside these dimensions and severities, so the Studio can render
 * them stably and a drifting model cannot invent categories.
 */
export const REVIEW_DIMENSIONS = [
  "pacing",
  "continuity",
  "pov",
  "foreshadowing",
  "dialogue",
] as const;
export type ReviewDimension = (typeof REVIEW_DIMENSIONS)[number];

export const REVIEW_SEVERITIES = ["blocker", "warning"] as const;
export type ReviewSeverity = (typeof REVIEW_SEVERITIES)[number];

const DIMENSION_SET: ReadonlySet<string> = new Set(REVIEW_DIMENSIONS);
const SEVERITY_RANK: Readonly<Record<string, number>> = { blocker: 0, warning: 1 };

export function isReviewDimension(value: string): value is ReviewDimension {
  return DIMENSION_SET.has(value);
}

function asNonEmptyString(value: unknown): string | null {
  return typeof value === "string" && value.trim() !== "" ? value.trim() : null;
}

/**
 * Coerce a provider's editorial output into persisted findings: entries are
 * kept only when they name a captured chapter document, use a closed
 * dimension (case-insensitive), and carry a message; unknown severities fall
 * back to `warning`; everything else is dropped rather than fabricated.
 */
export function coerceEditorialFindings(
  raw: unknown,
  documents: readonly ReviewSourceDocument[],
): EditorialIssueInput[] {
  const findings = (raw as { findings?: unknown } | null)?.findings;
  if (!Array.isArray(findings)) {
    return [];
  }
  const byDocumentId = new Map(documents.map((document) => [document.documentId, document]));
  const coerced: Array<{ issue: EditorialIssueInput; position: number }> = [];
  for (const entry of findings) {
    if (typeof entry !== "object" || entry === null) {
      continue;
    }
    const candidate = entry as Record<string, unknown>;
    const documentId = asNonEmptyString(candidate.document_id);
    const dimension = asNonEmptyString(candidate.dimension)?.toLowerCase() ?? "";
    const message = asNonEmptyString(candidate.message);
    if (documentId === null || !byDocumentId.has(documentId) || !isReviewDimension(dimension)) {
      continue;
    }
    if (message === null) {
      continue;
    }
    const severity =
      asNonEmptyString(candidate.severity)?.toLowerCase() === "blocker" ? "blocker" : "warning";
    coerced.push({
      issue: {
        documentId,
        severity,
        code: dimension,
        message,
        suggestion: asNonEmptyString(candidate.suggestion) ?? "",
        evidence: {},
      },
      position: byDocumentId.get(documentId)?.position ?? 0,
    });
  }
  return coerced
    .sort(
      (left, right) =>
        (SEVERITY_RANK[left.issue.severity] ?? 1) - (SEVERITY_RANK[right.issue.severity] ?? 1) ||
        left.issue.code.localeCompare(right.issue.code) ||
        left.position - right.position,
    )
    .map((entry) => entry.issue);
}

/** Word-count thresholds feed the deterministic provider's chapter checks. */
export const THIN_CHAPTER_WORDS = 250;

export function chapterWordCounts(
  documents: readonly ReviewSourceDocument[],
): Array<{ id: string; title: string; words: number; empty: boolean }> {
  return documents
    .filter((document) => document.kind === "chapter")
    .map((document) => ({
      id: document.documentId,
      title: document.title,
      words: revisionWordCount(document.contentMarkdown),
      empty: document.contentMarkdown.trim() === "",
    }));
}
