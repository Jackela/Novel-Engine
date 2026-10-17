import { act } from "react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { api, HttpError } from "@/app/api";
import type { StudioDocument } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness, flushEffects } from "@/test/harness";
import { resolveStudioRoute } from "../studioRouteState";
import { summarizeDocument } from "./projectState";
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
      saveDocument: vi.fn<typeof actual.api.saveDocument>(),
    },
  };
});
const harness = createMountHarness();
afterEach(() => {
  harness.cleanup();
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.resetAllMocks();
});

async function mountModel(documents: StudioDocument[]) {
  const project = projectWith(documents.map(summarizeDocument));
  vi.mocked(api.project).mockResolvedValue(project);
  vi.mocked(api.document).mockImplementation(async (_projectId, id) => {
    const document = documents.find((candidate) => candidate.id === id);
    if (!document) throw new Error("Unexpected document read.");
    return document;
  });
  vi.mocked(api.providers).mockResolvedValue({ providers: [] });
  vi.mocked(api.jobs).mockResolvedValue({ jobs: [], next_cursor: null });
  vi.mocked(api.revisions).mockResolvedValue({ revisions: [], next_cursor: null });
  let current: ReturnType<typeof useStudioPageModel> | undefined;
  function Probe() {
    current = useStudioPageModel(
      project.id,
      resolveStudioRoute(
        project.id,
        documents[0]?.kind === "chapter" ? "manuscript" : "characters",
        "",
      ),
      useNavigate(),
    );
    return null;
  }
  harness.mount(
    <MemoryRouter>
      <Probe />
    </MemoryRouter>,
  );
  await flushEffects();
  return () => {
    if (!current?.viewProps) throw new Error("Expected loaded Studio.");
    return current.viewProps;
  };
}

it("retains the notice through a refused save and removes it after an accepted retry", async () => {
  vi.useFakeTimers();
  const original = chapter("chapter-1", { content_markdown: "Saved text." });
  const view = await mountModel([original]);
  expect(view().inspector.model.hasUnsavedChapter).toBe(false);
  vi.mocked(api.saveDocument).mockRejectedValueOnce(new HttpError("Refused", 422));
  act(() => view().editor.onDraftChange("Pending corrected text."));
  expect(view().inspector.model.hasUnsavedChapter).toBe(true);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1500);
  });
  await flushEffects();
  expect(view().editor.saveState).toBe("error");
  expect(view().inspector.model.hasUnsavedChapter).toBe(true);
  const accepted = {
    ...original,
    current_revision_id: "accepted-retry",
    content_markdown: "Pending corrected text.",
  };
  vi.mocked(api.document).mockResolvedValue(accepted);
  vi.mocked(api.saveDocument).mockResolvedValue(accepted);
  act(() => view().editor.onRetrySave?.());
  await flushEffects();
  expect(api.saveDocument).toHaveBeenCalledTimes(2);
  expect(view().editor.draft).toBe(accepted.content_markdown);
  expect(view().inspector.model.hasUnsavedChapter).toBe(false);
});

it("tracks actual title changes and resets the notice to the newly selected chapter", async () => {
  vi.useFakeTimers();
  const original = chapter("chapter-1", { title: "Saved title" });
  const other = chapter("chapter-2", { title: "Other saved chapter", position: 1 });
  const view = await mountModel([original, other]);
  act(() => view().editor.onTitleChange("Unfinished title"));
  expect(view().inspector.model.hasUnsavedChapter).toBe(true);
  act(() => view().editor.onTitleChange(original.title));
  expect(view().inspector.model.hasUnsavedChapter).toBe(false);
  act(() => view().editor.onDraftChange("Unsaved departing chapter"));
  expect(view().inspector.model.hasUnsavedChapter).toBe(true);
  act(() => view().navigator.onSelectDocument(other.id));
  await flushEffects();
  expect(view().editor.activeDocument?.id).toBe(other.id);
  expect(view().inspector.model.hasUnsavedChapter).toBe(false);
  expect(api.saveDocument).toHaveBeenCalledExactlyOnceWith(
    "project-1",
    original.id,
    expect.objectContaining({
      content_markdown: "Unsaved departing chapter",
      title: original.title,
      base_revision_id: original.current_revision_id,
    }),
  );
});

it("does not imply unsaved Lore text will enter chapter Review or Export after saving", async () => {
  vi.useFakeTimers();
  const lore = chapter("lore-1", { kind: "character", lore_status: "draft", title: "Mira" });
  const view = await mountModel([lore]);
  act(() => view().editor.onDraftChange("Unfinished character notes"));
  expect(view().editor.draft).toBe("Unfinished character notes");
  expect(view().inspector.model.hasUnsavedChapter).toBe(false);
});
