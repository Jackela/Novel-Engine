import type { Principal } from "../../../shared/application/ports/auth.js";
import type { RevisionSource } from "../domain/kinds.js";
import type { DocumentStore } from "./ports/document_store.js";
import type { StudioJobLedgerStore } from "./ports/job_ledger_store.js";
import { USAGE_DAILY_WINDOW_DAYS } from "./ports/project_usage.js";
import { scopeForPrincipal } from "./ports/studio_store.js";
import type {
  WritingStatsDayRow,
  WritingStatsHistory,
  WritingStatsSummary,
  WritingStatsWeekRow,
  WritingStatsWords,
} from "./ports/writing_stats.js";

/** One UTC day in milliseconds; every calendar bucket anchors on UTC days. */
const DAY_MS = 86_400_000;
/** A weekly rollup is exactly seven UTC days. */
const WEEK_DAYS = 7;

interface WritingStatsServiceOptions {
  readonly now?: (() => Date) | undefined;
}

/** One revision's attributed contribution: which UTC day and whose words. */
interface AttributedDelta {
  readonly dayIndex: number;
  readonly source: RevisionSource;
  readonly words: number;
}

function zeroWords(): WritingStatsWords {
  return { author: 0, aiAccepted: 0, restore: 0 };
}

function addWords(total: WritingStatsWords, source: RevisionSource, delta: number): void {
  if (source === "author") {
    total.author += delta;
  } else if (source === "ai-accepted") {
    total.aiAccepted += delta;
  } else if (source === "restore") {
    total.restore += delta;
  } else {
    // A closed enum with an unhandled member is a programming error: keep it
    // visible instead of silently misattributing a future source.
    throw new Error(`Unsupported revision source for stats attribution: ${source}.`);
  }
}

function utcDayIndex(timestamp: Date): number {
  return Math.floor(timestamp.getTime() / DAY_MS);
}

function utcDayKey(dayIndex: number): string {
  return new Date(dayIndex * DAY_MS).toISOString().slice(0, 10);
}

/**
 * Delta attribution over immutable revisions: each revision contributes its
 * unified word-count delta against its parent revision of the same document,
 * attributed to its own source. A document's first revision has no parent,
 * so its full count is attributed as-is; a dangling parent reference (whole
 * histories disappear only with their document, so this is unreachable in
 * practice) degrades to the same full-count attribution rather than
 * inventing a delta.
 */
function attributedDeltas(revisions: WritingStatsHistory["revisions"]): AttributedDelta[] {
  const byId = new Map(revisions.map((revision) => [revision.id, revision]));
  return revisions.map((revision) => {
    const parent =
      revision.parentRevisionId === null ? undefined : byId.get(revision.parentRevisionId);
    const base = parent === undefined ? 0 : parent.wordCount;
    return {
      dayIndex: utcDayIndex(revision.createdAt),
      source: revision.source,
      words: revision.wordCount - base,
    };
  });
}

/** The trailing usage-window day rows, zero-filled and oldest first (#653). */
function dailyRows(deltas: AttributedDelta[], now: Date): WritingStatsDayRow[] {
  const todayIndex = utcDayIndex(now);
  const firstIndex = todayIndex - (USAGE_DAILY_WINDOW_DAYS - 1);
  const rows = new Map<number, WritingStatsDayRow>();
  for (let index = firstIndex; index <= todayIndex; index += 1) {
    rows.set(index, { date: utcDayKey(index), words: zeroWords() });
  }
  for (const delta of deltas) {
    const row = rows.get(delta.dayIndex);
    if (row === undefined) continue;
    addWords(row.words, delta.source, delta.words);
  }
  return [...rows.values()];
}

/**
 * The complete trailing 7-UTC-day buckets of the window, oldest first.
 * Buckets anchor on the newest end so the current week (today included) is
 * always whole; only the window's oldest leftover days stay out of weekly.
 */
function weeklyRows(daily: WritingStatsDayRow[]): WritingStatsWeekRow[] {
  const weeks: WritingStatsWeekRow[] = [];
  for (let end = daily.length; end >= WEEK_DAYS; end -= WEEK_DAYS) {
    const days = daily.slice(end - WEEK_DAYS, end);
    const startDate = days.at(0)?.date;
    if (startDate === undefined) break;
    const words = zeroWords();
    for (const day of days) {
      words.author += day.words.author;
      words.aiAccepted += day.words.aiAccepted;
      words.restore += day.words.restore;
    }
    weeks.push({ startDate, words });
  }
  return weeks.reverse();
}

/**
 * The streak: consecutive UTC days with at least one `author` revision,
 * ending on the current UTC day or the one before it (so the streak
 * survives until the UTC day is over). AI-only and restore-only days never
 * extend it.
 */
function authorDayStreak(deltas: AttributedDelta[], now: Date): number {
  const authorDays = new Set(
    deltas.filter((delta) => delta.source === "author").map((delta) => delta.dayIndex),
  );
  const today = utcDayIndex(now);
  const end = authorDays.has(today) ? today : authorDays.has(today - 1) ? today - 1 : null;
  if (end === null) return 0;
  let streak = 0;
  for (let day = end; authorDays.has(day); day -= 1) {
    streak += 1;
  }
  return streak;
}

/**
 * The writing-statistics aggregation (#653): word-count deltas per revision
 * against its parent, attributed to the revision's source and bucketed into
 * UTC days — the same anchor the usage aggregation's daily buckets use, so
 * stats day rows and usage day rows line up for the same project.
 * Everything is derived from already-recorded data; the usage summary is
 * the existing `aggregateProjectUsage` result reused verbatim, never a
 * second accounting.
 */
export class WritingStatsService {
  private readonly documents: DocumentStore;
  private readonly jobs: StudioJobLedgerStore;
  private readonly now: () => Date;

  constructor(
    documents: DocumentStore,
    jobs: StudioJobLedgerStore,
    options: WritingStatsServiceOptions,
  ) {
    this.documents = documents;
    this.jobs = jobs;
    this.now = options.now ?? (() => new Date());
  }

  /** The owner-scoped, rendered-ready summary the stats endpoint maps. */
  aggregateWritingStats(principal: Principal, projectId: string): WritingStatsSummary {
    const scope = scopeForPrincipal(principal);
    const now = this.now();
    const history = this.documents.readWritingStatsHistory(scope, projectId);
    const deltas = attributedDeltas(history.revisions);
    const daily = dailyRows(deltas, now);
    return {
      projectId,
      daily,
      weekly: weeklyRows(daily),
      streakDays: authorDayStreak(deltas, now),
      chapters: {
        total: history.chapters.length,
        started: history.chapters.filter((chapter) => chapter.currentWordCount > 0).length,
      },
      usage: this.jobs.aggregateProjectUsage(scope, projectId, now),
    };
  }
}
