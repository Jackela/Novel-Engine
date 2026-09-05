import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { ReviewsPage } from "@/app/types/studio";
import { reviewSummary, reviewsPage } from "@/test/factories";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";
import type { InspectorTab } from "../studioConstants";

import { useLazyInspectorHistories } from "./useLazyInspectorHistories";

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

function renderHistories(initialInspector: InspectorTab = "copilot") {
  let inspector = initialInspector;
  let current: ReturnType<typeof useLazyInspectorHistories> | undefined;
  const recheckProject = vi.fn<(signal: AbortSignal) => Promise<boolean>>().mockResolvedValue(true);
  const onSessionLost = vi.fn();

  function Probe(): null {
    current = useLazyInspectorHistories({
      enabled: true,
      inspector,
      projectId: "project-1",
      recheckProject,
      onSessionLost,
    });
    return null;
  }

  const mounted = harness.mount(<Probe />);
  return {
    result: () => {
      if (!current) throw new Error("Expected histories hook result.");
      return current;
    },
    select: (nextInspector: InspectorTab) => {
      inspector = nextInspector;
      act(() => mounted.root.render(<Probe />));
    },
    recheckProject,
    onSessionLost,
  };
}

describe("useLazyInspectorHistories", () => {
  it("activates only the URL-selected history and reuses settled project cache", async () => {
    vi.mocked(api.reviews).mockResolvedValue(reviewsPage());
    const mounted = renderHistories();
    await flushEffects();
    expect(api.reviews).not.toHaveBeenCalled();

    mounted.select("review");
    await flushEffects();
    expect(api.reviews).toHaveBeenCalledOnce();
    expect(mounted.result().review.initialized).toBe(true);

    mounted.select("copilot");
    await flushEffects();
    expect(api.reviews).toHaveBeenCalledOnce();

    mounted.select("review");
    await flushEffects();
    expect(api.reviews).toHaveBeenCalledOnce();
  });

  it("suppresses a late review result after leaving and reloads when the panel returns", async () => {
    const first = deferred<ReviewsPage>();
    const secondPage = reviewsPage([reviewSummary({ id: "review-2" })]);
    vi.mocked(api.reviews).mockReturnValueOnce(first.promise).mockResolvedValueOnce(secondPage);
    const mounted = renderHistories("review");
    await flushEffects();
    const firstSignal = vi.mocked(api.reviews).mock.calls[0]?.[1]?.signal;

    mounted.select("copilot");
    expect(firstSignal?.aborted).toBe(true);
    await act(async () => {
      first.resolve(reviewsPage([reviewSummary({ id: "stale" })]));
      await first.promise;
    });
    expect(mounted.result().review.summaries).toEqual([]);

    mounted.select("review");
    await flushEffects();
    expect(api.reviews).toHaveBeenCalledTimes(2);
    expect(mounted.result().review.summaries).toEqual(secondPage.reviews);
  });

  it("keeps review failure distinct from empty success and retries only Review", async () => {
    vi.mocked(api.reviews)
      .mockRejectedValueOnce(new HttpError("Review service unavailable.", 503))
      .mockResolvedValueOnce(reviewsPage([]));
    const mounted = renderHistories("review");
    await flushEffects();

    expect(mounted.result().review.initialized).toBe(false);
    expect(mounted.result().review.error).toBe("Review service unavailable.");

    await act(async () => mounted.result().review.retry());
    expect(mounted.result().review.initialized).toBe(true);
    expect(mounted.result().review.summaries).toEqual([]);
  });

  it("lets a completed Review mutation replace and cancel an older history read", async () => {
    const history = deferred<ReviewsPage>();
    vi.mocked(api.reviews).mockReturnValueOnce(history.promise);
    const mounted = renderHistories("review");
    await flushEffects();
    const historySignal = vi.mocked(api.reviews).mock.calls[0]?.[1]?.signal;
    const created = reviewsPage([reviewSummary({ id: "review-created" })]);

    act(() => mounted.result().review.setFirstPage(created));
    expect(historySignal?.aborted).toBe(true);
    expect(mounted.result().review.summaries).toEqual(created.reviews);

    await act(async () => {
      history.resolve(reviewsPage([reviewSummary({ id: "stale" })]));
      await history.promise;
    });
    expect(mounted.result().review.summaries).toEqual(created.reviews);
  });

  it("routes authentication loss without rechecking shell authority", async () => {
    vi.mocked(api.reviews).mockRejectedValueOnce(new HttpError("Authentication required.", 401));
    const authenticated = renderHistories("review");
    await flushEffects();
    expect(authenticated.onSessionLost).toHaveBeenCalledOnce();
    expect(authenticated.recheckProject).not.toHaveBeenCalled();
  });
});
