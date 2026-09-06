import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { DocumentSummary, Project } from "@/app/types/studio";
import { chapter, projectWith, volume } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { useStudioDocumentActions } from "./useStudioDocumentActions";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      reorderDocuments: vi.fn<typeof actual.api.reorderDocuments>(),
    },
  };
});

const volumeOne = volume("volume-1", 1);
const volumeTwo = volume("volume-2", 2);
const volumeOneChapterOne = chapter("v1-c1", { title: "V1C1", position: 1 });
const volumeOneChapterTwo = chapter("v1-c2", { title: "V1C2", position: 2 });
const volumeTwoChapterOne = chapter("v2-c1", {
  title: "V2C1",
  position: 1,
  volume_id: "volume-2",
});
const volumeTwoChapterTwo = chapter("v2-c2", {
  title: "V2C2",
  position: 2,
  volume_id: "volume-2",
});
const characterOne = chapter("character-1", {
  kind: "character",
  title: "Mara",
  position: 1,
  volume_id: null,
});
// Non-chapter positions are one dense flat sequence in reading order
// (character before note), mirroring the server's projection.
const noteOne = chapter("note-1", {
  kind: "note",
  title: "Note One",
  position: 2,
  volume_id: null,
});
const noteTwo = chapter("note-2", {
  kind: "note",
  title: "Note Two",
  position: 3,
  volume_id: null,
});
// Server reading order (compareReadingOrder): chapters by volume and
// in-volume position first, then non-chapter kinds alphabetically.
const mixedProject = projectWith(
  [
    volumeOneChapterOne,
    volumeOneChapterTwo,
    volumeTwoChapterOne,
    volumeTwoChapterTwo,
    characterOne,
    noteOne,
    noteTwo,
  ],
  { volumes: [volumeOne, volumeTwo] },
);
const pureChapterProject = projectWith(
  [
    chapter("c1", { title: "C1", position: 1 }),
    chapter("c2", { title: "C2", position: 2 }),
    chapter("c3", { title: "C3", position: 3 }),
  ],
  { volumes: [volumeOne] },
);
const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

/** Payload assertions only care about the submitted ids; the merge has its own test. */
function stubReorderResponse(): void {
  vi.mocked(api.reorderDocuments).mockResolvedValue({ documents: [] });
}

interface DocumentActionsHarness {
  readonly move: (documentId: string, direction: -1 | 1) => Promise<void>;
  readonly project: () => Project | null;
  readonly error: () => string | null;
}

function renderDocumentActions(initialProject: Project): DocumentActionsHarness {
  let current: DocumentActionsHarness | undefined;

  function Probe(): null {
    const [project, setProject] = useState<Project | null>(initialProject);
    const [error, setError] = useState<string | null>(null);
    const owner = { projectId: initialProject.id };
    const actions = useStudioDocumentActions({
      project,
      projectId: initialProject.id,
      setProject,
      setActiveId: vi.fn(),
      currentOwner: () => owner,
      isCurrentOwner: () => true,
      publishError: (_owner, _source, value) => setError(value),
    });
    current = {
      move: actions.moveDocument,
      project: () => project,
      error: () => error,
    };
    return null;
  }

  harness.mount(<Probe />);
  const snapshot = (): DocumentActionsHarness => {
    if (current === undefined) throw new Error("Expected document actions after render.");
    return current;
  };
  return {
    move: (documentId, direction) => snapshot().move(documentId, direction),
    project: () => snapshot().project(),
    error: () => snapshot().error(),
  };
}

function submittedDocumentIds(): string[] {
  const calls = vi.mocked(api.reorderDocuments).mock.calls;
  const latest = calls.at(-1);
  if (latest === undefined) {
    throw new Error("Expected a reorder request, but none was submitted.");
  }
  return latest[1];
}

/**
 * Mirror of the server's whole-set projection (volume_projection): chapters
 * renumber per volume in submission order, non-chapters keep one flat order.
 * A move only persists when the moving document's projected position moves.
 */
function projectedPositions(documentIds: readonly string[], project: Project): Map<string, number> {
  const byId = new Map(project.documents.map((document) => [document.id, document]));
  const projected = new Map<string, number>();
  const nextInVolume = new Map<string, number>();
  let nextFlat = 0;
  for (const id of documentIds) {
    const document = byId.get(id);
    if (document === undefined) {
      throw new Error(`Submitted unknown document id: ${id}`);
    }
    if (document.kind === "chapter") {
      const volumeId = document.volume_id ?? project.volumes[0]?.id ?? "";
      const position = (nextInVolume.get(volumeId) ?? 0) + 1;
      nextInVolume.set(volumeId, position);
      projected.set(id, position);
    } else {
      nextFlat += 1;
      projected.set(id, nextFlat);
    }
  }
  return projected;
}

