import { act } from "react";
import { describe, expect, it, vi } from "vitest";
import { api, HttpError } from "@/app/api";
import { ApiContractError } from "@/app/apiContract";
import { streamProposal } from "@/app/proposalStream";
import type { StudioDocument, StudioJob } from "@/app/types/studio";
import { deferred, flushEffects } from "@/test/harness";
import * as diagnostics from "./reportUnexpectedError";
import {
  accepted,
  before,
  mount,
  other,
  proposal,
  restored,
  restoreThroughHistory,
  startPendingAcceptance,
  until,
  view,
  wholeBook,
} from "./useStudioPageModel.proposalAcceptanceOrdering.test-harness";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      project: vi.fn<typeof actual.api.project>(),
      document: vi.fn<typeof actual.api.document>(),
      providers: vi.fn<typeof actual.api.providers>(),
      jobs: vi.fn<typeof actual.api.jobs>(),
      revisions: vi.fn<typeof actual.api.revisions>(),
      reviews: vi.fn<typeof actual.api.reviews>(),
      exports: vi.fn<typeof actual.api.exports>(),
      acceptProposal: vi.fn<typeof actual.api.acceptProposal>(),
      restoreRevision: vi.fn<typeof actual.api.restoreRevision>(),
      saveDocument: vi.fn<typeof actual.api.saveDocument>(),
    },
  };
});

vi.mock("@/app/proposalStream", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/proposalStream")>();
  return { ...actual, streamProposal: vi.fn<typeof actual.streamProposal>() };
});

