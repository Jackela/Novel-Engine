import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { RevisionPage } from "@/app/types/studio";
import { revision } from "@/test/factories";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import {
  resetRevisionCacheForTests,
  revisionCacheStatsForTests,
  useRevisionCache,
} from "./useRevisionCache";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return { ...actual, api: { ...actual.api, revisions: vi.fn<typeof actual.api.revisions>() } };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  resetRevisionCacheForTests();
  vi.resetAllMocks();
});

function resolvedPage(documentId: string): RevisionPage {
  return {
    revisions: [revision(`revision-${documentId}`, { document_id: documentId })],
    next_cursor: null,
  };
}

function renderMutableOwner(initialDocumentId: string) {
  let documentId = initialDocumentId;
  let result: ReturnType<typeof useRevisionCache> | undefined;
  const onError = vi.fn();
  function Wrapper(): null {
    result = useRevisionCache("project-1", documentId, onError);
    return null;
  }
  const { root } = harness.mount(<Wrapper />);
  return {
    result: () => {
      if (!result) throw new Error("Expected revision cache result.");
      return result;
    },
    select: (nextDocumentId: string) => {
      documentId = nextDocumentId;
      act(() => root.render(<Wrapper />));
    },
  };
}

function renderFixedOwner(documentId: string) {
  let result: ReturnType<typeof useRevisionCache> | undefined;
  const onError = vi.fn();
  function Wrapper(): null {
    result = useRevisionCache("project-1", documentId, onError);
    return null;
  }
  const { container } = harness.mount(<Wrapper />);
  return {
    result: () => {
      if (!result) throw new Error("Expected revision cache result.");
      return result;
    },
    dispose: () => harness.unmount(container),
  };
}

describe("useRevisionCache owner LRU", () => {
  it("evicts the least-recent inactive owner after eight cached owners", async () => {
    vi.mocked(api.revisions).mockImplementation((_projectId, documentId) =>
      Promise.resolve(resolvedPage(documentId)),
    );
    const view = renderMutableOwner("document-1");
    await flushEffects();
    for (let index = 2; index <= 9; index += 1) {
      view.select(`document-${index}`);
      await flushEffects();
    }

    const reload = deferred<RevisionPage>();
    vi.mocked(api.revisions).mockReturnValueOnce(reload.promise);
    view.select("document-1");

    expect(view.result().revisions).toEqual([]);
    expect(api.revisions).toHaveBeenLastCalledWith(
      "project-1",
      "document-1",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it("protects an active owner while inactive owners rotate through the bound", async () => {
    vi.mocked(api.revisions).mockImplementation((_projectId, documentId) =>
      Promise.resolve(resolvedPage(documentId)),
    );
    const protectedOwner = renderMutableOwner("document-protected");
    const rotatingOwner = renderMutableOwner("document-1");
    await flushEffects();
    for (let index = 2; index <= 9; index += 1) {
      rotatingOwner.select(`document-${index}`);
      await flushEffects();
    }

    const secondProtectedConsumer = renderMutableOwner("document-protected");

    expect(secondProtectedConsumer.result().revisions).toEqual(protectedOwner.result().revisions);
    expect(secondProtectedConsumer.result().revisions).toHaveLength(1);
  });

  it("touches a revisited owner so the next least-recent owner is evicted", async () => {
    vi.mocked(api.revisions).mockImplementation((_projectId, documentId) =>
      Promise.resolve(resolvedPage(documentId)),
    );
    const view = renderMutableOwner("document-1");
    await flushEffects();
    for (let index = 2; index <= 8; index += 1) {
      view.select(`document-${index}`);
      await flushEffects();
    }
    view.select("document-1");
    await flushEffects();
    view.select("document-9");
    await flushEffects();

    const reload = deferred<RevisionPage>();
    vi.mocked(api.revisions).mockReturnValueOnce(reload.promise);
    view.select("document-2");
    expect(view.result().revisions).toEqual([]);
    view.select("document-1");
    expect(view.result().revisions).toEqual(resolvedPage("document-1").revisions);
  });

  it("bounds owners whose activation pages all fail", async () => {
    vi.mocked(api.revisions).mockRejectedValue(new Error("offline"));
    const view = renderMutableOwner("document-1");
    await flushEffects();
    for (let index = 2; index <= 12; index += 1) {
      view.select(`document-${index}`);
      await flushEffects();
    }

    expect(revisionCacheStatsForTests()).toEqual({ cachedOwners: 8, requestingOwners: 0 });
  });

  it("retains a nine-owner active working set then converges after unmount", async () => {
    vi.mocked(api.revisions).mockImplementation((_projectId, documentId) =>
      Promise.resolve(resolvedPage(documentId)),
    );
    const owners = Array.from({ length: 9 }, (_, index) =>
      renderFixedOwner(`document-active-${index + 1}`),
    );
    await flushEffects();
    expect(revisionCacheStatsForTests().cachedOwners).toBe(9);

    owners[0]?.dispose();
    expect(revisionCacheStatsForTests().cachedOwners).toBe(8);
    expect(owners[1]?.result().revisions).toHaveLength(1);
  });

  it("protects nine active requests and aborts them as the working set unmounts", () => {
    vi.mocked(api.revisions).mockReturnValue(new Promise(() => undefined));
    const owners = Array.from({ length: 9 }, (_, index) =>
      renderFixedOwner(`document-pending-${index + 1}`),
    );
    expect(revisionCacheStatsForTests()).toEqual({ cachedOwners: 9, requestingOwners: 9 });

    owners[0]?.dispose();
    expect(revisionCacheStatsForTests()).toEqual({ cachedOwners: 8, requestingOwners: 8 });
    for (const owner of owners.slice(1)) owner.dispose();
    expect(revisionCacheStatsForTests()).toEqual({ cachedOwners: 8, requestingOwners: 0 });
  });
});
