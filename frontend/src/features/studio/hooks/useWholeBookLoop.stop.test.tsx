import { act } from "react";
import { describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { streamProposal } from "@/app/proposalStream";
import type { Project, StudioJob } from "@/app/types/studio";
import {
  baseProject,
  deferred,
  firstChapter,
  proposalJobFor,
  renderLoopHook,
  secondChapter,
  traceApiCalls,
} from "./useWholeBookLoop.test-harness";
import { wholeBookPlan } from "./wholeBookPlan";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();

  return {
    ...actual,
    api: {
      ...actual.api,
      proposal: vi.fn<typeof actual.api.proposal>(),
      acceptProposal: vi.fn<typeof actual.api.acceptProposal>(),
      project: vi.fn<typeof actual.api.project>(),
    },
  };
});

vi.mock("@/app/proposalStream", () => ({
  streamProposal: vi.fn(),
}));

describe("useWholeBookLoop interruption", () => {
  it("abandons an in-flight draft once stopped and never starts the next chapter", async () => {
    const events: string[] = [];
    const firstDraft = deferred<StudioJob>();
    const secondDraft = deferred<StudioJob>();
    traceApiCalls(events);
    // The deferred stubs must record their own initiation: a vitest
    // mockReturnValueOnce shadows the traceApiCalls implementation entirely,
    // and this fixture pins the call sequence through the shared events log.
    vi.mocked(streamProposal)
      .mockImplementationOnce(async ({ documentId }) => {
        events.push(`proposal:${documentId}`);
        return firstDraft.promise;
      })
      .mockImplementationOnce(async ({ documentId }) => {
        events.push(`proposal:${documentId}`);
        return secondDraft.promise;
      });

    const harness = renderLoopHook(baseProject);
    let finished: Promise<void> = Promise.resolve();

    await act(async () => {
      finished = harness.result().hook.start(wholeBookPlan(baseProject));
      firstDraft.resolve(proposalJobFor(firstChapter.id));
      await vi.waitFor(() =>
        expect(events.filter((event) => event.startsWith("proposal:"))).toHaveLength(2),
      );
      // Stop lands while the second draft request is still unresolved.
      harness.result().hook.stop();
      expect(vi.mocked(streamProposal).mock.calls[1]?.[0].signal?.aborted).toBe(true);
      secondDraft.resolve(proposalJobFor(secondChapter.id));
      await finished;
    });

    expect(events.filter((event) => event === "accept:job-two")).toEqual([]);
    expect(events.filter((event) => event === "refresh")).toHaveLength(1);
    expect(harness.result().hook.phase).toEqual({
      kind: "done",
      generated: 1,
      stoppedEarly: true,
    });
    expect(harness.result().accepted.map((document) => document.id)).toEqual(["one"]);
  });

  it("keeps a committed acceptance refresh failure visible when Stop races the refresh", async () => {
    let rejectRefresh: ((reason: unknown) => void) | undefined;
    vi.mocked(streamProposal).mockResolvedValue(proposalJobFor(firstChapter.id));
    vi.mocked(api.acceptProposal).mockResolvedValue(proposalJobFor(firstChapter.id));
    vi.mocked(api.project).mockReturnValue(
      new Promise<Project>((_resolve, reject) => {
        rejectRefresh = reject;
      }),
    );
    const harness = renderLoopHook(baseProject);
    let finished: Promise<void> = Promise.resolve();

    act(() => {
      finished = harness.result().hook.start([firstChapter]);
    });
    await vi.waitFor(() => expect(api.project).toHaveBeenCalledTimes(1));
    act(() => harness.result().hook.stop());
    await act(async () => {
      rejectRefresh?.(new Error("Aggregate refresh unavailable."));
      await finished;
    });

    expect(harness.result().hook.phase).toEqual({
      kind: "failed",
      generated: 1,
      failedChapterTitle: firstChapter.title,
      message:
        "Proposal was accepted, but refreshing the project failed. Reload the project to sync.",
    });
  });

  it("#390 halts the loop when the page unmounts: no further chapter is drafted or accepted", async () => {
    const events: string[] = [];
    const firstDraft = deferred<StudioJob>();
    traceApiCalls(events);
    vi.mocked(streamProposal).mockImplementationOnce(async ({ documentId }) => {
      events.push(`proposal:${documentId}`);
      return firstDraft.promise;
    });

    const harness = renderLoopHook(baseProject);
    let finished: Promise<void> = Promise.resolve();

    await act(async () => {
      finished = harness.result().hook.start(wholeBookPlan(baseProject));
      await vi.waitFor(() =>
        expect(events.filter((event) => event.startsWith("proposal:"))).toHaveLength(1),
      );
      // Unmount while the first draft is still in flight.
      harness.unmount();
      expect(vi.mocked(streamProposal).mock.calls[0]?.[0].signal?.aborted).toBe(true);
      firstDraft.resolve(proposalJobFor(firstChapter.id));
      await finished;
    });

    // The unmounted run never accepts the in-flight draft and never starts
    // the next chapter.
    expect(events.some((event) => event.startsWith("accept:"))).toBe(false);
    expect(events.filter((event) => event.startsWith("proposal:"))).toEqual(["proposal:one"]);
    expect(vi.mocked(api.acceptProposal)).not.toHaveBeenCalled();
  });

  it("aborts the old project run and never publishes its late completion into the new project", async () => {
    const firstDraft = deferred<StudioJob>();
    const secondDraft = deferred<StudioJob>();
    const secondProject: Project = {
      ...baseProject,
      id: "project-2",
      documents: baseProject.documents?.map((document) => ({
        ...document,
        project_id: "project-2",
      })),
    };
    vi.mocked(streamProposal).mockImplementation(({ projectId }) =>
      projectId === baseProject.id ? firstDraft.promise : secondDraft.promise,
    );
    vi.mocked(api.acceptProposal).mockImplementation(async (projectId, jobId) => ({
      ...proposalJobFor(jobId.replace("job-", "")),
      project_id: projectId,
    }));
    vi.mocked(api.project).mockImplementation(async (projectId) =>
      projectId === secondProject.id ? secondProject : baseProject,
    );
    const harness = renderLoopHook(baseProject);
    let oldRun: Promise<void> = Promise.resolve();
    let currentRun: Promise<void> = Promise.resolve();

    act(() => {
      oldRun = harness.result().hook.start([firstChapter]);
    });
    await vi.waitFor(() => expect(streamProposal).toHaveBeenCalledTimes(1));
    const oldSignal = vi.mocked(streamProposal).mock.calls[0]?.[0].signal;

    harness.rerender(secondProject);
    expect(oldSignal?.aborted).toBe(true);
    expect(harness.result().hook.phase).toEqual({ kind: "idle" });
    act(() => {
      currentRun = harness.result().hook.start([firstChapter]);
    });
    await vi.waitFor(() => expect(streamProposal).toHaveBeenCalledTimes(2));

    await act(async () => {
      firstDraft.resolve(proposalJobFor(firstChapter.id));
      await oldRun;
    });

    expect(harness.result().project?.id).toBe(secondProject.id);
    expect(harness.result().hook.phase).toEqual({ kind: "running", current: 1, total: 1 });
    expect(api.acceptProposal).not.toHaveBeenCalledWith(baseProject.id, expect.any(String));

    await act(async () => {
      secondDraft.resolve({
        ...proposalJobFor(firstChapter.id),
        project_id: secondProject.id,
      });
      await currentRun;
    });

    expect(harness.result().project?.id).toBe(secondProject.id);
    expect(harness.result().hook.phase).toEqual({
      kind: "done",
      generated: 1,
      stoppedEarly: false,
    });
    expect(harness.result().accepted).toEqual([
      expect.objectContaining({ id: firstChapter.id, project_id: secondProject.id }),
    ]);
  });

  it("does not resurrect project A running state after an A to B to A route cycle", async () => {
    const firstDraft = deferred<StudioJob>();
    const secondProject: Project = {
      ...baseProject,
      id: "project-2",
      documents: baseProject.documents?.map((document) => ({
        ...document,
        project_id: "project-2",
      })),
    };
    vi.mocked(streamProposal).mockReturnValue(firstDraft.promise);
    const harness = renderLoopHook(baseProject);
    let oldRun: Promise<void> = Promise.resolve();

    act(() => {
      oldRun = harness.result().hook.start([firstChapter]);
    });
    await vi.waitFor(() => expect(streamProposal).toHaveBeenCalledTimes(1));
    harness.rerender(secondProject);
    expect(harness.result().hook.phase).toEqual({ kind: "idle" });

    harness.rerender(baseProject);
    expect(harness.result().hook.phase).toEqual({ kind: "idle" });
    await act(async () => {
      firstDraft.resolve(proposalJobFor(firstChapter.id));
      await oldRun;
    });

    expect(api.acceptProposal).not.toHaveBeenCalled();
    expect(harness.result().hook.phase).toEqual({ kind: "idle" });
  });
});
