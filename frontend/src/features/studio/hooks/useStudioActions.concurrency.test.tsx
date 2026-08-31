import { act, type FormEvent, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { Project, StudioDocument } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { useStudioActions } from "./useStudioActions";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      reorderDocuments: vi.fn<typeof actual.api.reorderDocuments>(),
      updateProject: vi.fn<typeof actual.api.updateProject>(),
    },
  };
});

const chapterOne = chapter("chapter-1", {
  title: "Chapter One",
  current_revision_id: "revision-1",
  content_markdown: "Original chapter",
  position: 0,
});
const note = chapter("note-1", {
  kind: "note",
  title: "Note One",
  current_revision_id: "note-revision-1",
  content_markdown: "",
  position: 1,
});
const project = projectWith([chapterOne, note], {
  description: "Old description",
  settings: { provider: "mock", temperature: 0.5 },
});
const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function renderActions() {
  let current:
    | { readonly actions: ReturnType<typeof useStudioActions>; readonly project: Project | null }
    | undefined;
  let publishProject: ((next: Project) => void) | undefined;

  function Wrapper(): null {
    const [visibleProject, setProject] = useState<Project | null>(project);
    publishProject = setProject;
    current = {
      project: visibleProject,
      actions: useStudioActions({
        project: visibleProject,
        projectId: project.id,
        setProject,
        setReviews: vi.fn(),
        setError: vi.fn(),
        setActiveId: vi.fn(),
        settingsForm: {
          title: "Updated Harbor",
          description: "Updated description",
          provider: "dashscope",
        },
        loadJobs: vi.fn().mockResolvedValue(undefined),
      }),
    };
    return null;
  }

  harness.mount(<Wrapper />);
  const result = () => {
    if (!current) throw new Error("Expected Studio actions after render.");
    return current;
  };
  return {
    result,
    replaceProject: (next: Project) => act(() => publishProject?.(next)),
    submitSettings: () =>
      result().actions.updateProjectSettings({ preventDefault: vi.fn() } as unknown as FormEvent),
  };
}

describe("useStudioActions concurrent aggregate publication", () => {
  it("applies a delayed reorder without rolling back a newer document revision", async () => {
    const response = deferred<{ documents: StudioDocument[] }>();
    vi.mocked(api.reorderDocuments).mockReturnValue(response.promise);
    const view = renderActions();
    let moving: Promise<void> = Promise.resolve();

    act(() => {
      moving = view.result().actions.moveDocument(note.id, -1);
    });
    const committedChapter = {
      ...chapterOne,
      current_revision_id: "revision-2",
      content_markdown: "Newer committed chapter",
      revision_source: "ai-accepted",
    };
    view.replaceProject({ ...project, documents: [committedChapter, note] });

    await act(async () => {
      response.resolve({
        documents: [
          { ...note, position: 0 },
          { ...chapterOne, position: 1 },
        ],
      });
      await moving;
    });

    expect(view.result().project?.documents).toEqual([
      { ...note, position: 0 },
      { ...committedChapter, position: 1 },
    ]);
  });

  it("applies delayed settings without rolling back a newer document revision", async () => {
    const response = deferred<Project>();
    vi.mocked(api.updateProject).mockReturnValue(response.promise);
    const view = renderActions();
    const committedChapter = {
      ...chapterOne,
      current_revision_id: "revision-2",
      content_markdown: "Newer committed chapter",
      revision_source: "ai-accepted",
    };
    const newerProjectTimestamp = "2026-08-27T00:05:00Z";
    let saving: Promise<void> = Promise.resolve();

    act(() => {
      saving = view.submitSettings();
    });
    view.replaceProject({
      ...project,
      documents: [committedChapter, note],
      updated_at: newerProjectTimestamp,
    });
    await act(async () => {
      response.resolve({
        ...project,
        title: "Updated Harbor",
        description: "Updated description",
        settings: { provider: "dashscope", temperature: 0.5 },
      });
      await saving;
    });

    expect(view.result().project).toMatchObject({
      title: "Updated Harbor",
      description: "Updated description",
      settings: { provider: "dashscope", temperature: 0.5 },
      documents: [committedChapter, note],
      updated_at: newerProjectTimestamp,
    });
  });
});