describe("useStudioDocumentActions moveDocument reading-group neighbors", () => {
  it("moves a chapter up against the previous chapter of the same volume in a mixed-kind project", async () => {
    stubReorderResponse();
    const view = renderDocumentActions(mixedProject);

    await act(async () => {
      await view.move(volumeOneChapterTwo.id, -1);
    });

    expect(api.reorderDocuments).toHaveBeenCalledTimes(1);
    expect(submittedDocumentIds()).toEqual([
      volumeOneChapterTwo.id,
      volumeOneChapterOne.id,
      volumeTwoChapterOne.id,
      volumeTwoChapterTwo.id,
      characterOne.id,
      noteOne.id,
      noteTwo.id,
    ]);
    const projected = projectedPositions(submittedDocumentIds(), mixedProject);
    expect(projected.get(volumeOneChapterTwo.id)).toBe(1);
    expect(projected.get(volumeOneChapterOne.id)).toBe(2);
  });

  it("moves a note up against the previous note without touching chapters in a mixed-kind project", async () => {
    stubReorderResponse();
    const view = renderDocumentActions(mixedProject);

    await act(async () => {
      await view.move(noteTwo.id, -1);
    });

    expect(api.reorderDocuments).toHaveBeenCalledTimes(1);
    expect(submittedDocumentIds()).toEqual([
      volumeOneChapterOne.id,
      volumeOneChapterTwo.id,
      volumeTwoChapterOne.id,
      volumeTwoChapterTwo.id,
      characterOne.id,
      noteTwo.id,
      noteOne.id,
    ]);
    const projected = projectedPositions(submittedDocumentIds(), mixedProject);
    // The character keeps flat position 1; the notes swap behind it.
    expect(projected.get(noteTwo.id)).toBe(2);
    expect(projected.get(noteOne.id)).toBe(3);
    expect(projected.get(characterOne.id)).toBe(1);
    expect(projected.get(volumeOneChapterOne.id)).toBe(1);
  });

  it("moves a chapter down inside its own volume rather than into the next volume", async () => {
    stubReorderResponse();
    const view = renderDocumentActions(mixedProject);

    await act(async () => {
      await view.move(volumeTwoChapterOne.id, 1);
    });

    expect(api.reorderDocuments).toHaveBeenCalledTimes(1);
    const projected = projectedPositions(submittedDocumentIds(), mixedProject);
    expect(projected.get(volumeTwoChapterOne.id)).toBe(2);
    expect(projected.get(volumeTwoChapterTwo.id)).toBe(1);
  });

  it("sends no reorder when the document sits at the edge of its reading group", async () => {
    stubReorderResponse();
    const view = renderDocumentActions(mixedProject);

    await act(async () => {
      // Last chapter of volume one: the flat-position neighbor belongs to
      // volume two, which is not a move inside the displayed group.
      await view.move(volumeOneChapterTwo.id, 1);
    });

    expect(api.reorderDocuments).not.toHaveBeenCalled();
    expect(view.error()).toBeNull();
  });

  it("keeps swapping flat-position neighbors inside one single-volume chapter list", async () => {
    stubReorderResponse();
    const view = renderDocumentActions(pureChapterProject);

    await act(async () => {
      await view.move("c2", -1);
    });

    expect(api.reorderDocuments).toHaveBeenCalledTimes(1);
    expect(submittedDocumentIds()).toEqual(["c2", "c1", "c3"]);
    const projected = projectedPositions(submittedDocumentIds(), pureChapterProject);
    expect(projected.get("c2")).toBe(1);
    expect(projected.get("c1")).toBe(2);
  });

  it("leaves documents unchanged when the moved id is unknown", async () => {
    stubReorderResponse();
    const view = renderDocumentActions(mixedProject);

    await act(async () => {
      await view.move("missing-document", -1);
    });

    expect(api.reorderDocuments).not.toHaveBeenCalled();
    expect(view.project()?.documents).toEqual(mixedProject.documents);
  });

  it("merges the server ordering after a group move", async () => {
    const reordered: DocumentSummary[] = [
      { ...volumeOneChapterTwo, position: 1 },
      { ...volumeOneChapterOne, position: 2 },
      volumeTwoChapterOne,
      volumeTwoChapterTwo,
      characterOne,
      noteOne,
      noteTwo,
    ];
    vi.mocked(api.reorderDocuments).mockResolvedValue({ documents: reordered });
    const view = renderDocumentActions(mixedProject);

    await act(async () => {
      await view.move(volumeOneChapterTwo.id, -1);
    });

    expect(view.project()?.documents).toEqual(reordered);
    expect(view.error()).toBeNull();
  });
});
