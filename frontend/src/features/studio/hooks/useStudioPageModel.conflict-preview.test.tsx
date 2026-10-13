import { act, type ComponentProps } from "react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { RevisionDetail } from "@/app/types/revision";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness, flushEffects } from "@/test/harness";
import type { StudioEditorPane } from "../StudioEditorPane";
import { resolveStudioRoute } from "../studioRouteState";
import { summarizeDocument } from "./projectState";
import { resetRevisionCacheForTests } from "./useRevisionCache";
import { useStudioPageModel } from "./useStudioPageModel";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      project: vi.fn<typeof actual.api.project>(),
      document: vi.fn<typeof actual.api.document>(),
      providers: vi.fn<typeof actual.api.providers>(),
      jobs: vi.fn<typeof actual.api.jobs>(),
      revisions: vi.fn<typeof actual.api.revisions>(),
      revision: vi.fn<typeof actual.api.revision>(),
      saveDocument: vi.fn<typeof actual.api.saveDocument>(),
    },
  };
});

const harness = createMountHarness();
const originalDocument = chapter("chapter-one", {
  content_markdown: "Original scene.",
  current_revision_id: "revision-1",
});
const latestDocument = {
  ...originalDocument,
  content_markdown: "Second tab wins.",
  current_revision_id: "revision-2",
};
const latestRevision: RevisionDetail = {
  id: "revision-2",
  document_id: originalDocument.id,
  parent_revision_id: "revision-1",
  revision_number: 2,
  content_markdown: "Second tab wins.",
  metadata: {},
  source: "author",
  word_count: 3,
  created_at: "2026-10-12T00:01:00Z",
};
let current: ReturnType<typeof useStudioPageModel> | undefined;

function StudioPageModelProbe(): null {
  current = useStudioPageModel(
    "project-1",
    resolveStudioRoute("project-1", "manuscript", ""),
    useNavigate(),
  );
  return null;
}

function editor(): ComponentProps<typeof StudioEditorPane> {
  const model = current?.viewProps?.editor;
  if (!model) throw new Error("Expected the mounted page model's editor surface.");
  return model;
}

async function settleUntil(description: string, ready: () => boolean): Promise<void> {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    if (ready()) return;
    await flushEffects();
  }
  throw new Error(`Timed out waiting for ${description}.`);
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.mocked(api.project).mockResolvedValue(projectWith([summarizeDocument(originalDocument)]));
  vi.mocked(api.document).mockResolvedValueOnce(originalDocument).mockResolvedValue(latestDocument);
  vi.mocked(api.providers).mockResolvedValue({ providers: [] });
  vi.mocked(api.jobs).mockResolvedValue({ jobs: [], next_cursor: null });
  vi.mocked(api.revisions).mockResolvedValue({ revisions: [], next_cursor: null });
  vi.mocked(api.revision).mockResolvedValue(latestRevision);
  vi.mocked(api.saveDocument).mockRejectedValue(new HttpError("revision conflict", 409));
});

afterEach(() => {
  harness.cleanup();
  resetRevisionCacheForTests();
  current = undefined;
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.resetAllMocks();
});

describe("Studio page conflict preview", () => {
  it("lets the editor view the server revision while preserving its conflicted local Draft", async () => {
    harness.mount(
      <MemoryRouter initialEntries={["/projects/project-1/manuscript"]}>
        <StudioPageModelProbe />
      </MemoryRouter>,
    );
    await settleUntil(
      "the bootstrap active Document",
      () => current?.viewProps?.editor.activeDocument?.id === "chapter-one",
    );

    act(() => editor().onDraftChange("Stale tab overwrite."));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });
    await settleUntil("the save conflict", () => editor().saveState === "conflict");
    expect(editor().draft).toBe("Stale tab overwrite.");

    // DR-012 is usable only when the route model supplies the editor's
    // read-only controller; the draft hook alone is not the page surface.
    const preview = editor().serverVersion;
    expect(preview).toBeDefined();
    if (!preview) throw new Error("Expected the editor's server revision preview.");
    const projectBefore = current?.project;
    const titleBefore = editor().titleDraft;
    await act(async () => {
      await preview.view();
    });

    expect(editor().serverVersion?.isOpen).toBe(true);
    expect(editor().serverVersion?.currentRevisionId).toBe("revision-2");
    expect(editor().serverVersion?.revision?.content_markdown).toBe("Second tab wins.");
    expect(editor().draft).toBe("Stale tab overwrite.");
    expect(editor().titleDraft).toBe(titleBefore);
    expect(editor().saveState).toBe("conflict");
    expect(current?.project).toBe(projectBefore);
    expect(api.saveDocument).toHaveBeenCalledTimes(1);
  });
});
