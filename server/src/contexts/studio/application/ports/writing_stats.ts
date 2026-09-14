import type { RevisionSource } from "../../domain/kinds.js";
import type { ProjectUsageAggregate } from "./project_usage.js";

/**
 * One revision's stats evidence: identity, lineage, and the stored unified
 * word count. Bodies and metadata stay unread — attribution needs deltas
 * only.
 */
export interface WritingStatsRevisionRow {
  id: string;
  documentId: string;
  parentRevisionId: string | null;
  source: RevisionSource;
  wordCount: number;
  createdAt: Date;
}

/**
 * One chapter document's current content word count (0 when no current
 * revision exists). The completion share is a count over chapter documents,
 * so no ordering or body is projected.
 */
export interface WritingStatsChapterRow {
  documentId: string;
  currentWordCount: number;
}

/** The bounded revision-and-structure read the stats aggregation folds. */
export interface WritingStatsHistory {
  revisions: WritingStatsRevisionRow[];
  chapters: WritingStatsChapterRow[];
}

/** Word figures split by revision source: the attribution the view shows. */
export interface WritingStatsWords {
  /** Words from `author` revisions (editor saves, including first revisions). */
  author: number;
  /** Words from `ai-accepted` revisions (accepted proposal text). */
  aiAccepted: number;
  /**
   * Words from `restore` revisions (history movement, not new writing):
   * reported as their own line, never merged into author words.
   */
  restore: number;
}

/** One UTC day of attributed words; `date` is `YYYY-MM-DD`. */
export interface WritingStatsDayRow {
  date: string;
  words: WritingStatsWords;
}

/** One complete 7-UTC-day rollup; `startDate` is its first `YYYY-MM-DD`. */
export interface WritingStatsWeekRow {
  startDate: string;
  words: WritingStatsWords;
}

/** Chapter completion against existing content only — no targets, no plans. */
export interface WritingStatsChapterShare {
  /** Chapter documents of the project. */
  total: number;
  /** Chapters whose current content has a positive unified word count. */
  started: number;
}

/**
 * The project-scoped writing-statistics summary (#653): derived entirely
 * from revisions, structure, and the existing usage aggregation — nothing
 * is recorded. Daily rows and weekly rollups use UTC days, the same anchor
 * as the usage aggregation's daily buckets.
 */
export interface WritingStatsSummary {
  projectId: string;
  /** The trailing 30 UTC days (today included), zero-filled, oldest first. */
  daily: WritingStatsDayRow[];
  /** The trailing complete 7-UTC-day weeks within that window, oldest first. */
  weekly: WritingStatsWeekRow[];
  /**
   * Consecutive UTC days with at least one `author` revision, ending on the
   * current UTC day or the one before it.
   */
  streakDays: number;
  chapters: WritingStatsChapterShare;
  /** The existing project usage aggregation reused verbatim (#653). */
  usage: ProjectUsageAggregate;
}
