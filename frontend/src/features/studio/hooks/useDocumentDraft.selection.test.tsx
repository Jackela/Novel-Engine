import { act, useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { Project, StudioDocument } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness, deferred, flushMicrotasks } from "@/test/harness";

import { useDocumentDraft } from "./useDocumentDraft";

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

const harness = createMountHarness();
const documentA = chapter("document-a", { content_markdown: "Accepted A", title: "Title A" });
const documentB = chapter("document-b", { content_markdown: "Accepted B", title: "Title B" });
const project = projectWith([documentA, documentB]);

beforeEach(() => {
  vi.useFakeTimers();
  vi.mocked(api.revisions).mockResolvedValue({ revisions: [], next_cursor: null });
  vi.mocked(api.document).mockResolvedValue(documentA);
});

afterEach(() => {
  harness.cleanup();
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.resetAllMocks();
});

function renderDraft() {
  let body: StudioDocument | null = documentA;
  let selectedId: string | null = documentA.id;
  let current: { hook: ReturnType<typeof useDocumentDraft>; error: string | null } | undefined;
  function Wrapper() {
    const [, setProject] = useState<Project | null>(project);
    const [error, setError] = useState<string | null>(null);
    const hook = useDocumentDraft(
      body,
      project.id,
      setProject,
      setError,
      setError,
      setError,
      selectedId,
    );
    current = { hook, error };
    return null;
  }
  const { root, container } = harness.mount(<Wrapper />);
  return {
    result: () => {
      if (!current) throw new Error("Expected mounted draft.");
      return current;
    },
    select: async (document: StudioDocument | null, id: string | null = document?.id ?? null) => {
      body = document;
      selectedId = id;
      act(() => root.render(<Wrapper />));
      await flushMicrotasks();
    },
    unmount: () => harness.unmount(container),
  };
}

async function advance(milliseconds = 1500) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(milliseconds);
  });
}

describe("Document selection owns the Draft lifetime", () => {
  it("discards unsaved title and body across a body-loading selection", async () => {
    const view = renderDraft();
    await flushMicrotasks();
    act(() => {
      view.result().hook.setDraft("Unsaved A");
      view.result().hook.setTitleDraft("Unsaved title");
    });
    await advance(1000);
    await view.select(null, documentB.id);
    await view.select(null, documentA.id);
    await view.select(documentA);
    expect(view.result().hook.draft).toBe(documentA.content_markdown);
    expect(view.result().hook.titleDraft).toBe(documentA.title);
    await advance();
    expect(api.saveDocument).not.toHaveBeenCalled();
  });

  it("preserves the selected Draft during a temporary missing body and retry", async () => {
    const view = renderDraft();
    await flushMicrotasks();
    act(() => view.result().hook.setDraft("Still editing A"));
    await view.select(null, documentA.id);
    await advance();
    expect(api.saveDocument).not.toHaveBeenCalled();
    expect(view.result().hook.draft).toBe("Still editing A");
    await view.select(documentA);
    expect(view.result().hook.draft).toBe("Still editing A");
    vi.mocked(api.saveDocument).mockResolvedValue({
      ...documentA,
      content_markdown: "Still editing A",
      current_revision_id: "saved-a",
    });
    await advance(1499);
    expect(api.saveDocument).not.toHaveBeenCalled();
    await advance(1);
    expect(api.saveDocument).toHaveBeenCalledOnce();
  });

  it("retains an active conflict through loading, then discards it on selection", async () => {
    vi.mocked(api.saveDocument).mockRejectedValue(new HttpError("Conflict", 409));
    const view = renderDraft();
    await flushMicrotasks();
    act(() => view.result().hook.setDraft("Conflicted A"));
    await advance();
    expect(view.result().hook.saveState).toBe("conflict");
    await view.select(null, documentA.id);
    await view.select(documentA);
    expect(view.result().hook.draft).toBe("Conflicted A");
    expect(view.result().hook.saveState).toBe("conflict");
    await view.select(documentB);
    await view.select(documentA);
    expect(view.result().hook.draft).toBe(documentA.content_markdown);
    expect(view.result().hook.saveState).toBe("idle");
    expect(view.result().error).toBeNull();
  });

  it.each([409, 500])("does not publish an obsolete %s into a new A lifecycle", async (status) => {
    let rejectSave!: (reason: unknown) => void;
    const save = new Promise<StudioDocument>((_resolve, reject) => {
      rejectSave = reject;
    });
    vi.mocked(api.saveDocument)
      .mockReturnValueOnce(save)
      .mockResolvedValueOnce({
        ...documentA,
        content_markdown: "New A",
        current_revision_id: "new-a",
      });
    const view = renderDraft();
    await flushMicrotasks();
    act(() => view.result().hook.setDraft("Old A"));
    await advance();
    await view.select(documentB);
    await view.select(documentA);
    act(() => view.result().hook.setDraft("New A"));
    await advance();
    expect(api.saveDocument).toHaveBeenCalledOnce();
    await act(async () => {
      rejectSave(new HttpError("Obsolete failure", status));
      await save.catch(() => undefined);
    });
    expect(view.result().hook.draft).toBe("New A");
    expect(view.result().hook.saveState).toBe("saving");
    expect(view.result().error).toBeNull();
    await advance();
    expect(api.saveDocument).toHaveBeenCalledTimes(2);
    expect(api.saveDocument).toHaveBeenLastCalledWith(
      project.id,
      documentA.id,
      expect.objectContaining({ content_markdown: "New A" }),
    );
  });

  it("adopts a late committed revision without resurrecting the discarded newer Draft", async () => {
    const save = deferred<StudioDocument>();
    vi.mocked(api.saveDocument).mockReturnValue(save.promise);
    const view = renderDraft();
    await flushMicrotasks();
    act(() => view.result().hook.setDraft("Committed A"));
    await advance();
    act(() => view.result().hook.setDraft("Discard me"));
    await view.select(documentB);
    await view.select(documentA);
    const committed = { ...documentA, content_markdown: "Committed A", current_revision_id: "a-2" };
    await act(async () => {
      save.resolve(committed);
      await save.promise;
    });
    expect(view.result().hook.draft).toBe(committed.content_markdown);
    expect(view.result().hook.loadedRevision.current).toBe(committed.current_revision_id);
    expect(view.result().hook.saveState).toBe("saved");
  });

  it("discards a Draft on route departure and remount", async () => {
    const view = renderDraft();
    await flushMicrotasks();
    act(() => view.result().hook.setDraft("Departed A"));
    view.unmount();
    const next = renderDraft();
    await flushMicrotasks();
    expect(next.result().hook.draft).toBe(documentA.content_markdown);
    await advance();
    expect(api.saveDocument).not.toHaveBeenCalled();
  });
});
