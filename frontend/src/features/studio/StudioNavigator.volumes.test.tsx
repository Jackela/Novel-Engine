import { fireEvent } from "@testing-library/dom";
import { act, type FormEvent } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { chapter, projectWith, volume } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import type { NavigatorVolumeCommands } from "./components/StudioNavigatorVolumeHeader";
import { StudioNavigator } from "./StudioNavigator";

const harness = createMountHarness();

afterEach(() => harness.cleanup());

const volumeOne = volume("volume-1", 1, { title: "Volume One" });
const volumeTwo = volume("volume-2", 2, { title: "Volume Two" });
const opening = chapter("doc-1", { title: "Opening", position: 1, volume_id: volumeOne.id });
const second = chapter("doc-2", { title: "Second", position: 2, volume_id: volumeTwo.id });
const project = projectWith([opening, second], { volumes: [volumeOne, volumeTwo] });
const singleVolumeProject = projectWith([opening], { volumes: [volumeOne] });

interface VolumeHarness {
  readonly container: HTMLElement;
  readonly setCommands: (next: NavigatorVolumeCommands) => void;
}

function renderNavigator(commands: NavigatorVolumeCommands, target = project): VolumeHarness {
  let current = commands;
  const content = () => (
    <StudioNavigator
      project={target}
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
      volumeCommands={current}
    />
  );
  const mounted = harness.mount(content());
  return {
    container: mounted.container,
    setCommands: (next) => {
      current = next;
      act(() => mounted.root.render(content()));
    },
  };
}

function idleVolumeCommands(
  overrides: Partial<NavigatorVolumeCommands> = {},
): NavigatorVolumeCommands {
  return {
    onAddVolume: vi.fn(),
    onRenameVolume: vi.fn(),
    onDeleteVolume: vi.fn(),
    onMoveVolume: vi.fn(),
    isCreatingVolume: false,
    createError: null,
    renamingVolume: null,
    renameErrorFor: () => null,
    deletingVolume: null,
    deleteErrorFor: () => null,
    movingVolume: null,
    moveErrorFor: () => null,
    ...overrides,
  };
}

function control(container: HTMLElement, label: string): HTMLElement {
  const element = container.querySelector<HTMLElement>(`[aria-label="${label}"]`);
  if (element === null) throw new Error(`Expected control: ${label}`);
  return element;
}

