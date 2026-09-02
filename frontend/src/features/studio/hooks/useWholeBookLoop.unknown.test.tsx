import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { ProposalOutcomeUnknownError, streamProposal } from "@/app/proposalStream";
import type { Project, StudioJob, StudioJobSummary } from "@/app/types/studio";
import { createMountHarness } from "@/test/harness";

import { useStudioJobs } from "./useStudioJobs";
import { useWholeBookLoop } from "./useWholeBookLoop";
import {
  baseProject,
  firstChapter,
  proposalJobFor,
  secondChapter,
} from "./useWholeBookLoop.test-harness";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      jobs: vi.fn<typeof actual.api.jobs>(),
      acceptProposal: vi.fn<typeof actual.api.acceptProposal>(),
      project: vi.fn<typeof actual.api.project>(),
    },
  };
});

vi.mock("@/app/proposalStream", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/proposalStream")>();
  return { ...actual, streamProposal: vi.fn<typeof actual.streamProposal>() };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function rejectable<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function renderUnknownLoop(): {
  readonly result: () => {
    readonly loop: ReturnType<typeof useWholeBookLoop>;
    readonly jobs: ReturnType<typeof useStudioJobs>;
  };
  readonly rerender: (project: Project) => void;
} {
  let activeProject = baseProject;
  let current:
    | {
        readonly loop: ReturnType<typeof useWholeBookLoop>;
        readonly jobs: ReturnType<typeof useStudioJobs>;
      }
    | undefined;

  function Wrapper(): null {
    const [, setProject] = useState<Project | null>(baseProject);
    const [, setError] = useState<string | null>(null);
    const jobs = useStudioJobs(activeProject.id, setError);
    const loop = useWholeBookLoop({
      projectId: activeProject.id,
      provider: "mock",
      setProject,
      loadJobs: jobs.loadJobs,
      proposalAudit: {
        status: jobs.proposalAuditStatus,
        audit: jobs.auditProposalOutcome,
        clear: jobs.clearProposalAudit,
        epoch: jobs.proposalAuditEpoch,
        isGated: jobs.isProposalAuditGated,
      },
    });
    current = { loop, jobs };
    return null;
  }

  const { root } = harness.mount(<Wrapper />);
  return {
    result: () => {
      if (!current) throw new Error("Expected whole-book audit harness.");
      return current;
    },
    rerender: (project) => {
      activeProject = project;
      act(() => root.render(<Wrapper />));
    },
  };
}

describe("useWholeBookLoop unknown outcome audit", () => {
  it("stops before accept or the next chapter and gates resume until audit succeeds", async () => {
    const firstStream = rejectable<StudioJob>();
    const secondStream = rejectable<StudioJob>();
    vi.mocked(streamProposal)
      .mockReturnValueOnce(firstStream.promise)
      .mockReturnValueOnce(secondStream.promise);
    const firstAudit = rejectable<{ jobs: StudioJobSummary[]; next_cursor: string | null }>();
    vi.mocked(api.jobs)
      .mockReturnValueOnce(firstAudit.promise)
      .mockResolvedValueOnce({ jobs: [], next_cursor: "older-summary-page" });
    const view = renderUnknownLoop();
    let run: Promise<void> = Promise.resolve();

    act(() => {
      run = view.result().loop.start([firstChapter, secondChapter]);
    });
    act(() => view.result().loop.stop());
    await act(async () => {
      firstStream.reject(new ProposalOutcomeUnknownError(new Error("done frame lost")));
      await vi.waitFor(() => expect(api.jobs).toHaveBeenCalledTimes(1));
    });

    expect(api.acceptProposal).not.toHaveBeenCalled();
    expect(streamProposal).toHaveBeenCalledTimes(1);
    expect(view.result().loop.phase).toEqual({
      kind: "outcome_unknown",
      generated: 0,
      interruptedChapterTitle: firstChapter.title,
    });
    expect(view.result().jobs.proposalAuditStatus).toBe("auditing");

    await act(async () => {
      firstAudit.reject(new Error("audit unavailable"));
      await run;
    });
    expect(view.result().jobs.proposalAuditStatus).toBe("audit_failed");
    act(() => void view.result().loop.start([firstChapter, secondChapter]));
    expect(streamProposal).toHaveBeenCalledTimes(1);

    await act(async () => {
      await view.result().loop.retryProposalAudit();
    });
    expect(api.jobs).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.jobs).mock.calls[1]?.[1]).not.toHaveProperty("cursor");
    expect(view.result().jobs.proposalAuditStatus).toBe("audit_succeeded");
    expect(view.result().loop.proposalOutcomeUnknown).toBe(true);

    act(() => void view.result().loop.start([firstChapter, secondChapter]));
    expect(streamProposal).toHaveBeenCalledTimes(2);
    expect(view.result().jobs.proposalAuditStatus).toBe("idle");
    secondStream.resolve(proposalJobFor(firstChapter.id));
  });

  it("does not audit an old run through the replacement project's jobs surface", async () => {
    const oldStream = rejectable<StudioJob>();
    vi.mocked(streamProposal).mockReturnValue(oldStream.promise);
    const view = renderUnknownLoop();
    const projectB: Project = { ...baseProject, id: "project-b" };

    act(() => void view.result().loop.start([firstChapter]));
    view.rerender(projectB);
    await act(async () => {
      oldStream.reject(new ProposalOutcomeUnknownError(new Error("old response lost")));
      await Promise.resolve();
    });

    expect(api.jobs).not.toHaveBeenCalled();
    expect(view.result().loop.phase).toEqual({ kind: "idle" });
  });

  it("never accepts an old run after a newer audit succeeds and its notice is cleared", async () => {
    const oldStream = rejectable<StudioJob>();
    vi.mocked(streamProposal).mockReturnValueOnce(oldStream.promise);
    vi.mocked(api.jobs).mockResolvedValue({ jobs: [], next_cursor: null });
    const view = renderUnknownLoop();
    let run: Promise<void> = Promise.resolve();

    act(() => {
      run = view.result().loop.start([firstChapter, secondChapter]);
    });
    await act(async () => {
      await expect(view.result().jobs.auditProposalOutcome()).resolves.toBe(true);
    });
    expect(view.result().jobs.proposalAuditStatus).toBe("audit_succeeded");
    act(() => view.result().jobs.clearProposalAudit());
    expect(view.result().jobs.proposalAuditStatus).toBe("idle");

    await act(async () => {
      oldStream.resolve(proposalJobFor(firstChapter.id));
      await run;
    });

    expect(api.acceptProposal).not.toHaveBeenCalled();
    expect(streamProposal).toHaveBeenCalledTimes(1);
    expect(view.result().loop.phase).toEqual({ kind: "done", generated: 0, stoppedEarly: true });
  });
});
