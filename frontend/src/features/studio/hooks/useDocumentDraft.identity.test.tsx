import { act, useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { Project, StudioDocument } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness, deferred, flushMicrotasks } from "@/test/harness";

import { summarizeDocument } from "./projectState";
import { useDocumentDraft } from "./useDocumentDraft";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      document: vi.fn<typeof actual.api.document>(),
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
  readonly error: string | null;
}

const harness = createMountHarness();
const documentA = chapter("document-1", {
  title: "Chapter One",
  current_revision_id: "revision-a-1",
  content_markdown: "Document A original",
});
const projectA = projectWith([documentA]);
const projectBDocument = {
  ...documentA,
  project_id: "project-2",
  title: "Project Two Chapter",
  current_revision_id: "revision-b-1",
  content_markdown: "Project B original",
};
const projectB = projectWith([projectBDocument], { id: "project-2", title: "Second novel" });
const summaries = (...documents: StudioDocument[]) => documents.map(summarizeDocument);

beforeEach(() => {
  vi.useFakeTimers();
  vi.mocked(api.revisions).mockResolvedValue({ revisions: [], next_cursor: null });
});

afterEach(() => {
  harness.cleanup();
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.resetAllMocks();
});

function renderDraft(
  initialDocument: StudioDocument,
  initialProject: Project,
): {
  readonly result: () => HarnessResult;
  readonly rerender: (document: StudioDocument, project: Project) => void;
} {
  let activeDocument = initialDocument;
  let projectId = initialProject.id;
  let current: HarnessResult | undefined;
  let replaceProject: ((project: Project) => void) | undefined;

  function Wrapper(): null {
    const [project, setProject] = useState<Project | null>(initialProject);
    const [error, setError] = useState<string | null>(null);
    replaceProject = setProject;
    current = {
      hook: useDocumentDraft(activeDocument, projectId, setProject, setError),
      project,
      error,
    };
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

async function advanceAutosave(): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1500);
  });
}

