import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { ExportsPage } from "@/app/apiWorkflowContract";
import type { StudioExport } from "@/app/types/studio";
import { studioExport } from "@/test/factories";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { mergeRefreshedFirstPage, useExportHistory } from "./useExportHistory";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      exports: vi.fn<typeof actual.api.exports>(),
    },
  };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function page(exports: StudioExport[], nextCursor: string | null = null): ExportsPage {
  return { exports, next_cursor: nextCursor };
}

function renderExportHistory(initialActive: boolean, projectId = "project-1") {
  let active = initialActive;
  let current: ReturnType<typeof useExportHistory> | undefined;
  const recheckProject = vi.fn<(signal: AbortSignal) => Promise<boolean>>().mockResolvedValue(true);
  const onSessionLost = vi.fn();

  function Probe(): null {
    current = useExportHistory({ active, projectId, recheckProject, onSessionLost });
    return null;
  }

  const mounted = harness.mount(<Probe />);
  return {
    result: () => {
      if (!current) throw new Error("Expected export history hook result.");
      return current;
    },
    setActive: (nextActive: boolean) => {
      active = nextActive;
      act(() => mounted.root.render(<Probe />));
    },
    recheckProject,
    onSessionLost,
    unmount: () => harness.unmount(mounted.container),
  };
}

describe("useExportHistory", () => {
  it("loads one bounded first page only when the panel is active", async () => {
    vi.mocked(api.exports).mockResolvedValue(page([studioExport()], "cursor-1"));
    const mounted = renderExportHistory(false);
    await flushEffects();
    expect(api.exports).not.toHaveBeenCalled();

    mounted.setActive(true);
    await flushEffects();
    expect(api.exports).toHaveBeenCalledOnce();
    expect(vi.mocked(api.exports).mock.calls[0]?.[0]).toBe("project-1");
    expect(vi.mocked(api.exports).mock.calls[0]?.[1]?.cursor).toBeUndefined();
    expect(mounted.result().historyInitialized).toBe(true);
    expect(mounted.result().exports).toHaveLength(1);
    expect(mounted.result().hasOlderExports).toBe(true);
  });

  it("appends unique older summaries after an explicit action and keeps failures retryable", async () => {
    const older = studioExport({ id: "export-old", created_at: "2026-09-01T00:00:00Z" });
    vi.mocked(api.exports)
      .mockResolvedValueOnce(page([studioExport({ id: "export-new" })], "cursor-1"))
      .mockRejectedValueOnce(new HttpError("Older exports unavailable.", 503))
      .mockResolvedValueOnce(page([older]));
    const mounted = renderExportHistory(true);
    await flushEffects();

    await act(async () => mounted.result().onLoadOlderExports());
    expect(vi.mocked(api.exports).mock.calls[1]?.[1]?.cursor).toBe("cursor-1");
    expect(mounted.result().olderError).toBe("Older exports unavailable.");
    expect(mounted.result().exports).toHaveLength(1);
    expect(mounted.result().hasOlderExports).toBe(true);

    await act(async () => mounted.result().onLoadOlderExports());
    expect(mounted.result().exports.map((item) => item.id)).toEqual(["export-new", "export-old"]);
    expect(mounted.result().hasOlderExports).toBe(false);
    expect(mounted.result().olderError).toBeNull();
  });

  it("merges a bounded post-export first-page refresh without walking cursors", async () => {
    const fresh = studioExport({ id: "export-fresh", created_at: "2026-09-05T00:00:00Z" });
    const current = studioExport({ id: "export-new", created_at: "2026-09-04T00:00:00Z" });
    vi.mocked(api.exports).mockResolvedValue(page([current], "cursor-1"));
    const mounted = renderExportHistory(true);
    await flushEffects();

    act(() => mounted.result().applyRefreshedFirstPage(page([fresh, current], "cursor-1")));
    expect(mounted.result().exports.map((item) => item.id)).toEqual(["export-fresh", "export-new"]);
    expect(mounted.result().hasOlderExports).toBe(true);
    expect(api.exports).toHaveBeenCalledOnce();
  });

  it("rechecks shell authority for a scoped 404 and routes session loss", async () => {
    vi.mocked(api.exports).mockRejectedValueOnce(new HttpError("Not found.", 404));
    const mounted = renderExportHistory(true);
    await flushEffects();
    expect(mounted.recheckProject).toHaveBeenCalledOnce();
    expect(mounted.result().historyError).toBe("Export history is unavailable for this project.");

    harness.cleanup();
    vi.mocked(api.exports).mockRejectedValueOnce(new HttpError("Authentication required.", 401));
    const lost = renderExportHistory(true);
    await flushEffects();
    expect(lost.onSessionLost).toHaveBeenCalledOnce();
    expect(lost.recheckProject).not.toHaveBeenCalled();
  });

  it("aborts an older-page request on unmount without publishing", async () => {
    const olderPage = deferred<ExportsPage>();
    vi.mocked(api.exports)
      .mockResolvedValueOnce(page([studioExport()], "cursor-1"))
      .mockReturnValueOnce(olderPage.promise);
    const mounted = renderExportHistory(true);
    await flushEffects();

    const pending = act(() => mounted.result().onLoadOlderExports());
    const signal = vi.mocked(api.exports).mock.calls[1]?.[1]?.signal;
    mounted.unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      olderPage.resolve(page([studioExport({ id: "export-old" })]));
      await pending;
    });
  });
});

describe("mergeRefreshedFirstPage", () => {
  it("prepends new summaries and preserves a loaded tail with its cursor", () => {
    const current = page(
      [
        studioExport({ id: "export-b", created_at: "2026-09-03T00:00:00Z" }),
        studioExport({ id: "export-a", created_at: "2026-09-02T00:00:00Z" }),
      ],
      "cursor-old",
    );
    const refreshed = page(
      [
        studioExport({ id: "export-c", created_at: "2026-09-05T00:00:00Z" }),
        studioExport({ id: "export-b", created_at: "2026-09-03T00:00:00Z" }),
      ],
      "cursor-new",
    );
    expect(mergeRefreshedFirstPage(current, refreshed)).toEqual({
      exports: [
        expect.objectContaining({ id: "export-c" }),
        expect.objectContaining({ id: "export-b" }),
        expect.objectContaining({ id: "export-a" }),
      ],
      next_cursor: "cursor-old",
    });
  });

  it("replaces the cache when the fresh page exposes an unknown gap", () => {
    const current = page(
      [studioExport({ id: "export-z", created_at: "2026-08-01T00:00:00Z" })],
      "cursor-old",
    );
    const refreshed = page([studioExport({ id: "export-c" })], "cursor-new");
    expect(mergeRefreshedFirstPage(current, refreshed)).toEqual(refreshed);
  });

  it("adopts a terminal refreshed page wholesale", () => {
    const current = page([studioExport({ id: "export-a" })], "cursor-old");
    const refreshed = page([studioExport({ id: "export-c" })]);
    expect(mergeRefreshedFirstPage(current, refreshed)).toEqual(refreshed);
  });

  it("adopts the first page into an empty cache", () => {
    const refreshed = page([studioExport()], "cursor-1");
    expect(mergeRefreshedFirstPage(page([]), refreshed)).toEqual(refreshed);
  });
});
