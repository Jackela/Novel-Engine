import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { job } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { useStudioJobs } from "./useStudioJobs";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: { ...actual.api, jobs: vi.fn<typeof actual.api.jobs>() },
  };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

describe("useStudioJobs proposal audit ownership", () => {
  it("returns an aborted project audit to retryable failure across an A to B to A cycle", async () => {
    const projectAAudit = deferred<{
      jobs: ReturnType<typeof job>[];
      next_cursor: string | null;
    }>();
    vi.mocked(api.jobs)
      .mockReturnValueOnce(projectAAudit.promise)
      .mockResolvedValueOnce({ jobs: [job()], next_cursor: null });
    let projectId = "project-a";
    let jobs: ReturnType<typeof useStudioJobs> | undefined;

    function Wrapper() {
      const [, setError] = useState<string | null>(null);
      jobs = useStudioJobs(projectId, setError);
      return null;
    }

    const { root } = harness.mount(<Wrapper />);
    let oldAudit: Promise<boolean> = Promise.resolve(true);
    act(() => {
      oldAudit = jobs?.auditProposalOutcome() ?? Promise.resolve(true);
    });
    const oldSignal = vi.mocked(api.jobs).mock.calls[0]?.[1]?.signal;

    projectId = "project-b";
    act(() => root.render(<Wrapper />));
    expect(oldSignal?.aborted).toBe(true);
    expect(jobs?.proposalAuditStatus).toBe("idle");
    expect(api.jobs).toHaveBeenCalledTimes(1);

    projectId = "project-a";
    act(() => root.render(<Wrapper />));
    expect(jobs?.proposalAuditStatus).toBe("audit_failed");
    expect(api.jobs).toHaveBeenCalledTimes(1);

    await act(async () => {
      projectAAudit.resolve({ jobs: [], next_cursor: null });
      await expect(oldAudit).resolves.toBe(false);
    });
    expect(jobs?.proposalAuditStatus).toBe("audit_failed");

    await act(async () => {
      await expect(jobs?.auditProposalOutcome()).resolves.toBe(true);
    });
    expect(api.jobs).toHaveBeenCalledTimes(2);
    expect(jobs?.proposalAuditStatus).toBe("audit_succeeded");
  });
});
