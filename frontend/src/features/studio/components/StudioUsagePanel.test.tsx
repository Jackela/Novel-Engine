import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { ProjectUsage, UsageDailyBucket } from "@/app/types/studio";
import { createMountHarness } from "@/test/harness";

import { StudioUsagePanel } from "./StudioUsagePanel";

function dailyBucketsWithToday(requests: number): UsageDailyBucket[] {
  const today = new Date().toISOString().slice(0, 10);
  return Array.from({ length: 30 }, (_, index) => ({
    date: new Date(Date.parse(`${today}T00:00:00Z`) - (29 - index) * 86_400_000)
      .toISOString()
      .slice(0, 10),
    request_count: index === 29 ? requests : 0,
    prompt_tokens: index === 29 ? 300 : 0,
    completion_tokens: index === 29 ? 100 : 0,
  }));
}

vi.mock("@/app/api", () => ({
  api: { usage: vi.fn() },
}));

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.clearAllMocks();
});

function renderUsagePanel(active: boolean): HTMLDivElement {
  return harness.mount(<StudioUsagePanel active={active} projectId="project-1" />).container;
}

const emptyUsage: ProjectUsage = {
  project_id: "project-1",
  request_count: 0,
  prompt_tokens: 0,
  completion_tokens: 0,
  per_model: [],
  daily: dailyBucketsWithToday(0),
};

const multiModelUsage: ProjectUsage = {
  project_id: "project-1",
  request_count: 1234,
  prompt_tokens: 120000,
  completion_tokens: 4500,
  per_model: [
    {
      model: "qwen-max",
      requests: 1000,
      prompt_tokens: 100000,
      completion_tokens: 4000,
    },
    {
      model: "mock",
      requests: 234,
      prompt_tokens: 20000,
      completion_tokens: 500,
    },
  ],
  daily: dailyBucketsWithToday(4),
};

function flush(): Promise<void> {
  return act(async () => {
    await Promise.resolve();
  });
}

describe("StudioUsagePanel", () => {
  beforeEach(() => {
    vi.mocked(api.usage).mockResolvedValue(emptyUsage);
  });

  it("renders an empty state without a per-model table when usage is empty", async () => {
    const container = renderUsagePanel(true);
    await flush();

    expect(api.usage).toHaveBeenCalledWith("project-1");
    expect(container.querySelector(".usage-table")).toBeNull();
    expect(container.textContent).toContain("No usage recorded yet.");
    expect(container.textContent).toContain("0");
  });

  it("renders totals cards and a per-model row per model with thousands separators", async () => {
    vi.mocked(api.usage).mockResolvedValue(multiModelUsage);
    const container = renderUsagePanel(true);
    await flush();

    const cards = Array.from(container.querySelectorAll(".usage-total-card"));
    expect(cards.map((card) => card.textContent)).toEqual([
      "1,234Requests",
      "120,000Prompt tokens",
      "4,500Completion tokens",
    ]);

    const rows = Array.from(container.querySelectorAll(".usage-table tbody tr"));
    expect(rows).toHaveLength(2);
    expect(rows[0].textContent).toContain("qwen-max");
    expect(rows[0].textContent).toContain("100,000");
    expect(rows[1].textContent).toContain("mock");
    expect(rows[1].textContent).toContain("500");
  });

  it("renders the 30-day daily bars above the per-model table (#384)", async () => {
    vi.mocked(api.usage).mockResolvedValue(multiModelUsage);
    const container = renderUsagePanel(true);
    await flush();

    const daily = container.querySelector(".usage-daily");
    expect(daily).not.toBeNull();
    if (daily === null) throw new Error("expected daily section");
    expect(daily?.querySelector("h3")?.textContent).toBe("Last 30 days");
    const dailyRows = Array.from(daily?.querySelectorAll(".usage-daily-row") ?? []);
    expect(dailyRows).toHaveLength(30);
    // Today's row (last) carries the only usage; bar width is set inline.
    const todayRow = dailyRows[dailyRows.length - 1];
    expect(todayRow.textContent).toContain("400");
    const bar = todayRow.querySelector<HTMLElement>(".usage-daily-bar");
    expect(bar?.style.width).toBe("100%");
    const zeroBar = dailyRows[0]?.querySelector<HTMLElement>(".usage-daily-bar");
    expect(zeroBar?.style.width).toBe("0%");
    // The daily section sits above the per-model table.
    const table = container.querySelector(".usage-table");
    expect(table).not.toBeNull();
    if (table === null) throw new Error("expected usage table");
    expect(daily.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0);
  });

  it("omits the daily section when no day has usage (empty state)", async () => {
    const container = renderUsagePanel(true);
    await flush();

    expect(container.querySelector(".usage-daily")).toBeNull();
    expect(container.textContent).toContain("No usage recorded yet.");
  });

  it("does not fetch while the tab is inactive", async () => {
    renderUsagePanel(false);
    await flush();
    expect(api.usage).not.toHaveBeenCalled();
  });
});
