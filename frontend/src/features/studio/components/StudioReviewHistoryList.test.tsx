import { getByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { reviewSummary } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { StudioReviewHistoryList } from "./StudioReviewHistoryList";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

const summaries = [reviewSummary({ id: "review-1", issue_count: 2 })];

function content(overrides: Partial<Parameters<typeof StudioReviewHistoryList>[0]>) {
  return (
    <StudioReviewHistoryList
      summaries={summaries}
      historyInitialized
      hasOlderReviews
      isLoadingOlder={false}
      isLoadingHistory={false}
      olderError={null}
      onLoadOlderReviews={vi.fn()}
      {...overrides}
    />
  );
}

describe("StudioReviewHistoryList", () => {
  it("renders bounded summaries with an explicit load-older action", () => {
    const { container } = harness.mount(content({}));
    expect(container).toHaveTextContent("Review history");
    expect(container).toHaveTextContent("2 findings");
    expect(getByRole(container, "button", { name: "Load older reviews" })).toBeDefined();
  });

  it("keeps the retryable control while an older page fails", () => {
    const onLoadOlderReviews = vi.fn().mockResolvedValue(undefined);
    const { container } = harness.mount(
      content({ olderError: "Unable to load older reviews.", onLoadOlderReviews }),
    );
    const retry = getByRole(container, "button", { name: "Try again" });
    expect(retry).toBeDefined();
    const loadOlder = getByRole(container, "button", { name: "Load older reviews" });
    expect(loadOlder).toBeDefined();
    act(() => {
      loadOlder.click();
    });
    expect(onLoadOlderReviews).toHaveBeenCalledOnce();
  });

  it("moves terminal keyboard focus to the heading after the last page", () => {
    let hasOlderReviews = true;
    let isLoadingOlder = false;
    const mounted = harness.mount(content({ hasOlderReviews, isLoadingOlder }));
    const button = getByRole(mounted.container, "button", { name: "Load older reviews" });
    button.focus();
    act(() => {
      button.click();
      isLoadingOlder = true;
      hasOlderReviews = false;
      mounted.root.render(content({ hasOlderReviews, isLoadingOlder }));
    });
    const heading = mounted.container.querySelector("h3");
    if (heading === null) throw new Error("Expected the review-history heading.");

    act(() => {
      isLoadingOlder = false;
      mounted.root.render(content({ hasOlderReviews, isLoadingOlder }));
    });

    expect(document.activeElement).toBe(heading);
    expect(mounted.container).toHaveTextContent("All reviews loaded");
  });

  it("does not steal focus from a newer connected target on terminal success", () => {
    const elsewhere = document.createElement("button");
    document.body.append(elsewhere);
    elsewhere.focus();
    const mounted = harness.mount(content({ hasOlderReviews: false }));
    act(() => {
      mounted.root.render(content({ hasOlderReviews: false }));
    });
    expect(document.activeElement).toBe(elsewhere);
    elsewhere.remove();
  });
});
