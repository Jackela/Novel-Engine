import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { LinkedBeat } from "@/app/apiContract";
import type { DocumentSummary, Project } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { useStudioActions } from "./useStudioActions";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      linkChapterBeat: vi.fn<typeof actual.api.linkChapterBeat>(),
      saveLoreStatus: vi.fn<typeof actual.api.saveLoreStatus>(),
    },
  };
});

const chapterOne = chapter("chapter-1", {
  title: "Chapter One",
  current_revision_id: "revision-1",
  beat_ref: null,
  position: 0,
});
const character = chapter("character-a", {
  kind: "character",
  title: "Mara",
  lore_status: "draft",
  current_revision_id: "character-revision-1",
  position: 1,
});
const outline = chapter("outline-1", {
  kind: "outline",
  title: "Outline",
  current_revision_id: "outline-revision-1",
  content_markdown: "## The Storm\n\n## The Harbor\n",
  position: 2,
});
const project = projectWith([chapterOne, character, outline]);
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
        settingsForm: { title: project.title, description: project.description, provider: "mock" },
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
    summaryOf: (documentId: string): DocumentSummary | undefined =>
      result().project?.documents.find((document) => document.id === documentId),
  };
}

function withRevision(document: DocumentSummary, revisionId: string): DocumentSummary {
  return { ...document, current_revision_id: revisionId };
}

describe("useStudioActions narrow Lore/beat causal-authority matrix (#466)", () => {
  it("lets the newer Lore intent win when same-revision responses settle in reverse", async () => {
    const first = deferred<{ lore_status: "stable" }>();
    const second = deferred<{ lore_status: "deprecated" }>();
    vi.mocked(api.saveLoreStatus)
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const view = renderActions();
    let firstSave!: Promise<void>;
    let secondSave!: Promise<void>;

    act(() => {
      firstSave = view.result().actions.changeLoreStatus(character.id, "stable");
      secondSave = view.result().actions.changeLoreStatus(character.id, "deprecated");
    });

    await act(async () => {
      second.resolve({ lore_status: "deprecated" });
      await secondSave;
    });
    expect(view.summaryOf(character.id)?.lore_status).toBe("deprecated");

    await act(async () => {
      first.resolve({ lore_status: "stable" });
      await firstSave;
    });

    expect(view.summaryOf(character.id)?.lore_status).toBe("deprecated");
    expect(view.result().actions.loreStatusFor(character.id)).toEqual({
      isSaving: false,
      error: null,
      attemptedStatus: null,
    });
  });

  it("lets the newer beat intent win when same-revision responses settle in reverse", async () => {
    const first = deferred<{ beat: LinkedBeat | null }>();
    const second = deferred<{ beat: LinkedBeat | null }>();
    vi.mocked(api.linkChapterBeat)
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const view = renderActions();
    let firstLink!: Promise<void>;
    let secondLink!: Promise<void>;

    act(() => {
      firstLink = view.result().actions.linkBeat(chapterOne.id, "The Storm");
      secondLink = view.result().actions.linkBeat(chapterOne.id, "The Harbor");
    });

    await act(async () => {
      second.resolve({ beat: { title: "The Harbor", content: "quiet pier" } });
      await secondLink;
    });
    expect(view.summaryOf(chapterOne.id)?.beat_ref).toBe("The Harbor");

    await act(async () => {
      first.resolve({ beat: { title: "The Storm", content: "washed-up chart" } });
      await firstLink;
    });

    expect(view.summaryOf(chapterOne.id)?.beat_ref).toBe("The Harbor");
    expect(view.result().actions.beatFor(chapterOne.id)).toEqual({
      isSaving: false,
      error: null,
      attemptedTitle: null,
    });
  });

  it("patches the normalized requested beat despite a concurrently renamed outline heading", async () => {
    // The outline heading renames between persistence and resolution, so the
    // resolved display comes back null; stored-reference authority is still
    // the successful command's trimmed requested title.
    const response = deferred<{ beat: LinkedBeat | null }>();
    vi.mocked(api.linkChapterBeat).mockReturnValue(response.promise);
    const view = renderActions();
    let linking!: Promise<void>;

    act(() => {
      linking = view.result().actions.linkBeat(chapterOne.id, "  The Storm  ");
    });
    const renamedOutline = withRevision(outline, "outline-revision-2");
    view.replaceProject({ ...project, documents: [chapterOne, character, renamedOutline] });

    await act(async () => {
      response.resolve({ beat: null });
      await linking;
    });

    expect(api.linkChapterBeat).toHaveBeenCalledWith(project.id, chapterOne.id, "The Storm");
    expect(view.summaryOf(chapterOne.id)?.beat_ref).toBe("The Storm");
    expect(view.summaryOf(outline.id)?.current_revision_id).toBe("outline-revision-2");
  });

  it("ignores an older-revision Lore response after a newer revision owns the row", async () => {
    const response = deferred<{ lore_status: "stable" }>();
    vi.mocked(api.saveLoreStatus).mockReturnValue(response.promise);
    const view = renderActions();
    let saving!: Promise<void>;

    act(() => {
      saving = view.result().actions.changeLoreStatus(character.id, "stable");
    });
    const newerCharacter = {
      ...withRevision(character, "character-revision-2"),
      lore_status: "draft" as const,
      word_count: 1200,
    };
    view.replaceProject({ ...project, documents: [chapterOne, newerCharacter, outline] });

    await act(async () => {
      response.resolve({ lore_status: "stable" });
      await saving;
    });

    expect(view.summaryOf(character.id)).toEqual(newerCharacter);
  });

  it("ignores an older-revision beat response after a newer revision owns the row", async () => {
    const response = deferred<{ beat: LinkedBeat | null }>();
    vi.mocked(api.linkChapterBeat).mockReturnValue(response.promise);
    const view = renderActions();
    let linking!: Promise<void>;

    act(() => {
      linking = view.result().actions.linkBeat(chapterOne.id, "The Storm");
    });
    const newerChapter = {
      ...withRevision(chapterOne, "revision-2"),
      beat_ref: "The Harbor",
      revision_source: "author" as const,
      word_count: 900,
    };
    view.replaceProject({ ...project, documents: [newerChapter, character, outline] });

    await act(async () => {
      response.resolve({ beat: { title: "The Storm", content: "washed-up chart" } });
      await linking;
    });

    expect(view.summaryOf(chapterOne.id)).toEqual(newerChapter);
  });

  it("clears a linked beat with an explicit null command", async () => {
    vi.mocked(api.linkChapterBeat).mockResolvedValue({ beat: null });
    const view = renderActions();
    view.replaceProject({
      ...project,
      documents: [{ ...chapterOne, beat_ref: "The Storm" }, character, outline],
    });

    await act(async () => {
      await view.result().actions.linkBeat(chapterOne.id, null);
    });

    expect(api.linkChapterBeat).toHaveBeenCalledWith(project.id, chapterOne.id, null);
    expect(view.summaryOf(chapterOne.id)?.beat_ref).toBeNull();
  });
});
