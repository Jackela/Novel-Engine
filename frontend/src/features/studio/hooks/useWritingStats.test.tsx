import { act, StrictMode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { WritingStats } from "@/app/types/studio";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { useWritingStats } from "./useWritingStats";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      writingStats: vi.fn<typeof actual.api.writingStats>(),
    },
  };
});

type HookResult = ReturnType<typeof useWritingStats>;

const mountHarness = createMountHarness();

afterEach(() => {
  mountHarness.cleanup();
  vi.resetAllMocks();
});

const utcDay = (offsetFromToday: number): string =>
  new Date(Date.now() + offsetFromToday * 86_400_000).toISOString().slice(0, 10);

/** A minimal, complete summary; `wordsToday` lands on the newest day row. */
function stats(projectId: string, wordsToday: number): WritingStats {
  return {
    project_id: projectId,
    streak_days: wordsToday > 0 ? 1 : 0,
    daily: Array.from({ length: 30 }, (_, index) => ({
      date: utcDay(index - 29),
      words:
        index === 29
          ? { author: wordsToday, ai_accepted: 0, restore: 0 }
          : { author: 0, ai_accepted: 0, restore: 0 },
    })),
    weekly: Array.from({ length: 4 }, (_, index) => ({
      start_date: utcDay(-27 + index * 7),
      words:
        index === 3
          ? { author: wordsToday, ai_accepted: 0, restore: 0 }
          : { author: 0, ai_accepted: 0, restore: 0 },
    })),
    chapters: { total: 1, started: wordsToday > 0 ? 1 : 0 },
    usage: {
      project_id: projectId,
      request_count: 0,
      prompt_tokens: 0,
      completion_tokens: 0,
      per_model: [],
      daily: [],
    },
  };
}

function renderStatsHook(initialProjectId: string, initialActive: boolean, strict = false) {
  let projectId = initialProjectId;
  let active = initialActive;
  let current: HookResult | undefined;

  function Harness(): null {
    current = useWritingStats(projectId, active);
    return null;
  }

  const content = () =>
    strict ? (
      <StrictMode>
        <Harness />
      </StrictMode>
    ) : (
      <Harness />
    );
  const { root } = mountHarness.mount(content());
  const render = () => root.render(content());

  return {
    result: () => {
      if (current === undefined) throw new Error("Expected stats hook result after render.");
      return current;
    },
    rerender: (nextProjectId: string, nextActive = active) => {
      projectId = nextProjectId;
      active = nextActive;
      act(render);
    },
  };
}

describe("useWritingStats", () => {
  it("stays idle while inactive and lazy-loads once on first activation", async () => {
    vi.mocked(api.writingStats).mockResolvedValue(stats("project-1", 0));
    const hook = renderStatsHook("project-1", false);
    await flushEffects();
    expect(api.writingStats).not.toHaveBeenCalled();
    expect(hook.result().stats).toBeNull();

    hook.rerender("project-1", true);
    await flushEffects();
    expect(api.writingStats).toHaveBeenCalledTimes(1);
    expect(hook.result().stats).toEqual(stats("project-1", 0));

    // Re-activating the already-loaded project does not fire a second load.
    hook.rerender("project-1", false);
    hook.rerender("project-1", true);
    await flushEffects();
    expect(api.writingStats).toHaveBeenCalledTimes(1);
  });

  it("aborts a duplicate in-flight submission and publishes only the latest result", async () => {
    const firstRequest = deferred<WritingStats>();
    const second = stats("project-1", 5);
    vi.mocked(api.writingStats)
      .mockReturnValueOnce(firstRequest.promise)
      .mockResolvedValueOnce(second);
    const hook = renderStatsHook("project-1", true);
    await flushEffects();
    expect(hook.result().isLoading).toBe(true);

    const firstSignal = vi.mocked(api.writingStats).mock.calls[0]?.[1]?.signal;
    await act(async () => {
      const reload = hook.result().reload();
      await Promise.resolve();
      firstRequest.resolve(stats("project-1", 99));
      await reload;
    });

    expect(firstSignal?.aborted).toBe(true);
    expect(hook.result().stats).toEqual(second);
    expect(hook.result().isLoading).toBe(false);
    expect(hook.result().error).toBeNull();
  });

  it("recovers from a load failure through retry", async () => {
    const recovered = stats("project-1", 3);
    vi.mocked(api.writingStats)
      .mockRejectedValueOnce(new Error("stats unavailable"))
      .mockResolvedValueOnce(recovered);
    const hook = renderStatsHook("project-1", true);
    await flushEffects();
    expect(hook.result().error).toBe("stats unavailable");
    expect(hook.result().stats).toBeNull();

    await act(async () => {
      await hook.result().reload();
    });

    expect(hook.result().stats).toEqual(recovered);
    expect(hook.result().error).toBeNull();
  });
});
