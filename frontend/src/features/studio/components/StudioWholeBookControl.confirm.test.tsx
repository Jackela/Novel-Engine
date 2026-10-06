import { fireEvent, getByRole, queryByRole, within } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createMountHarness } from "@/test/harness";
import type { WholeBookChapter } from "../hooks/wholeBookPlan";

import { StudioWholeBookControl } from "./StudioWholeBookControl";

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

const occupiedChapters: readonly WholeBookChapter[] = [
  { id: "hand", title: "Hand-Written Opening", requiresConfirmation: true },
  { id: "imported", title: "Imported Chapter", requiresConfirmation: true },
];

function renderConfirming(props: {
  readonly onStart?: () => void | Promise<void>;
  readonly onConfirmReplace?: () => void | Promise<void>;
  readonly remaining?: number;
  readonly safeCount?: number;
}) {
  return harness.mount(
    <StudioWholeBookControl
      occupiedChapters={occupiedChapters}
      onConfirmReplace={props.onConfirmReplace ?? vi.fn()}
      onStart={props.onStart ?? vi.fn()}
      onStop={vi.fn()}
      phase={{ kind: "idle" }}
      remaining={props.remaining ?? 3}
      safeCount={props.safeCount ?? 1}
    />,
  );
}

const startButton = (container: HTMLElement) =>
  getByRole(container, "button", { name: /Generate whole book/i });

/**
 * #DR-007 replacement confirmation: a run that would replace existing author
 * text starts only after the author picks an explicit scope, and the surface
 * names every chapter that scope would overwrite.
 */
describe("StudioWholeBookControl replacement confirmation", () => {
  it("shows the dry-run list instead of starting silently", () => {
    const onStart = vi.fn();
    const onConfirmReplace = vi.fn();
    const mounted = renderConfirming({ onConfirmReplace, onStart });

    act(() => startButton(mounted.container).click());

    expect(onStart).not.toHaveBeenCalled();
    expect(onConfirmReplace).not.toHaveBeenCalled();
    const dryRunList = getByRole(mounted.container, "list", {
      name: "Chapters that would be replaced",
    });
    expect(
      within(dryRunList)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(["Hand-Written Opening", "Imported Chapter"]);
    // The safe scope is offered first and holds focus.
    const emptyOnly = getByRole(mounted.container, "button", {
      name: "Generate the 1 empty chapter only",
    });
    expect(document.activeElement).toBe(emptyOnly);
    expect(
      getByRole(mounted.container, "button", { name: "Replace the 2 chapters with AI drafts" }),
    ).toBeVisible();
    expect(queryByRole(mounted.container, "button", { name: /Generate whole book/i })).toBeNull();
  });

  it("runs only the empty chapters when the author keeps the existing text", () => {
    const onStart = vi.fn();
    const onConfirmReplace = vi.fn();
    const mounted = renderConfirming({ onConfirmReplace, onStart });

    act(() => startButton(mounted.container).click());
    act(() =>
      getByRole(mounted.container, "button", { name: "Generate the 1 empty chapter only" }).click(),
    );

    expect(onStart).toHaveBeenCalledOnce();
    expect(onConfirmReplace).not.toHaveBeenCalled();
  });

  it("runs the replacement scope only after the explicit choice", () => {
    const onStart = vi.fn();
    const onConfirmReplace = vi.fn();
    const mounted = renderConfirming({ onConfirmReplace, onStart });

    act(() => startButton(mounted.container).click());
    act(() =>
      getByRole(mounted.container, "button", {
        name: "Replace the 2 chapters with AI drafts",
      }).click(),
    );

    expect(onConfirmReplace).toHaveBeenCalledOnce();
    expect(onStart).not.toHaveBeenCalled();
  });

  it("offers only the replacement and cancel when every chapter has text", () => {
    const onConfirmReplace = vi.fn();
    const mounted = renderConfirming({ onConfirmReplace, remaining: 2, safeCount: 0 });

    act(() => startButton(mounted.container).click());

    expect(
      queryByRole(mounted.container, "button", { name: /Generate the .* empty .* only/i }),
    ).toBeNull();
    const replace = getByRole(mounted.container, "button", {
      name: "Replace the 2 chapters with AI drafts",
    });
    expect(document.activeElement).toBe(replace);
  });

  it("cancels back to the start command without running anything", () => {
    const onStart = vi.fn();
    const onConfirmReplace = vi.fn();
    const mounted = renderConfirming({ onConfirmReplace, onStart });

    act(() => startButton(mounted.container).click());
    act(() => getByRole(mounted.container, "button", { name: "Cancel" }).click());

    expect(onStart).not.toHaveBeenCalled();
    expect(onConfirmReplace).not.toHaveBeenCalled();
    expect(queryByRole(mounted.container, "list")).toBeNull();
    expect(document.activeElement).toBe(startButton(mounted.container));
  });

  it("keeps Escape as a cancel while the confirmation is open", () => {
    const onStart = vi.fn();
    const onConfirmReplace = vi.fn();
    const mounted = renderConfirming({ onConfirmReplace, onStart });

    act(() => startButton(mounted.container).click());
    act(() => {
      fireEvent.keyDown(getByRole(mounted.container, "button", { name: "Cancel" }), {
        key: "Escape",
      });
    });

    expect(onStart).not.toHaveBeenCalled();
    expect(onConfirmReplace).not.toHaveBeenCalled();
    expect(startButton(mounted.container)).toBeVisible();
  });
});
