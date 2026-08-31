import { act, StrictMode, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { type ProposalStreamRequest, streamProposal } from "@/app/proposalStream";
import type { Project, StudioDocument, StudioJob } from "@/app/types/studio";
import { chapter, job, projectWith } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { useOwnerKeyedErrors } from "./useOwnerKeyedErrors";
import { useStudioProposal } from "./useStudioProposal";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      acceptProposal: vi.fn<typeof actual.api.acceptProposal>(),
      project: vi.fn<typeof actual.api.project>(),
    },
  };
});

vi.mock("@/app/proposalStream", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/proposalStream")>();
  return { ...actual, streamProposal: vi.fn<typeof actual.streamProposal>() };
});

type ProposalHook = ReturnType<typeof useStudioProposal>;

interface Snapshot {
  readonly hook: ProposalHook;
  readonly project: Project | null;
  readonly error: string | null;
  readonly accepted: StudioDocument | null;
}

const harness = createMountHarness();
const proposalErrorSources = ["proposal"] as const;
const documentA = chapter("document-1", { content_markdown: "Document A" });
const documentB = chapter("document-2", { content_markdown: "Document B" });
const project = projectWith([documentA, documentB]);
const proposalA = job({
  id: "proposal-a",
  project_id: project.id,
  document_id: documentA.id,
  result: { proposal_markdown: "Proposal A" },
});
const proposalB = job({
  id: "proposal-b",
  project_id: project.id,
  document_id: documentB.id,
  result: { proposal_markdown: "Proposal B" },
});

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function renderProposal(): {
  readonly result: () => Snapshot;
  readonly rerender: (projectId: string, document: StudioDocument) => void;
  readonly replaceProject: (project: Project) => void;
  readonly unmount: () => void;
  readonly loadJobs: ReturnType<typeof vi.fn<() => void>>;
  readonly acceptanceCaptures: string[];
} {
  let projectId = project.id;
  let activeDocument = documentA;
  let current: Snapshot | undefined;
  const loadJobs = vi.fn<() => void>();
  const acceptanceCaptures: string[] = [];
  let publishProject: ((next: Project) => void) | undefined;

  function Wrapper(): null {
    const [visibleProject, setProject] = useState<Project | null>(project);
    publishProject = setProject;
    const proposalErrors = useOwnerKeyedErrors(
      `${projectId}\u0000${activeDocument.id}`,
      proposalErrorSources,
    );
    const [accepted, setAccepted] = useState<StudioDocument | null>(null);
    current = {
      hook: useStudioProposal(
        projectId,
        activeDocument,
        visibleProject,
        setProject,
        proposalErrors.publishers.proposal,
        loadJobs,
        (documentId) => {
          acceptanceCaptures.push(documentId);
          return documentId === activeDocument.id ? setAccepted : undefined;
        },
      ),
      project: visibleProject,
      error: proposalErrors.error,
      accepted,
    };
    return null;
  }

  const render = () => (
    <StrictMode>
      <Wrapper />
    </StrictMode>
  );
  const { container, root } = harness.mount(render());
  return {
    result: () => {
      if (!current) throw new Error("Expected proposal hook after render.");
      return current;
    },
    rerender: (nextProjectId, document) => {
      projectId = nextProjectId;
      activeDocument = document;
      act(() => root.render(render()));
    },
    replaceProject: (nextProject) => act(() => publishProject?.(nextProject)),
    unmount: () => harness.unmount(container),
    loadJobs,
    acceptanceCaptures,
  };
}

function deferredStreams(): {
  readonly requests: ProposalStreamRequest[];
  readonly settle: (job: StudioJob, failure?: unknown) => Promise<void>;
} {
  const requests: ProposalStreamRequest[] = [];
  const pending: Array<{
    resolve: (job: StudioJob) => void;
    reject: (reason: unknown) => void;
  }> = [];
  vi.mocked(streamProposal).mockImplementation(async (request) => {
    requests.push(request);
    return new Promise<StudioJob>((resolve, reject) => pending.push({ resolve, reject }));
  });
  return {
    requests,
    settle: async (result, failure) => {
      const entry = pending.shift();
      if (!entry) throw new Error("Expected a pending proposal stream.");
      await act(async () => {
        failure === undefined ? entry.resolve(result) : entry.reject(failure);
        await Promise.resolve();
      });
    },
  };
}

