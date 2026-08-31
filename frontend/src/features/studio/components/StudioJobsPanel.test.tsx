import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { job } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { StudioJobsPanel } from "./StudioJobsPanel";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

const jobs = [
  job({ id: "job-rewrite", operation: "rewrite", status: "failed", error: "Failed" }),
  job({ id: "job-continue", operation: "continue", status: "interrupted", error: "Stopped" }),
];

describe("StudioJobsPanel", () => {
  it("announces only Retry as busy while its jobs refresh settles", () => {
    const mounted = harness.mount(
      <StudioJobsPanel
        jobs={jobs}
        onLoadJobs={vi.fn()}
        onRetryJob={vi.fn()}
        isLoading
        loadingInitiator="retry"
        retryingJobId="job-continue"
      />,
    );
    const refresh = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Refresh jobs"]',
    );
    const retry = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Retrying continue"]',
    );

    expect(refresh).toBeDisabled();
    expect(refresh).not.toHaveAttribute("aria-busy");
    expect(retry).toBeDisabled();
    expect(retry).toHaveAttribute("aria-busy", "true");
    expect(mounted.container.querySelectorAll('button[aria-busy="true"]')).toHaveLength(1);
  });

  it("does not steal focus after retry when the author moved elsewhere", async () => {
    const completion = deferred<void>();
    const onRetryJob = vi.fn(() => completion.promise);
    const onLoadJobs = vi.fn();
    const mounted = harness.mount(
      <StudioJobsPanel jobs={jobs} onLoadJobs={onLoadJobs} onRetryJob={onRetryJob} />,
    );
    const retryButton = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Retry continue"]',
    );
    if (retryButton === null) throw new Error("Expected the second retry button.");

    act(() => {
      retryButton.click();
      mounted.root.render(
        <StudioJobsPanel
          jobs={jobs}
          onLoadJobs={onLoadJobs}
          onRetryJob={onRetryJob}
          retryingJobId="job-continue"
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
        <StudioJobsPanel
          jobs={jobs}
          onLoadJobs={onLoadJobs}
          onRetryJob={onRetryJob}
          retryingJobId={null}
        />,
      );
    });
    expect(document.activeElement).toBe(otherButton);
    expect(onRetryJob).toHaveBeenCalledWith("job-continue");
    otherButton.remove();
  });

  it("moves orphaned retry focus to Refresh jobs when the retry command disappears", async () => {
    const completion = deferred<void>();
    const onRetryJob = vi.fn(() => completion.promise);
    const onLoadJobs = vi.fn();
    const content = (currentJobs: typeof jobs, retryingJobId: string | null) => (
      <StudioJobsPanel
        jobs={currentJobs}
        onLoadJobs={onLoadJobs}
        onRetryJob={onRetryJob}
        retryingJobId={retryingJobId}
      />
    );
    const mounted = harness.mount(content(jobs, null));
    const retry = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Retry continue"]',
    );
    const refresh = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Refresh jobs"]',
    );
    if (retry === null || refresh === null) throw new Error("Expected Jobs commands.");

    retry.focus();
    act(() => {
      retry.click();
      mounted.root.render(content(jobs, "job-continue"));
    });
    await act(async () => {
      completion.resolve(undefined);
      await completion.promise;
    });
    act(() => {
      mounted.root.render(
        content(
          [jobs[0], job({ id: "job-continue", operation: "continue", status: "completed" })],
          null,
        ),
      );
    });

    expect(document.activeElement).toBe(refresh);
  });
});
