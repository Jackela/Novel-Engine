import { act } from "react";
import { describe, expect, it, vi } from "vitest";
import { api, HttpError } from "@/app/api";
import { streamProposal } from "@/app/proposalStream";
import type { StudioJob } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";
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
      document: vi.fn<typeof actual.api.document>(),
      project: vi.fn<typeof actual.api.project>(),
    },
  };
});

vi.mock("@/app/proposalStream", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/proposalStream")>();
  return { ...actual, streamProposal: vi.fn<typeof actual.streamProposal>() };
});

describe("useWholeBookLoop run lifecycle (#318)", () => {
  it("drafts and auto-accepts every planned chapter in reading order", async () => {
    const events: string[] = [];
    traceApiCalls(events);
    const harness = renderLoopHook(baseProject, (documentId) => {
      events.push(`capture:${documentId}`);
    });

    await act(async () => {
      await harness.result().hook.start(wholeBookPlan(baseProject));
    });

    expect(events).toEqual([
      "capture:one",
      "proposal:one",
      "accept:job-one",
      "refresh",
      "capture:two",
      "proposal:two",
      "accept:job-two",
      "refresh",
    ]);
    expect(harness.result().hook.phase).toEqual({
      kind: "done",
      generated: 2,
      stoppedEarly: false,
    });
    expect(harness.result().accepted.map((document) => document.id)).toEqual(["one", "two"]);
    expect(vi.mocked(streamProposal).mock.calls[0]?.[0]).toMatchObject({
      operation: "generate",
      instruction: "",
      provider: "mock",
    });
    expect(vi.mocked(streamProposal).mock.calls[0]?.[0].onDelta).toEqual(expect.any(Function));
  });

  it("surfaces a proposal failure with the failing chapter identified", async () => {
    const events: string[] = [];
    traceApiCalls(events);
    vi.mocked(streamProposal).mockRejectedValue(new Error("Provider exploded."));
    const harness = renderLoopHook(baseProject);

    await act(async () => {
      await harness.result().hook.start(wholeBookPlan(baseProject));
    });

    expect(harness.result().hook.phase).toEqual({
      kind: "failed",
      generated: 0,
      failedChapterTitle: "Chapter One",
      message: "Provider exploded.",
    });
    expect(events.some((event) => event.startsWith("accept:"))).toBe(false);
  });

  it("resumes after a generation-capacity refusal from the first unaccepted chapter", async () => {
    const events: string[] = [];
    const thirdChapter = chapter("three", {
      title: "Chapter Three",
      position: 2,
    });
    const threeChapterProject = projectWith([firstChapter, secondChapter, thirdChapter]);
    traceApiCalls(events, threeChapterProject);
    vi.mocked(streamProposal)
      .mockImplementationOnce(async ({ documentId }) => {
        events.push(`proposal:${documentId}`);
        return proposalJobFor(documentId);
      })
      .mockImplementationOnce(async ({ documentId }) => {
        events.push(`proposal:${documentId}`);
        throw new HttpError(
          "Generation capacity exceeded.",
          422,
          {
            resource: "prompt_bytes",
            limit: 8_388_608,
            observed: 8_388_609,
          },
          "GENERATION_CAPACITY_EXCEEDED",
        );
      });
    const harness = renderLoopHook(threeChapterProject);

    await act(async () => {
      await harness.result().hook.start(wholeBookPlan(threeChapterProject));
    });

    expect(events).toEqual(["proposal:one", "accept:job-one", "refresh", "proposal:two"]);
    expect(vi.mocked(streamProposal)).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.acceptProposal)).toHaveBeenCalledTimes(1);
    expect(harness.result().accepted.map((document) => document.id)).toEqual(["one"]);
    expect(harness.result().hook.phase).toEqual({
      kind: "failed",
      generated: 1,
      failedChapterTitle: "Chapter Two",
      message: "Generation capacity exceeded.",
    });

    const reducedProject = projectWith([
      firstChapter,
      { ...secondChapter, content_markdown: "Shortened chapter context." },
      thirdChapter,
    ]);
    harness.rerender(reducedProject);

    await act(async () => {
      await harness.result().hook.start(wholeBookPlan(reducedProject));
    });

    expect(events).toEqual([
      "proposal:one",
      "accept:job-one",
      "refresh",
      "proposal:two",
      "proposal:two",
      "accept:job-two",
      "refresh",
      "proposal:three",
      "accept:job-three",
      "refresh",
    ]);
    expect(vi.mocked(streamProposal).mock.calls.map(([request]) => request.documentId)).toEqual([
      "one",
      "two",
      "two",
      "three",
    ]);
    expect(harness.result().accepted.map((document) => document.id)).toEqual([
      "one",
      "two",
      "three",
    ]);
    expect(harness.result().hook.phase).toEqual({
      kind: "done",
      generated: 2,
      stoppedEarly: false,
    });
  });

  it("stops after an accept failure and keeps earlier chapters intact", async () => {
    const events: string[] = [];
    traceApiCalls(events);
    // Same shadowing rule as above: the value-level stubs also record their
    // initiation. The failing accept stays unrecorded on purpose — it never
    // lands — while its rejection is what the loop must surface.
    vi.mocked(streamProposal)
      .mockImplementationOnce(async ({ documentId }) => {
        events.push(`proposal:${documentId}`);
        return proposalJobFor(firstChapter.id);
      })
      .mockImplementationOnce(async ({ documentId }) => {
        events.push(`proposal:${documentId}`);
        return proposalJobFor(secondChapter.id);
      })
      .mockRejectedValue(new Error("Provider exploded again."));
    vi.mocked(api.acceptProposal)
      .mockImplementationOnce(async (_projectId, jobId) => {
        events.push(`accept:${jobId}`);
        return proposalJobFor(firstChapter.id);
      })
      .mockRejectedValue(new Error("Accept rejected by the server."));
    const harness = renderLoopHook(baseProject);

    await act(async () => {
      await harness.result().hook.start(wholeBookPlan(baseProject));
    });

    expect(events.slice(0, 3)).toEqual(["proposal:one", "accept:job-one", "refresh"]);
    expect(events.some((event) => event === "accept:job-two")).toBe(false);
    expect(harness.result().hook.phase).toEqual({
      kind: "failed",
      generated: 1,
      failedChapterTitle: "Chapter Two",
      message: "Accept rejected by the server.",
    });
    expect(harness.result().accepted.map((document) => document.id)).toEqual(["one"]);
  });

  it("ignores a start request while the loop is already running", async () => {
    const gate = deferred<StudioJob>();
    traceApiCalls([]);
    vi.mocked(streamProposal).mockImplementation(({ documentId }) =>
      documentId === firstChapter.id ? gate.promise : Promise.resolve(proposalJobFor(documentId)),
    );
    const harness = renderLoopHook(baseProject);
    let ignoredStart: Promise<void> = Promise.resolve();
    let realStart: Promise<void> = Promise.resolve();

    act(() => {
      realStart = harness.result().hook.start(wholeBookPlan(baseProject));
      ignoredStart = harness.result().hook.start(wholeBookPlan(baseProject));
    });
    expect(harness.result().hook.phase).toEqual({
      kind: "running",
      current: 1,
      total: 2,
    });

    await act(async () => {
      gate.resolve(proposalJobFor(firstChapter.id));
      await realStart;
      await ignoredStart;
    });

    expect(vi.mocked(streamProposal)).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.acceptProposal)).toHaveBeenCalledTimes(2);
    expect(harness.result().hook.phase).toEqual({
      kind: "done",
      generated: 2,
      stoppedEarly: false,
    });
  });

  it("counts a committed acceptance when refresh fails and skips it on resume", async () => {
    const draftedDocuments: string[] = [];
    vi.mocked(streamProposal).mockImplementation(async ({ documentId }) => {
      draftedDocuments.push(documentId);
      return proposalJobFor(documentId);
    });
    vi.mocked(api.acceptProposal).mockImplementation(async (_projectId, jobId) =>
      proposalJobFor(jobId.replace("job-", "")),
    );
    vi.mocked(api.project)
      .mockRejectedValueOnce(new Error("Aggregate refresh unavailable."))
      .mockResolvedValue(baseProject);
    const harness = renderLoopHook(baseProject);

    await act(async () => {
      await harness.result().hook.start([firstChapter, secondChapter]);
    });

    expect(harness.result().hook.phase).toEqual({
      kind: "failed",
      generated: 1,
      failedChapterTitle: firstChapter.title,
      message:
        "Proposal was accepted, but refreshing the project failed. Reload the project to sync.",
    });
    expect(draftedDocuments).toEqual([firstChapter.id]);

    await act(async () => {
      await harness.result().hook.start([firstChapter, secondChapter]);
    });

    expect(draftedDocuments).toEqual([firstChapter.id, secondChapter.id]);
    expect(harness.result().hook.phase).toEqual({
      kind: "done",
      generated: 1,
      stoppedEarly: false,
    });
  });

  it("reports idle before any run starts", () => {
    const harness = renderLoopHook(baseProject);
    expect(harness.result().hook.phase).toEqual({ kind: "idle" });
  });
});
