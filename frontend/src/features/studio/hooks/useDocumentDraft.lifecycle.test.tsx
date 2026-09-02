import { act, type Dispatch, type SetStateAction, StrictMode, useState } from "react";
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
const project = projectWith([documentA, documentB]);

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

describe("useDocumentDraft lifecycle", () => {
  it("does not publish a committed save after the workbench unmounts", async () => {
    const save = deferred<StudioDocument>();
    vi.mocked(api.saveDocument).mockReturnValue(save.promise);
    const setProject = vi.fn<Dispatch<SetStateAction<Project | null>>>();
    const setError = vi.fn<Dispatch<SetStateAction<string | null>>>();
    let hook: DraftHook | undefined;

    function Wrapper(): null {
      hook = useDocumentDraft(documentA, project.id, setProject, setError);
      return null;
    }

    const { container } = harness.mount(<Wrapper />);
    await flushMicrotasks();
    setProject.mockClear();
    setError.mockClear();
    act(() => hook?.setDraft("Document A committed draft"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });
    const revisionRequestsBeforeUnmount = vi.mocked(api.revisions).mock.calls.length;

    harness.unmount(container);
    await act(async () => {
      save.resolve({
        ...documentA,
        current_revision_id: "revision-a-2",
        content_markdown: "Document A committed draft",
      });
      await save.promise;
      await Promise.resolve();
    });

    expect(setProject).not.toHaveBeenCalled();
    expect(setError).not.toHaveBeenCalled();
    expect(api.revisions).toHaveBeenCalledTimes(revisionRequestsBeforeUnmount);
  });

  it("preserves owner drafts and autosaves once under StrictMode effect replay", async () => {
    const committedA = {
      ...documentA,
      current_revision_id: "revision-a-2",
      content_markdown: "Document A strict draft",
    };
    vi.mocked(api.saveDocument).mockResolvedValue(committedA);
    let activeDocument = documentA;
    let current: DraftHook | undefined;

    function Wrapper(): null {
      const [, setProject] = useState<Project | null>(project);
      const [, setError] = useState<string | null>(null);
      current = useDocumentDraft(activeDocument, project.id, setProject, setError);
      return null;
    }

    const { root } = harness.mount(
      <StrictMode>
        <Wrapper />
      </StrictMode>,
    );
    await flushMicrotasks();
    act(() => current?.setDraft(committedA.content_markdown));
    activeDocument = documentB;
    act(() =>
      root.render(
        <StrictMode>
          <Wrapper />
        </StrictMode>,
      ),
    );
    activeDocument = documentA;
    act(() =>
      root.render(
        <StrictMode>
          <Wrapper />
        </StrictMode>,
      ),
    );

    expect(current?.draft).toBe(committedA.content_markdown);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    expect(api.saveDocument).toHaveBeenCalledOnce();
    expect(current?.loadedRevision.current).toBe(committedA.current_revision_id);
    expect(current?.saveState).toBe("saved");
  });

  it("merges a delayed A conflict refresh without regressing a committed document B", async () => {
    const latestA = {
      ...documentA,
      current_revision_id: "revision-a-2",
      content_markdown: "Document A server edit",
    };
    const committedB = {
      ...documentB,
      current_revision_id: "revision-b-2",
      content_markdown: "Document B committed edit",
    };
    const staleARefresh = deferred<Project>();
    let rejectSaveA!: (reason: unknown) => void;
    const saveA = new Promise<StudioDocument>((_resolve, reject) => {
      rejectSaveA = reject;
    });
    vi.mocked(api.project).mockReturnValue(staleARefresh.promise);
    vi.mocked(api.saveDocument).mockReturnValueOnce(saveA).mockResolvedValueOnce(committedB);
    let activeDocument = documentA;
    let current: { readonly hook: DraftHook; readonly project: Project | null } | undefined;

    function Wrapper(): null {
      const [visibleProject, setProject] = useState<Project | null>(project);
      const [, setError] = useState<string | null>(null);
      current = {
        hook: useDocumentDraft(activeDocument, project.id, setProject, setError),
        project: visibleProject,
      };
      return null;
    }

    const result = () => {
      if (!current) throw new Error("Expected draft hook after render.");
      return current;
    };
    const { root } = harness.mount(<Wrapper />);
    await flushMicrotasks();

    act(() => result().hook.setDraft("Document A local edit"));
    await act(async () => {
      vi.advanceTimersByTime(1500);
      await Promise.resolve();
    });
    expect(api.saveDocument).toHaveBeenCalledTimes(1);

    activeDocument = documentB;
    act(() => root.render(<Wrapper />));
    act(() => result().hook.setDraft(committedB.content_markdown));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });
    expect(result().project?.documents).toEqual([documentA, committedB]);

    await act(async () => {
      rejectSaveA(new HttpError("revision conflict", 409));
      await saveA.catch(() => undefined);
      await Promise.resolve();
      await Promise.resolve();
    });
    await vi.waitFor(() => expect(api.project).toHaveBeenCalledTimes(1));

    await act(async () => {
      staleARefresh.resolve({ ...project, documents: [latestA, documentB] });
      await staleARefresh.promise;
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result().project?.documents).toEqual([latestA, committedB]);
  });
});
