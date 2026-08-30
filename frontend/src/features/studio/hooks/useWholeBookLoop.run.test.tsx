import { act } from "react";
import { describe, expect, it, vi } from "vitest";
import { api } from "@/app/api";
import type { StudioJob } from "@/app/types/studio";
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

describe("useWholeBookLoop run lifecycle (#318)", () => {
  it("drafts and auto-accepts every planned chapter in reading order", async () => {
    const events: string[] = [];
    traceApiCalls(events);
    const harness = renderLoopHook(baseProject);

    await act(async () => {
      await harness.result().hook.start(wholeBookPlan(baseProject));
    });

    expect(events).toEqual([
      "proposal:one",
      "accept:job-one",
      "refresh",
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
    expect(vi.mocked(api.proposal).mock.calls[0]?.[2]).toBe("generate");
  });

  it("surfaces a proposal failure with the failing chapter identified", async () => {
    const events: string[] = [];
    traceApiCalls(events);
    vi.mocked(api.proposal).mockRejectedValue(new Error("Provider exploded."));
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

  it("stops after an accept failure and keeps earlier chapters intact", async () => {
    const events: string[] = [];
    traceApiCalls(events);
    // Same shadowing rule as above: the value-level stubs also record their
    // initiation. The failing accept stays unrecorded on purpose — it never
    // lands — while its rejection is what the loop must surface.
    vi.mocked(api.proposal)
      .mockImplementationOnce(async (_projectId, documentId) => {
        events.push(`proposal:${documentId}`);
        return proposalJobFor(firstChapter.id);
      })
      .mockImplementationOnce(async (_projectId, documentId) => {
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
    vi.mocked(api.proposal).mockImplementation((_projectId, documentId) =>
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

    expect(vi.mocked(api.proposal)).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.acceptProposal)).toHaveBeenCalledTimes(2);
    expect(harness.result().hook.phase).toEqual({
      kind: "done",
      generated: 2,
      stoppedEarly: false,
    });
  });

  it("reports idle before any run starts", () => {
    const harness = renderLoopHook(baseProject);
    expect(harness.result().hook.phase).toEqual({ kind: "idle" });
  });
});
