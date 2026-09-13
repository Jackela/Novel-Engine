import { act, useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import type { Project, StudioDocument } from "@/app/types/studio";
import { chapter, projectWith, revision } from "@/test/factories";
import { createMountHarness, deferred, flushEffects, flushMicrotasks } from "@/test/harness";

import { summarizeDocument } from "./projectState";
import { useDocumentDraft } from "./useDocumentDraft";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      document: vi.fn<typeof actual.api.document>(),
      project: vi.fn<typeof actual.api.project>(),
      revisions: vi.fn<typeof actual.api.revisions>(),
      restoreRevision: vi.fn<typeof actual.api.restoreRevision>(),
      saveDocument: vi.fn<typeof actual.api.saveDocument>(),
    },
  };
});

const harness = createMountHarness();

const activeDocument = chapter("document-1", {
  title: "Chapter One",
  current_revision_id: "revision-1",
  content_markdown: "Original draft",
  revision_source: "author",
  word_count: 2,
});

const initialProject = projectWith([activeDocument]);
const initialRevision = revision("revision-1", { document_id: activeDocument.id, word_count: 2 });

const latestDocument: StudioDocument = {
  ...activeDocument,
  current_revision_id: "revision-2",
  content_markdown: "Second tab wins.",
  updated_at: "2026-09-05T00:01:00Z",
};

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  harness.cleanup();
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.resetAllMocks();
});

function renderDocumentDraftHook(): { readonly result: () => HarnessResult } {
  let current: HarnessResult | undefined;
  function Wrapper(): null {
    const [project, setProject] = useState<Project | null>(initialProject);
    const [error, setError] = useState<string | null>(null);
    const hook = useDocumentDraft(activeDocument, activeDocument.project_id, setProject, setError);
    current = { hook, project, error };
    return null;
  }
  harness.mount(<Wrapper />);
  return {
    result: () => {
      if (current === undefined) {
        throw new Error("Expected hook result after render.");
      }
      return current;
    },
  };
}

interface HarnessResult {
  readonly hook: ReturnType<typeof useDocumentDraft>;
  readonly project: Project | null;
  readonly error: string | null;
}

describe("useDocumentDraft conflict recovery timing (#472)", () => {
  it("withholds the conflict surface until the failed autosave's recovery refresh settles", async () => {
    // The CI flake: a 409 autosave published "Save conflict" while the same
    // save still held the saveInFlight lock through its recovery refresh,
    // so the "Load latest" click landed inside loadLatest's silent-refusal
    // window and the editor stranded in conflict forever.
    vi.mocked(api.revisions).mockResolvedValue({ revisions: [initialRevision], next_cursor: null });
    const recovery = deferred<StudioDocument>();
    vi.mocked(api.document).mockReturnValueOnce(recovery.promise).mockResolvedValue(latestDocument);
    vi.mocked(api.saveDocument).mockRejectedValue(new HttpError("revision conflict", 409));
    const view = renderDocumentDraftHook();
    await flushMicrotasks();

    act(() => {
      view.result().hook.setDraft("Stale tab overwrite.");
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    // The 409 has landed but its recovery refresh has not. Conflict actions
    // refuse to run while the failing save still holds the lifecycle lock,
    // so the conflict surface must stay withheld until the lock releases.
    expect(view.result().hook.saveState).toBe("saving");

    // The winning body lands first; only then may the conflict publish.
    await act(async () => {
      recovery.resolve(latestDocument);
      await recovery.promise;
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });
    await flushEffects();
    expect(view.result().hook.saveState).toBe("conflict");
    expect(view.result().hook.draft).toBe("Stale tab overwrite.");
    expect(view.result().error).toBe("revision conflict");
    expect(view.result().project?.documents).toEqual([summarizeDocument(latestDocument)]);

    // The discard click now sits outside the refusal window: loading the
    // latest resolves onto the newest revision instead of being swallowed.
    await act(async () => {
      await view.result().hook.loadLatest();
    });
    expect(api.document).toHaveBeenCalledTimes(2);
    expect(view.result().hook.draft).toBe(latestDocument.content_markdown);
    expect(view.result().hook.titleDraft).toBe(latestDocument.title);
    expect(view.result().hook.saveState).toBe("idle");
    expect(view.result().hook.isConflictActionPending).toBe(false);
    expect(view.result().error).toBeNull();
  });
});
