import { act, useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { Project, StudioDocument } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness, deferred, flushEffects, flushMicrotasks } from "@/test/harness";

import { useDocumentDraft } from "./useDocumentDraft";
import { useOwnerKeyedErrors } from "./useOwnerKeyedErrors";

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
const initialProject = projectWith([documentA, documentB]);
const draftErrorSources = ["draft", "revision", "restore"] as const;

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
  readonly result: () => DraftHook;
  readonly rerender: (document: StudioDocument, project: Project) => void;
} {
  let activeDocument = documentA;
  let projectId = initialProject.id;
  let current: DraftHook | undefined;
  let replaceProject: ((project: Project) => void) | undefined;

  function Wrapper(): null {
    const [, setProject] = useState<Project | null>(initialProject);
    const [, setError] = useState<string | null>(null);
    replaceProject = setProject;
    current = useDocumentDraft(activeDocument, projectId, setProject, setError);
    return null;
  }

  const { root } = harness.mount(<Wrapper />);
  return {
    result: () => {
      if (!current) throw new Error("Expected draft hook after render.");
      return current;
    },
    rerender: (document, project) => {
      activeDocument = document;
      projectId = project.id;
      act(() => {
        replaceProject?.(project);
        root.render(<Wrapper />);
      });
    },
  };
}

function renderDraftWithErrors(): {
  readonly result: () => {
    readonly hook: DraftHook;
    readonly error: string | null;
    readonly publishDraftError: (error: string | null) => void;
  };
  readonly rerender: (document: StudioDocument) => void;
} {
  let activeDocument = documentA;
  let current:
    | {
        readonly hook: DraftHook;
        readonly error: string | null;
        readonly publishDraftError: (error: string | null) => void;
      }
    | undefined;

  function Wrapper(): null {
    const [, setProject] = useState<Project | null>(initialProject);
    const errors = useOwnerKeyedErrors(
      `${initialProject.id}\u0000${activeDocument.id}`,
      draftErrorSources,
    );
    current = {
      hook: useDocumentDraft(
        activeDocument,
        initialProject.id,
        setProject,
        errors.publishers.draft,
        errors.publishers.revision,
        errors.publishers.restore,
      ),
      error: errors.error,
      publishDraftError: errors.publishers.draft,
    };
    return null;
  }

  const { root } = harness.mount(<Wrapper />);
  return {
    result: () => {
      if (!current) throw new Error("Expected keyed draft hook after render.");
      return current;
    },
    rerender: (document) => {
      activeDocument = document;
      act(() => root.render(<Wrapper />));
    },
  };
}

async function advanceAutosave(): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1500);
  });
}

