import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import {
  ProposalOutcomeUnknownError,
  type ProposalStreamRequest,
  streamProposal,
} from "@/app/proposalStream";
import type { Project, StudioDocument, StudioJob } from "@/app/types/studio";
import { chapter, job, projectWith } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { useStudioJobs } from "./useStudioJobs";
import { useStudioProposal } from "./useStudioProposal";

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
const documentA = chapter("document-a", { title: "Chapter A" });
const documentB = chapter("document-b", { title: "Chapter B" });
const projectA = projectWith([documentA, documentB]);

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

interface Snapshot {
  readonly proposal: ReturnType<typeof useStudioProposal>;
  readonly jobs: ReturnType<typeof useStudioJobs>;
  readonly error: string | null;
}

function renderUnknownHarness(): {
  readonly result: () => Snapshot;
  readonly rerender: (projectId: string, document: StudioDocument) => void;
} {
  let projectId = projectA.id;
  let activeDocument = documentA;
  let current: Snapshot | undefined;

  function Wrapper(): null {
    const [project, setProject] = useState<Project | null>(projectA);
    const [error, setError] = useState<string | null>(null);
    const jobs = useStudioJobs(projectId, setError);
    const proposal = useStudioProposal(
      projectId,
      activeDocument,
      project,
      setProject,
      setError,
      jobs.loadJobs,
      () => undefined,
      {
        status: jobs.proposalAuditStatus,
        audit: jobs.auditProposalOutcome,
        clear: jobs.clearProposalAudit,
        epoch: jobs.proposalAuditEpoch,
        isGated: jobs.isProposalAuditGated,
      },
    );
    current = { proposal, jobs, error };
    return null;
  }

  const { root } = harness.mount(<Wrapper />);
  return {
    result: () => {
      if (!current) throw new Error("Expected proposal audit harness.");
      return current;
    },
    rerender: (nextProjectId, nextDocument) => {
      projectId = nextProjectId;
      activeDocument = nextDocument;
      act(() => root.render(<Wrapper />));
    },
  };
}

function deferredStreams() {
  const requests: ProposalStreamRequest[] = [];
  const pending: Array<ReturnType<typeof rejectable<StudioJob>>> = [];
  vi.mocked(streamProposal).mockImplementation((request) => {
    requests.push(request);
    const next = rejectable<StudioJob>();
    pending.push(next);
    return next.promise;
  });
  return { requests, pending };
}

function rejectable<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

describe("useStudioProposal unknown outcome audit", () => {
  it("discards partial text, gates proposal actions, and offers audit-only retry until audit succeeds", async () => {
    const streams = deferredStreams();
    const firstAudit = rejectable<{ jobs: StudioJob[] }>();
    vi.mocked(api.jobs).mockReturnValueOnce(firstAudit.promise).mockResolvedValueOnce({ jobs: [] });
    const view = renderUnknownHarness();
    let running: Promise<void> = Promise.resolve();

    act(() => {
      running = view.result().proposal.runProposal("continue");
    });
    act(() => streams.requests[0]?.onDelta("untrusted partial"));
    act(() => view.result().proposal.stopProposal());
    await act(async () => {
      streams.pending[0]?.reject(
        new ProposalOutcomeUnknownError(new Error("terminal response lost")),
      );
      await vi.waitFor(() => expect(api.jobs).toHaveBeenCalledTimes(1));
    });

    expect(view.result().proposal.streamingText).toBeNull();
    expect(view.result().proposal.proposal).toBeNull();
    expect(view.result().proposal.proposalOutcomeUnknown).toBe(true);
    expect(view.result().jobs.proposalAuditStatus).toBe("auditing");
    act(() => void view.result().proposal.runProposal("rewrite"));
    expect(streamProposal).toHaveBeenCalledTimes(1);

    await act(async () => {
      firstAudit.reject(new Error("audit unavailable"));
      await running;
    });
    expect(view.result().jobs.proposalAuditStatus).toBe("audit_failed");
    expect(view.result().error).toBeNull();

    await act(async () => {
      await view.result().proposal.retryProposalAudit();
    });
    expect(view.result().jobs.proposalAuditStatus).toBe("audit_succeeded");
    expect(view.result().proposal.proposalOutcomeUnknown).toBe(true);

    act(() => void view.result().proposal.runProposal("continue"));
    expect(streamProposal).toHaveBeenCalledTimes(2);
    expect(view.result().jobs.proposalAuditStatus).toBe("idle");
  });

  it("audits an interrupted document without publishing its stale state into another document", async () => {
    const streams = deferredStreams();
    vi.mocked(api.jobs).mockResolvedValue({ jobs: [] });
    const view = renderUnknownHarness();

    act(() => void view.result().proposal.runProposal("rewrite"));
    act(() => streams.requests[0]?.onDelta("document A partial"));
    view.rerender(projectA.id, documentB);
    expect(streams.requests[0]?.signal?.aborted).toBe(true);

    await act(async () => {
      streams.pending[0]?.reject(
        new ProposalOutcomeUnknownError(new Error("document changed before terminal")),
      );
      await vi.waitFor(() => expect(api.jobs).toHaveBeenCalledWith(projectA.id, expect.anything()));
    });

    expect(view.result().proposal.proposal).toBeNull();
    expect(view.result().proposal.streamingText).toBeNull();
    expect(view.result().proposal.proposalOutcomeUnknown).toBe(true);
  });

  it("does not turn an old-project settlement into a jobs read for the new project", async () => {
    const streams = deferredStreams();
    const view = renderUnknownHarness();

    act(() => void view.result().proposal.runProposal("continue"));
    view.rerender("project-b", documentB);
    await act(async () => {
      streams.pending[0]?.reject(
        new ProposalOutcomeUnknownError(new Error("old project terminal lost")),
      );
      await Promise.resolve();
    });

    expect(api.jobs).not.toHaveBeenCalled();
    expect(view.result().proposal.proposalOutcomeUnknown).toBe(false);
  });

  it("does not publish an old terminal result after a newer audit epoch is cleared", async () => {
    const streams = deferredStreams();
    vi.mocked(api.jobs).mockResolvedValue({ jobs: [] });
    const view = renderUnknownHarness();
    let running: Promise<void> = Promise.resolve();

    act(() => {
      running = view.result().proposal.runProposal("continue");
    });
    await act(async () => {
      await expect(view.result().jobs.auditProposalOutcome()).resolves.toBe(true);
    });
    act(() => view.result().jobs.clearProposalAudit());

    await act(async () => {
      streams.pending[0]?.resolve(job({ id: "old-terminal-job" }));
      await running;
    });

    expect(view.result().proposal.proposal).toBeNull();
    expect(view.result().proposal.streamingText).toBeNull();
  });
});
