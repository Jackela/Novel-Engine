import { getByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { LANGUAGE_STORAGE_KEY } from "@/app/i18n/language";
import type { WritingStats, WritingStatsWords } from "@/app/types/studio";
import { createMountHarness } from "@/test/harness";

import { StudioWritingStatsPanel } from "./StudioWritingStatsPanel";

const dayKey = (offsetFromToday: number): string =>
  new Date(Date.now() + offsetFromToday * 86_400_000).toISOString().slice(0, 10);

const zeroWords = (): WritingStatsWords => ({ author: 0, ai_accepted: 0, restore: 0 });

vi.mock("@/app/api", () => ({
  api: { writingStats: vi.fn() },
}));

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.clearAllMocks();
  window.localStorage.clear();
});

/**
 * A trailing-30-UTC-day window whose day rows take their words from
 * `wordsByOffset` (keyed by days before today); weekly rollups mirror the
 * service's complete-7-day buckets, oldest first.
 */
function writingStats(
  wordsByOffset: Record<number, WritingStatsWords> = {},
  overrides: Partial<WritingStats> = {},
): WritingStats {
  const daily = Array.from({ length: 30 }, (_, index) => ({
    date: dayKey(index - 29),
    words: wordsByOffset[index - 29] ?? zeroWords(),
  }));
  const weekly = Array.from({ length: 4 }, (_, index) => {
    const startOffset = -27 + index * 7;
    const words = zeroWords();
    for (let day = startOffset; day < startOffset + 7; day += 1) {
      const dayWords = wordsByOffset[day] ?? zeroWords();
      words.author += dayWords.author;
      words.ai_accepted += dayWords.ai_accepted;
      words.restore += dayWords.restore;
    }
    return { start_date: dayKey(startOffset), words };
  });
  return {
    project_id: "project-1",
    streak_days: 0,
    daily,
    weekly,
    chapters: { total: 0, started: 0 },
    usage: {
      project_id: "project-1",
      request_count: 0,
      prompt_tokens: 0,
      completion_tokens: 0,
      per_model: [],
      daily: [],
    },
    ...overrides,
  };
}

function renderStatsPanel(active: boolean): HTMLDivElement {
  return harness.mount(<StudioWritingStatsPanel active={active} projectId="project-1" />).container;
}

function flush(): Promise<void> {
  return act(async () => {
    await Promise.resolve();
  });
}

describe("StudioWritingStatsPanel", () => {
  beforeEach(() => {
    vi.mocked(api.writingStats).mockResolvedValue(writingStats());
  });

  it("renders a defined zero state for an empty project", async () => {
    const container = renderStatsPanel(true);
    await flush();

    expect(api.writingStats).toHaveBeenCalledWith("project-1", {
      signal: expect.any(AbortSignal),
    });
    expect(getByRole(container, "heading", { name: "Writing stats" })).toBeVisible();
    // Every summary card — stats and usage alike — renders an honest zero
    // instead of a placeholder.
    const cards = Array.from(container.querySelectorAll(".stats__total-card"));
    expect(cards.map((card) => card.textContent)).toEqual([
      "0Day streak",
      "0Chapters started",
      "0Words today",
      "0Requests",
      "0Prompt tokens",
      "0Completion tokens",
    ]);
    expect(container.textContent).toContain("0 of 0 chapters started");
    expect(container.textContent).toContain("No writing recorded yet.");
    expect(container.textContent).toContain("AI usage");
    expect(container.querySelector(".stats__table")).toBeNull();
  });

  it("renders the daily and weekly source split with its totals", async () => {
    vi.mocked(api.writingStats).mockResolvedValue(
      writingStats(
        {
          // Today: a 500-word author save, a 300-word accepted proposal, and
          // an honest -100 restore movement.
          0: { author: 500, ai_accepted: 300, restore: -100 },
          // Yesterday: author-only words.
          [-1]: { author: 220, ai_accepted: 0, restore: 0 },
        },
        {
          streak_days: 3,
          chapters: { total: 10, started: 7 },
          usage: {
            project_id: "project-1",
            request_count: 4,
            prompt_tokens: 300,
            completion_tokens: 100,
            per_model: [],
            daily: [],
          },
        },
      ),
    );

    const container = renderStatsPanel(true);
    await flush();

    const tables = Array.from(container.querySelectorAll("table.stats__table"));
    expect(tables).toHaveLength(2);
    const [dailyTable, weeklyTable] = tables;
    const dailyRows = Array.from(dailyTable?.querySelectorAll("tbody tr") ?? []);
    // Only days with words render; zero-filled days stay implicit.
    expect(dailyRows).toHaveLength(2);
    expect(dailyRows[0]?.textContent).toBe(`${dayKey(-1)}22000220`);
    expect(dailyRows[1]?.textContent).toBe(`${dayKey(0)}500300-100700`);
    // The newest whole week sums its seven UTC days, signed figures and all.
    const weeklyRows = Array.from(weeklyTable?.querySelectorAll("tbody tr") ?? []);
    expect(weeklyRows.at(-1)?.textContent).toBe(`${dayKey(-6)}720300-100920`);
    // Summary cards reflect the same aggregation.
    expect(container.textContent).toContain("3Day streak");
    expect(container.textContent).toContain("700Words today");
    expect(container.textContent).toContain("7 of 10 chapters started");
    expect(container.textContent).toContain("4Requests");
  });

  it("surfaces load failures through the alert region", async () => {
    vi.mocked(api.writingStats).mockRejectedValue(new Error("stats unavailable"));
    const container = renderStatsPanel(true);
    await flush();

    const alert = getByRole(container, "alert");
    expect(alert.textContent).toContain("stats unavailable");
  });

  it("renders the zh surface when the stored language is Chinese", async () => {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, "zh");
    const container = renderStatsPanel(true);
    await flush();

    expect(getByRole(container, "heading", { name: "写作统计" })).toBeVisible();
    expect(container.textContent).toContain("暂无写作记录。");
    expect(container.textContent).toContain("0 章中已开篇 0 章");
  });
});