describe("useDocumentDraft external commit reconciliation", () => {
  it("adopts an accepted aggregate revision for a clean inactive document", async () => {
    const acceptedA = {
      ...documentA,
      current_revision_id: "revision-a-accepted",
      content_markdown: "Document A accepted proposal",
      updated_at: documentA.updated_at,
    };
    const acceptedProject = projectWith([acceptedA, documentB]);
    const draft = renderDraft();
    await flushMicrotasks();

    draft.rerender(documentB, acceptedProject);
    draft.rerender(acceptedA, acceptedProject);

    expect(draft.result().draft).toBe(acceptedA.content_markdown);
    expect(draft.result().titleDraft).toBe(acceptedA.title);
    expect(draft.result().loadedRevision.current).toBe(acceptedA.current_revision_id);
    await advanceAutosave();
    expect(api.saveDocument).not.toHaveBeenCalled();
  });

  it("keeps a newer local draft in conflict with an accepted aggregate revision", async () => {
    const acceptedA = {
      ...documentA,
      current_revision_id: "revision-a-accepted",
      content_markdown: "Document A accepted proposal",
      updated_at: documentA.updated_at,
    };
    const acceptedProject = projectWith([acceptedA, documentB]);
    const draft = renderDraft();
    await flushMicrotasks();

    act(() => draft.result().setDraft("Document A newer local draft"));
    draft.rerender(documentB, acceptedProject);
    draft.rerender(acceptedA, acceptedProject);

    expect(draft.result().draft).toBe("Document A newer local draft");
    expect(draft.result().loadedRevision.current).toBe(acceptedA.current_revision_id);
    expect(draft.result().saveState).toBe("conflict");
    await advanceAutosave();
    expect(api.saveDocument).not.toHaveBeenCalled();
  });

  it("does not start a second document A save after A to B to A", async () => {
    const saveA = deferred<StudioDocument>();
    vi.mocked(api.saveDocument).mockReturnValue(saveA.promise);
    const draft = renderDraft();
    await flushMicrotasks();

    act(() => draft.result().setDraft("Document A pending draft"));
    await advanceAutosave();
    draft.rerender(documentB, initialProject);
    draft.rerender(documentA, initialProject);
    await advanceAutosave();

    expect(api.saveDocument).toHaveBeenCalledOnce();

    await act(async () => {
      saveA.resolve({
        ...documentA,
        current_revision_id: "revision-a-2",
        content_markdown: "Document A pending draft",
      });
      await saveA.promise;
    });
  });

  it("publishes an in-flight A save failure after A to B to A without polluting B", async () => {
    let rejectSave!: (reason: unknown) => void;
    const saveA = new Promise<StudioDocument>((_resolve, reject) => {
      rejectSave = reject;
    });
    vi.mocked(api.saveDocument).mockReturnValue(saveA);
    const draft = renderDraftWithErrors();
    await flushMicrotasks();

    act(() => draft.result().hook.setDraft("Document A pending draft"));
    await advanceAutosave();
    draft.rerender(documentB);
    expect(draft.result().error).toBeNull();
    draft.rerender(documentA);
    await advanceAutosave();
    expect(api.saveDocument).toHaveBeenCalledOnce();

    await act(async () => {
      rejectSave(new Error("Document A save failed."));
      await saveA.catch(() => undefined);
    });
    await flushEffects();

    expect(draft.result().hook.saveState).toBe("error");
    expect(draft.result().error).toBe("Document A save failed.");
    draft.rerender(documentB);
    expect(draft.result().error).toBeNull();
    draft.rerender(documentA);
    expect(draft.result().error).toBe("Document A save failed.");
  });

  it("clears A's prior draft error when an inactive retry save commits", async () => {
    const retrySave = deferred<StudioDocument>();
    vi.mocked(api.saveDocument)
      .mockRejectedValueOnce(new Error("First A save failed."))
      .mockReturnValueOnce(retrySave.promise);
    const draft = renderDraftWithErrors();
    await flushMicrotasks();

    act(() => draft.result().hook.setDraft("Document A first edit"));
    await advanceAutosave();
    await flushEffects();
    expect(draft.result().error).toBe("First A save failed.");

    act(() => draft.result().hook.setDraft("Document A retry edit"));
    await advanceAutosave();
    expect(api.saveDocument).toHaveBeenCalledTimes(2);
    draft.rerender(documentB);
    await act(async () => {
      retrySave.resolve({
        ...documentA,
        current_revision_id: "revision-a-2",
        content_markdown: "Document A retry edit",
      });
      await retrySave.promise;
    });
    await flushEffects();

    expect(draft.result().error).toBeNull();
    draft.rerender(documentA);
    expect(draft.result().error).toBeNull();
  });

  it("clears A's prior draft error when acceptance reconciles while B is active", async () => {
    const draft = renderDraftWithErrors();
    await flushMicrotasks();
    act(() => draft.result().publishDraftError("Prior A save failed."));
    const acceptA = draft.result().hook.captureAcceptance(documentA.id);

    draft.rerender(documentB);
    act(() =>
      acceptA?.({
        ...documentA,
        current_revision_id: "revision-a-accepted",
        content_markdown: "Accepted A",
      }),
    );
    expect(draft.result().error).toBeNull();

    draft.rerender(documentA);
    expect(draft.result().error).toBeNull();
  });
});
