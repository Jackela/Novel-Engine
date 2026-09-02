import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { ProposalStreamRequest } from "@/app/proposalStream";
import { streamProposal } from "@/app/proposalStream";
import type { Project, StudioDocument, StudioJob } from "@/app/types/studio";
import type { InspectorTab } from "@/features/studio/studioConstants";
import { chapter, job, projectWith } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

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

  return {
    ...actual,
    streamProposal: vi.fn<typeof actual.streamProposal>(),
  };
});

type HookResult = ReturnType<typeof useStudioProposal>;

interface HarnessSnapshot {
  readonly hook: HookResult;
  readonly project: Project | null;
  readonly inspector: InspectorTab;
  readonly error: string | null;
  readonly accepted: StudioDocument | null;
}

const harness = createMountHarness();

const firstDocument = chapter("document-1", {
  title: "Chapter One",
  current_revision_id: "revision-1",
  content_markdown: "Original scene",
  revision_source: "manual",
  word_count: 2,
});

const secondDocument = {
  ...firstDocument,
  id: "document-2",
  title: "Chapter Two",
  current_revision_id: "revision-2",
};

const baseProject = projectWith([firstDocument, secondDocument], {
  description: "A harbor of brass clocks.",
});

const proposalJob = job({
  project_id: baseProject.id,
  document_id: firstDocument.id,
  result: { proposal_markdown: "A generated continuation." },
});

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function renderProposalHook(): {
  readonly result: () => HarnessSnapshot;
  readonly rerender: (document: StudioDocument) => void;
  readonly loadJobs: ReturnType<typeof vi.fn<() => void>>;
} {
  let activeDocument = firstDocument;
  let current: HarnessSnapshot | undefined;
  const loadJobs = vi.fn<() => void>();

  function Wrapper(): null {
    const [project, setProject] = useState<Project | null>(baseProject);
    const [inspector] = useState<InspectorTab>("history");
    const [error, setError] = useState<string | null>("previous error");
    const [accepted, setAccepted] = useState<StudioDocument | null>(null);
    const hook = useStudioProposal(
      baseProject.id,
      activeDocument,
      project,
      setProject,
      setError,
      loadJobs,
      (documentId) =>
        documentId === activeDocument.id ? (document) => setAccepted(document) : undefined,
    );
    current = { hook, project, inspector, error, accepted };
    return null;
  }

  const { root } = harness.mount(<Wrapper />);

  const render = () => root.render(<Wrapper />);

  return {
    result: () => {
      if (current === undefined) {
        throw new Error("Expected hook result after render.");
      }
      return current;
    },
    rerender: (document) => {
      activeDocument = document;
      act(render);
    },
    loadJobs,
  };
}

function deferredStream(): {
  requests: ProposalStreamRequest[];
  settle: (job: StudioJob | Promise<StudioJob>, failure?: unknown) => Promise<void>;
} {
  const requests: ProposalStreamRequest[] = [];
  const pending: Array<{
    resolve: (job: StudioJob) => void;
    reject: (reason: unknown) => void;
  }> = [];
  vi.mocked(streamProposal).mockImplementation(async (request) => {
    requests.push(request);
    return new Promise<StudioJob>((resolve, reject) => {
      pending.push({ resolve, reject });
    });
  });
  return {
    requests,
    settle: async (job, failure) => {
      const entry = pending.shift();
      if (entry === undefined) throw new Error("Expected a pending stream.");
      await act(async () => {
        if (failure !== undefined) {
          entry.reject(failure);
        } else {
          entry.resolve(await job);
        }
        await Promise.resolve();
      });
    },
  };
}