describe("useDocumentDraft identity", () => {
  it("lets project B autosave and discards the late same-id project A save", async () => {
    const saveA = deferred<StudioDocument>();
    const saveB = deferred<StudioDocument>();
    const savedB = {
      ...projectBDocument,
      current_revision_id: "revision-b-2",
      content_markdown: "Project B edit",
    };
    vi.mocked(api.saveDocument).mockImplementation((projectId) =>
      projectId === projectA.id ? saveA.promise : saveB.promise,
    );
    const draft = renderDraft(documentA, projectA);
    await flushMicrotasks();

    act(() => draft.result().hook.setDraft("Project A edit"));
    await advanceAutosave();
    draft.rerender(projectBDocument, projectB);
    expect(draft.result().hook.draft).toBe(projectBDocument.content_markdown);
    expect(draft.result().hook.loadedRevision.current).toBe(projectBDocument.current_revision_id);
    act(() => draft.result().hook.setDraft(savedB.content_markdown));
    await advanceAutosave();

    expect(api.saveDocument).toHaveBeenCalledTimes(2);
    expect(api.saveDocument).toHaveBeenLastCalledWith(
      projectB.id,
      projectBDocument.id,
      expect.objectContaining({ base_revision_id: projectBDocument.current_revision_id }),
    );
    await act(async () => {
      saveB.resolve(savedB);
      await saveB.promise;
      saveA.resolve({ ...documentA, content_markdown: "Late project A edit" });
      await saveA.promise;
      await Promise.resolve();
    });

    expect(draft.result().hook.draft).toBe(savedB.content_markdown);
    expect(draft.result().hook.loadedRevision.current).toBe(savedB.current_revision_id);
    expect(draft.result().project?.documents).toEqual([summarizeDocument(savedB)]);
    expect(draft.result().error).toBeNull();
  });

  it("lets document B autosave while reconciling document A's committed result", async () => {
    const documentB = chapter("document-2", {
      title: "Chapter Two",
      current_revision_id: "revision-document-b-1",
      content_markdown: "Document B original",
    });
    const project = projectWith(summaries(documentA, documentB));
    const savedB = {
      ...documentB,
      current_revision_id: "revision-document-b-2",
      content_markdown: "Document B edit",
    };
    const saveA = deferred<StudioDocument>();
    const saveB = deferred<StudioDocument>();
    vi.mocked(api.saveDocument).mockImplementation((_projectId, documentId) =>
      documentId === documentA.id ? saveA.promise : saveB.promise,
    );
    const draft = renderDraft(documentA, project);
    await flushMicrotasks();

    act(() => draft.result().hook.setDraft("Document A edit"));
    await advanceAutosave();
    draft.rerender(documentB, project);
    act(() => draft.result().hook.setDraft(savedB.content_markdown));
    await advanceAutosave();

    expect(api.saveDocument).toHaveBeenCalledTimes(2);
    expect(api.saveDocument).toHaveBeenLastCalledWith(
      project.id,
      documentB.id,
      expect.objectContaining({ base_revision_id: documentB.current_revision_id }),
    );
    await act(async () => {
      saveB.resolve(savedB);
      await saveB.promise;
      saveA.resolve({ ...documentA, content_markdown: "Late document A edit" });
      await saveA.promise;
      await Promise.resolve();
    });

    expect(draft.result().hook.draft).toBe(savedB.content_markdown);
    expect(draft.result().hook.loadedRevision.current).toBe(savedB.current_revision_id);
    expect(draft.result().hook.saveState).toBe("saved");
    expect(draft.result().project?.documents).toEqual(
      summaries({ ...documentA, content_markdown: "Late document A edit" }, savedB),
    );
  });

  it("discards a restore completion after the project identity changes", async () => {
    const restore = deferred<StudioDocument>();
    vi.mocked(api.restoreRevision).mockReturnValue(restore.promise);
    const draft = renderDraft(documentA, projectA);
    await flushMicrotasks();
    let restoring: Promise<void> = Promise.resolve();

    act(() => {
      restoring = draft.result().hook.restoreRevision("revision-old");
    });
    await vi.waitFor(() => expect(api.restoreRevision).toHaveBeenCalledTimes(1));
    draft.rerender(projectBDocument, projectB);
    await act(async () => {
      restore.resolve({
        ...documentA,
        current_revision_id: "late-restored-revision",
        content_markdown: "Late project A restore",
      });
      await restoring;
    });

    expect(draft.result().hook.draft).toBe(projectBDocument.content_markdown);
    expect(draft.result().hook.loadedRevision.current).toBe(projectBDocument.current_revision_id);
    expect(draft.result().project).toEqual(projectB);
    expect(draft.result().error).toBeNull();
  });

  it("refreshes a stale restore baseline and allows a truthful retry", async () => {
    const latestDocument = {
      ...documentA,
      current_revision_id: "revision-a-2",
      content_markdown: "Server advanced document A",
    };
    const restoredDocument = {
      ...documentA,
      current_revision_id: "revision-a-3",
      content_markdown: "Restored document A",
    };
    vi.mocked(api.restoreRevision)
      .mockRejectedValueOnce(new HttpError("Revision conflict", 409))
      .mockResolvedValueOnce(restoredDocument);
    vi.mocked(api.document).mockResolvedValue(latestDocument);
    const draft = renderDraft(documentA, projectA);
    await flushMicrotasks();

    act(() => draft.result().hook.setDraft("Unsaved local document A"));
    await act(async () => {
      await draft.result().hook.restoreRevision("revision-old");
    });

    expect(draft.result().hook.draft).toBe("Unsaved local document A");
    expect(draft.result().hook.loadedRevision.current).toBe(latestDocument.current_revision_id);
    expect(draft.result().hook.saveState).toBe("conflict");
    expect(draft.result().error).toContain("latest revision is ready");

    await act(async () => {
      await draft.result().hook.restoreRevision("revision-old");
    });

    expect(api.restoreRevision).toHaveBeenLastCalledWith(
      projectA.id,
      documentA.id,
      "revision-old",
      latestDocument.current_revision_id,
    );
    expect(draft.result().hook.draft).toBe(restoredDocument.content_markdown);
    expect(draft.result().hook.loadedRevision.current).toBe(restoredDocument.current_revision_id);
    expect(draft.result().hook.saveState).toBe("idle");
    expect(draft.result().error).toBeNull();
  });

  it("refreshes document A's stale restore baseline while document B stays active", async () => {
    const documentB = chapter("document-2", {
      title: "Chapter Two",
      current_revision_id: "revision-b-1",
      content_markdown: "Document B original",
    });
    const project = projectWith(summaries(documentA, documentB));
    const latestA = {
      ...documentA,
      current_revision_id: "revision-a-2",
      content_markdown: "Server advanced document A",
    };
    const restoredA = {
      ...documentA,
      current_revision_id: "revision-a-3",
      content_markdown: "Restored document A",
    };
    let rejectRestore!: (reason: unknown) => void;
    const firstRestore = new Promise<StudioDocument>((_resolve, reject) => {
      rejectRestore = reject;
    });
    vi.mocked(api.restoreRevision)
      .mockReturnValueOnce(firstRestore)
      .mockResolvedValueOnce(restoredA);
    vi.mocked(api.document).mockResolvedValue(latestA);
    const draft = renderDraft(documentA, project);
    await flushMicrotasks();
    act(() => draft.result().hook.setDraft("Unsaved local document A"));
    let restoring!: Promise<void>;

    act(() => {
      restoring = draft.result().hook.restoreRevision("revision-old");
    });
    draft.rerender(documentB, project);
    await act(async () => {
      rejectRestore(new HttpError("Revision conflict", 409));
      await restoring;
    });

    expect(draft.result().hook.draft).toBe(documentB.content_markdown);
    expect(draft.result().hook.loadedRevision.current).toBe(documentB.current_revision_id);
    expect(draft.result().project?.documents).toEqual(summaries(latestA, documentB));

    draft.rerender(latestA, draft.result().project ?? project);
    expect(draft.result().hook.draft).toBe("Unsaved local document A");
    expect(draft.result().hook.loadedRevision.current).toBe(latestA.current_revision_id);
    expect(draft.result().hook.saveState).toBe("conflict");
    await act(async () => {
      await draft.result().hook.restoreRevision("revision-old");
    });
    expect(api.restoreRevision).toHaveBeenLastCalledWith(
      project.id,
      documentA.id,
      "revision-old",
      latestA.current_revision_id,
    );
  });
});
