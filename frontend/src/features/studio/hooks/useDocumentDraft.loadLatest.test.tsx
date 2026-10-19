import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { StudioDocument } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";
import { deferred, flushEffects } from "@/test/harness";

import { createDocumentDraftTestHarness } from "./createDocumentDraftTestHarness";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      document: vi.fn<typeof actual.api.document>(),
      revisions: vi.fn<typeof actual.api.revisions>(),
      saveDocument: vi.fn<typeof actual.api.saveDocument>(),
    },
  };
});

const original = chapter("document-one", {
  content_markdown: "Original manuscript",
  current_revision_id: "revision-one",
});
const serverDocument: StudioDocument = {
  ...original,
  content_markdown: "Accepted in another tab",
  current_revision_id: "revision-two",
};
const latestDocument: StudioDocument = {
  ...serverDocument,
  title: "Latest server title",
  content_markdown: "Server advanced again",
  current_revision_id: "revision-three",
};
const documentB = chapter("document-two");
const harness = createDocumentDraftTestHarness(projectWith([original, documentB]), original);

beforeEach(() => {
  vi.useFakeTimers();
  vi.mocked(api.revisions).mockResolvedValue({ revisions: [], next_cursor: null });
  vi.mocked(api.document).mockResolvedValue(serverDocument);
  vi.mocked(api.saveDocument).mockRejectedValue(
    new HttpError("Revision conflict", 409, undefined, "REVISION_CONFLICT"),
  );
});

afterEach(() => {
  harness.cleanup();
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.resetAllMocks();
});

async function conflictedDraft() {
  const view = harness.renderDraft();
  await flushEffects();
  act(() => view.result().hook.setDraft("Local text before discard"));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1500);
  });
  expect(view.result().hook.saveState).toBe("conflict");
  return view;
}

function beginLoadLatest(view: Awaited<ReturnType<typeof conflictedDraft>>) {
  const response = deferred<StudioDocument>();
  vi.mocked(api.document).mockReturnValueOnce(response.promise);
  let pending!: Promise<void>;
  act(() => {
    pending = view.result().hook.loadLatest();
  });
  expect(view.result().hook.isConflictActionPending).toBe(true);
  return {
    response,
    pending,
    settle: async () => {
      await act(async () => {
        response.resolve(latestDocument);
        await pending;
      });
    },
  };
}

describe("useDocumentDraft Load latest intent", () => {
  it.each(["body", "title", "both"])(
    "retains %s edits made after discard starts against the latest server baseline",
    async (editedField) => {
      const view = await conflictedDraft();
      const loading = beginLoadLatest(view);
      act(() => {
        if (editedField !== "title") view.result().hook.setDraft("Text after discard");
        if (editedField !== "body") view.result().hook.setTitleDraft("Title after discard");
      });
      await loading.settle();

      expect(view.result().hook.draft).toBe(
        editedField === "title" ? "Local text before discard" : "Text after discard",
      );
      expect(view.result().hook.titleDraft).toBe(
        editedField === "body" ? original.title : "Title after discard",
      );
      expect(view.result().hook.loadedRevision.current).toBe(latestDocument.current_revision_id);
      expect(view.result().hook.saveState).toBe("conflict");
      expect(view.result().hook.isConflictActionPending).toBe(false);
      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });
      expect(api.saveDocument).toHaveBeenCalledTimes(1);
    },
  );

  it("discards the old Draft when no edit follows the discard command", async () => {
    const view = await conflictedDraft();
    const loading = beginLoadLatest(view);
    await loading.settle();

    expect(view.result().hook.draft).toBe(latestDocument.content_markdown);
    expect(view.result().hook.titleDraft).toBe(latestDocument.title);
    expect(view.result().hook.loadedRevision.current).toBe(latestDocument.current_revision_id);
    expect(view.result().hook.saveState).toBe("idle");
    expect(view.result().error).toBeNull();
  });

  it("keeps new edits when loading the server baseline fails", async () => {
    const view = await conflictedDraft();
    const response = deferred<void>();
    vi.mocked(api.document).mockImplementationOnce(async () => {
      await response.promise;
      throw new HttpError("Server unavailable", 503);
    });
    let pending!: Promise<void>;
    act(() => {
      pending = view.result().hook.loadLatest();
    });
    act(() => {
      view.result().hook.setDraft("New text while unavailable");
      view.result().hook.setTitleDraft("New title while unavailable");
    });
    await act(async () => {
      response.resolve(undefined);
      await pending;
    });

    expect(view.result().hook.draft).toBe("New text while unavailable");
    expect(view.result().hook.titleDraft).toBe("New title while unavailable");
    expect(view.result().hook.loadedRevision.current).toBe(serverDocument.current_revision_id);
    expect(view.result().hook.saveState).toBe("error");
    expect(view.result().error).toBe("Server unavailable");
    expect(view.result().hook.isConflictActionPending).toBe(false);
  });

  it("aborts a departed owner's load and leaves the selected Document unchanged", async () => {
    const view = await conflictedDraft();
    const loading = beginLoadLatest(view);
    const signal = vi.mocked(api.document).mock.lastCall?.[2]?.signal;
    await view.select(documentB);
    expect(signal?.aborted).toBe(true);
    await loading.settle();

    expect(view.result().hook.draft).toBe(documentB.content_markdown);
    expect(view.result().hook.titleDraft).toBe(documentB.title);
    expect(view.result().hook.loadedRevision.current).toBe(documentB.current_revision_id);
    expect(view.result().hook.saveState).toBe("idle");
    expect(view.result().error).toBeNull();
  });

  it("overwrites from the latest baseline only after the author chooses to keep new edits", async () => {
    const view = await conflictedDraft();
    const loading = beginLoadLatest(view);
    act(() => {
      view.result().hook.setDraft("New text to keep");
      view.result().hook.setTitleDraft("New title to keep");
    });
    await loading.settle();
    expect(view.result().hook.saveState).toBe("conflict");
    vi.mocked(api.document).mockResolvedValue(latestDocument);
    vi.mocked(api.saveDocument).mockResolvedValue({
      ...latestDocument,
      content_markdown: "New text to keep",
      title: "New title to keep",
      current_revision_id: "revision-four",
    });
    await act(async () => {
      await view.result().hook.retryOverwrite();
    });

    expect(api.saveDocument).toHaveBeenLastCalledWith(original.project_id, original.id, {
      base_revision_id: latestDocument.current_revision_id,
      content_markdown: "New text to keep",
      title: "New title to keep",
      autosave: true,
    });
    expect(view.result().hook.draft).toBe("New text to keep");
    expect(view.result().hook.titleDraft).toBe("New title to keep");
    expect(view.result().hook.loadedRevision.current).toBe("revision-four");
    expect(view.result().hook.saveState).toBe("saved");
  });
});
