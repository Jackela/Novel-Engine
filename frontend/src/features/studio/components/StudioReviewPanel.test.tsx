import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

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
        isLoadingHistory
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
});
