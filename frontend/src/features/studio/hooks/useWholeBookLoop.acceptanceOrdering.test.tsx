import { act } from "react";
import { describe, expect, it, vi } from "vitest";
import { api, HttpError } from "@/app/api";
import { streamProposal } from "@/app/proposalStream";
import type { StudioDocument } from "@/app/types/studio";
import {
  baseProject,
  deferred,
  firstChapter,
  renderLoopHook,
  safeChapterPlan,
  secondChapter,
  traceApiCalls,
} from "./useWholeBookLoop.test-harness";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: { ...actual.api, acceptProposal: vi.fn(), document: vi.fn(), project: vi.fn() },
  };
});
vi.mock("@/app/proposalStream", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/proposalStream")>();
  return { ...actual, streamProposal: vi.fn<typeof actual.streamProposal>() };
});

describe("whole-book acceptance refresh ordering", () => {
  it.each([false, true])(
    "counts a committed chapter after a superseded body settles, stops and resumes (failure=%s)",
    async (failure) => {
      traceApiCalls([]);
      const body = deferred<StudioDocument>();
      let rejectBody!: (reason: unknown) => void;
      vi.mocked(api.document).mockImplementationOnce(() =>
        failure
          ? new Promise<StudioDocument>((_resolve, reject) => {
              rejectBody = reject;
            })
          : body.promise,
      );
      let current = true;
      const harness = renderLoopHook(
        baseProject,
        () => undefined,
        () => current,
      );
      const plan = safeChapterPlan(firstChapter, secondChapter);
      let pending = Promise.resolve();
      act(() => {
        pending = harness.result().hook.start(plan);
      });
      await vi.waitFor(() => expect(api.document).toHaveBeenCalledOnce());
      current = false;
      act(() => harness.result().hook.stop());
      await act(async () => {
        if (failure) rejectBody(new HttpError("Obsolete read failed", 503));
        else body.resolve(firstChapter);
        await pending;
      });
      expect(harness.result().hook.phase).toEqual({
        kind: "done",
        generated: 1,
        stoppedEarly: true,
      });
      expect(harness.result().accepted).toEqual([]);
      expect(api.acceptProposal).toHaveBeenCalledOnce();
      current = true;
      await act(async () => {
        await harness.result().hook.start(plan);
      });
      expect(harness.result().hook.phase).toEqual({
        kind: "done",
        generated: 1,
        stoppedEarly: false,
      });
      expect(harness.result().accepted).toEqual([secondChapter]);
      expect(api.acceptProposal).toHaveBeenCalledTimes(2);
      expect(streamProposal).toHaveBeenLastCalledWith(
        expect.objectContaining({ documentId: secondChapter.id }),
      );
    },
  );
});
