import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { RevisionPage } from "@/app/types/studio";
import { revision } from "@/test/factories";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { resetRevisionCacheForTests, useRevisionCache } from "./useRevisionCache";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return { ...actual, api: { ...actual.api, revisions: vi.fn<typeof actual.api.revisions>() } };
});

const harness = createMountHarness();
const newest = revision("revision-newest", { revision_number: 3 });

afterEach(() => {
  harness.cleanup();
  resetRevisionCacheForTests();
  vi.resetAllMocks();
});

function renderCache(projectId = "project-1", documentId = "document-1") {
  let result: ReturnType<typeof useRevisionCache> | undefined;
  const onError = vi.fn();
  function Wrapper(): null {
    result = useRevisionCache(projectId, documentId, onError);
    return null;
  }
  harness.mount(<Wrapper />);
  return {
    result: () => {
      if (!result) throw new Error("Expected revision cache result.");
      return result;
    },
    onError,
  };
}

describe("useRevisionCache pagination", () => {
  it("appends unique older summaries and coalesces the same owner cursor", async () => {
    const olderPage = deferred<RevisionPage>();
    vi.mocked(api.revisions)
      .mockResolvedValueOnce({ revisions: [newest], next_cursor: "cursor-2" })
      .mockReturnValueOnce(olderPage.promise);
    const cache = renderCache();
    await flushEffects();

    const first = cache.result().loadOlderRevisions();
    const duplicate = cache.result().loadOlderRevisions();
    expect(duplicate).toBe(first);
    expect(api.revisions).toHaveBeenCalledTimes(2);

    await act(async () => {
      olderPage.resolve({
        revisions: [newest, revision("revision-older"), revision("revision-older")],
        next_cursor: null,
      });
      await first;
    });
    expect(cache.result().revisions.map((item) => item.id)).toEqual([newest.id, "revision-older"]);
    expect(cache.result().hasOlderRevisions).toBe(false);
  });

  it("preserves committed summaries and cursor when an older page fails", async () => {
    vi.mocked(api.revisions)
      .mockResolvedValueOnce({ revisions: [newest], next_cursor: "cursor-2" })
      .mockRejectedValueOnce(new Error("older unavailable"));
    const cache = renderCache();
    await flushEffects();
    await act(async () => cache.result().loadOlderRevisions());

    expect(cache.result().revisions).toEqual([newest]);
    expect(cache.result().hasOlderRevisions).toBe(true);
    expect(cache.onError).toHaveBeenCalledWith(
      expect.objectContaining({ message: "older unavailable" }),
    );
  });

  it("prepends an overlapping fresh page and preserves the loaded terminal tail", async () => {
    const revisionTwo = revision("revision-2", { revision_number: 2 });
    const revisionOlder = revision("revision-old", { revision_number: 1 });
    const revisionFour = revision("revision-4", { revision_number: 4 });
    vi.mocked(api.revisions)
      .mockResolvedValueOnce({ revisions: [newest, revisionTwo], next_cursor: "cursor-2" })
      .mockResolvedValueOnce({ revisions: [revisionOlder], next_cursor: null })
      .mockResolvedValueOnce({
        revisions: [revisionFour, newest],
        next_cursor: "fresh-cursor",
      });
    const cache = renderCache();
    await flushEffects();
    await act(async () => cache.result().loadOlderRevisions());
    await act(async () => cache.result().refreshDocumentRevisions("document-1"));

    expect(cache.result().revisions.map((item) => item.id)).toEqual([
      revisionFour.id,
      newest.id,
      revisionTwo.id,
      revisionOlder.id,
    ]);
    expect(cache.result().hasOlderRevisions).toBe(false);
  });

  it("replaces a non-terminal cached range when a fresh page has no overlap", async () => {
    const fresh = revision("revision-fresh", { revision_number: 100 });
    vi.mocked(api.revisions)
      .mockResolvedValueOnce({ revisions: [newest], next_cursor: "old-cursor" })
      .mockResolvedValueOnce({ revisions: [fresh], next_cursor: "fresh-cursor" })
      .mockResolvedValueOnce({ revisions: [], next_cursor: null });
    const cache = renderCache();
    await flushEffects();
    await act(async () => cache.result().refreshDocumentRevisions("document-1"));
    expect(cache.result().revisions).toEqual([fresh]);
    await act(async () => cache.result().loadOlderRevisions());
    expect(vi.mocked(api.revisions).mock.calls[2]?.[2]).toEqual(
      expect.objectContaining({ cursor: "fresh-cursor" }),
    );
  });

  it("lets a mutation refresh supersede a cursorless activation response", async () => {
    const activation = deferred<RevisionPage>();
    const refreshed = revision("revision-after-save", { revision_number: 4 });
    vi.mocked(api.revisions)
      .mockReturnValueOnce(activation.promise)
      .mockResolvedValueOnce({ revisions: [refreshed], next_cursor: null });
    const cache = renderCache();
    const activationInit = vi.mocked(api.revisions).mock.calls[0]?.[2];
    await act(async () => cache.result().refreshDocumentRevisions("document-1"));
    expect(activationInit?.signal?.aborted).toBe(true);

    await act(async () => {
      activation.resolve({ revisions: [newest], next_cursor: null });
      await activation.promise;
    });
    expect(cache.result().revisions).toEqual([refreshed]);
  });

  it("rejects a repeated cursor without appending its ambiguous page", async () => {
    vi.mocked(api.revisions)
      .mockResolvedValueOnce({ revisions: [newest], next_cursor: "cursor-2" })
      .mockResolvedValueOnce({
        revisions: [revision("revision-ambiguous")],
        next_cursor: "cursor-2",
      });
    const cache = renderCache();
    await flushEffects();
    await act(async () => cache.result().loadOlderRevisions());

    expect(cache.result().revisions).toEqual([newest]);
    expect(cache.result().hasOlderRevisions).toBe(true);
    expect(cache.onError).toHaveBeenCalledWith(
      expect.objectContaining({
        message: "The revision service repeated its continuation cursor.",
      }),
    );
  });

  it("does not report a failed first page as terminal History", async () => {
    vi.mocked(api.revisions).mockRejectedValueOnce(new Error("first unavailable"));
    const cache = renderCache();
    await flushEffects();

    expect(cache.result().historyInitialized).toBe(false);
    expect(cache.result().hasOlderRevisions).toBe(false);
  });
});
