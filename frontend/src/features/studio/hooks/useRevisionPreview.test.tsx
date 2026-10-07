import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { RevisionDetail } from "@/app/types/revision";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import {
  type RevisionPreviewController,
  type RevisionPreviewScope,
  useRevisionPreview,
} from "./useRevisionPreview";

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

const firstDetail: RevisionDetail = {
  id: "revision-a",
  document_id: "document-a",
  parent_revision_id: null,
  revision_number: 1,
  content_markdown: "first body",
  metadata: {},
  source: "author",
  word_count: 2,
  created_at: "2026-08-27T00:00:00Z",
};

const secondDetail: RevisionDetail = {
  ...firstDetail,
  id: "revision-b",
  parent_revision_id: "revision-a",
  revision_number: 2,
  content_markdown: "second body",
};

function scopeFor(documentId: string): RevisionPreviewScope {
  return { projectId: "project-1", documentId, currentContent: "current body" };
}

let preview: RevisionPreviewController | undefined;

function PreviewProbe({ scope }: { readonly scope: RevisionPreviewScope }) {
  preview = useRevisionPreview(scope);
  return null;
}

function controller(): RevisionPreviewController {
  if (preview === undefined) throw new Error("preview probe is not mounted");
  return preview;
}

describe("useRevisionPreview request ownership", () => {
  it("settles a row's read even when another row's read superseded it in flight", async () => {
    const first = deferred<RevisionDetail>();
    const second = deferred<RevisionDetail>();
    vi.mocked(api.revision).mockImplementation((_projectId, _documentId, revisionId) =>
      revisionId === "revision-a" ? first.promise : second.promise,
    );
    harness.mount(<PreviewProbe scope={scopeFor("document-a")} />);
    await flushEffects();

    act(() => controller().toggle("revision-a"));
    act(() => controller().toggle("revision-b"));
    expect(api.revision).toHaveBeenCalledTimes(2);

    await act(async () => {
      first.resolve(firstDetail);
      await first.promise;
    });
    expect(controller().stateFor("revision-a")).toEqual({
      status: "loaded",
      revision: firstDetail,
    });

    await act(async () => {
      second.resolve(secondDetail);
      await second.promise;
    });
    expect(controller().stateFor("revision-b")).toEqual({
      status: "loaded",
      revision: secondDetail,
    });

    // Both reads settled, so reopening a row is a cache hit, not a re-read.
    act(() => controller().toggle("revision-a"));
    expect(api.revision).toHaveBeenCalledTimes(2);
  });

  it("never publishes a previous document's in-flight read into the new scope", async () => {
    const stale = deferred<RevisionDetail>();
    vi.mocked(api.revision).mockReturnValue(stale.promise);
    const { root } = harness.mount(<PreviewProbe scope={scopeFor("document-a")} />);
    await flushEffects();
    act(() => controller().toggle("revision-a"));
    expect(controller().stateFor("revision-a")).toEqual({ status: "loading" });

    // The author opens another document while this read is still in flight.
    act(() => root.render(<PreviewProbe scope={scopeFor("document-b")} />));
    await flushEffects();
    expect(controller().stateFor("revision-a")).toEqual({ status: "idle" });

    await act(async () => {
      stale.resolve(firstDetail);
      await stale.promise;
    });
    // The reset scope stays reset; the abandoned read publishes nothing.
    expect(controller().stateFor("revision-a")).toEqual({ status: "idle" });
  });
});
