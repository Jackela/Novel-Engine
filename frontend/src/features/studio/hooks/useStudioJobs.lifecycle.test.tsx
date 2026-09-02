import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { JobsPage } from "@/app/apiWorkflowContract";
import { job } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { useStudioJobs } from "./useStudioJobs";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return { ...actual, api: { ...actual.api, jobs: vi.fn<typeof actual.api.jobs>() } };
});

const mountHarness = createMountHarness();
const fixture = job();

afterEach(() => {
  mountHarness.cleanup();
  vi.resetAllMocks();
});

function renderJobs(initialProjectId = "project-1") {
  let projectId = initialProjectId;
  let jobs: ReturnType<typeof useStudioJobs> | undefined;
  let error: string | null = null;
  let publishError: ((value: string | null) => void) | undefined;

  function Wrapper() {
    const [currentError, setError] = useState<string | null>(null);
    error = currentError;
    publishError = setError;
    jobs = useStudioJobs(projectId, setError);
    return null;
  }

  const { root } = mountHarness.mount(<Wrapper />);
  return {
    result: () => {
      if (!jobs) throw new Error("Expected jobs hook result.");
      return jobs;
    },
    error: () => error,
    setError: (value: string | null) => act(() => publishError?.(value)),
    rerender: (nextProjectId: string) => {
      projectId = nextProjectId;
      act(() => root.render(<Wrapper />));
    },
  };
}

describe("useStudioJobs lifecycle", () => {
  it("loads jobs and clears an owned stale error", async () => {
    vi.mocked(api.jobs).mockResolvedValue({ jobs: [fixture], next_cursor: null });
    const view = renderJobs();
    view.setError("Previous jobs refresh failed.");

    await act(async () => view.result().loadJobs());

    expect(view.result().jobs).toEqual([fixture]);
    expect(view.error()).toBeNull();
  });

  it("lets a newer first-page read supersede an earlier one", async () => {
    const earlier = deferred<JobsPage>();
    const latest = deferred<JobsPage>();
    vi.mocked(api.jobs).mockReturnValueOnce(earlier.promise).mockReturnValueOnce(latest.promise);
    const view = renderJobs();
    let first!: Promise<void>;
    let replacement!: Promise<void>;
    act(() => {
      first = view.result().loadJobs("refresh");
      replacement = view.result().loadJobs("refresh");
    });

    expect(api.jobs).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.jobs).mock.calls[0]?.[1]?.signal?.aborted).toBe(true);
    await act(async () => {
      earlier.resolve({ jobs: [], next_cursor: null });
      latest.resolve({ jobs: [fixture], next_cursor: null });
      await first;
      await replacement;
    });
    expect(view.result().jobs).toEqual([fixture]);
  });

  it("starts a fresh proposal audit after cancelling an earlier read", async () => {
    const earlier = deferred<JobsPage>();
    const audit = deferred<JobsPage>();
    vi.mocked(api.jobs).mockReturnValueOnce(earlier.promise).mockReturnValueOnce(audit.promise);
    const view = renderJobs();
    let earlierLoad!: Promise<void>;
    let audited!: Promise<boolean>;
    act(() => {
      earlierLoad = view.result().loadJobs("refresh");
      audited = view.result().auditProposalOutcome();
    });

    expect(vi.mocked(api.jobs).mock.calls[0]?.[1]?.signal?.aborted).toBe(true);
    expect(view.result().proposalAuditStatus).toBe("auditing");
    await act(async () => {
      earlier.resolve({ jobs: [], next_cursor: null });
      audit.resolve({ jobs: [fixture], next_cursor: null });
      await earlierLoad;
      await expect(audited).resolves.toBe(true);
    });
    expect(view.result().proposalAuditStatus).toBe("audit_succeeded");
  });

  it("keeps an unknown proposal gated when audit fails", async () => {
    vi.mocked(api.jobs).mockRejectedValue(new Error("audit unavailable"));
    const view = renderJobs();

    await act(async () => expect(view.result().auditProposalOutcome()).resolves.toBe(false));

    expect(view.result().proposalAuditStatus).toBe("audit_failed");
    expect(view.error()).toBeNull();
  });

  it("reports an initial jobs failure without inventing older history", async () => {
    vi.mocked(api.jobs).mockRejectedValue(new Error("jobs unavailable"));
    const view = renderJobs();

    await act(async () => view.result().loadJobs());

    expect(view.result().jobs).toEqual([]);
    expect(view.result().hasOlderJobs).toBe(false);
    expect(view.error()).toBe("jobs unavailable");
  });

  it("discards a previous project's reverse-order completion", async () => {
    const firstRequest = deferred<JobsPage>();
    const secondJob = job({ id: "job-project-2", project_id: "project-2" });
    vi.mocked(api.jobs)
      .mockReturnValueOnce(firstRequest.promise)
      .mockResolvedValueOnce({ jobs: [secondJob], next_cursor: null });
    const view = renderJobs("project-1");
    let firstLoad!: Promise<void>;
    act(() => {
      firstLoad = view.result().loadJobs();
    });

    view.rerender("project-2");
    await act(async () => view.result().loadJobs());
    const firstSignal = vi.mocked(api.jobs).mock.calls[0]?.[1]?.signal;
    await act(async () => {
      firstRequest.resolve({ jobs: [fixture], next_cursor: null });
      await firstLoad;
    });

    expect(firstSignal?.aborted).toBe(true);
    expect(view.result().jobs).toEqual([secondJob]);
  });
});
