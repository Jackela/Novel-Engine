import type { Dispatch, SetStateAction } from "react";
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
const newest = job({ id: "job-newest" });

afterEach(() => {
  mountHarness.cleanup();
  vi.resetAllMocks();
});

function renderJobs(projectId = "project-1") {
  let currentProjectId = projectId;
  let result: ReturnType<typeof useStudioJobs> | undefined;
  let error: string | null = null;

  function Wrapper() {
    const [currentError, setError] = useState<string | null>(null);
    error = currentError;
    result = useStudioJobs(currentProjectId, setError as Dispatch<SetStateAction<string | null>>);
    return null;
  }

  const { root } = mountHarness.mount(<Wrapper />);
  return {
    result: () => {
      if (!result) throw new Error("Expected jobs hook result.");
      return result;
    },
    error: () => error,
    rerender: (nextProjectId: string) => {
      currentProjectId = nextProjectId;
      act(() => root.render(<Wrapper />));
    },
  };
}

describe("useStudioJobs pagination", () => {
  it("appends unique older jobs and coalesces the same cursor", async () => {
    const olderPage = deferred<JobsPage>();
    vi.mocked(api.jobs)
      .mockResolvedValueOnce({ jobs: [newest], next_cursor: "cursor-2" })
      .mockReturnValueOnce(olderPage.promise);
    const view = renderJobs();
    await act(async () => view.result().loadJobs());
    let first!: Promise<void>;
    let duplicate!: Promise<void>;
    act(() => {
      first = view.result().loadOlderJobs();
      duplicate = view.result().loadOlderJobs();
    });

    expect(duplicate).toBe(first);
    expect(api.jobs).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.jobs).mock.calls[1]?.[1]).toEqual(
      expect.objectContaining({ cursor: "cursor-2" }),
    );
    expect(view.result().loadingInitiator).toBe("load_older");

    await act(async () => {
      olderPage.resolve({
        jobs: [job({ id: newest.id }), job({ id: "job-older" }), job({ id: "job-older" })],
        next_cursor: null,
      });
      await first;
    });
    expect(view.result().jobs.map((item) => item.id)).toEqual([newest.id, "job-older"]);
    expect(view.result().hasOlderJobs).toBe(false);
  });

  it("preserves committed jobs and cursor when an older page fails", async () => {
    vi.mocked(api.jobs)
      .mockResolvedValueOnce({ jobs: [newest], next_cursor: "cursor-2" })
      .mockRejectedValueOnce(new Error("older unavailable"));
    const view = renderJobs();
    await act(async () => view.result().loadJobs());
    await act(async () => view.result().loadOlderJobs());

    expect(view.result().jobs).toEqual([newest]);
    expect(view.result().hasOlderJobs).toBe(true);
    expect(view.error()).toBe("older unavailable");
  });

  it.each(["auto", "refresh", "retry"] as const)(
    "lets a %s first-page intent invalidate an older append",
    async (initiator) => {
      const olderPage = deferred<JobsPage>();
      const replacement = deferred<JobsPage>();
      const replacementJob = job({ id: `job-${initiator}` });
      vi.mocked(api.jobs)
        .mockResolvedValueOnce({ jobs: [newest], next_cursor: "cursor-2" })
        .mockReturnValueOnce(olderPage.promise)
        .mockReturnValueOnce(replacement.promise);
      const view = renderJobs();
      await act(async () => view.result().loadJobs());
      let older!: Promise<void>;
      let fresh!: Promise<void>;
      act(() => {
        older = view.result().loadOlderJobs();
        fresh = view.result().loadJobs(initiator);
      });

      expect(vi.mocked(api.jobs).mock.calls[1]?.[1]?.signal?.aborted).toBe(true);
      expect(vi.mocked(api.jobs).mock.calls[2]?.[1]).not.toHaveProperty("cursor");
      await act(async () => {
        replacement.resolve({ jobs: [replacementJob], next_cursor: null });
        olderPage.resolve({ jobs: [job({ id: "stale-older" })], next_cursor: null });
        await fresh;
        await older;
      });
      expect(view.result().jobs).toEqual([replacementJob]);
    },
  );

  it("preserves a committed page when a same-project refresh fails", async () => {
    vi.mocked(api.jobs)
      .mockResolvedValueOnce({ jobs: [newest], next_cursor: "cursor-2" })
      .mockRejectedValueOnce(new Error("refresh unavailable"));
    const view = renderJobs();
    await act(async () => view.result().loadJobs());
    await act(async () => view.result().loadJobs("refresh"));

    expect(view.result().jobs).toEqual([newest]);
    expect(view.result().hasOlderJobs).toBe(true);
    expect(view.error()).toBe("refresh unavailable");
  });

  it("audits one fresh page and preserves history when it fails", async () => {
    const olderPage = deferred<JobsPage>();
    vi.mocked(api.jobs)
      .mockResolvedValueOnce({ jobs: [newest], next_cursor: "cursor-2" })
      .mockReturnValueOnce(olderPage.promise)
      .mockRejectedValueOnce(new Error("audit unavailable"));
    const view = renderJobs();
    await act(async () => view.result().loadJobs());
    let older!: Promise<void>;
    let audited!: Promise<boolean>;
    act(() => {
      older = view.result().loadOlderJobs();
      audited = view.result().auditProposalOutcome();
    });

    expect(api.jobs).toHaveBeenCalledTimes(3);
    expect(vi.mocked(api.jobs).mock.calls[1]?.[1]?.signal?.aborted).toBe(true);
    expect(vi.mocked(api.jobs).mock.calls[2]?.[1]).not.toHaveProperty("cursor");
    await act(async () => {
      await expect(audited).resolves.toBe(false);
      olderPage.resolve({ jobs: [job({ id: "stale-older" })], next_cursor: null });
      await older;
    });
    expect(view.result().jobs).toEqual([newest]);
    expect(view.result().hasOlderJobs).toBe(true);
    expect(view.result().proposalAuditStatus).toBe("audit_failed");
    expect(view.error()).toBeNull();
  });

  it("keeps a successful bounded audit settled while older pages succeed or fail", async () => {
    vi.mocked(api.jobs)
      .mockResolvedValueOnce({ jobs: [newest], next_cursor: "cursor-2" })
      .mockResolvedValueOnce({
        jobs: [job({ id: "job-older" })],
        next_cursor: "cursor-3",
      })
      .mockRejectedValueOnce(new Error("older unavailable"));
    const view = renderJobs();

    await act(async () => {
      await expect(view.result().auditProposalOutcome()).resolves.toBe(true);
    });
    expect(api.jobs).toHaveBeenCalledTimes(1);
    expect(vi.mocked(api.jobs).mock.calls[0]?.[1]).not.toHaveProperty("cursor");
    expect(view.result().proposalAuditStatus).toBe("audit_succeeded");
    expect(view.result().hasOlderJobs).toBe(true);

    await act(async () => view.result().loadOlderJobs());
    expect(view.result().proposalAuditStatus).toBe("audit_succeeded");
    expect(view.result().hasOlderJobs).toBe(true);

    await act(async () => view.result().loadOlderJobs());
    expect(view.result().proposalAuditStatus).toBe("audit_succeeded");
    expect(view.result().hasOlderJobs).toBe(true);
    expect(view.error()).toBe("older unavailable");
  });

  it("clears old jobs and cursor immediately across a failed project switch", async () => {
    vi.mocked(api.jobs)
      .mockResolvedValueOnce({ jobs: [newest], next_cursor: "cursor-2" })
      .mockRejectedValueOnce(new Error("new project unavailable"));
    const view = renderJobs("project-1");
    await act(async () => view.result().loadJobs());

    view.rerender("project-2");
    expect(view.result().jobs).toEqual([]);
    expect(view.result().hasOlderJobs).toBe(false);
    await act(async () => view.result().loadJobs());

    expect(view.result().jobs).toEqual([]);
    expect(view.result().hasOlderJobs).toBe(false);
    expect(view.error()).toBe("new project unavailable");
  });
});
