import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { Project, StudioDocument } from "@/app/types/studio";
import { chapter, projectWith, volume } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { useStudioChapterPlacement } from "./useStudioChapterPlacement";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      moveChapterToVolume: vi.fn<typeof actual.api.moveChapterToVolume>(),
    },
  };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

const volumeOne = volume("volume-1", 1, { title: "Volume One" });
const volumeTwo = volume("volume-2", 2, { title: "Volume Two" });
const chapterOne = chapter("doc-1", { title: "Opening", position: 1 });
const chapterTwo = chapter("doc-2", { title: "Second", position: 2, volume_id: "volume-2" });
const project = projectWith([chapterOne, chapterTwo], { volumes: [volumeOne, volumeTwo] });

/** The server's placement response: complete Document, revision unchanged. */
function placedDocument(base: StudioDocument, volumeId: string, position: number): StudioDocument {
  return {
    ...base,
    volume_id: volumeId,
    position,
    updated_at: "2026-09-06T00:00:00Z",
  };
}

interface PlacementHarness {
  readonly placeChapter: (documentId: string, volumeId: string) => Promise<void>;
  readonly placementFor: (documentId: string) => {
    isPlacing: boolean;
    error: string | null;
    attemptedVolumeId: string | null;
  };
  readonly placingDocument: () => { documentId: string; volumeId: string } | null;
  readonly setProject: (next: Project) => void;
  readonly project: () => Project | null;
}

function renderPlacement(initialProject: Project): PlacementHarness {
  let current: PlacementHarness | undefined;
  let replaceProject: ((next: Project) => void) | undefined;

  function Probe(): null {
    const [project, setProject] = useState<Project | null>(initialProject);
    replaceProject = setProject;
    const owner = { projectId: initialProject.id };
    const actions = useStudioChapterPlacement({
      project,
      projectId: initialProject.id,
      setProject,
      currentOwner: () => owner,
      isCurrentOwner: () => true,
    });
    current = {
      placeChapter: actions.placeChapter,
      placementFor: actions.placementFor,
      placingDocument: () => actions.placingDocument,
      setProject: (next) => setProject(next),
      project: () => project,
    };
    return null;
  }

  harness.mount(<Probe />);
  const snapshot = (): PlacementHarness => {
    if (current === undefined) throw new Error("Expected placement actions after render.");
    return current;
  };
  return {
    placeChapter: (documentId, volumeId) => snapshot().placeChapter(documentId, volumeId),
    placementFor: (documentId) => snapshot().placementFor(documentId),
    placingDocument: () => snapshot().placingDocument(),
    setProject: (next) => {
      const replace = replaceProject;
      if (replace === undefined) throw new Error("Expected a mounted probe.");
      act(() => replace(next));
    },
    project: () => snapshot().project(),
  };
}

