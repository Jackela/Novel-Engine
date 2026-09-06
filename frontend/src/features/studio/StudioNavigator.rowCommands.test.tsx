import { act, type FormEvent } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { chapter, projectWith, volume } from "@/test/factories";
import { createMountHarness } from "@/test/harness";
import type { NavigatorRowCommands } from "./components/StudioNavigatorRowActions";

import { StudioNavigator } from "./StudioNavigator";

const harness = createMountHarness();

afterEach(() => harness.cleanup());

const volumeOne = volume("volume-1", 1, { title: "Volume One" });
const volumeTwo = volume("volume-2", 2, { title: "Volume Two" });
const opening = chapter("doc-1", { title: "Opening", position: 1 });
const second = chapter("doc-2", { title: "Second", position: 2 });
const project = projectWith([opening, second], { volumes: [volumeOne, volumeTwo] });

interface RowCommandsHarness {
  readonly container: HTMLElement;
  readonly setRowCommands: (next: NavigatorRowCommands) => void;
}

function renderNavigator(rowCommands: NavigatorRowCommands): RowCommandsHarness {
  let current = rowCommands;
  const content = () => (
    <StudioNavigator
      project={project}
      section="manuscript"
      activeId={opening.id}
      search=""
      isSearching={false}
      searchResults={[]}
      onSearchChange={() => undefined}
      onSearchSubmit={(event: FormEvent) => event.preventDefault()}
      onNavigateSection={() => undefined}
      onSelectDocument={() => undefined}
      onCreateDocument={() => undefined}
      onMoveDocument={() => undefined}
      rowCommands={current}
    />
  );
  const mounted = harness.mount(content());
  return {
    container: mounted.container,
    setRowCommands: (next) => {
      current = next;
      act(() => mounted.root.render(content()));
    },
  };
}

function idleRowCommands(overrides: Partial<NavigatorRowCommands> = {}): NavigatorRowCommands {
  return {
    onDeleteDocument: vi.fn(),
    onPlaceChapter: vi.fn(),
    deletingDocument: null,
    placingDocument: null,
    deletionErrorFor: () => null,
    placementErrorFor: () => null,
    ...overrides,
  };
}

function button(container: HTMLElement, label: string): HTMLButtonElement {
  const element = container.querySelector<HTMLButtonElement>(`button[aria-label="${label}"]`);
  if (element === null) throw new Error(`Expected button: ${label}`);
  return element;
}