describe("useStudioProposal", () => {
  it("streams the proposal into the preview and lands the job on the done frame", async () => {
    // Given
    const harness = renderProposalHook();
    const deferred = deferredStream();
    act(() => {
      harness.result().hook.setInstruction("Expand the scene");
    });
    let running: Promise<void> | undefined;
    act(() => {
      running = harness.result().hook.runProposal("continue");
    });
    if (running === undefined) throw new Error("Expected runProposal to start.");
    await act(async () => {
      deferred.requests[0]?.onDelta("A generated");
    });
    expect(harness.result().hook.streamingText).toBe("A generated");
    await act(async () => {
      deferred.requests[0]?.onDelta(" continuation.");
    });
    expect(harness.result().hook.streamingText).toBe("A generated continuation.");

    // When
    await deferred.settle(proposalJob);
    await act(async () => {
      await running;
    });

    // Then
    const request = deferred.requests[0];
    expect(request).toMatchObject({
      projectId: baseProject.id,
      documentId: firstDocument.id,
      operation: "continue",
      instruction: "Expand the scene",
      provider: "mock",
    });
    expect(request?.signal).toBeInstanceOf(AbortSignal);
    expect(harness.result().hook.proposal).toEqual(proposalJob);
    expect(harness.result().hook.streamingText).toBeNull();
    expect(harness.result().hook.isRunningProposal).toBe(false);
    expect(harness.result().inspector).toBe("history");
    expect(harness.result().error).toBeNull();
  });

  it("stops client preview without publishing a stale terminal error", async () => {
    // Given
    const harness = renderProposalHook();
    const deferred = deferredStream();
    await act(async () => {
      void harness.result().hook.runProposal("continue");
      await Promise.resolve();
    });

    // When
    act(() => {
      harness.result().hook.stopProposal();
    });
    const signal = deferred.requests[0]?.signal;
    await deferred.settle(proposalJob, new Error("Request cancelled."));

    // Then
    expect(signal?.aborted).toBe(true);
    expect(harness.result().hook.proposal).toBeNull();
    expect(harness.result().hook.streamingText).toBeNull();
    expect(harness.result().hook.isRunningProposal).toBe(false);
    expect(harness.result().error).toBeNull();
  });

  it("surfaces stream failures as the inspector error and clears the preview", async () => {
    // Given
    const harness = renderProposalHook();
    const deferred = deferredStream();
    await act(async () => {
      void harness.result().hook.runProposal("rewrite");
      await Promise.resolve();
    });

    // When
    await deferred.settle(proposalJob, new Error("provider exploded"));

    // Then
    expect(harness.result().error).toBe("provider exploded");
    expect(harness.result().hook.proposal).toBeNull();
    expect(harness.result().hook.streamingText).toBeNull();
  });

  it("refreshes project state and the accepted document after accepting a proposal", async () => {
    // Given
    const acceptedDocument = {
      ...firstDocument,
      current_revision_id: "revision-accepted",
      content_markdown: "Accepted continuation",
    };
    const refreshedProject = {
      ...baseProject,
      documents: [acceptedDocument, secondDocument],
    };
    vi.mocked(api.acceptProposal).mockResolvedValue(proposalJob);
    vi.mocked(api.project).mockResolvedValue(refreshedProject);
    const harness = renderProposalHook();
    act(() => {
      harness.result().hook.setProposal(proposalJob);
    });

    // When
    await act(async () => {
      await harness.result().hook.acceptProposal();
    });

    // Then
    expect(harness.result().project).toEqual(refreshedProject);
    expect(harness.result().accepted).toEqual(acceptedDocument);
    expect(harness.result().hook.proposal).toBeNull();
    expect(harness.loadJobs).toHaveBeenCalledTimes(1);
  });

  it("reports a committed acceptance truthfully when the aggregate refresh fails", async () => {
    vi.mocked(api.acceptProposal).mockResolvedValue(proposalJob);
    vi.mocked(api.project).mockRejectedValue(new Error("refresh unavailable"));
    const harness = renderProposalHook();
    act(() => harness.result().hook.setProposal(proposalJob));

    await act(async () => {
      await harness.result().hook.acceptProposal();
    });

    expect(harness.result().hook.proposal).toBeNull();
    expect(harness.result().error).toBe(
      "Proposal was accepted, but refreshing the project failed. Reload the project to sync.",
    );
    expect(harness.loadJobs).not.toHaveBeenCalled();
  });

  it("clears a stale proposal when the active document changes", () => {
    // Given
    const harness = renderProposalHook();
    act(() => {
      harness.result().hook.setProposal(proposalJob);
    });
    expect(harness.result().hook.proposal).toEqual(proposalJob);

    // When
    harness.rerender(secondDocument);

    // Then
    expect(harness.result().hook.proposal).toBeNull();
  });
});
