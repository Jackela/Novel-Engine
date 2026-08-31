import { act, useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
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
      project: vi.fn<typeof actual.api.project>(),
      revisions: vi.fn<typeof actual.api.revisions>(),
      restoreRevision: vi.fn<typeof actual.api.restoreRevision>(),
      saveDocument: vi.fn<typeof actual.api.saveDocument>(),
    },
  };
});

type DraftHook = ReturnType<typeof useDocumentDraft>;

interface HarnessResult {
  readonly hook: DraftHook;
  readonly project: Project | null;
}

const harness = createMountHarness();
const documentA = chapter("document-1", {
  title: "Chapter One",
  current_revision_id: "revision-a-1",
  content_markdown: "Document A original",
});
const documentB = chapter("document-2", {
  title: "Chapter Two",
  current_revision_id: "revision-b-1",
  content_markdown: "Document B original",
});
const project = projectWith([documentA, documentB]);

beforeEach(() => {
  vi.useFakeTimers();
  vi.mocked(api.revisions).mockResolvedValue({ revisions: [] });
});

afterEach(() => {
  harness.cleanup();
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.resetAllMocks();
});

function renderDraft(): {
  readonly result: () => HarnessResult;
  readonly rerender: (document: StudioDocument, nextProject?: Project) => void;
} {
  let activeDocument = documentA;
  let current: HarnessResult | undefined;
  let replaceProject: ((nextProject: Project) => void) | undefined;

  function Wrapper(): null {
    const [activeProject, setProject] = useState<Project | null>(project);
    const [, setError] = useState<string | null>(null);
    replaceProject = setProject;
    current = {
      hook: useDocumentDraft(activeDocument, project.id, setProject, setError),
      project: activeProject,
    };
    return null;
  }

  const { root } = harness.mount(<Wrapper />);
  return {
    result: () => {
      if (!current) throw new Error("Expected draft hook after render.");
      return current;
    },
    rerender: (document, nextProject = project) => {
      activeDocument = document;
      act(() => {
        replaceProject?.(nextProject);
        root.render(<Wrapper />);
      });
    },
  };
}

async function advanceAutosave(): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1500);
  });
}