function click(element: HTMLElement): void {
  act(() => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

describe("StudioNavigator delete surface", () => {
  it("opens an inline confirmation that names the document and its Draft loss", () => {
    const view = renderNavigator(idleRowCommands());
    click(button(view.container, "Delete Opening"));

    const strip = view.container.querySelector(".document-row__confirm");
    expect(strip).not.toBeNull();
    expect(strip?.textContent).toContain("Permanently delete Opening?");
    expect(strip?.textContent).toContain("Unsaved changes are lost");
    expect(button(view.container, "Confirm delete Opening")).toBeDefined();
    expect(button(view.container, "Cancel delete Opening")).toBeDefined();
    expect(document.activeElement).toBe(button(view.container, "Confirm delete Opening"));
  });

  it("keeps the document when cancelled and refocuses the delete trigger", () => {
    const commands = idleRowCommands();
    const view = renderNavigator(commands);
    click(button(view.container, "Delete Opening"));

    click(button(view.container, "Cancel delete Opening"));

    expect(commands.onDeleteDocument).not.toHaveBeenCalled();
    expect(view.container.querySelector(".document-row__confirm")).toBeNull();
    expect(document.activeElement).toBe(button(view.container, "Delete Opening"));
  });

  it("cancels on Escape and leaves the document untouched", () => {
    const commands = idleRowCommands();
    const view = renderNavigator(commands);
    click(button(view.container, "Delete Opening"));

    const strip = view.container.querySelector(".document-row__confirm");
    if (strip === null) throw new Error("Expected the confirmation strip.");
    act(() => {
      strip.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    });

    expect(commands.onDeleteDocument).not.toHaveBeenCalled();
    expect(view.container.querySelector(".document-row__confirm")).toBeNull();
    expect(document.activeElement).toBe(button(view.container, "Delete Opening"));
  });

  it("fires the command only from the confirmation and marks only it busy", () => {
    const commands = idleRowCommands();
    const view = renderNavigator(commands);
    click(button(view.container, "Delete Opening"));
    click(button(view.container, "Confirm delete Opening"));
    expect(commands.onDeleteDocument).toHaveBeenCalledWith(opening.id);

    // The command went in flight: the confirmation carries the busy naming
    // and the shared mutation conflict group disables without busy naming.
    view.setRowCommands(
      idleRowCommands({
        deletingDocument: { documentId: opening.id },
        onDeleteDocument: commands.onDeleteDocument,
      }),
    );

    const confirm = button(view.container, "Deleting Opening");
    expect(confirm).toBeDisabled();
    expect(confirm).toHaveAttribute("aria-busy", "true");
    expect(button(view.container, "Cancel delete Opening")).toBeDisabled();
    const otherDelete = button(view.container, "Delete Second");
    expect(otherDelete).toBeDisabled();
    expect(otherDelete).not.toHaveAttribute("aria-busy");
    expect(button(view.container, "Move Second up")).toBeDisabled();
    expect(button(view.container, "Add Manuscript")).toBeDisabled();
  });

  it("renders the row's inline deletion error inside the open confirmation", () => {
    const view = renderNavigator(
      idleRowCommands({
        deletionErrorFor: (id) => (id === opening.id ? "Referenced by a snapshot." : null),
      }),
    );
    click(button(view.container, "Delete Opening"));

    const alert = view.container.querySelector(".document-row__confirm .document-row__error");
    expect(alert?.getAttribute("role")).toBe("alert");
    expect(alert?.textContent).toBe("Referenced by a snapshot.");
  });
});

describe("StudioNavigator volume placement surface", () => {
  it("offers only other volumes and never the chapter's current one", () => {
    const view = renderNavigator(idleRowCommands());

    const select = view.container.querySelector<HTMLSelectElement>(
      'select[aria-label="Place Opening in volume"]',
    );
    if (select === null) throw new Error("Expected the placement select.");
    const options = Array.from(select.options).map((option) => option.value);
    expect(options).toEqual(["", volumeTwo.id]);
    expect(select.options[0]?.disabled).toBe(true);
    expect(select.value).toBe("");
  });

  it("issues the placement command once and returns to the neutral placeholder", () => {
    const commands = idleRowCommands();
    const view = renderNavigator(commands);
    const select = view.container.querySelector<HTMLSelectElement>(
      'select[aria-label="Place Opening in volume"]',
    );
    if (select === null) throw new Error("Expected the placement select.");

    act(() => {
      select.value = volumeTwo.id;
      select.dispatchEvent(new Event("change", { bubbles: true }));
    });

    expect(commands.onPlaceChapter).toHaveBeenCalledTimes(1);
    expect(commands.onPlaceChapter).toHaveBeenCalledWith(opening.id, volumeTwo.id);
    expect(select.value).toBe("");
  });

  it("names the in-flight placement with its attempted volume", () => {
    const view = renderNavigator(
      idleRowCommands({
        placingDocument: { documentId: opening.id, volumeId: volumeTwo.id },
      }),
    );

    const select = view.container.querySelector<HTMLSelectElement>(
      'select[aria-label="Placing Opening in Volume Two"]',
    );
    if (select === null) throw new Error("Expected the busy placement select.");
    expect(select).toBeDisabled();
    expect(select).toHaveAttribute("aria-busy", "true");
    // The shared mutation conflict group disables without busy naming.
    expect(button(view.container, "Delete Second")).toBeDisabled();
    expect(button(view.container, "Move Second up")).toBeDisabled();
  });

  it("renders the row's inline placement error as an alert", () => {
    const view = renderNavigator(
      idleRowCommands({
        placementErrorFor: (id) => (id === opening.id ? "That volume is full." : null),
      }),
    );

    const alert = view.container.querySelector(".document-row__error");
    expect(alert?.getAttribute("role")).toBe("alert");
    expect(alert?.textContent).toBe("That volume is full.");
  });

  it("renders no placement select outside the chapter group", () => {
    const view = renderNavigator(idleRowCommands());

    const characterGroup = view.container.querySelector(
      ".studio-nav__document-group:not(:has(.volume-group))",
    );
    expect(characterGroup?.querySelector("select")).toBeNull();
  });
});
