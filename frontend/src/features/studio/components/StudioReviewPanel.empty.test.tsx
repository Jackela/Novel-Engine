import { afterEach, expect, it, vi } from "vitest";
import { review, reviewSummary } from "@/test/factories";
import { createMountHarness } from "@/test/harness";
import { StudioReviewPanel } from "./StudioReviewPanel";

const harness = createMountHarness();
afterEach(() => harness.cleanup());

it("distinguishes a completed review with zero findings from a review that has never run", () => {
  const mounted = harness.mount(
    <StudioReviewPanel
      latestReview={review({ issues: [] })}
      summaries={[reviewSummary({ issue_count: 0 })]}
      onRunReview={vi.fn()}
    />,
  );
  expect(mounted.container.textContent).toContain("This review reported no findings.");
  expect(mounted.container.textContent).not.toContain("Run a review when ready.");
});

it.each([
  { detailLoading: true },
  { detailError: "Unable to read this review." },
  { historyInitialized: false },
  { latestReview: null },
])("does not manufacture a zero-findings result for unavailable detail: %j", (state) => {
  const mounted = harness.mount(
    <StudioReviewPanel
      latestReview={review({ issues: [] })}
      summaries={[reviewSummary({ issue_count: 0 })]}
      onRunReview={vi.fn()}
      {...state}
    />,
  );
  expect(mounted.container.textContent).not.toContain("This review reported no findings.");
});
