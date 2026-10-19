import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { job, projectWith, review, reviewSummary, reviewsPage } from "@/test/factories";
import { deferred, flushEffects } from "@/test/harness";
import { retryReviewHarness } from "./retryReviewHarness";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: { ...actual.api, reviews: vi.fn(), reviewDetail: vi.fn(), retryJob: vi.fn() },
  };
});

const project = projectWith([]);
const old = reviewSummary({ id: "review-old", project_id: project.id });
const older = reviewSummary({ id: "review-older", project_id: project.id });
const fresh = reviewSummary({ id: "review-fresh", project_id: project.id });
const completed = job({
  project_id: project.id,
  kind: "review",
  status: "completed",
  result: { review_id: fresh.id },
});
let mounted: ReturnType<typeof retryReviewHarness> | undefined;
afterEach(() => {
  mounted?.cleanup();
  mounted = undefined;
  vi.resetAllMocks();
});

async function ready() {
  vi.mocked(api.reviews).mockResolvedValue(reviewsPage([old, older], "older-cursor"));
  vi.mocked(api.reviewDetail).mockImplementation(async (_projectId, id) => review({ id }));
  mounted = retryReviewHarness(project);
  await flushEffects();
  return mounted;
}

async function retry(target: ReturnType<typeof retryReviewHarness>) {
  await act(async () => {
    await target.actions().retryJob("failed-review-job");
  });
}

describe("completed Review retry history", () => {
  it("waits for activation, resets an older selection, and reads only the fresh first page and detail", async () => {
    const target = await ready();
    act(() => target.history().selectReview(older.id));
    await flushEffects();
    target.activate(false);
    const detailReads = vi.mocked(api.reviewDetail).mock.calls.length;
    vi.mocked(api.retryJob).mockResolvedValue(completed);
    vi.mocked(api.reviews).mockResolvedValue(reviewsPage([fresh, old]));
    await retry(target);
    expect(target.reviewError()).toBeNull();
    expect(api.reviews).toHaveBeenCalledTimes(1);
    expect(api.reviewDetail).toHaveBeenCalledTimes(detailReads);
    expect(target.loadJobs).toHaveBeenCalledWith("retry");
    target.activate(true);
    await flushEffects();
    expect(api.reviews).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.reviews).mock.calls[1]?.[1]?.cursor).toBeUndefined();
    expect(api.reviewDetail).toHaveBeenCalledTimes(detailReads + 1);
    expect(target.history().detail.review?.id).toBe(fresh.id);
    expect(target.history().selectedReviewId).toBe(fresh.id);
  });

  it.each([
    { kind: "review" as const, status: "failed" as const },
    { kind: "export" as const, status: "completed" as const },
  ])("retains history for $status $kind retries", async ({ kind, status }) => {
    const target = await ready();
    target.activate(false);
    vi.mocked(api.retryJob).mockResolvedValue(job({ kind, status }));
    await retry(target);
    target.activate(true);
    await flushEffects();
    expect(target.invalidateReview).not.toHaveBeenCalled();
    expect(target.reviewError()).toBe("Previous Review failed");
    expect(api.reviews).toHaveBeenCalledTimes(1);
    expect(target.history().detail.review?.id).toBe(old.id);
  });

  it("invalidates completed Review before a failing Jobs refresh", async () => {
    const target = await ready();
    target.activate(false);
    vi.mocked(api.retryJob).mockResolvedValue(completed);
    target.loadJobs.mockRejectedValueOnce(new Error("Jobs unavailable"));
    vi.mocked(api.reviews).mockResolvedValue(reviewsPage([fresh]));
    await retry(target);
    expect(target.invalidateReview).toHaveBeenCalledOnce();
    expect(target.reviewError()).toBeNull();
    target.activate(true);
    await flushEffects();
    expect(target.history().detail.review?.id).toBe(fresh.id);
  });

  it("rejects a completed retry after its project owner changed", async () => {
    const target = await ready();
    const response = deferred<ReturnType<typeof job>>();
    vi.mocked(api.retryJob).mockReturnValue(response.promise);
    let pending!: Promise<void>;
    act(() => {
      pending = target.actions().retryJob("failed-review-job");
    });
    target.switchProject(projectWith([], { id: "other-project" }));
    await act(async () => {
      response.resolve(completed);
      await pending;
    });
    expect(target.invalidateReview).not.toHaveBeenCalled();
    expect(target.loadJobs).not.toHaveBeenCalled();
    expect(target.reviewError()).toBe("Previous Review failed");
  });

  it("aborts old page, detail and older reads and rejects their late outcomes", async () => {
    const target = await ready();
    const detail = deferred<ReturnType<typeof review>>();
    vi.mocked(api.reviewDetail).mockReturnValueOnce(detail.promise);
    act(() => target.history().selectReview(older.id));
    await flushEffects();
    const detailSignal = vi.mocked(api.reviewDetail).mock.calls.at(-1)?.[2]?.signal;
    const olderPage = deferred<ReturnType<typeof reviewsPage>>();
    vi.mocked(api.reviews).mockReturnValueOnce(olderPage.promise);
    let olderRead!: Promise<void>;
    act(() => {
      olderRead = target.history().loadOlder();
    });
    const olderSignal = vi.mocked(api.reviews).mock.calls.at(-1)?.[1]?.signal;
    const firstPage = deferred<ReturnType<typeof reviewsPage>>();
    vi.mocked(api.reviews).mockReturnValueOnce(firstPage.promise);
    let firstRead!: Promise<void>;
    act(() => {
      firstRead = target.history().retry();
    });
    const firstSignal = vi.mocked(api.reviews).mock.calls.at(-1)?.[1]?.signal;
    vi.mocked(api.retryJob).mockResolvedValue(completed);
    vi.mocked(api.reviews).mockResolvedValue(reviewsPage([fresh]));
    await retry(target);
    await flushEffects();
    expect([detailSignal?.aborted, olderSignal?.aborted, firstSignal?.aborted]).toEqual([
      true,
      true,
      true,
    ]);
    await act(async () => {
      detail.resolve(review({ id: older.id }));
      olderPage.resolve(reviewsPage([older]));
      firstPage.resolve(reviewsPage([old]));
      await Promise.all([olderRead, firstRead]);
    });
    expect(target.history().summaries.map((item) => item.id)).toEqual([fresh.id]);
    expect(target.history().detail.review?.id).toBe(fresh.id);
  });
});