describe("useStudioChapterPlacement", () => {
  it("patches only volume, position, and updated_at on the captured row", async () => {
    const response = placedDocument(chapterOne, volumeTwo.id, 3);
    vi.mocked(api.moveChapterToVolume).mockResolvedValue(response);
    const view = renderPlacement(project);

    await act(async () => {
      await view.placeChapter(chapterOne.id, volumeTwo.id);
    });

    expect(api.moveChapterToVolume).toHaveBeenCalledWith(project.id, chapterOne.id, volumeTwo.id);
    const documents = view.project()?.documents ?? [];
    const placed = documents.find((document) => document.id === chapterOne.id);
    expect(placed).toMatchObject({
      volume_id: volumeTwo.id,
      position: 3,
      updated_at: "2026-09-06T00:00:00Z",
      // Fields placement does not own keep their shell values.
      title: chapterOne.title,
      current_revision_id: chapterOne.current_revision_id,
      word_count: chapterOne.word_count,
    });
    expect(documents.find((document) => document.id === chapterTwo.id)).toEqual(chapterTwo);
  });

  it("rejects a late response whose captured revision no longer owns the row", async () => {
    const command = deferred<StudioDocument>();
    vi.mocked(api.moveChapterToVolume).mockReturnValue(command.promise);
    const view = renderPlacement(project);

    let pending: Promise<void> | undefined;
    act(() => {
      pending = view.placeChapter(chapterOne.id, volumeTwo.id);
    });
    // A newer save advances the shell revision before the response settles.
    view.setProject(
      projectWith([{ ...chapterOne, current_revision_id: "revision-newer" }, chapterTwo], {
        volumes: [volumeOne, volumeTwo],
      }),
    );
    await act(async () => {
      command.resolve(placedDocument(chapterOne, volumeTwo.id, 3));
      await pending;
    });

    const placed = view.project()?.documents.find((document) => document.id === chapterOne.id);
    expect(placed).toMatchObject({
      current_revision_id: "revision-newer",
      volume_id: volumeOne.id,
      position: chapterOne.position,
    });
  });

  it("supersedes an older in-flight intent when a newer placement targets another volume", async () => {
    const older = deferred<StudioDocument>();
    const newer = deferred<StudioDocument>();
    vi.mocked(api.moveChapterToVolume)
      .mockReturnValueOnce(older.promise)
      .mockReturnValueOnce(newer.promise);
    const view = renderPlacement(project);

    let olderPending: Promise<void> | undefined;
    let newerPending: Promise<void> | undefined;
    act(() => {
      olderPending = view.placeChapter(chapterOne.id, volumeTwo.id);
    });
    act(() => {
      newerPending = view.placeChapter(chapterOne.id, "volume-3");
    });

    // The older response settles last and must not overwrite the newer one.
    await act(async () => {
      newer.resolve(placedDocument(chapterOne, "volume-3", 1));
      await newerPending;
    });
    await act(async () => {
      older.resolve(placedDocument(chapterOne, volumeTwo.id, 9));
      await olderPending;
    });

    const placed = view.project()?.documents.find((document) => document.id === chapterOne.id);
    expect(placed).toMatchObject({ volume_id: "volume-3", position: 1 });
  });

  it("coalesces a duplicate in-flight intent for the same target volume", async () => {
    const command = deferred<StudioDocument>();
    vi.mocked(api.moveChapterToVolume).mockReturnValue(command.promise);
    const view = renderPlacement(project);

    let first: Promise<void> | undefined;
    act(() => {
      first = view.placeChapter(chapterOne.id, volumeTwo.id);
    });
    // The duplicate rides the first intent's promise; awaiting it inside
    // act would deadlock the test until the response settles below.
    let duplicate: Promise<void> = Promise.resolve();
    act(() => {
      duplicate = view.placeChapter(chapterOne.id, volumeTwo.id);
    });

    expect(api.moveChapterToVolume).toHaveBeenCalledTimes(1);
    await act(async () => {
      command.resolve(placedDocument(chapterOne, volumeTwo.id, 2));
      await first;
      await duplicate;
    });
    const placed = view.project()?.documents.find((document) => document.id === chapterOne.id);
    expect(placed).toMatchObject({ volume_id: volumeTwo.id, position: 2 });
  });

  it("surfaces a capacity refusal inline with its envelope details and keeps the row", async () => {
    vi.mocked(api.moveChapterToVolume).mockRejectedValue(
      new Error("That volume is full: volume_chapters limit is 2000."),
    );
    const view = renderPlacement(project);

    await act(async () => {
      await view.placeChapter(chapterOne.id, volumeTwo.id);
    });

    expect(view.project()?.documents.find((document) => document.id === chapterOne.id)).toEqual(
      chapterOne,
    );
    expect(view.placementFor(chapterOne.id)).toEqual({
      isPlacing: false,
      error: "That volume is full: volume_chapters limit is 2000.",
      attemptedVolumeId: volumeTwo.id,
    });
    expect(view.placementFor(chapterTwo.id).error).toBeNull();
  });

  it("exposes the in-flight placement identity while the request runs", async () => {
    const command = deferred<StudioDocument>();
    vi.mocked(api.moveChapterToVolume).mockReturnValue(command.promise);
    const view = renderPlacement(project);

    let pending: Promise<void> | undefined;
    act(() => {
      pending = view.placeChapter(chapterOne.id, volumeTwo.id);
    });

    expect(view.placingDocument()).toEqual({ documentId: chapterOne.id, volumeId: volumeTwo.id });
    expect(view.placementFor(chapterOne.id)).toEqual({
      isPlacing: true,
      error: null,
      attemptedVolumeId: volumeTwo.id,
    });

    await act(async () => {
      command.resolve(placedDocument(chapterOne, volumeTwo.id, 2));
      await pending;
    });
    expect(view.placingDocument()).toBeNull();
  });

  it("sends no request for an unknown document", async () => {
    const view = renderPlacement(project);

    await act(async () => {
      await view.placeChapter("missing-document", volumeTwo.id);
    });

    expect(api.moveChapterToVolume).not.toHaveBeenCalled();
  });
});
