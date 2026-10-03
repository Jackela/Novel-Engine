import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { review, reviewSummary } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { StudioReviewPanel } from "./StudioReviewPanel";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

describe("StudioReviewPanel", () => {
  it("distinguishes pending and failed history from an empty successful history", () => {
    const pending = harness.mount(
      <StudioReviewPanel
        historyInitialized={false}
        historyPaging={{ isLoading: true, hasOlder: false, isLoadingOlder: false }}
        latestReview={null}
        summaries={[]}
        onRunReview={vi.fn()}
      />,
    );
    expect(pending.container.querySelector('[role="status"]')?.textContent).toContain(
      "Loading review history",
    );
    expect(pending.container.textContent).not.toContain("No review findings");

    act(() => {
      pending.root.render(
        <StudioReviewPanel
          historyError="Unable to load review history."
          historyInitialized={false}
          latestReview={null}
          summaries={[]}
          onRetryHistory={vi.fn()}
          onRunReview={vi.fn()}
        />,
      );
    });
    expect(pending.container.querySelector('[role="alert"]')?.textContent).toContain(
      "Unable to load review history.",
    );
    expect(pending.container.textContent).not.toContain("No review findings");
  });

  it("does not steal focus when the author moves to another connected control", async () => {
    const completion = deferred<void>();
    const onRunReview = vi.fn(() => completion.promise);
    const mounted = harness.mount(
      <StudioReviewPanel latestReview={null} summaries={[]} onRunReview={onRunReview} />,
    );
    const runButton = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Run review"]',
    );
    if (runButton === null) throw new Error("Expected the Run review button.");

    act(() => {
      runButton.click();
      mounted.root.render(
        <StudioReviewPanel
          latestReview={null}
          summaries={[]}
          onRunReview={onRunReview}
          isRunning
        />,
      );
    });
    const otherButton = document.createElement("button");
    document.body.appendChild(otherButton);
    otherButton.focus();

    await act(async () => {
      completion.resolve(undefined);
      await completion.promise;
    });
    expect(document.activeElement).toBe(otherButton);

    act(() => {
      mounted.root.render(
        <StudioReviewPanel
          latestReview={null}
          summaries={[]}
          onRunReview={onRunReview}
          isRunning={false}
        />,
      );
    });
    expect(document.activeElement).toBe(otherButton);
    otherButton.remove();
  });

  it("labels the provider and model that produced the current review (DR-024)", () => {
    const mounted = harness.mount(
      <StudioReviewPanel
        latestReview={review({ provider: "dashscope", model: "qwen3.5-flash" })}
        summaries={[]}
        onRunReview={vi.fn()}
      />,
    );

    expect(mounted.container.textContent).toContain("Reviewed by DashScope · qwen3.5-flash");
  });

  it("opens a history row's detail and marks the selected row (DR-042)", () => {
    const onSelectReview = vi.fn();
    const mounted = harness.mount(
      <StudioReviewPanel
        latestReview={review()}
        onSelectReview={onSelectReview}
        selectedReviewId="review-2"
        summaries={[reviewSummary({ id: "review-1" }), reviewSummary({ id: "review-2" })]}
        onRunReview={vi.fn()}
      />,
    );

    const rows = Array.from(
      mounted.container.querySelectorAll<HTMLButtonElement>(".studio-inspector__history-row"),
    );
    expect(rows).toHaveLength(2);
    expect(rows[1]?.getAttribute("aria-pressed")).toBe("true");

    act(() => {
      rows[0]?.click();
    });
    expect(onSelectReview).toHaveBeenCalledWith("review-1");
  });

  it("names the snapshot behind the review (DR-042)", () => {
    const mounted = harness.mount(
      <StudioReviewPanel
        latestReview={review({
          provider: "dashscope",
          snapshot_id: "12345678-aaaa-bbbb-cccc-1234567890ab",
        })}
        summaries={[]}
        onRunReview={vi.fn()}
      />,
    );

    expect(mounted.container.textContent).toContain("Review snapshot 12345678");
  });
});
