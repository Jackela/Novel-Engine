import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { StudioDocument } from "@/app/types/studio";
import { chapter, projectWith, revision } from "@/test/factories";
import { deferred, flushMicrotasks } from "@/test/harness";

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

const documentA = chapter("document-a", {
  title: "Chapter A",
  current_revision_id: "revision-a1",
  content_markdown: "Accepted A",
});
const documentB = chapter("document-b", {
  title: "Chapter B",
  current_revision_id: "revision-b1",
  content_markdown: "Accepted B",
});
const project = projectWith([documentA, documentB]);
const initialRevision = revision("revision-a1", { document_id: documentA.id });

const savedA = {
  ...documentA,
  current_revision_id: "revision-a2",
  content_markdown: "Unsaved A",
  updated_at: "2026-10-01T00:01:00Z",
};

const { renderDraft, cleanup } = createDocumentDraftTestHarness(project, documentA);

async function advance(milliseconds: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(milliseconds);
  });
}

function dispatchBeforeUnload(): Event {
  const event = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(event);
  return event;
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.mocked(api.revisions).mockResolvedValue({ revisions: [initialRevision], next_cursor: null });
  vi.mocked(api.document).mockResolvedValue(documentA);
});

afterEach(() => {
  cleanup();
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.resetAllMocks();
});

describe("autosave recovery", () => {
  it("retries a failed autosave without further typing and recovers to saved", async () => {
    vi.mocked(api.saveDocument)
      .mockRejectedValueOnce(new Error("service unavailable"))
      .mockResolvedValueOnce(savedA);
    const view = renderDraft();
    await flushMicrotasks();
    act(() => view.result().hook.setDraft(savedA.content_markdown));
    await advance(1500);
    expect(view.result().hook.saveState).toBe("error");

    await advance(4999);
    expect(api.saveDocument).toHaveBeenCalledTimes(1);
    await advance(1);
    await flushMicrotasks();
    expect(api.saveDocument).toHaveBeenCalledTimes(2);
    expect(api.saveDocument).toHaveBeenLastCalledWith(project.id, documentA.id, {
      content_markdown: savedA.content_markdown,
      base_revision_id: documentA.current_revision_id,
      title: documentA.title,
      autosave: true,
    });
    expect(view.result().hook.saveState).toBe("saved");
  });

  it("keeps retrying with a capped backoff while the service stays down", async () => {
    vi.mocked(api.saveDocument).mockRejectedValue(new Error("service unavailable"));
    const view = renderDraft();
    await flushMicrotasks();
    act(() => view.result().hook.setDraft("Offline edit"));
    await advance(1500);
    expect(api.saveDocument).toHaveBeenCalledTimes(1);

    await advance(5000);
    expect(api.saveDocument).toHaveBeenCalledTimes(2);

    await advance(14999);
    expect(api.saveDocument).toHaveBeenCalledTimes(2);
    await advance(1);
    expect(api.saveDocument).toHaveBeenCalledTimes(3);

    await advance(30000);
    expect(api.saveDocument).toHaveBeenCalledTimes(4);
    expect(view.result().hook.saveState).toBe("error");
  });

  it.each([413, 422])(
    "keeps a permanent %s refusal without retrying unchanged text",
    async (status) => {
      vi.mocked(api.saveDocument)
        .mockRejectedValueOnce(new HttpError("Chapter capacity exceeded.", status))
        .mockResolvedValueOnce({ ...savedA, content_markdown: "Shorter draft" });
      const view = renderDraft();
      await flushMicrotasks();
      act(() => view.result().hook.setDraft("Oversized draft"));
      await advance(1500);
      expect(view.result().hook.saveState).toBe("error");
      const failureMessage = view.result().error;
      expect(failureMessage).toBeTruthy();
      expect(view.result().hook.draft).toBe("Oversized draft");

      await advance(65_000);
      expect(api.saveDocument).toHaveBeenCalledTimes(1);
      expect(view.result().hook.saveState).toBe("error");
      expect(view.result().error).toBe(failureMessage);

      act(() => view.result().hook.setDraft("Shorter draft"));
      await advance(1500);
      expect(api.saveDocument).toHaveBeenCalledTimes(2);
      expect(view.result().hook.saveState).toBe("saved");
      expect(view.result().hook.draft).toBe("Shorter draft");
    },
  );

  it.each([413, 422])(
    "saves a corrected Draft edited while a %s response was pending",
    async (status) => {
      const firstSave = deferred<StudioDocument>();
      vi.mocked(api.saveDocument)
        .mockImplementationOnce(() =>
          firstSave.promise.then(() => {
            throw new HttpError("Chapter capacity exceeded.", status);
          }),
        )
        .mockResolvedValueOnce({ ...savedA, content_markdown: "Shorter draft" });
      const view = renderDraft();
      await flushMicrotasks();
      act(() => view.result().hook.setDraft("Oversized draft"));
      await advance(1500);
      act(() => view.result().hook.setDraft("Shorter draft"));
      await act(async () => {
        firstSave.resolve(documentA);
      });
      await advance(1500);
      expect(api.saveDocument).toHaveBeenCalledTimes(2);
      expect(vi.mocked(api.saveDocument).mock.lastCall?.[2].content_markdown).toBe("Shorter draft");
      expect(view.result().hook.saveState).toBe("saved");
      expect(view.result().hook.draft).toBe("Shorter draft");
      expect(view.result().error).toBeNull();
    },
  );

  it("keeps a title conflict editable without adopting a new revision baseline", async () => {
    vi.mocked(api.saveDocument)
      .mockRejectedValueOnce(
        new HttpError("Document title already exists.", 409, undefined, "DOCUMENT_CONFLICT"),
      )
      .mockResolvedValueOnce({ ...savedA, title: "Unique title" });
    const view = renderDraft();
    await flushMicrotasks();
    act(() => {
      view.result().hook.setDraft(savedA.content_markdown);
      view.result().hook.setTitleDraft("Duplicate title");
    });
    await advance(1500);
    expect(view.result().hook.saveState).toBe("error");
    expect(view.result().hook.draft).toBe(savedA.content_markdown);
    expect(view.result().hook.titleDraft).toBe("Duplicate title");
    expect(view.result().error).toBeTruthy();
    expect(view.result().hook.loadedRevision.current).toBe(documentA.current_revision_id);
    expect(api.document).not.toHaveBeenCalled();

    await advance(65_000);
    expect(api.saveDocument).toHaveBeenCalledTimes(1);
    act(() => view.result().hook.setTitleDraft("Unique title"));
    await advance(1500);
    expect(api.saveDocument).toHaveBeenLastCalledWith(project.id, documentA.id, {
      content_markdown: savedA.content_markdown,
      base_revision_id: documentA.current_revision_id,
      title: "Unique title",
      autosave: true,
    });
    expect(view.result().hook.saveState).toBe("saved");
  });

  it("recovers on the next keystroke after a failure", async () => {
    vi.mocked(api.saveDocument)
      .mockRejectedValueOnce(new Error("service unavailable"))
      .mockResolvedValueOnce({ ...savedA, content_markdown: "Second try" });
    const view = renderDraft();
    await flushMicrotasks();
    act(() => view.result().hook.setDraft("First try"));
    await advance(1500);
    expect(view.result().hook.saveState).toBe("error");

    act(() => view.result().hook.setDraft("Second try"));
    await advance(1500);
    expect(api.saveDocument).toHaveBeenCalledTimes(2);
    expect(view.result().hook.saveState).toBe("saved");
  });

  it("saves immediately when the author asks for a manual retry", async () => {
    vi.mocked(api.saveDocument)
      .mockRejectedValueOnce(new Error("service unavailable"))
      .mockResolvedValueOnce(savedA);
    const view = renderDraft();
    await flushMicrotasks();
    act(() => view.result().hook.setDraft(savedA.content_markdown));
    await advance(1500);
    expect(view.result().hook.saveState).toBe("error");

    act(() => view.result().hook.retrySave());
    await flushMicrotasks();
    expect(api.saveDocument).toHaveBeenCalledTimes(2);
    expect(view.result().hook.saveState).toBe("saved");
  });
});

