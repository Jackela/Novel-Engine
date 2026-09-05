import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { ReviewsPage } from "@/app/types/studio";
import { review, reviewSummary, reviewsPage } from "@/test/factories";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { useReviewHistory } from "./useReviewHistory";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      reviews: vi.fn<typeof actual.api.reviews>(),
      reviewDetail: vi.fn<typeof actual.api.reviewDetail>(),
    },
  };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function renderReviewHistory(active: boolean, projectId = "project-1") {
  let current: ReturnType<typeof useReviewHistory> | undefined;
  const recheckProject = vi.fn<(signal: AbortSignal) => Promise<boolean>>().mockResolvedValue(true);
  const onSessionLost = vi.fn();

  function Probe(): null {
    current = useReviewHistory({
      enabled: true,
      inspector: active ? "review" : "copilot",
      projectId,
      recheckProject,
      onSessionLost,
    });
    return null;
  }

  harness.mount(<Probe />);
  return {
    result: () => {
      if (!current) throw new Error("Expected review history hook result.");
      return current;
    },
    recheckProject,
    onSessionLost,
  };
}

describe("useReviewHistory", () => {
  it("reads one cursorless first page and the newest detail on activation", async () => {
    const newest = reviewSummary({ id: "review-newest" });
    vi.mocked(api.reviews).mockResolvedValue(reviewsPage([newest], "cursor-1"));
    vi.mocked(api.reviewDetail).mockResolvedValue(review({ id: "review-newest" }));
    const mounted = renderReviewHistory(true);
    await flushEffects();

    expect(api.reviews).toHaveBeenCalledWith("project-1", { signal: expect.any(AbortSignal) });
    expect(vi.mocked(api.reviews).mock.calls[0]?.[1]?.cursor).toBeUndefined();
    expect(mounted.result().summaries).toEqual([newest]);
    expect(mounted.result().nextCursor).toBe("cursor-1");
    expect(api.reviewDetail).toHaveBeenCalledWith(
      "project-1",
      "review-newest",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(mounted.result().detail.review?.id).toBe("review-newest");
  });

  it("skips the detail read for an empty first page", async () => {
    vi.mocked(api.reviews).mockResolvedValue(reviewsPage([]));
    const mounted = renderReviewHistory(true);
    await flushEffects();

    expect(mounted.result().summaries).toEqual([]);
    expect(api.reviewDetail).not.toHaveBeenCalled();
    expect(mounted.result().detail.review).toBeNull();
  });

  it("appends unique older summaries only after an explicit action and keeps failure retryable", async () => {
    const first = reviewSummary({ id: "review-1" });
    vi.mocked(api.reviews).mockResolvedValueOnce(reviewsPage([first], "cursor-1"));
    vi.mocked(api.reviewDetail).mockResolvedValue(review({ id: "review-1" }));
    vi.mocked(api.reviews).mockResolvedValueOnce(
      reviewsPage([reviewSummary({ id: "older-1" }), reviewSummary({ id: "older-2" })], null),
    );
    const mounted = renderReviewHistory(true);
    await flushEffects();

    await act(async () => {
      await mounted.result().loadOlder();
    });
    expect(api.reviews).toHaveBeenLastCalledWith("project-1", {
      cursor: "cursor-1",
      signal: expect.any(AbortSignal),
    });
    expect(mounted.result().summaries.map((summary) => summary.id)).toEqual([
      "review-1",
      "older-1",
      "older-2",
    ]);
    expect(mounted.result().nextCursor).toBeNull();
    expect(mounted.result().isLoadingOlder).toBe(false);
  });

  it("preserves committed summaries and cursor when an older page fails", async () => {
    vi.mocked(api.reviews).mockResolvedValueOnce(
      reviewsPage([reviewSummary({ id: "review-1" })], "cursor-1"),
    );
    vi.mocked(api.reviewDetail).mockResolvedValue(review({ id: "review-1" }));
    vi.mocked(api.reviews).mockRejectedValueOnce(new HttpError("Older reviews unavailable.", 503));
    const mounted = renderReviewHistory(true);
    await flushEffects();

    await act(async () => {
      await mounted.result().loadOlder();
    });
    expect(mounted.result().summaries.map((summary) => summary.id)).toEqual(["review-1"]);
    expect(mounted.result().nextCursor).toBe("cursor-1");
    expect(mounted.result().olderError).toBe("Older reviews unavailable.");

    vi.mocked(api.reviews).mockResolvedValueOnce(
      reviewsPage([reviewSummary({ id: "older-1" })], null),
    );
    await act(async () => {
      await mounted.result().loadOlder();
    });
    expect(mounted.result().summaries.map((summary) => summary.id)).toEqual([
      "review-1",
      "older-1",
    ]);
    expect(mounted.result().olderError).toBeNull();
  });

  it("de-duplicates an older page that repeats loaded summaries", async () => {
    const first = reviewSummary({ id: "review-1" });
    vi.mocked(api.reviews).mockResolvedValueOnce(reviewsPage([first], "cursor-1"));
    vi.mocked(api.reviewDetail).mockResolvedValue(review({ id: "review-1" }));
    vi.mocked(api.reviews).mockResolvedValueOnce(reviewsPage([first], null));
    const mounted = renderReviewHistory(true);
    await flushEffects();

    await act(async () => {
      await mounted.result().loadOlder();
    });
    expect(mounted.result().summaries.map((summary) => summary.id)).toEqual(["review-1"]);
    expect(mounted.result().nextCursor).toBeNull();
  });

  it("replaces the first page after a completed run and follows the new detail", async () => {
    vi.mocked(api.reviews).mockResolvedValueOnce(
      reviewsPage([reviewSummary({ id: "review-1" })], "cursor-1"),
    );
    vi.mocked(api.reviewDetail).mockResolvedValueOnce(review({ id: "review-1" }));
    const mounted = renderReviewHistory(true);
    await flushEffects();

    const created = reviewsPage(
      [reviewSummary({ id: "review-2" }), reviewSummary({ id: "review-1" })],
      null,
    );
    vi.mocked(api.reviewDetail).mockResolvedValueOnce(review({ id: "review-2" }));
    act(() => mounted.result().setFirstPage(created));
    await flushEffects();

    expect(mounted.result().summaries.map((summary) => summary.id)).toEqual([
      "review-2",
      "review-1",
    ]);
    expect(mounted.result().nextCursor).toBeNull();
    expect(api.reviewDetail).toHaveBeenLastCalledWith(
      "project-1",
      "review-2",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(mounted.result().detail.review?.id).toBe("review-2");
  });

  it("aborts an in-flight older read when a completed run replaces the page", async () => {
    vi.mocked(api.reviews).mockResolvedValueOnce(
      reviewsPage([reviewSummary({ id: "review-1" })], "cursor-1"),
    );
    vi.mocked(api.reviewDetail).mockResolvedValue(review({ id: "review-1" }));
    const older = deferred<ReviewsPage>();
    vi.mocked(api.reviews).mockReturnValueOnce(older.promise);
    const mounted = renderReviewHistory(true);
    await flushEffects();

    let olderPromise: Promise<void> = Promise.resolve();
    act(() => {
      olderPromise = mounted.result().loadOlder();
    });
    const olderSignal = vi.mocked(api.reviews).mock.calls[1]?.[1]?.signal;
    act(() => mounted.result().setFirstPage(reviewsPage([reviewSummary({ id: "review-2" })])));
    expect(olderSignal?.aborted).toBe(true);
    await act(async () => {
      older.resolve(reviewsPage([reviewSummary({ id: "stale-older" })]));
      await olderPromise;
    });
    expect(mounted.result().summaries.map((summary) => summary.id)).toEqual(["review-2"]);
    expect(mounted.result().isLoadingOlder).toBe(false);
  });

  it("does not prefetch while another inspector tab is selected", async () => {
    const mounted = renderReviewHistory(false);
    await flushEffects();
    expect(api.reviews).not.toHaveBeenCalled();
    expect(api.reviewDetail).not.toHaveBeenCalled();
    expect(mounted.result().summaries).toEqual([]);
    expect(mounted.result().detail.isLoading).toBe(false);
  });

  it("surfaces a retryable detail failure separately from history failures", async () => {
    vi.mocked(api.reviews).mockResolvedValueOnce(
      reviewsPage([reviewSummary({ id: "review-1" })], null),
    );
    vi.mocked(api.reviewDetail).mockRejectedValueOnce(new HttpError("Findings unavailable.", 503));
    const mounted = renderReviewHistory(true);
    await flushEffects();

    expect(mounted.result().detail.error).toBe("Findings unavailable.");
    expect(mounted.result().error).toBeNull();
    expect(mounted.result().summaries.map((summary) => summary.id)).toEqual(["review-1"]);

    vi.mocked(api.reviewDetail).mockResolvedValueOnce(review({ id: "review-1" }));
    await act(async () => {
      await mounted.result().detail.retry();
    });
    expect(mounted.result().detail.error).toBeNull();
    expect(mounted.result().detail.review?.id).toBe("review-1");
  });

  it("routes session loss on the detail read through the shared handler", async () => {
    vi.mocked(api.reviews).mockResolvedValueOnce(
      reviewsPage([reviewSummary({ id: "review-1" })], null),
    );
    vi.mocked(api.reviewDetail).mockRejectedValueOnce(
      new HttpError("Authentication required.", 401),
    );
    const mounted = renderReviewHistory(true);
    await flushEffects();

    expect(mounted.onSessionLost).toHaveBeenCalledOnce();
  });
});

describe("useReviewHistory project boundaries", () => {
  it("rejects a stale response after the project changes", async () => {
    let projectId = "project-1";
    let current: ReturnType<typeof useReviewHistory> | undefined;
    const recheckProject = vi
      .fn<(signal: AbortSignal) => Promise<boolean>>()
      .mockResolvedValue(true);
    const onSessionLost = vi.fn();

    function Probe(): null {
      current = useReviewHistory({
        enabled: true,
        inspector: "review",
        projectId,
        recheckProject,
        onSessionLost,
      });
      return null;
    }

    const first = deferred<ReviewsPage>();
    vi.mocked(api.reviews).mockReturnValueOnce(first.promise).mockResolvedValue(reviewsPage([]));
    const mounted = harness.mount(<Probe />);
    await flushEffects();
    const firstSignal = vi.mocked(api.reviews).mock.calls[0]?.[1]?.signal;

    projectId = "project-2";
    act(() => mounted.root.render(<Probe />));
    expect(firstSignal?.aborted).toBe(true);
    expect(current?.summaries).toEqual([]);

    await act(async () => {
      first.resolve(reviewsPage([reviewSummary({ id: "stale" })]));
      await first.promise;
    });
    expect(current?.summaries).toEqual([]);
    expect(api.reviews).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.reviews).mock.calls[1]?.[0]).toBe("project-2");
  });
});