describe("Studio proposal acceptance refresh ordering", () => {
  it("lands an ordinary acceptance and saves the next edit against its accepted revision", async () => {
    await mount();
    await act(async () => {
      await view().inspector.model.copilot.onAcceptProposal();
    });
    expect(view().statusbar.loadedRevisionId).toBe(accepted.current_revision_id);
    expect(view().editor.draft).toBe(accepted.content_markdown);
    act(() => view().editor.onDraftChange("Next author edit"));
    await flushEffects();
    act(() => view().editor.onSaveNow?.());
    await flushEffects();
    expect(api.saveDocument).toHaveBeenLastCalledWith(
      "project-1",
      before.id,
      expect.objectContaining({ base_revision_id: accepted.current_revision_id }),
    );
  });

  it.each([false, true])(
    "keeps a later History restore when an older acceptance body arrives (edit=%s)",
    async (edit) => {
      await mount();
      const { pending, response } = await startPendingAcceptance();
      await restoreThroughHistory();
      if (edit) {
        act(() => view().editor.onDraftChange("Author text after restore"));
        await flushEffects();
      }
      await act(async () => {
        response.resolve(accepted);
        await pending;
      });
      expect
        .soft(view().project.documents[0]?.current_revision_id)
        .toBe(restored.current_revision_id);
      expect.soft(view().statusbar.loadedRevisionId).toBe(restored.current_revision_id);
      expect
        .soft(view().editor.draft)
        .toBe(edit ? "Author text after restore" : restored.content_markdown);
      expect.soft(view().editor.saveState).not.toBe("conflict");
      if (!edit) act(() => view().editor.onDraftChange("Next author edit"));
      await flushEffects();
      act(() => view().editor.onSaveNow?.());
      await flushEffects();
      expect(api.saveDocument).toHaveBeenLastCalledWith(
        "project-1",
        before.id,
        expect.objectContaining({ base_revision_id: restored.current_revision_id }),
      );
    },
  );

  it.each([
    new HttpError("Old acceptance body unavailable", 503),
    new Error("Unexpected acceptance body failure"),
    new ApiContractError("accepted document"),
  ])(
    "ignores a superseded body failure but retains unexpected diagnostics (%s)",
    async (failure) => {
      const diagnostic = vi
        .spyOn(diagnostics, "reportUnexpectedError")
        .mockImplementation(() => {});
      await mount();
      const { pending, response } = await startPendingAcceptance();
      await restoreThroughHistory();
      await act(async () => {
        response.reject(failure);
        await pending;
      });
      expect(view().statusbar.loadedRevisionId).toBe(restored.current_revision_id);
      expect(view().editor.draft).toBe(restored.content_markdown);
      expect(view().inspector.error).toBeNull();
      if (!(failure instanceof HttpError)) {
        expect(diagnostic).toHaveBeenCalledWith(
          "Superseded proposal acceptance refresh failed.",
          failure,
        );
      } else {
        expect(diagnostic).not.toHaveBeenCalled();
      }
      diagnostic.mockRestore();
    },
  );

  it.each([false, true])(
    "keeps the restored shell after document navigation (return=%s)",
    async (returnToOriginal) => {
      await mount();
      const { pending, response } = await startPendingAcceptance();
      await restoreThroughHistory();
      act(() => view().navigator.onSelectDocument(other.id));
      await until(() => view().editor.activeDocument?.id === other.id);
      if (returnToOriginal) {
        act(() => view().navigator.onSelectDocument(before.id));
        await until(() => view().editor.activeDocument?.id === before.id);
      }
      await act(async () => {
        response.resolve(accepted);
        await pending;
      });
      expect(
        view().project.documents.find((document) => document.id === before.id)?.current_revision_id,
      ).toBe(restored.current_revision_id);
      expect(view().editor.draft).toBe(
        returnToOriginal ? restored.content_markdown : other.content_markdown,
      );
      expect(view().statusbar.loadedRevisionId).toBe(
        returnToOriginal ? restored.current_revision_id : other.current_revision_id,
      );
      if (!returnToOriginal) {
        act(() => view().navigator.onSelectDocument(before.id));
        await until(() => view().editor.activeDocument?.id === before.id);
        expect(view().editor.draft).toBe(restored.content_markdown);
        expect(view().statusbar.loadedRevisionId).toBe(restored.current_revision_id);
      }
    },
  );
  it.each(
    [false, true].flatMap((leaveAgain) => [
      { failure: new HttpError("Obsolete inactive chapter read", 503), leaveAgain },
      { failure: new Error("Unexpected inactive chapter read"), leaveAgain },
      { failure: new ApiContractError("inactive chapter"), leaveAgain },
    ]),
  )(
    "keeps whole-book progress when an initially inactive chapter advances (leave=$leaveAgain, $failure)",
    async ({ failure, leaveAgain }) => {
      const diagnostic = vi
        .spyOn(diagnostics, "reportUnexpectedError")
        .mockImplementation(() => {});
      await mount();
      act(() => view().navigator.onSelectDocument(other.id));
      await until(() => view().editor.activeDocument?.id === other.id);
      const generation = deferred<StudioJob>();
      vi.mocked(streamProposal).mockReturnValueOnce(generation.promise);
      let pending = Promise.resolve();
      const start = wholeBook().onConfirmReplace;
      if (!start) throw new Error("Expected replacement confirmation");
      act(() => {
        pending = Promise.resolve(start());
      });
      await until(() => vi.mocked(streamProposal).mock.calls.length === 1);
      act(() => view().navigator.onSelectDocument(before.id));
      await until(() => view().editor.activeDocument?.id === before.id);
      let rejectBody!: (reason: unknown) => void;
      vi.mocked(api.document).mockImplementationOnce(
        () =>
          new Promise<StudioDocument>((_resolve, reject) => {
            rejectBody = reject;
          }),
      );
      const previousReads = vi.mocked(api.document).mock.calls.length;
      act(() => generation.resolve(proposal));
      await until(() => vi.mocked(api.document).mock.calls.length > previousReads);
      await restoreThroughHistory();
      if (leaveAgain) {
        act(() => view().navigator.onSelectDocument(other.id));
        await until(() => view().editor.activeDocument?.id === other.id);
      }
      await act(async () => {
        rejectBody(failure);
        await pending;
      });
      expect(wholeBook().phase).toEqual({
        kind: "done",
        generated: 1,
        stoppedEarly: false,
      });
      expect(
        view().project.documents.find((document) => document.id === before.id)?.current_revision_id,
      ).toBe(restored.current_revision_id);
      expect(view().statusbar.loadedRevisionId).toBe(
        leaveAgain ? other.current_revision_id : restored.current_revision_id,
      );
      expect(view().editor.draft).toBe(
        leaveAgain ? other.content_markdown : restored.content_markdown,
      );
      expect(view().inspector.error).toBeNull();
      if (!(failure instanceof HttpError))
        expect(diagnostic).toHaveBeenCalledWith(
          "Superseded proposal acceptance refresh failed.",
          failure,
        );
      else expect(diagnostic).not.toHaveBeenCalled();
      diagnostic.mockRestore();
    },
  );
  it.each([false, true])(
    "retains a normal inactive refresh failure after an unrelated document change (edit=%s)",
    async (editOther) => {
      await mount();
      act(() => view().navigator.onSelectDocument(other.id));
      await until(() => view().editor.activeDocument?.id === other.id);
      vi.mocked(streamProposal).mockResolvedValueOnce(proposal);
      let rejectBody!: (reason: unknown) => void;
      vi.mocked(api.document).mockImplementationOnce(
        () =>
          new Promise<StudioDocument>((_resolve, reject) => {
            rejectBody = reject;
          }),
      );
      const start = wholeBook().onConfirmReplace;
      if (!start) throw new Error("Expected replacement confirmation");
      const previousReads = vi.mocked(api.document).mock.calls.length;
      let pending = Promise.resolve();
      act(() => {
        pending = Promise.resolve(start());
      });
      await until(() => vi.mocked(api.document).mock.calls.length > previousReads);
      if (editOther) {
        const savedOther = {
          ...other,
          title: "Other chapter edited",
          current_revision_id: "other-new-revision",
        };
        vi.mocked(api.saveDocument).mockResolvedValueOnce(savedOther);
        vi.mocked(api.document).mockImplementation(async (_project, id) =>
          id === other.id ? savedOther : accepted,
        );
        act(() => view().editor.onTitleChange(savedOther.title));
        await flushEffects();
        act(() => view().editor.onSaveNow?.());
        await until(() => view().statusbar.loadedRevisionId === savedOther.current_revision_id);
      }
      await act(async () => {
        rejectBody(new HttpError("Current inactive read failed", 503));
        await pending;
      });
      expect(wholeBook().phase).toEqual({
        kind: "failed",
        generated: 1,
        failedChapterTitle: before.title,
        message:
          "Proposal was accepted, but refreshing the project failed. Reload the project to sync.",
      });
      expect(view().editor.activeDocument?.id).toBe(other.id);
      expect(view().editor.draft).toBe(other.content_markdown);
    },
  );
});
