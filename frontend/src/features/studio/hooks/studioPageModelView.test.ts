import { describe, expect, it, vi } from "vitest";

import { chapter, project as projectFixture } from "@/test/factories";
import { deferred } from "@/test/harness";

import { buildLoreStatusModel, buildStudioNavigatorProps } from "./studioPageModelView";

const project = projectFixture({ title: "Novel" });

describe("buildStudioNavigatorProps", () => {
  it("keeps navigation state local and adapts actions to the view interface", () => {
    const navigate = vi.fn();
    const createDocument = vi.fn();
    const moveDocument = vi.fn();
    const props = buildStudioNavigatorProps(
      {
        project,
        section: "outline",
        activeId: null,
        search: "chapter",
        isSearching: false,
        searchResults: [],
        onSearchChange: vi.fn(),
        onSearchSubmit: vi.fn(),
        onSelectDocument: vi.fn(),
        createDocument,
        moveDocument,
        isCreatingDocument: true,
        isMovingDocument: false,
      },
      navigate,
    );

    props.onNavigateSection("review");
    props.onCreateDocument("chapter");
    props.onMoveDocument("document-1", -1);

    expect(navigate).toHaveBeenCalledWith("/projects/project-1/review");
    expect(createDocument).toHaveBeenCalledWith("chapter");
    expect(moveDocument).toHaveBeenCalledWith("document-1", -1);
    expect(props.isCreatingDocument).toBe(true);
    expect(props.section).toBe("outline");
  });
});

describe("buildLoreStatusModel", () => {
  it("returns the mutation owner's exact Promise for the active Lore document", async () => {
    const save = deferred<void>();
    const changeLoreStatus = vi.fn(() => save.promise);
    const character = chapter("character-1", {
      kind: "character",
      lore_status: "draft",
    });

    const model = buildLoreStatusModel(character, changeLoreStatus);
    const submitted = model?.submit("stable");

    expect(changeLoreStatus).toHaveBeenCalledWith(character.id, "stable");
    expect(submitted).toBe(save.promise);

    save.resolve();
    await submitted;
  });

  it("does not expose the Lore editor for a non-Lore document", () => {
    const note = chapter("note-1", { kind: "note", lore_status: null });

    expect(buildLoreStatusModel(note, vi.fn())).toBeNull();
  });
});