function click(element: HTMLElement): void {
  act(() => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

function pressEscape(element: HTMLElement): void {
  act(() => {
    element.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  });
}

describe("StudioNavigator volume creation", () => {
  it("creates a volume from the chapter group's inline form", () => {
    const commands = idleVolumeCommands();
    const view = renderNavigator(commands);

    click(control(view.container, "Add volume"));
    const field = control(view.container, "Volume title") as HTMLInputElement;
    expect(document.activeElement).toBe(field);

    act(() => {
      fireEvent.change(field, { target: { value: "  Act Two  " } });
    });
    click(control(view.container, "Create volume"));
    expect(commands.onAddVolume).toHaveBeenCalledTimes(1);
    expect(commands.onAddVolume).toHaveBeenCalledWith("Act Two");
  });

  it("surfaces the server's create refusal inside the open form and cancels back", () => {
    const commands = idleVolumeCommands({
      createError: "A volume with this title already exists.",
    });
    const view = renderNavigator(commands);

    click(control(view.container, "Add volume"));
    const alert = view.container.querySelector(".volume-group__form .volume-group__error");
    expect(alert?.getAttribute("role")).toBe("alert");
    expect(alert?.textContent).toBe("A volume with this title already exists.");

    click(control(view.container, "Cancel add volume"));
    expect(view.container.querySelector('input[aria-label="Volume title"]')).toBeNull();
    expect(document.activeElement).toBe(control(view.container, "Add volume"));
  });
});

describe("StudioNavigator volume rename", () => {
  it("renames from the volume header with the current title prefilled", () => {
    const commands = idleVolumeCommands();
    const view = renderNavigator(commands);

    click(control(view.container, "Rename Volume Two"));
    const field = control(view.container, "New title for Volume Two") as HTMLInputElement;
    expect(field.value).toBe("Volume Two");
    expect(document.activeElement).toBe(field);

    act(() => {
      fireEvent.change(field, { target: { value: "Act Two" } });
    });
    click(control(view.container, "Save name for Volume Two"));

    expect(commands.onRenameVolume).toHaveBeenCalledTimes(1);
    expect(commands.onRenameVolume).toHaveBeenCalledWith(volumeTwo.id, "Act Two");
  });

  it("cancels with Escape and returns focus to the rename trigger", () => {
    const commands = idleVolumeCommands();
    const view = renderNavigator(commands);

    click(control(view.container, "Rename Volume Two"));
    pressEscape(control(view.container, "New title for Volume Two"));

    expect(commands.onRenameVolume).not.toHaveBeenCalled();
    expect(view.container.querySelector('input[aria-label="New title for Volume Two"]')).toBeNull();
    expect(document.activeElement).toBe(control(view.container, "Rename Volume Two"));
  });

  it("surfaces the server's rename refusal inside the open form", () => {
    const view = renderNavigator(
      idleVolumeCommands({
        renameErrorFor: (volumeId) =>
          volumeId === volumeTwo.id ? "A volume with this title already exists." : null,
      }),
    );

    click(control(view.container, "Rename Volume Two"));
    const alert = view.container.querySelector(".volume-group__form .volume-group__error");
    expect(alert?.getAttribute("role")).toBe("alert");
    expect(alert?.textContent).toBe("A volume with this title already exists.");
  });
});

describe("StudioNavigator volume deletion", () => {
  it("warns that chapters merge before confirming and cancels back to the trigger", () => {
    const commands = idleVolumeCommands();
    const view = renderNavigator(commands);

    click(control(view.container, "Delete Volume One"));
    const strip = view.container.querySelector(".volume-group__confirm");
    expect(strip?.getAttribute("role")).toBe("group");
    expect(strip?.textContent).toContain("Delete Volume One?");
    expect(strip?.textContent).toContain("chapters move to the adjacent volume");
    expect(document.activeElement).toBe(control(view.container, "Confirm delete Volume One"));

    click(control(view.container, "Cancel delete Volume One"));
    expect(commands.onDeleteVolume).not.toHaveBeenCalled();
    expect(view.container.querySelector(".volume-group__confirm")).toBeNull();
    expect(document.activeElement).toBe(control(view.container, "Delete Volume One"));
  });

  it("cancels on Escape and leaves the volume untouched", () => {
    const commands = idleVolumeCommands();
    const view = renderNavigator(commands);

    click(control(view.container, "Delete Volume One"));
    const strip = view.container.querySelector(".volume-group__confirm");
    if (strip === null) throw new Error("Expected the confirmation strip.");
    act(() => {
      strip.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    });

    expect(commands.onDeleteVolume).not.toHaveBeenCalled();
    expect(view.container.querySelector(".volume-group__confirm")).toBeNull();
    expect(document.activeElement).toBe(control(view.container, "Delete Volume One"));
  });

  it("fires only from the confirmation and marks only it busy", () => {
    const commands = idleVolumeCommands();
    const view = renderNavigator(commands);
    click(control(view.container, "Delete Volume One"));
    click(control(view.container, "Confirm delete Volume One"));
    expect(commands.onDeleteVolume).toHaveBeenCalledWith(volumeOne.id);

    view.setCommands(
      idleVolumeCommands({
        deletingVolume: { volumeId: volumeOne.id },
        onDeleteVolume: commands.onDeleteVolume,
      }),
    );

    const confirm = control(view.container, "Deleting Volume One");
    expect(confirm).toHaveAttribute("aria-busy", "true");
    expect(confirm).toBeDisabled();
    expect(control(view.container, "Cancel delete Volume One")).toBeDisabled();
    expect(control(view.container, "Delete Volume Two")).toBeDisabled();
    expect(control(view.container, "Move Volume Two up")).toBeDisabled();
    expect(control(view.container, "Add volume")).toBeDisabled();
  });

  it("surfaces the server's refusal inside the open confirmation", () => {
    const refusal =
      "A project must keep at least one volume; create another before deleting this one.";
    const view = renderNavigator(
      idleVolumeCommands({
        deleteErrorFor: (volumeId) => (volumeId === volumeOne.id ? refusal : null),
      }),
    );

    click(control(view.container, "Delete Volume One"));
    const alert = view.container.querySelector(".volume-group__confirm .volume-group__error");
    expect(alert?.getAttribute("role")).toBe("alert");
    expect(alert?.textContent).toBe(refusal);
  });

  it("keeps a single-volume project on the server's last-volume contract", () => {
    const commands = idleVolumeCommands();
    const view = renderNavigator(commands, singleVolumeProject);

    expect(control(view.container, "Move Volume One up")).toBeDisabled();
    expect(control(view.container, "Move Volume One down")).toBeDisabled();
    // Deletion stays reachable: the server owns the last-volume refusal.
    click(control(view.container, "Delete Volume One"));
    expect(view.container.querySelector(".volume-group__confirm")).not.toBeNull();
  });
});

describe("StudioNavigator volume reorder", () => {
  it("moves volumes with up/down and disables the edges", () => {
    const commands = idleVolumeCommands();
    const view = renderNavigator(commands);

    expect(control(view.container, "Move Volume One up")).toBeDisabled();
    expect(control(view.container, "Move Volume One down")).not.toBeDisabled();
    expect(control(view.container, "Move Volume Two down")).toBeDisabled();

    click(control(view.container, "Move Volume Two up"));
    expect(commands.onMoveVolume).toHaveBeenCalledTimes(1);
    expect(commands.onMoveVolume).toHaveBeenCalledWith(volumeTwo.id, -1);
  });

  it("names the in-flight move and disables the shared mutation group", () => {
    const view = renderNavigator(
      idleVolumeCommands({ movingVolume: { volumeId: volumeTwo.id, direction: -1 } }),
    );

    const button = control(view.container, "Moving Volume Two up");
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(button).toBeDisabled();
    expect(control(view.container, "Delete Volume One")).toBeDisabled();
    expect(control(view.container, "Rename Volume One")).toBeDisabled();
  });

  it("surfaces a reorder refusal under the volume header", () => {
    const view = renderNavigator(
      idleVolumeCommands({
        moveErrorFor: (volumeId) =>
          volumeId === volumeTwo.id ? "Reorder must include every project volume once." : null,
      }),
    );

    const alert = view.container.querySelector(".volume-group__error");
    expect(alert?.getAttribute("role")).toBe("alert");
    expect(alert?.textContent).toBe("Reorder must include every project volume once.");
  });
});
