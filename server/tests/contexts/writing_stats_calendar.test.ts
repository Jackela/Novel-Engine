import { describe, expect, it } from "vitest";

import {
  dayRow,
  newEmptyProject,
  openWritingStatsHarness,
  saveRevision,
  seedChapter,
  utcDayKeys,
  wordText,
} from "./writing_stats_harness.js";

describe("writing stats UTC calendar buckets (#653 T1)", () => {
  it("splits revisions one millisecond apart across the UTC-midnight boundary", async () => {
    const harness = await openWritingStatsHarness();
    try {
      const projectId = newEmptyProject(harness);
      const documentId = seedChapter(
        harness,
        projectId,
        "Chapter 1",
        100,
        new Date("2026-03-14T23:59:59.999Z"),
      );
      saveRevision(
        harness,
        projectId,
        documentId,
        wordText(150),
        "author",
        new Date("2026-03-15T00:00:00.000Z"),
      );

      const summary = harness.service.aggregateWritingStats(harness.principal, projectId);
      expect(dayRow(summary, "2026-03-14").words).toEqual({
        author: 100,
        aiAccepted: 0,
        restore: 0,
      });
      expect(dayRow(summary, "2026-03-15").words).toEqual({
        author: 50,
        aiAccepted: 0,
        restore: 0,
      });
    } finally {
      await harness.cleanup();
    }
  });

  it("counts a five-day author streak that AI-only days never extend", async () => {
    const harness = await openWritingStatsHarness();
    try {
      const projectId = newEmptyProject(harness);
      const documentId = seedChapter(
        harness,
        projectId,
        "Chapter 1",
        10,
        new Date("2026-03-01T09:00:00Z"),
      );
      // The UTC day before the chain holds only accepted proposal text.
      saveRevision(
        harness,
        projectId,
        documentId,
        wordText(90),
        "ai-accepted",
        new Date("2026-03-08T21:00:00Z"),
      );
      // Five consecutive author UTC days 03-10..03-14 (yesterday included);
      // the current UTC day (03-15) has no author revision yet.
      for (let day = 10; day <= 14; day += 1) {
        saveRevision(
          harness,
          projectId,
          documentId,
          wordText(90 + (day - 9) * 10),
          "author",
          new Date(`2026-03-${String(day).padStart(2, "0")}T09:00:00Z`),
        );
      }

      const summary = harness.service.aggregateWritingStats(harness.principal, projectId);
      expect(summary.streakDays).toBe(5);
      // The AI-only day renders as its own attribution, never author words.
      expect(dayRow(summary, "2026-03-08").words).toEqual({
        author: 0,
        aiAccepted: 80,
        restore: 0,
      });
    } finally {
      await harness.cleanup();
    }
  });

  it("keeps the streak while it ends yesterday and breaks it two days back", async () => {
    const harness = await openWritingStatsHarness();
    try {
      const endsYesterday = newEmptyProject(harness);
      const yesterdayDocument = seedChapter(
        harness,
        endsYesterday,
        "Chapter 1",
        20,
        new Date("2026-03-14T09:00:00Z"),
      );
      saveRevision(
        harness,
        endsYesterday,
        yesterdayDocument,
        wordText(30),
        "author",
        new Date("2026-03-15T00:30:00Z"),
      );
      expect(
        harness.service.aggregateWritingStats(harness.principal, endsYesterday).streakDays,
      ).toBe(2);

      // The last author UTC day is three days back and yesterday only holds
      // an accepted proposal: the chain is broken whatever its length was.
      const broken = newEmptyProject(harness);
      const brokenDocument = seedChapter(
        harness,
        broken,
        "Chapter 1",
        5,
        new Date("2026-03-12T09:00:00Z"),
      );
      saveRevision(
        harness,
        broken,
        brokenDocument,
        wordText(60),
        "ai-accepted",
        new Date("2026-03-14T10:00:00Z"),
      );
      const brokenSummary = harness.service.aggregateWritingStats(harness.principal, broken);
      expect(brokenSummary.streakDays).toBe(0);
      expect(dayRow(brokenSummary, "2026-03-14").words.author).toBe(0);
    } finally {
      await harness.cleanup();
    }
  });

  it("reports restore revisions as their own line that never extends the streak", async () => {
    const harness = await openWritingStatsHarness();
    try {
      const projectId = newEmptyProject(harness);
      const documentId = seedChapter(
        harness,
        projectId,
        "Chapter 1",
        40,
        new Date("2026-03-10T09:00:00Z"),
      );
      saveRevision(
        harness,
        projectId,
        documentId,
        wordText(120),
        "author",
        new Date("2026-03-11T09:00:00Z"),
      );
      // A restore replays the historic 40-word revision: history movement, so
      // its signed delta is attributed to `restore`, never to author words.
      saveRevision(
        harness,
        projectId,
        documentId,
        wordText(40),
        "restore",
        new Date("2026-03-15T09:00:00Z"),
      );

      const summary = harness.service.aggregateWritingStats(harness.principal, projectId);
      expect(dayRow(summary, "2026-03-15").words).toEqual({
        author: 0,
        aiAccepted: 0,
        restore: -80,
      });
      // The restore-only current UTC day does not extend the author streak.
      expect(summary.streakDays).toBe(0);
    } finally {
      await harness.cleanup();
    }
  });

  it("makes every weekly rollup equal the sum of its seven day rows", async () => {
    const harness = await openWritingStatsHarness();
    try {
      const projectId = newEmptyProject(harness);
      const documentId = seedChapter(
        harness,
        projectId,
        "Chapter 1",
        10,
        new Date("2026-03-15T08:00:00Z"),
      );
      saveRevision(
        harness,
        projectId,
        documentId,
        wordText(110),
        "ai-accepted",
        new Date("2026-03-14T08:00:00Z"),
      );
      saveRevision(
        harness,
        projectId,
        documentId,
        wordText(140),
        "author",
        new Date("2026-03-12T08:00:00Z"),
      );
      saveRevision(
        harness,
        projectId,
        documentId,
        wordText(150),
        "author",
        new Date("2026-03-05T08:00:00Z"),
      );

      const summary = harness.service.aggregateWritingStats(harness.principal, projectId);
      expect(summary.weekly).toHaveLength(4);
      expect(summary.weekly.map((week) => week.startDate)).toEqual([
        "2026-02-16",
        "2026-02-23",
        "2026-03-02",
        "2026-03-09",
      ]);
      for (const week of summary.weekly) {
        const weekDays = utcDayKeys(weekStartDate(week.startDate), 7);
        const days = summary.daily.filter((row) => weekDays.includes(row.date));
        expect(days).toHaveLength(7);
        expect(week.words).toEqual({
          author: days.reduce((total, row) => total + row.words.author, 0),
          aiAccepted: days.reduce((total, row) => total + row.words.aiAccepted, 0),
          restore: days.reduce((total, row) => total + row.words.restore, 0),
        });
      }
      expect(summary.weekly.at(-1)?.words).toEqual({ author: 40, aiAccepted: 100, restore: 0 });
      expect(summary.weekly.at(-2)?.words).toEqual({ author: 10, aiAccepted: 0, restore: 0 });
    } finally {
      await harness.cleanup();
    }
  });
});

/** The last UTC-day key of the week starting at `startDate`. */
function weekStartDate(startDate: string): string {
  const end = Date.parse(`${startDate}T00:00:00Z`) + 6 * 86_400_000;
  return new Date(end).toISOString().slice(0, 10);
}
