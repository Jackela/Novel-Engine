import { getByRole } from "@testing-library/dom";
import { act } from "react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { StudioDocument } from "@/app/types/studio";
import { chapter, projectWith, revision } from "@/test/factories";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";
import { StudioHistoryPanel } from "../components/StudioHistoryPanel";
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
      reviews: vi.fn<typeof actual.api.reviews>(),
      exports: vi.fn<typeof actual.api.exports>(),
      restoreRevision: vi.fn<typeof actual.api.restoreRevision>(),
      saveDocument: vi.fn<typeof actual.api.saveDocument>(),
    },
  };
});

const harness = createMountHarness();
const original = chapter("chapter-one", {
  content_markdown: "Original scene",
  current_revision_id: "revision-base",
});
const restored: StudioDocument = {
  ...original,
  title: "Restored title",
  content_markdown: "Restored scene",
  current_revision_id: "revision-restored",
  revision_source: "restore",
};
let serverBody = original;
let current: ReturnType<typeof useStudioPageModel> | undefined;

function PageProbe() {
  const navigate = useNavigate();
  current = useStudioPageModel(
    original.project_id,
    resolveStudioRoute(original.project_id, "manuscript", "?inspector=history"),
    navigate,
  );
  const inspector = current.viewProps?.inspector;
  return inspector ? (
    <StudioHistoryPanel
      {...inspector.model.history}
      previewScope={inspector.model.history.preview}
      restoringRevisionId={inspector.pending.history?.restoringRevisionId}
    />
  ) : null;
}

function view() {
  if (!current?.viewProps) throw new Error("Expected the mounted Studio page.");
  return current.viewProps;
}
function seedApi() {
  vi.mocked(api.project).mockImplementation(async () =>
    projectWith([summarizeDocument(serverBody)]),
  );
  vi.mocked(api.document).mockImplementation(async () => serverBody);
  vi.mocked(api.providers).mockResolvedValue({ providers: [] });
  vi.mocked(api.jobs).mockResolvedValue({ jobs: [], next_cursor: null });
  vi.mocked(api.reviews).mockResolvedValue({ reviews: [], next_cursor: null });
  vi.mocked(api.exports).mockResolvedValue({ exports: [], next_cursor: null });
  vi.mocked(api.revisions).mockResolvedValue({
    revisions: [revision("revision-old", { document_id: original.id })],
    next_cursor: null,
  });
  vi.mocked(api.saveDocument).mockImplementation(async (_project, _document, draft) => {
    if (draft.base_revision_id !== serverBody.current_revision_id) {
      throw new HttpError("Revision conflict", 409, undefined, "REVISION_CONFLICT");
    }
    serverBody = { ...serverBody, ...draft, current_revision_id: "revision-saved" };
    return serverBody;
  });
}
afterEach(() => {
  harness.cleanup();
  resetRevisionCacheForTests();
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.resetAllMocks();
  serverBody = original;
  current = undefined;
});
it.each(
  ["new-edits", "none", "no-restore"].flatMap((editing) =>
    [false, true].map((failure) => ({ editing, failure })),
  ),
)(
  "does not publish a superseded autosave conflict after History restore: $editing, recovery failure=$failure",
  async ({ editing, failure }) => {
    vi.useFakeTimers();
    seedApi();
    const { container } = harness.mount(
      <MemoryRouter initialEntries={["/projects/project-1/manuscript?inspector=history"]}>
        <PageProbe />
      </MemoryRouter>,
    );
    await flushEffects();
    expect(view().editor.activeDocument?.id).toBe(original.id);
    act(() => view().editor.onDraftChange("Unsaved draft before restore"));
    const restoreResponse = deferred<StudioDocument>();
    vi.mocked(api.restoreRevision).mockImplementation((_project, _document, _revision, base) => {
      // The restore commits while R1 is still current; only its response waits.
      expect(base).toBe(serverBody.current_revision_id);
      serverBody = restored;
      return restoreResponse.promise;
    });
    if (editing !== "no-restore") {
      act(() => getByRole(container, "button", { name: /Restore revision/ }).click());
      act(() => getByRole(container, "button", { name: "Confirm restore" }).click());
      expect(api.restoreRevision).toHaveBeenCalledTimes(1);
    } else {
      serverBody = restored; // A different tab advances the ordinary conflict baseline.
    }
    const recoveryResponse = deferred<void>();
    const recoveryBody = serverBody;
    vi.mocked(api.document).mockImplementationOnce(async () => {
      await recoveryResponse.promise;
      if (failure) throw new HttpError("Recovery unavailable", 503);
      return recoveryBody;
    });
    // Autosave still submits R1 after the server accepted R3, so its 409 is causal.
    await act(async () => vi.advanceTimersByTimeAsync(1500));
    expect(api.saveDocument).toHaveBeenCalledTimes(1);
    expect(api.saveDocument).toHaveBeenLastCalledWith(
      original.project_id,
      original.id,
      expect.objectContaining({ base_revision_id: original.current_revision_id }),
    );
    expect(api.document).toHaveBeenCalledTimes(2);
    if (editing !== "no-restore") {
      await act(async () => restoreResponse.resolve(restored));
      await flushEffects();
      expect(view().editor.draft).toBe(restored.content_markdown);
      expect(view().editor.saveState).toBe("idle");
    }
    if (editing === "new-edits") {
      act(() => {
        view().editor.onDraftChange("New manuscript after restore");
        view().editor.onTitleChange("New title after restore");
      });
    }
    await act(async () => recoveryResponse.resolve());
    await flushEffects();
    expect(view().statusbar.loadedRevisionId).toBe(
      editing === "no-restore" && failure
        ? original.current_revision_id
        : restored.current_revision_id,
    );
    if (editing === "no-restore") {
      expect(view().editor.draft).toBe("Unsaved draft before restore");
      expect(view().editor.saveState).toBe("conflict");
      expect(view().editor.error).toContain(
        failure ? "Recovery unavailable" : "changed since it was loaded",
      );
    } else {
      expect(view().editor.draft).toBe(
        editing === "new-edits" ? "New manuscript after restore" : restored.content_markdown,
      );
      expect(view().editor.titleDraft).toBe(
        editing === "new-edits" ? "New title after restore" : restored.title,
      );
      expect(view().editor.saveState).toBe(editing === "new-edits" ? "saving" : "idle");
      expect(view().editor.error).toBeNull();
    }
    await act(async () => vi.advanceTimersByTimeAsync(1500));
    expect(api.saveDocument).toHaveBeenCalledTimes(editing === "new-edits" ? 2 : 1);
    if (editing === "new-edits") {
      expect(api.saveDocument).toHaveBeenLastCalledWith(
        original.project_id,
        original.id,
        expect.objectContaining({
          base_revision_id: restored.current_revision_id,
          content_markdown: "New manuscript after restore",
          title: "New title after restore",
        }),
      );
      expect(view().editor.saveState).toBe("saved");
    }
  },
);
