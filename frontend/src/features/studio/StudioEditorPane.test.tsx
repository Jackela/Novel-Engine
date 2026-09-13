import { fireEvent, getByRole, queryByRole } from "@testing-library/dom";
import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { chapter } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

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
  it("shows a named pending surface instead of an empty or stale Document", () => {
    const container = render(
      <StudioEditorPane
        activeDocument={null}
        draft=""
        titleDraft=""
        saveState="idle"
        isLoadingDocument
        onDraftChange={vi.fn()}
        onTitleChange={vi.fn()}
      />,
    );

    expect(getByRole(container, "status")).toHaveTextContent("Loading document");
    expect(container).not.toHaveTextContent("Create a document");
    expect(container.querySelector('textarea[aria-label="Markdown body"]')).toBeNull();
  });

  it("keeps a failed body local and exposes Retry without inventing editor content", () => {
    const retry = vi.fn();
    const container = render(
      <StudioEditorPane
        activeDocument={null}
        draft=""
        titleDraft=""
        saveState="idle"
        documentLoadError="Unable to load this document."
        onDraftChange={vi.fn()}
        onTitleChange={vi.fn()}
        onRetryDocument={retry}
      />,
    );

    expect(getByRole(container, "alert")).toHaveTextContent("Unable to load this document.");
    act(() => getByRole(container, "button", { name: "Retry document" }).click());
    expect(retry).toHaveBeenCalledTimes(1);
    expect(container.querySelector('textarea[aria-label="Markdown body"]')).toBeNull();
  });

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

  it("marks only Load latest busy and returns orphaned focus to the document title", async () => {
    const completion = deferred<void>();

    function ConflictHarness() {
      const [saveState, setSaveState] = useState<"conflict" | "idle">("conflict");
      const [isPending, setIsPending] = useState(false);
      return (
        <StudioEditorPane
          activeDocument={baseDocument}
          draft="# Local opening"
          titleDraft="Opening"
          saveState={saveState}
          isConflictActionPending={isPending}
          onDraftChange={vi.fn()}
          onTitleChange={vi.fn()}
          onLoadLatest={async () => {
            setIsPending(true);
            await completion.promise;
            setSaveState("idle");
            setIsPending(false);
          }}
          onRetryOverwrite={vi.fn()}
        />
      );
    }

    const container = render(<ConflictHarness />);
    const loadLatest = getByRole(container, "button", { name: "Load latest (discard local)" });
    const retryOverwrite = getByRole(container, "button", {
      name: "Keep local and retry overwrite",
    });
    loadLatest.focus();

    act(() => loadLatest.click());
    expect(loadLatest).toBeDisabled();
    expect(loadLatest).toHaveAttribute("aria-busy", "true");
    expect(retryOverwrite).toBeDisabled();
    expect(retryOverwrite).not.toHaveAttribute("aria-busy");

    await act(async () => {
      completion.resolve(undefined);
      await completion.promise;
    });

    expect(queryByRole(container, "button", { name: "Load latest (discard local)" })).toBeNull();
    expect(document.activeElement).toBe(
      container.querySelector('input[aria-label="Document title"]'),
    );
  });

  it("marks only Retry overwrite busy while both conflict commands are locked", async () => {
    const completion = deferred<void>();
    const container = render(
      <StudioEditorPane
        activeDocument={baseDocument}
        draft="# Local opening"
        titleDraft="Opening"
        saveState="conflict"
        onDraftChange={vi.fn()}
        onTitleChange={vi.fn()}
        onLoadLatest={vi.fn()}
        onRetryOverwrite={() => completion.promise}
      />,
    );
    const loadLatest = getByRole(container, "button", { name: "Load latest (discard local)" });
    const retryOverwrite = getByRole(container, "button", {
      name: "Keep local and retry overwrite",
    });

    act(() => retryOverwrite.click());
    expect(retryOverwrite).toBeDisabled();
    expect(retryOverwrite).toHaveAttribute("aria-busy", "true");
    expect(loadLatest).toBeDisabled();
    expect(loadLatest).not.toHaveAttribute("aria-busy");

    await act(async () => {
      completion.resolve(undefined);
      await completion.promise;
    });
  });

  it("does not override focus the author moved during conflict recovery", async () => {
    const completion = deferred<void>();
    const container = render(
      <StudioEditorPane
        activeDocument={baseDocument}
        draft="# Local opening"
        titleDraft="Opening"
        saveState="conflict"
        onDraftChange={vi.fn()}
        onTitleChange={vi.fn()}
        onLoadLatest={() => completion.promise}
        onRetryOverwrite={vi.fn()}
      />,
    );
    const loadLatest = getByRole(container, "button", { name: "Load latest (discard local)" });
    const otherButton = document.createElement("button");
    document.body.appendChild(otherButton);
    loadLatest.focus();

    act(() => loadLatest.click());
    otherButton.focus();
    await act(async () => {
      completion.resolve(undefined);
      await completion.promise;
    });

    expect(document.activeElement).toBe(otherButton);
    otherButton.remove();
  });
});
