import { getAllByRole, getByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { RevisionDetail } from "@/app/types/revision";
import { revision } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { diffHistoryLines } from "../historyLineDiff";
import { StudioHistoryPanel } from "./StudioHistoryPanel";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: { ...actual.api, revision: vi.fn<typeof actual.api.revision>() },
  };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

const revisions = [
  revision("revision-old", { revision_number: 1, word_count: 3 }),
  revision("revision-current", {
    parent_revision_id: "revision-old",
    revision_number: 2,
    word_count: 4,
  }),
];

const ancestor: RevisionDetail = {
  id: "revision-old",
  document_id: "document-1",
  parent_revision_id: null,
  revision_number: 1,
  content_markdown: "line one\nline two\nline three",
  metadata: {},
  source: "author",
  word_count: 3,
  created_at: "2026-08-27T00:00:00Z",
};

const currentContent = "line one\nline two changed\nline three\nline four";

function renderHistory(onRestoreRevision = vi.fn()) {
  return {
    onRestoreRevision,
    container: harness.mount(
      <StudioHistoryPanel
        revisions={revisions}
        loadedRevisionId="revision-current"
        onRestoreRevision={onRestoreRevision}
        previewScope={{ projectId: "project-1", documentId: "document-1", currentContent }}
      />,
    ).container,
  };
}

function openFirstPreview(container: HTMLDivElement): void {
  act(() => getAllByRole(container, "button", { name: "Preview" })[0]?.click());
}

describe("StudioHistoryPanel revision preview (DR-011)", () => {
  it("lazy-loads one revision body on first expand and caches it across toggles", async () => {
    const load = deferred<RevisionDetail>();
    vi.mocked(api.revision).mockReturnValue(load.promise);
    const { container } = renderHistory();
    expect(api.revision).not.toHaveBeenCalled();

    openFirstPreview(container);
    expect(api.revision).toHaveBeenCalledTimes(1);
    expect(api.revision).toHaveBeenCalledWith("project-1", "document-1", "revision-old");
    expect(getByRole(container, "status")).toHaveTextContent("Loading revision…");

    await act(async () => {
      load.resolve(ancestor);
      await load.promise;
    });
    expect(container).toHaveTextContent("Revision 1 preview");
    expect(container).toHaveTextContent("line two");

    act(() => getByRole(container, "button", { name: "Hide preview" }).click());
    expect(container).not.toHaveTextContent("Revision 1 preview");

    openFirstPreview(container);
    expect(api.revision).toHaveBeenCalledTimes(1);
    expect(container).toHaveTextContent("Revision 1 preview");
  });

  it("highlights added and removed lines against the current revision", async () => {
    vi.mocked(api.revision).mockResolvedValue(ancestor);
    const { container } = renderHistory();
    openFirstPreview(container);
    await act(async () => {
      await Promise.resolve();
    });

    const removed = Array.from(container.querySelectorAll(".history-diff__line--removed"));
    const added = Array.from(container.querySelectorAll(".history-diff__line--added"));
    expect(removed.map((node) => node.textContent)).toEqual(["-line two"]);
    expect(added.map((node) => node.textContent)).toEqual(["+line two changed", "+line four"]);
  });

  it("keeps preview read-only: expanding a revision never restores it", async () => {
    vi.mocked(api.revision).mockResolvedValue(ancestor);
    const { container, onRestoreRevision } = renderHistory();
    openFirstPreview(container);
    await act(async () => {
      await Promise.resolve();
    });

    expect(container).toHaveTextContent("Revision 1 preview");
    expect(onRestoreRevision).not.toHaveBeenCalled();
  });

  it("surfaces a retryable preview failure without touching restore", async () => {
    vi.mocked(api.revision)
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(ancestor);
    const { container, onRestoreRevision } = renderHistory();
    openFirstPreview(container);
    await act(async () => {
      await Promise.resolve();
    });

    expect(getByRole(container, "alert")).toHaveTextContent("Unable to load this revision.");
    act(() => getByRole(container, "button", { name: "Retry preview" }).click());
    await act(async () => {
      await Promise.resolve();
    });
    expect(container).toHaveTextContent("Revision 1 preview");
    expect(onRestoreRevision).not.toHaveBeenCalled();
  });
});

describe("historyLineDiff", () => {
  it("marks removed, added, and context lines deterministically", () => {
    const previous = "line one\nline two\nline three";
    const next = "line one\nline two changed\nline three\nline four";
    const expected = [
      { kind: "context", text: "line one" },
      { kind: "removed", text: "line two" },
      { kind: "added", text: "line two changed" },
      { kind: "context", text: "line three" },
      { kind: "added", text: "line four" },
    ] as const;

    expect(diffHistoryLines(previous, next)).toEqual(expected);
    expect(diffHistoryLines(previous, next)).toEqual(diffHistoryLines(previous, next));
  });
});