describe("manual save (Ctrl/Cmd+S)", () => {
  it("flushes the pending debounce immediately through the autosave persist path", async () => {
    vi.mocked(api.saveDocument).mockResolvedValue(savedA);
    const view = renderDraft();
    await flushMicrotasks();
    act(() => view.result().hook.setDraft("Unsaved A"));
    await advance(1000);
    expect(api.saveDocument).not.toHaveBeenCalled();

    act(() => view.result().hook.saveNow());
    await flushMicrotasks();

    expect(api.saveDocument).toHaveBeenCalledTimes(1);
    expect(api.saveDocument).toHaveBeenCalledWith(project.id, documentA.id, {
      content_markdown: "Unsaved A",
      base_revision_id: documentA.current_revision_id,
      title: documentA.title,
      autosave: true,
    });
    expect(view.result().hook.saveState).toBe("saved");
  });

  it("does not write a revision when the draft has no unpersisted edits", async () => {
    const view = renderDraft();
    await flushMicrotasks();

    act(() => view.result().hook.saveNow());
    await flushMicrotasks();

    expect(api.saveDocument).not.toHaveBeenCalled();
  });

  it("retries a failed save through the DR-001 recovery path", async () => {
    vi.mocked(api.saveDocument)
      .mockRejectedValueOnce(new Error("service unavailable"))
      .mockResolvedValueOnce(savedA);
    const view = renderDraft();
    await flushMicrotasks();
    act(() => view.result().hook.setDraft(savedA.content_markdown));
    await advance(1500);
    expect(view.result().hook.saveState).toBe("error");

    act(() => view.result().hook.saveNow());
    await flushMicrotasks();

    expect(api.saveDocument).toHaveBeenCalledTimes(2);
    expect(view.result().hook.saveState).toBe("saved");
  });
});

describe("draft rescue on leave", () => {
  it("flushes the pending draft when switching documents before the debounce fires", async () => {
    vi.mocked(api.saveDocument).mockResolvedValue(savedA);
    const view = renderDraft();
    await flushMicrotasks();
    act(() => {
      view.result().hook.setDraft("Unsaved A");
      view.result().hook.setTitleDraft("Unsaved title");
    });
    await advance(1000);
    expect(api.saveDocument).not.toHaveBeenCalled();

    await view.select(documentB);
    expect(api.saveDocument).toHaveBeenCalledTimes(1);
    expect(api.saveDocument).toHaveBeenCalledWith(project.id, documentA.id, {
      content_markdown: "Unsaved A",
      base_revision_id: documentA.current_revision_id,
      title: "Unsaved title",
      autosave: true,
    });

    await view.select(documentA);
    expect(view.result().hook.draft).toBe(documentA.content_markdown);
    expect(api.saveDocument).toHaveBeenCalledTimes(1);
  });

  it("warns before unload while edits are unsaved and stops once the save lands", async () => {
    vi.mocked(api.saveDocument).mockResolvedValue(savedA);
    const view = renderDraft();
    await flushMicrotasks();
    act(() => view.result().hook.setDraft(savedA.content_markdown));
    expect(dispatchBeforeUnload().defaultPrevented).toBe(true);

    await advance(1500);
    await advance(1500);
    expect(view.result().hook.saveState).toBe("saved");
    await view.select(savedA);
    expect(dispatchBeforeUnload().defaultPrevented).toBe(false);
  });
});
