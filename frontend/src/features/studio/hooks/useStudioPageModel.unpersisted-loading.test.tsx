import { act } from "react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { StudioDocument } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";
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
const original = chapter("chapter-1", { content_markdown: "Accepted original text." });
const accepted = {
  ...original,
  current_revision_id: "accepted-first-edit",
  content_markdown: "First edit",
};
const other = chapter("chapter-2", { content_markdown: "Other accepted chapter." });

afterEach(() => {
  harness.cleanup();
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.resetAllMocks();
});

/** Mounts the real page composition with isolated API responses and no stored author data. */
async function mountModel() {
  vi.useFakeTimers();
  const project = projectWith([original, other].map(summarizeDocument));
  vi.mocked(api.project).mockResolvedValue(project);
  vi.mocked(api.document).mockImplementation(async (_projectId, id) =>
    id === other.id ? other : original,
  );
  vi.mocked(api.providers).mockResolvedValue({ providers: [] });
  vi.mocked(api.jobs).mockResolvedValue({ jobs: [], next_cursor: null });
  vi.mocked(api.revisions).mockResolvedValue({ revisions: [], next_cursor: null });
  let current: ReturnType<typeof useStudioPageModel> | undefined;
  function Probe() {
    current = useStudioPageModel(
      project.id,
      resolveStudioRoute(project.id, "manuscript", ""),
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

/** Reports whether an actual window unload event receives the unsaved-text guard. */
function unloadIsGuarded(): boolean {
  const event = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(event);
  return event.defaultPrevented;
}

/** Advances a real autosave before changing the text, so its accepted response is older. */
async function commitFirstEdit(
  view: Awaited<ReturnType<typeof mountModel>>,
  newerEdit = true,
  failure = false,
) {
  const save = deferred<StudioDocument>();
  const body = deferred<StudioDocument>();
  vi.mocked(api.saveDocument).mockReturnValue(save.promise);
  act(() => view().editor.onDraftChange(accepted.content_markdown));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1500);
  });
  expect(api.saveDocument).toHaveBeenCalledTimes(1);
  if (newerEdit) act(() => view().editor.onDraftChange("Newest local edit"));
  if (failure) {
    vi.mocked(api.document).mockRejectedValue(new HttpError("Body read failed", 503));
  } else {
    vi.mocked(api.document).mockReturnValue(body.promise);
  }
  await act(async () => {
    save.resolve(accepted);
    await save.promise;
  });
  await flushEffects();
  expect(view().editor.activeDocument).toBeNull();
  return body;
}

it.each([false, true])(
  "guards newer local text while the accepted-body read is unavailable (failed=%s)",
  async (failure) => {
    const view = await mountModel();
    const body = await commitFirstEdit(view, true, failure);
    expect(view().editor.draft).toBe("Newest local edit");
    expect(view().editor.saveState).toBe("conflict");
    if (failure) expect(view().editor.documentLoadError).toBeTruthy();
    expect(unloadIsGuarded()).toBe(true);
    expect(view().inspector.model.hasUnsavedChapter).toBe(true);

    vi.mocked(api.document).mockResolvedValue(accepted);
    if (failure) act(() => view().editor.onRetryDocument?.());
    else await act(async () => body.resolve(accepted));
    await flushEffects();
    expect(view().editor.activeDocument?.id).toBe(original.id);
    expect(unloadIsGuarded()).toBe(true);
    expect(view().inspector.model.hasUnsavedChapter).toBe(true);
    await act(async () => view().editor.onLoadLatest?.());
    expect(view().editor.draft).toBe(accepted.content_markdown);
    expect(unloadIsGuarded()).toBe(false);
    expect(view().inspector.model.hasUnsavedChapter).toBe(false);
  },
);

it("does not warn after the local text is changed back to its accepted baseline during loading", async () => {
  const view = await mountModel();
  await commitFirstEdit(view);
  expect(unloadIsGuarded()).toBe(true);
  expect(view().inspector.model.hasUnsavedChapter).toBe(true);
  act(() => view().editor.onDraftChange(accepted.content_markdown));
  expect(unloadIsGuarded()).toBe(false);
  expect(view().inspector.model.hasUnsavedChapter).toBe(false);
});

it("does not warn while re-reading a clean accepted body or after selecting another owner", async () => {
  const view = await mountModel();
  expect(unloadIsGuarded()).toBe(false);
  expect(view().inspector.model.hasUnsavedChapter).toBe(false);
  await commitFirstEdit(view, false);
  expect(view().editor.draft).toBe(accepted.content_markdown);
  expect(unloadIsGuarded()).toBe(false);
  expect(view().inspector.model.hasUnsavedChapter).toBe(false);
  vi.mocked(api.document).mockResolvedValue(other);
  act(() => view().navigator.onSelectDocument(other.id));
  await flushEffects();
  expect(view().editor.activeDocument?.id).toBe(other.id);
  expect(view().editor.draft).toBe(other.content_markdown);
  expect(unloadIsGuarded()).toBe(false);
  expect(view().inspector.model.hasUnsavedChapter).toBe(false);
});

it("clears the guard after explicitly accepting the newer local text", async () => {
  const view = await mountModel();
  const body = await commitFirstEdit(view);
  expect(unloadIsGuarded()).toBe(true);
  expect(view().inspector.model.hasUnsavedChapter).toBe(true);
  vi.mocked(api.document).mockResolvedValue(accepted);
  await act(async () => body.resolve(accepted));
  await flushEffects();
  const saved = {
    ...accepted,
    current_revision_id: "accepted-newest-edit",
    content_markdown: "Newest local edit",
  };
  vi.mocked(api.saveDocument).mockResolvedValue(saved);
  vi.mocked(api.document).mockResolvedValueOnce(accepted).mockResolvedValue(saved);
  await act(async () => view().editor.onRetryOverwrite?.());
  await flushEffects();
  expect(view().editor.draft).toBe(saved.content_markdown);
  expect(unloadIsGuarded()).toBe(false);
  expect(view().inspector.model.hasUnsavedChapter).toBe(false);
});
