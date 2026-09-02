import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { RevisionPage } from "@/app/types/studio";
import { revision } from "@/test/factories";
import { createMountHarness, flushEffects } from "@/test/harness";

import { resetRevisionCacheForTests, useRevisionCache } from "./useRevisionCache";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return { ...actual, api: { ...actual.api, revisions: vi.fn<typeof actual.api.revisions>() } };
});

const harness = createMountHarness();
const initial = revision("revision-initial");

afterEach(() => {
  harness.cleanup();
  resetRevisionCacheForTests();
  vi.resetAllMocks();
});

function renderCache() {
  let result: ReturnType<typeof useRevisionCache> | undefined;
  const onError = vi.fn();
  const onSuccess = vi.fn();
  function Consumer(): null {
    result = useRevisionCache("project-1", "document-1", onError, onSuccess);
    return null;
  }
  harness.mount(<Consumer />);
  return {
    result: () => {
      if (!result) throw new Error("Expected revision cache result.");
      return result;
    },
    onError,
    onSuccess,
  };
}

describe("useRevisionCache error intent ownership", () => {
  it("restores a first-page error after a newer older-page error recovers", async () => {
    const firstError = new Error("first page unavailable");
    const olderError = new Error("older unavailable");
    vi.mocked(api.revisions)
      .mockResolvedValueOnce({ revisions: [initial], next_cursor: "older-cursor" })
      .mockRejectedValueOnce(firstError)
      .mockRejectedValueOnce(olderError)
      .mockResolvedValueOnce({ revisions: [revision("revision-older")], next_cursor: null })
      .mockResolvedValueOnce({ revisions: [revision("revision-recovered")], next_cursor: null });
    const cache = renderCache();
    await flushEffects();
    cache.onError.mockClear();
    cache.onSuccess.mockClear();

    await act(async () =>
      cache.result().refreshDocumentRevisions("document-1", "revision-created"),
    );
    await act(async () => cache.result().loadOlderRevisions());
    await act(async () => cache.result().loadOlderRevisions());

    expect(cache.onSuccess).not.toHaveBeenCalled();
    expect(cache.onError).toHaveBeenLastCalledWith(firstError);

    await act(async () =>
      cache.result().refreshDocumentRevisions("document-1", "revision-recovered"),
    );
    expect(cache.onSuccess).toHaveBeenCalledTimes(1);
  });

  it("restores an older-page error after a newer first-page error recovers", async () => {
    const firstError = new Error("first page unavailable");
    const olderError = new Error("older unavailable");
    const recovered = revision("revision-recovered");
    vi.mocked(api.revisions)
      .mockResolvedValueOnce({ revisions: [initial], next_cursor: "older-cursor" })
      .mockRejectedValueOnce(olderError)
      .mockRejectedValueOnce(firstError)
      .mockResolvedValueOnce({ revisions: [recovered, initial], next_cursor: "fresh-cursor" })
      .mockResolvedValueOnce({ revisions: [revision("revision-older")], next_cursor: null });
    const cache = renderCache();
    await flushEffects();
    cache.onError.mockClear();
    cache.onSuccess.mockClear();

    await act(async () => cache.result().loadOlderRevisions());
    await act(async () =>
      cache.result().refreshDocumentRevisions("document-1", "revision-created"),
    );
    await act(async () => cache.result().refreshDocumentRevisions("document-1", recovered.id));

    expect(cache.onSuccess).not.toHaveBeenCalled();
    expect(cache.onError).toHaveBeenLastCalledWith(olderError);

    await act(async () => cache.result().loadOlderRevisions());
    expect(cache.onSuccess).toHaveBeenCalledTimes(1);
  });

  it("keeps a first-page error visible after queued older succeeds until first-page recovery", async () => {
    let rejectRefresh!: (reason: unknown) => void;
    const refreshFailure = new Promise<RevisionPage>((_resolve, reject) => {
      rejectRefresh = reject;
    });
    const recovered = revision("revision-recovered");
    vi.mocked(api.revisions)
      .mockResolvedValueOnce({ revisions: [initial], next_cursor: "older-cursor" })
      .mockReturnValueOnce(refreshFailure)
      .mockResolvedValueOnce({ revisions: [revision("revision-older")], next_cursor: null })
      .mockResolvedValueOnce({ revisions: [recovered], next_cursor: null });
    const cache = renderCache();
    await flushEffects();
    cache.onError.mockClear();
    cache.onSuccess.mockClear();

    let refresh!: Promise<void>;
    let older!: Promise<void>;
    act(() => {
      refresh = cache.result().refreshDocumentRevisions("document-1", "revision-created");
      older = cache.result().loadOlderRevisions();
    });
    await act(async () => {
      rejectRefresh(new Error("first page unavailable"));
      await refreshFailure.catch(() => undefined);
      await refresh;
      await older;
    });

    expect(cache.onError).toHaveBeenCalledWith(
      expect.objectContaining({ message: "first page unavailable" }),
    );
    expect(cache.onSuccess).not.toHaveBeenCalled();

    await act(async () => cache.result().refreshDocumentRevisions("document-1", recovered.id));
    expect(cache.onSuccess).toHaveBeenCalledTimes(1);
  });

  it("does not let first-page success clear an older-page error", async () => {
    const newer = revision("revision-new");
    vi.mocked(api.revisions)
      .mockResolvedValueOnce({ revisions: [initial], next_cursor: "older-cursor" })
      .mockRejectedValueOnce(new Error("older unavailable"))
      .mockResolvedValueOnce({ revisions: [newer, initial], next_cursor: "fresh-cursor" })
      .mockResolvedValueOnce({ revisions: [revision("revision-older")], next_cursor: null });
    const cache = renderCache();
    await flushEffects();
    cache.onError.mockClear();
    cache.onSuccess.mockClear();

    await act(async () => cache.result().loadOlderRevisions());
    expect(cache.onError).toHaveBeenCalledWith(
      expect.objectContaining({ message: "older unavailable" }),
    );
    await act(async () => cache.result().refreshDocumentRevisions("document-1", newer.id));

    expect(cache.onSuccess).not.toHaveBeenCalled();
    await act(async () => cache.result().loadOlderRevisions());
    expect(cache.onSuccess).toHaveBeenCalledTimes(1);
  });
});
