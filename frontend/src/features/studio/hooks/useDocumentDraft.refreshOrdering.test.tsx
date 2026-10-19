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
const concurrent = {
  ...original,
  title: "Other tab title",
  content_markdown: "Other tab accepted",
  current_revision_id: "revision-concurrent",
};
const restored: StudioDocument = {
  ...original,
  title: "Restored title",
  content_markdown: "Restored scene",
  current_revision_id: "revision-restored",
  revision_source: "restore",
};
let serverBody = original;
let current: ReturnType<typeof useStudioPageModel> | undefined;

/** Uses real resource ownership and History controls; only HTTP is mocked. */
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
  vi.mocked(api.restoreRevision).mockImplementation(async () => {
    serverBody = restored;
    return restored;
  });
  vi.mocked(api.saveDocument).mockRejectedValueOnce(
    new HttpError("Revision conflict", 409, undefined, "REVISION_CONFLICT"),
  );
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
  ["body", "title", "both", "none", "no-restore"].flatMap((editing) =>
    [false, true].map((failure) => ({ editing, failure })),
  ),
)(
  "keeps causal revision ownership when Load latest overlaps History: $editing, reload failure=$failure",
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
    serverBody = concurrent;
    for (let count = 0; count < 5; count += 1) {
      act(() => view().editor.onDraftChange(`Local edit ${count}`));
    }
    await act(async () => vi.advanceTimersByTimeAsync(1500));
    expect(view().editor.saveState).toBe("conflict");
    const response = deferred<void>();
    vi.mocked(api.document).mockImplementationOnce(async () => {
      await response.promise;
      if (failure) throw new HttpError("Reload unavailable", 503);
      return concurrent;
    });
    let loading: void | Promise<void>;
    act(() => {
      loading = view().editor.onLoadLatest?.();
    });
    expect(view().editor.isConflictActionPending).toBe(true);
    if (editing !== "no-restore") {
      const restore = getByRole(container, "button", { name: /Restore revision/ });
      expect(restore).not.toBeDisabled();
      act(() => restore.click());
      await act(async () => getByRole(container, "button", { name: "Confirm restore" }).click());
      await flushEffects();
      expect(api.restoreRevision).toHaveBeenCalledWith(
        original.project_id,
        original.id,
        "revision-old",
        concurrent.current_revision_id,
      );
      expect(view().editor.draft).toBe(restored.content_markdown);
      expect(view().statusbar.loadedRevisionId).toBe(restored.current_revision_id);
    }
    const nextBody = editing === "body" || editing === "both";
    const nextTitle = editing === "title" || editing === "both";
    act(() => {
      if (nextBody) view().editor.onDraftChange("New manuscript after restore");
      if (nextTitle) view().editor.onTitleChange("New title after restore");
    });
    await act(async () => {
      response.resolve();
      await loading;
    });
    const expected = editing === "no-restore" ? concurrent : restored;
    const failedWithoutRestore = failure && editing === "no-restore";
    expect(view().editor.draft).toBe(
      nextBody
        ? "New manuscript after restore"
        : failedWithoutRestore
          ? "Local edit 4"
          : expected.content_markdown,
    );
    expect(view().editor.titleDraft).toBe(
      nextTitle
        ? "New title after restore"
        : failedWithoutRestore
          ? original.title
          : expected.title,
    );
    expect(view().statusbar.loadedRevisionId).toBe(expected.current_revision_id);
    expect(current?.project?.documents[0]?.current_revision_id).toBe(expected.current_revision_id);
    expect(view().editor.isConflictActionPending).toBe(false);
    expect(view().editor.saveState).toBe(
      failedWithoutRestore ? "error" : nextBody || nextTitle ? "saving" : "idle",
    );
    if (failedWithoutRestore) expect(view().editor.error).toBe("Reload unavailable");
    expect(api.saveDocument).toHaveBeenCalledTimes(1);
    vi.mocked(api.saveDocument).mockImplementation(async (_project, _document, draft) => {
      serverBody = { ...expected, ...draft, current_revision_id: "revision-saved" };
      return serverBody;
    });
    act(() => view().editor.onDraftChange("Next save after the delayed response"));
    await act(async () => vi.advanceTimersByTimeAsync(1500));
    expect(api.saveDocument).toHaveBeenLastCalledWith(
      original.project_id,
      original.id,
      expect.objectContaining({ base_revision_id: expected.current_revision_id }),
    );
  },
);
