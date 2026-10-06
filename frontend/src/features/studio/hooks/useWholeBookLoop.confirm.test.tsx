import { act } from "react";
import { describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { streamProposal } from "@/app/proposalStream";
import type { Project, StudioJob } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";

import {
  deferred,
  proposalJobFor,
  renderLoopHook,
  secondChapter,
  traceApiCalls,
} from "./useWholeBookLoop.test-harness";
import { readingOrderChapters, wholeBookPlan } from "./wholeBookPlan";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();

  return {
    ...actual,
    api: {
      ...actual.api,
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

/**
 * A hand-written chapter: `revision_source` "author" with non-empty current
 * text. The old whole-book rule only asked whether the revision was
 * `ai-accepted`, so this chapter was drafted and auto-accepted like an empty
 * one (#DR-007).
 */
const authoredChapter = chapter("one", {
  title: "Chapter One",
  content_markdown: "The lighthouse keeper counted her debts aloud.",
  word_count: 7,
});
const authoredSecondChapter = chapter("two", {
  title: "Chapter Two",
  content_markdown: "The tide repaid nothing and owed even less.",
  word_count: 7,
});

describe("whole-book replacement confirmation (#DR-007)", () => {
  it("never drafts or accepts a hand-written chapter without confirmation", async () => {
    const events: string[] = [];
    const project = projectWith([authoredChapter, secondChapter]);
    traceApiCalls(events, project);
    const harness = renderLoopHook(project);

    await act(async () => {
      await harness.result().hook.start(wholeBookPlan(project).chapters);
    });

    // The empty chapter still generates without a confirmation surface...
    expect(events.filter((event) => event.startsWith("proposal:"))).toEqual(["proposal:two"]);
    expect(harness.result().accepted.map((document) => document.id)).toEqual(["two"]);
    // ...while the hand-written chapter was neither drafted nor accepted.
    expect(vi.mocked(streamProposal).mock.calls.map(([request]) => request.documentId)).toEqual([
      secondChapter.id,
    ]);
    expect(vi.mocked(api.acceptProposal).mock.calls.map(([, jobId]) => jobId)).toEqual(["job-two"]);
    expect(harness.result().hook.phase).toEqual({
      kind: "done",
      generated: 1,
      stoppedEarly: false,
    });
  });

  it("replaces the hand-written chapter once the run carries the confirmation", async () => {
    const events: string[] = [];
    const project = projectWith([authoredChapter, secondChapter]);
    traceApiCalls(events, project);
    const harness = renderLoopHook(project);

    await act(async () => {
      await harness.result().hook.start(wholeBookPlan(project).chapters, {
        replaceOccupied: true,
      });
    });

    // Reading order still decides the drafting order.
    expect(events).toEqual([
      "proposal:one",
      "accept:job-one",
      "refresh",
      "proposal:two",
      "accept:job-two",
      "refresh",
    ]);
    expect(harness.result().accepted.map((document) => document.id)).toEqual(["one", "two"]);
  });

  it("requires a fresh confirmation when a confirmed run resumes after a stop", async () => {
    const events: string[] = [];
    const project = projectWith([authoredChapter, authoredSecondChapter]);
    const acceptedFirst = { ...authoredChapter, revision_source: "ai-accepted" as const };
    const refreshed: Project = projectWith([acceptedFirst, authoredSecondChapter], {
      volumes: project.volumes,
    });
    const heldDraft = deferred<StudioJob>();
    traceApiCalls(events, refreshed);
    // The first chapter lands immediately; the second one stays in flight so
    // Stop can land between them and leave it unreplaced.
    vi.mocked(streamProposal)
      .mockImplementationOnce(async ({ documentId }) => {
        events.push(`proposal:${documentId}`);
        return proposalJobFor(documentId);
      })
      .mockImplementationOnce(async ({ documentId }) => {
        events.push(`proposal:${documentId}`);
        return heldDraft.promise;
      });
    const harness = renderLoopHook(project);

    await act(async () => {
      const run = harness.result().hook.start(wholeBookPlan(project).chapters, {
        replaceOccupied: true,
      });
      await vi.waitFor(() => expect(streamProposal).toHaveBeenCalledTimes(2));
      harness.result().hook.stop();
      heldDraft.resolve(proposalJobFor(authoredSecondChapter.id));
      await run;
    });
    expect(harness.result().hook.phase).toEqual({
      kind: "done",
      generated: 1,
      stoppedEarly: true,
    });
    expect(vi.mocked(api.acceptProposal).mock.calls.map(([, jobId]) => jobId)).toEqual(["job-one"]);

    // Resume re-derives the plan from the refreshed summaries: the accepted
    // chapter is gone, the stopped one is confirmation-gated again.
    harness.rerender(refreshed);
    const resumePlan = wholeBookPlan(refreshed);
    expect(readingOrderChapters(refreshed).length).toBe(2);
    expect(resumePlan.safe).toEqual([]);
    expect(resumePlan.confirmation.map((chapter) => chapter.id)).toEqual([
      authoredSecondChapter.id,
    ]);

    await act(async () => {
      await harness.result().hook.start(resumePlan.chapters);
    });
    // The unconfirmed chapter is still untouched...
    expect(streamProposal).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.acceptProposal)).toHaveBeenCalledTimes(1);

    await act(async () => {
      await harness.result().hook.start(resumePlan.chapters, { replaceOccupied: true });
    });
    // ...and only the resumed confirmation drafts and accepts it.
    expect(streamProposal).toHaveBeenCalledTimes(3);
    expect(vi.mocked(api.acceptProposal).mock.calls.map(([, jobId]) => jobId)).toEqual([
      "job-one",
      "job-two",
    ]);
    expect(harness.result().hook.phase).toEqual({
      kind: "done",
      generated: 1,
      stoppedEarly: false,
    });
  });

  it("drops a confirmation-gated plan entry from an unconfirmed run", async () => {
    const events: string[] = [];
    const project = projectWith([authoredChapter]);
    traceApiCalls(events, project);
    const harness = renderLoopHook(project);

    await act(async () => {
      // A hand-built plan entry carries its own gate: the executor must honor
      // it without consulting the shell again.
      await harness.result().hook.start([
        {
          id: authoredChapter.id,
          title: authoredChapter.title,
          requiresConfirmation: true,
        },
      ]);
    });

    expect(vi.mocked(streamProposal)).not.toHaveBeenCalled();
    expect(harness.result().accepted).toEqual([]);
    expect(harness.result().hook.phase).toEqual({
      kind: "done",
      generated: 0,
      stoppedEarly: false,
    });
  });
});
