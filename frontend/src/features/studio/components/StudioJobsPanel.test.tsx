import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { jobSummary } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { StudioJobsPanel } from "./StudioJobsPanel";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

const jobs = [
  jobSummary({ id: "job-rewrite", operation: "rewrite", status: "failed", error: "Failed" }),
  jobSummary({
    id: "job-continue",
    operation: "continue",
    status: "interrupted",
    error: "Stopped",
  }),
];

describe("StudioJobsPanel", () => {
  it("does not offer retry for terminal import jobs", () => {
    const onRetryJob = vi.fn();
    const mounted = harness.mount(
      <StudioJobsPanel
        jobs={[
          jobSummary({ kind: "import", operation: "import", status: "failed" }),
          jobSummary({ kind: "import", operation: "import", status: "interrupted" }),
        ]}
        onLoadJobs={vi.fn()}
        onRetryJob={onRetryJob}
      />,
    );

    expect(mounted.container.querySelector('[aria-label^="Retry "]')).toBeNull();
    expect(onRetryJob).not.toHaveBeenCalled();
  });

  it("disables job retry without claiming a retry is running while proposal audit gates actions", () => {
    const onRetryJob = vi.fn();
    const mounted = harness.mount(
      <StudioJobsPanel jobs={jobs} onLoadJobs={vi.fn()} onRetryJob={onRetryJob} retryGated />,
    );

    const retries = mounted.container.querySelectorAll<HTMLButtonElement>(
      'button[aria-label^="Retry "]',
    );
    expect(retries).toHaveLength(2);
    for (const retry of retries) {
      expect(retry).toBeDisabled();
      expect(retry).not.toHaveAttribute("aria-busy", "true");
    }
    expect(mounted.container.querySelector('[aria-label^="Retrying "]')).toBeNull();
    expect(onRetryJob).not.toHaveBeenCalled();
  });

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
          [jobs[0], jobSummary({ id: "job-continue", operation: "continue", status: "completed" })],
          null,
        ),
      );
    });

    expect(document.activeElement).toBe(refresh);
  });

  it("names and marks only the older-page command busy", () => {
    const mounted = harness.mount(
      <StudioJobsPanel
        jobs={jobs}
        hasOlderJobs
        onLoadJobs={vi.fn()}
        onLoadOlderJobs={vi.fn()}
        onRetryJob={vi.fn()}
        isLoading
        loadingInitiator="load_older"
      />,
    );
    const loadOlder = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-busy="true"]',
    );

    expect(loadOlder?.textContent).toBe("Loading older jobs");
    expect(loadOlder).toBeDisabled();
    expect(mounted.container.querySelectorAll('button[aria-busy="true"]')).toHaveLength(1);
  });

  it("moves terminal load-older focus to Refresh jobs", async () => {
    const completion = deferred<void>();
    const onLoadOlderJobs = vi.fn(() => completion.promise);
    const content = (hasOlderJobs: boolean, isLoading: boolean) => (
      <StudioJobsPanel
        jobs={jobs}
        hasOlderJobs={hasOlderJobs}
        onLoadJobs={vi.fn()}
        onLoadOlderJobs={onLoadOlderJobs}
        onRetryJob={vi.fn()}
        isLoading={isLoading}
        loadingInitiator={isLoading ? "load_older" : null}
      />
    );
    const mounted = harness.mount(content(true, false));
    const loadOlder = mounted.container.querySelector<HTMLButtonElement>(
      "button:not([aria-label])",
    );
    const refresh = mounted.container.querySelector<HTMLButtonElement>(
      'button[aria-label="Refresh jobs"]',
    );
    if (!loadOlder || !refresh) throw new Error("Expected jobs pagination commands.");

    loadOlder.focus();
    act(() => {
      loadOlder.click();
      mounted.root.render(content(true, true));
    });
    await act(async () => {
      completion.resolve(undefined);
      mounted.root.render(content(false, false));
      await completion.promise;
    });

    expect(document.activeElement).toBe(refresh);
  });

  it("keeps failed load-older focus on its retryable command", async () => {
    const completion = deferred<void>();
    const onLoadOlderJobs = vi.fn(() => completion.promise);
    const content = (isLoading: boolean) => (
      <StudioJobsPanel
        jobs={jobs}
        hasOlderJobs
        onLoadJobs={vi.fn()}
        onLoadOlderJobs={onLoadOlderJobs}
        onRetryJob={vi.fn()}
        isLoading={isLoading}
        loadingInitiator={isLoading ? "load_older" : null}
      />
    );
    const mounted = harness.mount(content(false));
    const loadOlder = mounted.container.querySelector<HTMLButtonElement>(
      "button:not([aria-label])",
    );
    if (!loadOlder) throw new Error("Expected load older command.");

    loadOlder.focus();
    act(() => {
      loadOlder.click();
      mounted.root.render(content(true));
    });
    await act(async () => {
      completion.resolve(undefined);
      mounted.root.render(content(false));
      await completion.promise;
    });

    expect(document.activeElement).toBe(loadOlder);
    expect(loadOlder).toBeEnabled();
  });
});
