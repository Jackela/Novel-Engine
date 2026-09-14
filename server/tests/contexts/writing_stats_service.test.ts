import { describe, expect, it } from "vitest";

import {
  dayRow,
  NOW,
  newEmptyProject,
  openWritingStatsHarness,
  recordUsage,
  saveRevision,
  seedChapter,
  usageBucket,
  utcDayKeys,
  wordText,
} from "./writing_stats_harness.js";

describe("writing stats summary service (#653 T1)", () => {
  it("returns defined zero states for a project with no revisions and no usage", async () => {
    const harness = await openWritingStatsHarness();
    try {
      const projectId = newEmptyProject(harness);
      const summary = harness.service.aggregateWritingStats(harness.principal, projectId);

      expect(summary.projectId).toBe(projectId);
      expect(summary.streakDays).toBe(0);
      expect(summary.chapters).toEqual({ total: 0, started: 0 });
      expect(summary.usage).toMatchObject({
        requestCount: 0,
        promptTokens: 0,
        completionTokens: 0,
        perModel: [],
      });
      expect(summary.daily).toHaveLength(30);
      expect(summary.daily.map((row) => row.date)).toEqual(utcDayKeys("2026-03-15", 30));
      for (const row of summary.daily) {
        expect(row.words).toEqual({ author: 0, aiAccepted: 0, restore: 0 });
      }
      expect(summary.weekly).toHaveLength(4);
      for (const week of summary.weekly) {
        expect(week.words).toEqual({ author: 0, aiAccepted: 0, restore: 0 });
      }
    } finally {
      await harness.cleanup();
    }
  });

  it("attributes first revisions in full and per-source deltas to the save's UTC day", async () => {
    const harness = await openWritingStatsHarness();
    try {
      const projectId = newEmptyProject(harness);
      const documentId = seedChapter(
        harness,
        projectId,
        "Chapter 1",
        500,
        new Date("2026-03-15T10:00:00Z"),
      );
      // Accepted proposal text adds 300 words (500 -> 800).
      saveRevision(
        harness,
        projectId,
        documentId,
        wordText(800),
        "ai-accepted",
        new Date("2026-03-15T11:00:00Z"),
      );
      // A later author cut of 100 words is an honest negative delta (800 -> 700).
      saveRevision(
        harness,
        projectId,
        documentId,
        wordText(700),
        "author",
        new Date("2026-03-15T12:00:00Z"),
      );

      const summary = harness.service.aggregateWritingStats(harness.principal, projectId);
      expect(dayRow(summary, "2026-03-15").words).toEqual({
        author: 500 - 100,
        aiAccepted: 300,
        restore: 0,
      });
    } finally {
      await harness.cleanup();
    }
  });

  it("counts chapter documents and their started share against current content", async () => {
    const harness = await openWritingStatsHarness();
    try {
      const projectId = newEmptyProject(harness);
      for (let index = 0; index < 10; index += 1) {
        seedChapter(
          harness,
          projectId,
          `Chapter ${index + 1}`,
          index < 7 ? 3 : 0,
          new Date("2026-03-15T06:00:00Z"),
        );
      }

      const summary = harness.service.aggregateWritingStats(harness.principal, projectId);
      expect(summary.chapters).toEqual({ total: 10, started: 7 });
    } finally {
      await harness.cleanup();
    }
  });

  it("reuses the usage aggregation verbatim on the same UTC-day rows", async () => {
    const harness = await openWritingStatsHarness();
    try {
      const projectId = newEmptyProject(harness);
      const boundary = new Date("2026-03-14T23:59:59.999Z");
      const documentId = seedChapter(harness, projectId, "Chapter 1", 100, boundary);
      recordUsage(harness, projectId, boundary, 12);
      saveRevision(
        harness,
        projectId,
        documentId,
        wordText(180),
        "ai-accepted",
        new Date("2026-03-15T00:00:00.000Z"),
      );
      recordUsage(harness, projectId, new Date("2026-03-15T00:00:00.000Z"), 8);

      const summary = harness.service.aggregateWritingStats(harness.principal, projectId);
      // One accounting: the usage summary is the existing aggregation result.
      expect(summary.usage).toEqual(
        harness.jobs.aggregateProjectUsage(harness.scope, projectId, NOW),
      );
      expect(summary.usage.requestCount).toBe(2);
      // Stats day rows and usage daily buckets share the UTC-day anchor.
      expect(summary.daily.map((row) => row.date)).toEqual(
        summary.usage.daily.map((bucket) => bucket.date),
      );
      // Identical instants bucket identically on both surfaces: the last
      // millisecond before UTC midnight stays on 03-14 everywhere.
      expect(dayRow(summary, "2026-03-14").words.author).toBe(100);
      expect(usageBucket(summary, "2026-03-14").requestCount).toBe(1);
      expect(dayRow(summary, "2026-03-15").words.aiAccepted).toBe(80);
      expect(usageBucket(summary, "2026-03-15").requestCount).toBe(1);
    } finally {
      await harness.cleanup();
    }
  });
});