describe("useStudioProposal identity", () => {
  it("aborts the old document stream and ignores all late callbacks", async () => {
    const view = renderProposal();
    const streams = deferredStreams();
    let runA: Promise<void> = Promise.resolve();
    let runB: Promise<void> = Promise.resolve();

    act(() => {
      runA = view.result().hook.runProposal("continue");
    });
    const requestA = streams.requests[0];
    act(() => requestA?.onDelta("old partial"));
    view.rerender(project.id, documentB);
    expect(requestA?.signal?.aborted).toBe(true);

    act(() => {
      runB = view.result().hook.runProposal("rewrite");
    });
    requestA?.onDelta(" ignored");
    await streams.settle(proposalA, new Error("late A failure"));
    await act(async () => runA);
    expect(view.result().error).toBeNull();
    expect(view.result().hook.isRunningProposal).toBe(true);

    streams.requests[1]?.onDelta("current partial");
    await streams.settle(proposalB);
    await act(async () => runB);
    expect(view.result().hook.proposal).toEqual(proposalB);
    expect(view.result().hook.isRunningProposal).toBe(false);
  });

  it("aborts the active stream when its owner unmounts", () => {
    const view = renderProposal();
    const streams = deferredStreams();
    act(() => void view.result().hook.runProposal("continue"));

    view.unmount();

    expect(streams.requests[0]?.signal?.aborted).toBe(true);
  });

  it("deduplicates accept synchronously before pending state renders", async () => {
    const acceptance = deferred<StudioJob>();
    vi.mocked(api.acceptProposal).mockReturnValue(acceptance.promise);
    vi.mocked(api.project).mockResolvedValue(project);
    const view = renderProposal();
    act(() => view.result().hook.setProposal(proposalA));
    let first: Promise<void> = Promise.resolve();
    let duplicate: Promise<void> = Promise.resolve();

    act(() => {
      first = view.result().hook.acceptProposal();
      duplicate = view.result().hook.acceptProposal();
    });

    expect(api.acceptProposal).toHaveBeenCalledTimes(1);
    expect(view.acceptanceCaptures).toEqual([documentA.id]);
    await act(async () => {
      acceptance.resolve(proposalA);
      await Promise.all([first, duplicate]);
    });
    expect(api.project).toHaveBeenCalledTimes(1);
  });

  it("reconciles a committed accept into its project after the document changes", async () => {
    const refresh = deferred<Project>();
    vi.mocked(api.acceptProposal).mockResolvedValue(proposalA);
    vi.mocked(api.project).mockReturnValue(refresh.promise);
    const view = renderProposal();
    act(() => view.result().hook.setProposal(proposalA));
    let accepting: Promise<void> = Promise.resolve();

    act(() => {
      accepting = view.result().hook.acceptProposal();
    });
    await vi.waitFor(() => expect(api.project).toHaveBeenCalledTimes(1));
    const refreshSignal = vi.mocked(api.project).mock.calls[0]?.[1]?.signal;
    view.rerender(project.id, documentB);
    expect(refreshSignal?.aborted).toBe(false);
    const committedB = {
      ...documentB,
      current_revision_id: "revision-b-committed",
      content_markdown: "Committed B",
    };
    view.replaceProject({ ...project, documents: [documentA, committedB] });
    const acceptedA = { ...documentA, title: "Committed A" };
    const refreshedProject = {
      ...project,
      documents: [acceptedA, documentB],
    };
    await act(async () => {
      refresh.resolve(refreshedProject);
      await accepting;
    });

    expect(view.result().project?.documents).toEqual([acceptedA, committedB]);
    expect(view.result().accepted).toEqual(acceptedA);
    expect(view.loadJobs).toHaveBeenCalledTimes(1);
    expect(view.result().error).toBeNull();
  });

  it("retains a committed accept refresh failure for its initiating document", async () => {
    let rejectRefresh!: (reason: unknown) => void;
    const refresh = new Promise<Project>((_resolve, reject) => {
      rejectRefresh = reject;
    });
    vi.mocked(api.acceptProposal).mockResolvedValue(proposalA);
    vi.mocked(api.project).mockReturnValue(refresh);
    const view = renderProposal();
    act(() => view.result().hook.setProposal(proposalA));
    let accepting: Promise<void> = Promise.resolve();

    act(() => {
      accepting = view.result().hook.acceptProposal();
    });
    await vi.waitFor(() => expect(api.project).toHaveBeenCalledTimes(1));
    view.rerender(project.id, documentB);
    await act(async () => {
      rejectRefresh(new Error("refresh unavailable"));
      await accepting;
    });

    expect(view.result().error).toBeNull();
    view.rerender(project.id, documentA);
    expect(view.result().error).toContain(
      "Proposal was accepted, but refreshing the project failed",
    );
  });

  it("aborts a committed accept refresh when the project owner changes", async () => {
    const refresh = deferred<Project>();
    vi.mocked(api.acceptProposal).mockResolvedValue(proposalA);
    vi.mocked(api.project).mockReturnValue(refresh.promise);
    const view = renderProposal();
    act(() => view.result().hook.setProposal(proposalA));
    let accepting: Promise<void> = Promise.resolve();

    act(() => {
      accepting = view.result().hook.acceptProposal();
    });
    await vi.waitFor(() => expect(api.project).toHaveBeenCalledTimes(1));
    const refreshSignal = vi.mocked(api.project).mock.calls[0]?.[1]?.signal;
    view.rerender("other-project", documentB);
    expect(refreshSignal?.aborted).toBe(true);
    await act(async () => {
      refresh.resolve({ ...project, documents: [{ ...documentA, title: "Late A" }, documentB] });
      await accepting;
    });

    expect(view.result().project).toEqual(project);
    expect(view.result().accepted).toBeNull();
    expect(view.loadJobs).not.toHaveBeenCalled();
    expect(view.result().error).toBeNull();
  });
});
