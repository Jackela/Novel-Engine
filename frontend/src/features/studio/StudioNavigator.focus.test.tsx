import { act, type FormEvent } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { DocumentKind } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { StudioNavigator } from "./StudioNavigator";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

const opening = chapter("doc-1", { title: "Opening", position: 1 });
const second = chapter("doc-2", { title: "Second", position: 2 });
const project = projectWith([opening, second]);

interface PendingState {
  readonly creating: boolean;
  readonly moving: boolean;
  readonly creatingDocumentKind?: DocumentKind | null;
  readonly movingDocument?: { documentId: string; direction: -1 | 1 } | null;
}

function renderNavigator(
  onCreateDocument: (kind: DocumentKind) => void | Promise<void>,
  onMoveDocument: (documentId: string, direction: -1 | 1) => void | Promise<void>,
) {
  let pending: PendingState = { creating: false, moving: false };
  let currentProject = project;
  const content = () => (
    <StudioNavigator
      project={currentProject}
      section="manuscript"
      activeId="doc-1"
      search=""
      isSearching={false}
      searchResults={[]}
      onSearchChange={() => undefined}
      onSearchSubmit={(event: FormEvent) => event.preventDefault()}
      onNavigateSection={() => undefined}
      onSelectDocument={() => undefined}
      onCreateDocument={onCreateDocument}
      onMoveDocument={onMoveDocument}
      isCreatingDocument={pending.creating}
      isMovingDocument={pending.moving}
      creatingDocumentKind={pending.creatingDocumentKind}
      movingDocument={pending.movingDocument}
    />
  );
  const { container, root } = harness.mount(content());
  return {
    container,
    rerender: (next: PendingState, nextProject = currentProject) => {
      pending = next;
      currentProject = nextProject;
      act(() => root.render(content()));
    },
  };
}

function button(container: HTMLElement, label: string): HTMLButtonElement {
  const element = container.querySelector<HTMLButtonElement>(`button[aria-label="${label}"]`);
  if (element === null) throw new Error(`Expected button: ${label}`);
  return element;
}

describe("StudioNavigator command focus", () => {
  it("keeps the search field focused and blocks repeat submits while searching", () => {
    let isSearching = false;
    const onSearchSubmit = vi.fn((event: FormEvent) => event.preventDefault());
    const content = () => (
      <StudioNavigator
        project={project}
        section="manuscript"
        activeId="doc-1"
        search="harbor"
        isSearching={isSearching}
        searchResults={[]}
        onSearchChange={() => undefined}
        onSearchSubmit={onSearchSubmit}
        onNavigateSection={() => undefined}
        onSelectDocument={() => undefined}
        onCreateDocument={() => undefined}
        onMoveDocument={() => undefined}
      />
    );
    const mounted = harness.mount(content());
    const input = mounted.container.querySelector<HTMLInputElement>(
      'input[aria-label="Search project"]',
    );
    const form = mounted.container.querySelector<HTMLFormElement>("form.studio-nav__search");
    if (input === null || form === null) throw new Error("Expected the project search form.");

    input.focus();
    isSearching = true;
    act(() => mounted.root.render(content()));

    expect(input).not.toBeDisabled();
    expect(input.readOnly).toBe(true);
    expect(input).toHaveAttribute("aria-busy", "true");
    expect(document.activeElement).toBe(input);
    act(() => {
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
    expect(onSearchSubmit).not.toHaveBeenCalled();
  });

  it("restores focus to the exact Add button after its async create settles and unlocks", async () => {
    const command = deferred<void>();
    const onCreate = vi.fn(() => command.promise);
    const navigator = renderNavigator(onCreate, vi.fn());
    const trigger = button(navigator.container, "Add Characters");
    const fallback = navigator.container.querySelector<HTMLInputElement>("input");
    if (fallback === null) throw new Error("Expected search input.");

    trigger.focus();
    act(() => trigger.click());
    navigator.rerender({ creating: true, moving: false, creatingDocumentKind: "character" });
    fallback.focus();
    await act(async () => {
      command.resolve(undefined);
      await command.promise;
    });
    expect(document.activeElement).toBe(fallback);

    navigator.rerender({ creating: false, moving: false });
    expect(onCreate).toHaveBeenCalledWith("character");
    expect(document.activeElement).toBe(fallback);
  });

  it.each([
    ["up", "Move Second up", "doc-2", -1],
    ["down", "Move Opening down", "doc-1", 1],
  ] as const)(
    "restores focus to the exact Move %s button after reordering settles and unlocks",
    async (_label, accessibleName, documentId, direction) => {
      const command = deferred<void>();
      const onMove = vi.fn(() => command.promise);
      const navigator = renderNavigator(vi.fn(), onMove);
      const trigger = button(navigator.container, accessibleName);
      const fallback = navigator.container.querySelector<HTMLInputElement>("input");
      if (fallback === null) throw new Error("Expected search input.");

      trigger.focus();
      act(() => trigger.click());
      navigator.rerender({
        creating: false,
        moving: true,
        movingDocument: { documentId, direction },
      });
      fallback.focus();
      await act(async () => {
        command.resolve(undefined);
        await command.promise;
      });
      expect(document.activeElement).toBe(fallback);

      navigator.rerender({ creating: false, moving: false });
      expect(onMove).toHaveBeenCalledWith(documentId, direction);
      expect(document.activeElement).toBe(fallback);
    },
  );

  it("moves orphaned boundary focus to the opposite command after a real reorder", async () => {
    const command = deferred<void>();
    const onMove = vi.fn(() => command.promise);
    const navigator = renderNavigator(vi.fn(), onMove);
    const trigger = button(navigator.container, "Move Opening down");

    trigger.focus();
    act(() => trigger.click());
    navigator.rerender({
      creating: false,
      moving: true,
      movingDocument: { documentId: opening.id, direction: 1 },
    });
    await act(async () => {
      command.resolve(undefined);
      await command.promise;
    });
    navigator.rerender(
      { creating: false, moving: false },
      projectWith([
        { ...second, position: 1 },
        { ...opening, position: 2 },
      ]),
    );

    const opposite = button(navigator.container, "Move Opening up");
    expect(trigger).toBeDisabled();
    expect(opposite).toBeEnabled();
    expect(document.activeElement).toBe(opposite);
  });
});
