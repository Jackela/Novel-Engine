import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { Review } from "@/app/types/studio";
import { job, projectWith, review } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { useStudioActions } from "./useStudioActions";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      createReview: vi.fn<typeof actual.api.createReview>(),
      reviews: vi.fn<typeof actual.api.reviews>(),
    },
  };
});

const projectA = projectWith([]);
const reviewFixture = review({ project_id: projectA.id });
const reviewJob = job({
  id: "job-review-1",
  project_id: projectA.id,
  document_id: null,
  kind: "review",
  operation: "review",
  result: { review_id: reviewFixture.id },
});
const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

describe("useStudioActions project lifecycle", () => {
  it("aborts and discards a project A review refresh after its workbench switches to B", async () => {
    const reviewResponse = deferred<{ reviews: Review[] }>();
    const setReviews = vi.fn();
    const setError = vi.fn();
    let actions: ReturnType<typeof useStudioActions> | undefined;
    vi.mocked(api.createReview).mockResolvedValue(reviewJob);
    vi.mocked(api.reviews).mockReturnValue(reviewResponse.promise);

    function ProjectAWorkbench(): null {
      actions = useStudioActions({
        project: projectA,
        projectId: projectA.id,
        setProject: vi.fn(),
        setReviews,
        setError,
        setActiveId: vi.fn(),
        settingsForm: {
          title: projectA.title,
          description: projectA.description,
          provider: "mock",
        },
        loadJobs: vi.fn().mockResolvedValue(undefined),
      });
      return null;
    }

    const { container } = harness.mount(<ProjectAWorkbench />);
    let pendingReview: Promise<void> = Promise.resolve();
    act(() => {
      pendingReview = actions?.runReview() ?? Promise.resolve();
    });
    await vi.waitFor(() => expect(api.reviews).toHaveBeenCalledTimes(1));
    const reviewSignal = vi.mocked(api.reviews).mock.calls[0]?.[1]?.signal;
    setReviews.mockClear();
    setError.mockClear();

    // StudioPage keys the complete workbench by projectId. Unmounting A is the
    // commit-phase boundary before project B becomes interactive.
    harness.unmount(container);
    expect(reviewSignal?.aborted).toBe(true);
    await act(async () => {
      reviewResponse.resolve({ reviews: [reviewFixture] });
      await pendingReview;
    });

    expect(setReviews).not.toHaveBeenCalled();
    expect(setError).not.toHaveBeenCalled();
  });
});
