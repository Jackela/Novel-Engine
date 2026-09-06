import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { Project } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { useStudioDocumentDeletion } from "./useStudioDocumentDeletion";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      deleteDocument: vi.fn<typeof actual.api.deleteDocument>(),
    },
  };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

interface DeletionHarness {
  readonly deleteDocument: (documentId: string) => Promise<void>;
  readonly deletionFor: (documentId: string) => { isDeleting: boolean; error: string | null };
  readonly deletingDocument: () => { documentId: string } | null;
  readonly project: () => Project | null;
  readonly activeId: () => string | null;
}

function renderDeletion(initialProject: Project, initialActiveId: string | null): DeletionHarness {
  let current: DeletionHarness | undefined;

  function Probe(): null {
    const [project, setProject] = useState<Project | null>(initialProject);
    const [activeId, setActiveId] = useState<string | null>(initialActiveId);
    const owner = { projectId: initialProject.id };
    const actions = useStudioDocumentDeletion({
      project,
      projectId: initialProject.id,
      setProject,
      setActiveId,
      currentOwner: () => owner,
      isCurrentOwner: () => true,
    });
    current = {
      deleteDocument: actions.deleteDocument,
      deletionFor: actions.deletionFor,
      deletingDocument: () => actions.deletingDocument,
      project: () => project,
      activeId: () => activeId,
    };
    return null;
  }

  harness.mount(<Probe />);
  const snapshot = (): DeletionHarness => {
    if (current === undefined) throw new Error("Expected deletion actions after render.");
    return current;
  };
  return {
    deleteDocument: (documentId) => snapshot().deleteDocument(documentId),
    deletionFor: (documentId) => snapshot().deletionFor(documentId),
    deletingDocument: () => snapshot().deletingDocument(),
    project: () => snapshot().project(),
    activeId: () => snapshot().activeId(),
  };
}

describe("useStudioDocumentDeletion", () => {
  const one = chapter("doc-1", { title: "Opening", position: 1 });
  const two = chapter("doc-2", { title: "Second", position: 2 });
  const project = projectWith([one, two]);

  it("removes exactly the deleted document's row and clears a matching active id", async () => {
    vi.mocked(api.deleteDocument).mockResolvedValue(undefined);
    const view = renderDeletion(project, one.id);

    await act(async () => {
      await view.deleteDocument(one.id);
    });

    expect(api.deleteDocument).toHaveBeenCalledWith(project.id, one.id);
    expect(view.project()?.documents.map((document) => document.id)).toEqual([two.id]);
    expect(view.activeId()).toBeNull();
  });

  it("keeps an active id that pointed at a different document", async () => {
    vi.mocked(api.deleteDocument).mockResolvedValue(undefined);
    const view = renderDeletion(project, two.id);

    await act(async () => {
      await view.deleteDocument(one.id);
    });

    expect(view.activeId()).toBe(two.id);
  });

  it("exposes the in-flight document identity while the request runs", async () => {
    const command = deferred<void>();
    vi.mocked(api.deleteDocument).mockReturnValue(command.promise);
    const view = renderDeletion(project, null);

    let pending: Promise<void> | undefined;
    act(() => {
      pending = view.deleteDocument(one.id);
    });

    expect(view.deletingDocument()).toEqual({ documentId: one.id });
    expect(view.deletionFor(one.id)).toEqual({ isDeleting: true, error: null });
    expect(view.deletionFor(two.id)).toEqual({ isDeleting: false, error: null });

    await act(async () => {
      command.resolve(undefined);
      await pending;
    });
    expect(view.deletingDocument()).toBeNull();
  });

  it("keeps the row and surfaces a readable inline error when the server refuses", async () => {
    vi.mocked(api.deleteDocument).mockRejectedValue(
      new Error("Document is referenced by a snapshot."),
    );
    const view = renderDeletion(project, one.id);

    await act(async () => {
      await view.deleteDocument(one.id);
    });

    expect(view.project()?.documents.map((document) => document.id)).toEqual([one.id, two.id]);
    expect(view.deletionFor(one.id)).toEqual({
      isDeleting: false,
      error: "Document is referenced by a snapshot.",
    });
    expect(view.deletionFor(two.id).error).toBeNull();
    expect(view.activeId()).toBe(one.id);
  });

  it("ignores a late response after the project owner changed", async () => {
    const command = deferred<void>();
    vi.mocked(api.deleteDocument).mockReturnValue(command.promise);
    let stale = false;
    let current: DeletionHarness | undefined;

    function Probe(): null {
      const [project, setProject] = useState<Project | null>(initialProject);
      const [activeId, setActiveId] = useState<string | null>(one.id);
      const owner = { projectId: initialProject.id };
      const actions = useStudioDocumentDeletion({
        project,
        projectId: initialProject.id,
        setProject,
        setActiveId,
        currentOwner: () => owner,
        isCurrentOwner: () => !stale,
      });
      current = {
        deleteDocument: actions.deleteDocument,
        deletionFor: actions.deletionFor,
        deletingDocument: () => actions.deletingDocument,
        project: () => project,
        activeId: () => activeId,
      };
      return null;
    }

    const initialProject = project;
    harness.mount(<Probe />);
    const snapshot = () => {
      if (current === undefined) throw new Error("Expected deletion actions after render.");
      return current;
    };

    let pending: Promise<void> | undefined;
    act(() => {
      pending = snapshot().deleteDocument(one.id);
    });
    // The route left this project before the response settled.
    act(() => {
      stale = true;
    });
    await act(async () => {
      command.resolve(undefined);
      await pending;
    });

    expect(
      snapshot()
        .project()
        ?.documents.map((document) => document.id),
    ).toEqual([one.id, two.id]);
    expect(snapshot().deletingDocument()).toBeNull();
  });
});
