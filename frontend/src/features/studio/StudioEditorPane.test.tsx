import { fireEvent } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { chapter } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { StudioEditorPane } from "./StudioEditorPane";

vi.mock("./MarkdownEditor", () => ({
  MarkdownEditor: ({ value, onChange }: { value: string; onChange: (value: string) => void }) => (
    <textarea
      aria-label="Markdown body"
      onChange={(event) => onChange(event.target.value)}
      value={value}
    />
  ),
}));

const harness = createMountHarness();

function render(element: Parameters<typeof harness.mount>[0]): HTMLDivElement {
  return harness.mount(element).container;
}

afterEach(() => {
  harness.cleanup();
});

const baseDocument = chapter("doc-1", {
  title: "Opening",
  position: 1,
  current_revision_id: "revision-abcdefghi",
  content_markdown: "# Opening",
  revision_source: "author",
  word_count: 42,
});

describe("Studio editor pane", () => {
  it("renders editor state and forwards title/body edits", async () => {
    const onTitleChange = vi.fn();
    const onDraftChange = vi.fn();
    const container = render(
      <StudioEditorPane
        activeDocument={baseDocument}
        draft="# Opening"
        titleDraft="Opening"
        saveState="saving"
        onDraftChange={onDraftChange}
        onTitleChange={onTitleChange}
      />,
    );

    await act(async () => {
      await Promise.resolve();
    });

    const title = container.querySelector('input[aria-label="Document title"]');
    const body = container.querySelector('textarea[aria-label="Markdown body"]');
    expect(container.textContent).toContain("42 words");
    expect(container.textContent).toContain("saving");

    act(() => {
      if (title instanceof HTMLInputElement) {
        fireEvent.input(title, { target: { value: "New Opening" } });
      }
      if (body instanceof HTMLTextAreaElement) {
        fireEvent.input(body, { target: { value: "# New Opening" } });
      }
    });

    expect(onTitleChange).toHaveBeenCalledWith("New Opening");
    expect(onDraftChange).toHaveBeenCalledWith("# New Opening");
  });

  it("renders a successful save status without the failure label", () => {
    const container = render(
      <StudioEditorPane
        activeDocument={baseDocument}
        draft="# Opening"
        titleDraft="Opening"
        saveState="saved"
        onDraftChange={vi.fn()}
        onTitleChange={vi.fn()}
      />,
    );

    const saveStatus = container.querySelector(".editor__save-state");
    expect(saveStatus?.textContent).toContain("Saved");
    expect(saveStatus?.textContent).not.toContain("Save failed");
  });
});
