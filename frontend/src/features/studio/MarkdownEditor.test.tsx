import { EditorView } from "@codemirror/view";
import { fireEvent, getByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createMountHarness } from "@/test/harness";

import { MarkdownEditor } from "./MarkdownEditor";

/**
 * DR-016 regression: the editor wires the CodeMirror search keymap
 * (Ctrl+F / Ctrl+H) and markdown formatting commands over the current
 * selection (toolbar buttons plus Ctrl+B / Ctrl+I).
 */

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

interface MountedEditor {
  readonly container: HTMLDivElement;
  readonly view: EditorView;
  readonly onChange: ReturnType<typeof vi.fn>;
}

/** Mount the real lazy-loaded CodeMirror view and expose its state. */
async function mountEditor(value: string): Promise<MountedEditor> {
  const onChange = vi.fn();
  const { container } = harness.mount(<MarkdownEditor onChange={onChange} value={value} />);
  await vi.waitFor(() => {
    expect(container.querySelector(".cm-content")).toBeTruthy();
  });
  const content = container.querySelector(".cm-content");
  const view = content instanceof HTMLElement ? EditorView.findFromDOM(content) : null;
  if (!view) throw new Error("Expected the mounted CodeMirror view.");
  return { container, view, onChange };
}

function contentOf(container: HTMLElement): HTMLElement {
  const content = container.querySelector(".cm-content");
  if (!(content instanceof HTMLElement)) throw new Error("Expected the editor content.");
  return content;
}

/** Dispatch the cancelable synthetic keydown CodeMirror's keymap consumes. */
function pressKey(target: HTMLElement, key: string, init: KeyboardEventInit = {}): KeyboardEvent {
  const event = new KeyboardEvent("keydown", { bubbles: true, cancelable: true, key, ...init });
  target.dispatchEvent(event);
  return event;
}

describe("Markdown editor find/replace shortcuts", () => {
  it("opens the search panel on Ctrl+F", async () => {
    const { container } = await mountEditor("alpha beta");

    pressKey(contentOf(container), "f", { ctrlKey: true });

    expect(container.querySelector(".cm-search")).toBeTruthy();
  });

  it("opens the search panel with its replace field on Ctrl+H", async () => {
    const { container } = await mountEditor("alpha beta");

    pressKey(contentOf(container), "h", { ctrlKey: true });

    expect(container.querySelector('.cm-search input[name="replace"]')).toBeTruthy();
  });
});

describe("Markdown editor formatting commands", () => {
  it("wraps the current selection in bold from the toolbar", async () => {
    const { container, view, onChange } = await mountEditor("alpha beta");
    act(() => {
      view.dispatch({ selection: { anchor: 0, head: 5 } });
    });

    fireEvent.click(getByRole(container, "button", { name: "Bold" }));

    expect(view.state.doc.toString()).toBe("**alpha** beta");
    expect(onChange).toHaveBeenCalledWith("**alpha** beta");
  });

  it("wraps the current selection in italics and toggles the markers off again", async () => {
    const { container, view } = await mountEditor("alpha beta");
    act(() => {
      view.dispatch({ selection: { anchor: 6, head: 10 } });
    });

    fireEvent.click(getByRole(container, "button", { name: "Italic" }));
    expect(view.state.doc.toString()).toBe("alpha *beta*");

    fireEvent.click(getByRole(container, "button", { name: "Italic" }));
    expect(view.state.doc.toString()).toBe("alpha beta");
  });

  it("toggles a heading on the current line and keeps the caret inside it", async () => {
    const { container, view } = await mountEditor("alpha\nbeta");
    act(() => {
      view.dispatch({ selection: { anchor: 0 } });
    });

    fireEvent.click(getByRole(container, "button", { name: "Heading" }));
    expect(view.state.doc.toString()).toBe("# alpha\nbeta");
    expect(view.state.selection.main.head).toBe(2);

    fireEvent.click(getByRole(container, "button", { name: "Heading" }));
    expect(view.state.doc.toString()).toBe("alpha\nbeta");
  });

  it("applies bold and italic with Ctrl+B / Ctrl+I while the editor is focused", async () => {
    const { container, view } = await mountEditor("alpha beta");
    act(() => {
      view.dispatch({ selection: { anchor: 0, head: 5 } });
    });

    pressKey(contentOf(container), "b", { ctrlKey: true });
    expect(view.state.doc.toString()).toBe("**alpha** beta");

    act(() => {
      view.dispatch({ selection: { anchor: 10, head: 14 } });
    });
    pressKey(contentOf(container), "i", { ctrlKey: true });
    expect(view.state.doc.toString()).toBe("**alpha** *beta*");
  });
});