describe("useDocumentDraft committed reconciliation", () => {
  it("keeps document A's pre-debounce draft isolated while visiting document B", async () => {
    const draft = renderDraft();
    await flushMicrotasks();

    act(() => draft.result().hook.setDraft("Document A local draft"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    draft.rerender(documentB);

    expect(draft.result().hook.draft).toBe(documentB.content_markdown);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(api.saveDocument).not.toHaveBeenCalled();
    expect(draft.result().hook.draft).toBe(documentB.content_markdown);

    draft.rerender(documentA);

    expect(draft.result().hook.draft).toBe("Document A local draft");
    expect(draft.result().hook.titleDraft).toBe(documentA.title);
  });

  it("reconciles a committed document A autosave without changing document B", async () => {
    const committedA = {
      ...documentA,
      current_revision_id: "revision-a-2",
      content_markdown: "Document A committed draft",
    };
    const saveA = deferred<StudioDocument>();
    vi.mocked(api.saveDocument).mockReturnValue(saveA.promise);
    const draft = renderDraft();
    await flushMicrotasks();

    act(() => draft.result().hook.setDraft(committedA.content_markdown));
    await advanceAutosave();
    draft.rerender(documentB);

    await act(async () => {
      saveA.resolve(committedA);
      await saveA.promise;
      await Promise.resolve();
    });

    expect(draft.result().hook.draft).toBe(documentB.content_markdown);
    expect(draft.result().hook.loadedRevision.current).toBe(documentB.current_revision_id);
    expect(draft.result().project?.documents).toEqual([committedA, documentB]);

    draft.rerender(committedA, draft.result().project ?? project);

    expect(draft.result().hook.draft).toBe(committedA.content_markdown);
    expect(draft.result().hook.loadedRevision.current).toBe(committedA.current_revision_id);
    expect(draft.result().hook.saveState).toBe("saved");
  });

  it("keeps a newer document A edit and exposes conflict after its older save commits", async () => {
    const committedA = {
      ...documentA,
      current_revision_id: "revision-a-2",
      content_markdown: "Document A first edit",
    };
    const saveA = deferred<StudioDocument>();
    vi.mocked(api.saveDocument).mockReturnValue(saveA.promise);
    const draft = renderDraft();
    await flushMicrotasks();

    act(() => draft.result().hook.setDraft(committedA.content_markdown));
    await advanceAutosave();
    draft.rerender(documentB);
    draft.rerender(documentA);
    act(() => draft.result().hook.setDraft("Document A newer local edit"));

    await act(async () => {
      saveA.resolve(committedA);
      await saveA.promise;
      await Promise.resolve();
    });

    expect(draft.result().hook.draft).toBe("Document A newer local edit");
    expect(draft.result().hook.loadedRevision.current).toBe(committedA.current_revision_id);
    expect(draft.result().hook.saveState).toBe("conflict");
    expect(draft.result().project?.documents).toEqual([committedA, documentB]);
  });

  it("preserves an edit made after proposal acceptance starts", async () => {
    const acceptedA = {
      ...documentA,
      current_revision_id: "revision-a-accepted",
      content_markdown: "AI accepted content",
      revision_source: "ai-accepted",
    };
    const draft = renderDraft();
    await flushMicrotasks();
    const reconcileAcceptance = draft.result().hook.captureAcceptance(documentA.id);
    if (!reconcileAcceptance) throw new Error("Expected an active-document reconciler.");

    act(() => draft.result().hook.setDraft("Newer author edit"));
    act(() => reconcileAcceptance(acceptedA));

    expect(draft.result().hook.draft).toBe("Newer author edit");
    expect(draft.result().hook.loadedRevision.current).toBe(acceptedA.current_revision_id);
    expect(draft.result().hook.saveState).toBe("conflict");
    expect(draft.result().project?.documents).toEqual([acceptedA, documentB]);
  });

  it("uses a clean externally advanced baseline for the next acceptance", async () => {
    const acceptedOnce = {
      ...documentA,
      current_revision_id: "revision-a-accepted-1",
      content_markdown: "First accepted content",
    };
    const acceptedTwice = {
      ...acceptedOnce,
      current_revision_id: "revision-a-accepted-2",
      content_markdown: "Second accepted content",
    };
    const draft = renderDraft();
    await flushMicrotasks();

    draft.rerender(documentB);
    draft.rerender(acceptedOnce, { ...project, documents: [acceptedOnce, documentB] });
    expect(draft.result().hook.draft).toBe(acceptedOnce.content_markdown);
    const reconcileAcceptance = draft.result().hook.captureAcceptance(documentA.id);
    if (!reconcileAcceptance) throw new Error("Expected an active-document reconciler.");

    act(() => reconcileAcceptance(acceptedTwice));

    expect(draft.result().hook.draft).toBe(acceptedTwice.content_markdown);
    expect(draft.result().hook.loadedRevision.current).toBe(acceptedTwice.current_revision_id);
    expect(draft.result().hook.saveState).toBe("saved");
  });

  it("retains the clean external baseline when the next acceptance finishes off-document", async () => {
    const acceptedOnce = {
      ...documentA,
      current_revision_id: "revision-a-accepted-1",
      content_markdown: "First accepted content",
    };
    const acceptedTwice = {
      ...acceptedOnce,
      current_revision_id: "revision-a-accepted-2",
      content_markdown: "Second accepted content",
    };
    const acceptedProject = { ...project, documents: [acceptedOnce, documentB] };
    const draft = renderDraft();
    await flushMicrotasks();

    draft.rerender(documentB);
    draft.rerender(acceptedOnce, acceptedProject);
    expect(draft.result().hook.draft).toBe(acceptedOnce.content_markdown);
    const reconcileAcceptance = draft.result().hook.captureAcceptance(documentA.id);
    if (!reconcileAcceptance) throw new Error("Expected an active-document reconciler.");

    draft.rerender(documentB, acceptedProject);
    act(() => reconcileAcceptance(acceptedTwice));

    expect(draft.result().hook.draft).toBe(documentB.content_markdown);
    expect(draft.result().hook.loadedRevision.current).toBe(documentB.current_revision_id);
    expect(draft.result().project?.documents).toEqual([acceptedTwice, documentB]);

    draft.rerender(acceptedTwice, draft.result().project ?? acceptedProject);

    expect(draft.result().hook.draft).toBe(acceptedTwice.content_markdown);
    expect(draft.result().hook.loadedRevision.current).toBe(acceptedTwice.current_revision_id);
    expect(draft.result().hook.saveState).toBe("saved");
  });

  it("reconciles a committed document A restore without changing document B", async () => {
    const restoredA = {
      ...documentA,
      current_revision_id: "revision-a-restored",
      content_markdown: "Document A restored",
    };
    const restoreA = deferred<StudioDocument>();
    vi.mocked(api.restoreRevision).mockReturnValue(restoreA.promise);
    const draft = renderDraft();
    await flushMicrotasks();
    let restoring = Promise.resolve();

    act(() => {
      restoring = draft.result().hook.restoreRevision("revision-a-old");
    });
    await vi.waitFor(() => expect(api.restoreRevision).toHaveBeenCalledTimes(1));
    draft.rerender(documentB);

    await act(async () => {
      restoreA.resolve(restoredA);
      await restoring;
    });

    expect(draft.result().hook.draft).toBe(documentB.content_markdown);
    expect(draft.result().hook.loadedRevision.current).toBe(documentB.current_revision_id);
    expect(draft.result().project?.documents).toEqual([restoredA, documentB]);

    draft.rerender(restoredA, draft.result().project ?? project);

    expect(draft.result().hook.draft).toBe(restoredA.content_markdown);
    expect(draft.result().hook.loadedRevision.current).toBe(restoredA.current_revision_id);
    expect(draft.result().hook.saveState).toBe("idle");
  });

  it("keeps a newer document A edit and exposes conflict after its restore commits", async () => {
    const restoredA = {
      ...documentA,
      current_revision_id: "revision-a-restored",
      content_markdown: "Document A restored",
    };
    const restoreA = deferred<StudioDocument>();
    vi.mocked(api.restoreRevision).mockReturnValue(restoreA.promise);
    const draft = renderDraft();
    await flushMicrotasks();
    let restoring = Promise.resolve();

    act(() => {
      restoring = draft.result().hook.restoreRevision("revision-a-old");
    });
    await vi.waitFor(() => expect(api.restoreRevision).toHaveBeenCalledTimes(1));
    draft.rerender(documentB);
    draft.rerender(documentA);
    act(() => draft.result().hook.setDraft("Document A newer local edit"));

    await act(async () => {
      restoreA.resolve(restoredA);
      await restoring;
    });

    expect(draft.result().hook.draft).toBe("Document A newer local edit");
    expect(draft.result().hook.loadedRevision.current).toBe(restoredA.current_revision_id);
    expect(draft.result().hook.saveState).toBe("conflict");
    expect(draft.result().project?.documents).toEqual([restoredA, documentB]);
  });
});
