import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { Review } from "@/app/types/studio";
import { review } from "@/test/factories";
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
  it("activates only the URL-selected review history and reuses settled project cache", async () => {
    vi.mocked(api.reviews).mockResolvedValue({ reviews: [] });
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

  it("suppresses a late result after leaving and reloads when the panel returns", async () => {
    const first = deferred<{ reviews: Review[] }>();
    const secondReview = review({ id: "review-2", project_id: "project-1" });
    vi.mocked(api.reviews)
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce({ reviews: [secondReview] });
    const mounted = renderHistories("review");
    await flushEffects();
    const firstSignal = vi.mocked(api.reviews).mock.calls[0]?.[1]?.signal;

    mounted.select("copilot");
    expect(firstSignal?.aborted).toBe(true);
    await act(async () => {
      first.resolve({ reviews: [review({ id: "stale", project_id: "project-1" })] });
      await first.promise;
    });
    expect(mounted.result().review.data).toEqual([]);

    mounted.select("review");
    await flushEffects();
    expect(api.reviews).toHaveBeenCalledTimes(2);
    expect(mounted.result().review.data).toEqual([secondReview]);
  });

  it("keeps failure distinct from empty success and retries only Review", async () => {
    vi.mocked(api.reviews)
      .mockRejectedValueOnce(new HttpError("Review service unavailable.", 503))
      .mockResolvedValueOnce({ reviews: [] });
    const mounted = renderHistories("review");
    await flushEffects();

    expect(mounted.result().review.phase).toBe("failure");
    expect(mounted.result().review.initialized).toBe(false);
    expect(mounted.result().review.error).toBe("Review service unavailable.");

    await act(async () => mounted.result().review.retry());
    expect(mounted.result().review.phase).toBe("success");
    expect(mounted.result().review.initialized).toBe(true);
    expect(mounted.result().review.data).toEqual([]);
  });

  it("lets a completed Review mutation replace and cancel an older history read", async () => {
    const history = deferred<{ reviews: Review[] }>();
    const createdReview = review({ id: "review-created", project_id: "project-1" });
    vi.mocked(api.reviews).mockReturnValueOnce(history.promise);
    const mounted = renderHistories("review");
    await flushEffects();
    const historySignal = vi.mocked(api.reviews).mock.calls[0]?.[1]?.signal;

    act(() => mounted.result().review.setData([createdReview]));
    expect(historySignal?.aborted).toBe(true);
    expect(mounted.result().review.data).toEqual([createdReview]);

    await act(async () => {
      history.resolve({ reviews: [review({ id: "stale", project_id: "project-1" })] });
      await history.promise;
    });
    expect(mounted.result().review.data).toEqual([createdReview]);
  });

  it("routes authentication loss without rechecking shell authority", async () => {
    vi.mocked(api.reviews).mockRejectedValueOnce(new HttpError("Authentication required.", 401));
    const authenticated = renderHistories("review");
    await flushEffects();
    expect(authenticated.onSessionLost).toHaveBeenCalledOnce();
    expect(authenticated.recheckProject).not.toHaveBeenCalled();
  });
});
