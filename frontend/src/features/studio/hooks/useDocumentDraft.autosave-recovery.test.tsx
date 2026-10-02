import { act, useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { Project, StudioDocument } from "@/app/types/studio";
import { chapter, projectWith, revision } from "@/test/factories";
import { createMountHarness, flushMicrotasks } from "@/test/harness";

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
  const { root } = harness.mount(<Wrapper />);
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
  };
}

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
  harness.cleanup();
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
